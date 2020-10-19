'''
  OnionPerf
  Authored by Rob Jansen, 2015
  Copyright 2015-2020 The Tor Project
  See LICENSE for licensing information
'''

import binascii, hashlib
import os, traceback, subprocess, threading, queue, logging, time, datetime, re, shlex
from lxml import etree

# stem imports
from stem.util import str_tools
from stem.control import Controller
from stem.version import Version, Requirement, get_system_tor_version
from stem import __version__ as stem_version

class TGenConf(object):
    """Represents a TGen configuration, for both client and server."""
    def __init__(self, listen_port=None, connect_ip=None, connect_port=None, tor_ctl_port=None, tor_socks_port=None):
        self.listen_port = str(listen_port)
        self.tor_ctl_port = tor_ctl_port
        self.tor_socks_port = tor_socks_port
        # TGen clients use connect_ip and connect_port.
        self.connect_ip = connect_ip
        self.connect_port = connect_port

# onionperf imports
from . import analysis, monitor, model, util

def generate_docroot_index(docroot_path):
    root = etree.Element("files")
    with os.scandir(docroot_path) as files:
        for entry in files:
            if not entry.name == 'index.xml' and entry.is_file():
                e = etree.SubElement(root, "file")
                e.set("name", entry.name)
                stat_result = entry.stat()
                e.set("size", str(stat_result.st_size))
                mtime = datetime.datetime.fromtimestamp(stat_result.st_mtime)
                e.set("last_modified", mtime.replace(microsecond=0).isoformat(sep=' '))
                with open(entry, 'rb') as f:
                    fbytes = f.read()
                    e.set("sha256", binascii.b2a_base64(hashlib.sha256(fbytes).digest(), newline=False))
    with open("{0}/index.xml".format(docroot_path), 'wb') as f:
        et = etree.ElementTree(root)
        et.write(f, pretty_print=True, xml_declaration=True)

def readline_thread_task(instream, q):
    # wait for lines from stdout until the EOF
    for line in iter(instream.readline, b''): q.put(line)

def watchdog_thread_task(cmd, cwd, writable, done_ev, send_stdin, ready_search_str, ready_ev, no_relaunch):

    # launch or re-launch (or don't re-launch, if no_relaunch is set) our sub
    # process until we are told to stop if we fail too many times in too short
    # of time, give up and exit
    failure_times = []
    pause_time_seconds = 0
    while done_ev.is_set() is False:
        if pause_time_seconds > 0:
            time.sleep(pause_time_seconds)

        stdin_handle = subprocess.PIPE if send_stdin is not None else None
        subp = subprocess.Popen(shlex.split(cmd), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=stdin_handle)

        # send some data to stdin if requested
        if send_stdin is not None:
            subp.stdin.write(send_stdin)
            subp.stdin.close()

        # wait for a string to appear in stdout if requested
        if ready_search_str is not None:
            boot_re = re.compile(ready_search_str)
            for bytes in iter(subp.stdout.readline, b''):
                line = bytes.decode('utf-8')
                writable.write(line)
                if boot_re.search(line):
                    break  # got it!

        # now the process is running *and* 'ready'
        if ready_ev is not None:
            ready_ev.set()

        # a helper will block on stdout and return lines back to us in a queue
        stdout_q = queue.Queue()
        t = threading.Thread(target=readline_thread_task, args=(subp.stdout, stdout_q))
        t.start()

        # collect output from the helper and write it, continuously checking to make
        # sure that the subprocess is still alive and the master doesn't want us to quit
        while subp.poll() is None and done_ev.is_set() is False:
            try:
                bytes = stdout_q.get(True, 1)
                writable.write(bytes.decode('utf-8'))
            except queue.Empty:
                # the queue is empty and the get() timed out, recheck loop conditions
                continue

        # either the process died, or we should shut down gracefully

        # if the process is still running, stop it
        if subp.poll() is None:
            # we collected no exit code, so it is still running
            subp.terminate()
            subp.wait()
        elif done_ev.is_set():
            logging.info("command '{}' finished as expected".format(cmd))
        elif no_relaunch:
            logging.info("command '{}' finished on its own".format(cmd))
            # our command finished on its own. time to terminate.
            done_ev.set()
        else:
            logging.warning("command '{}' finished before expected".format(cmd))
            now = time.time()
            # remove failures that happened more than an hour ago
            while len(failure_times) > 0 and failure_times[0] < (now-3600.0):
                failure_times.pop(0)
            # add a new failure that just occurred
            failure_times.append(now)
            pause_time_seconds = 30

        # the subp should be stopped now, flush any remaining lines
        #subp.stdout.close() # results in concurrent write error

        # the helper should stop since stdout was closed
        t.join()

        # helper thread is done, make sure we drain the remaining lines from the stdout queue
        while not stdout_q.empty():
            bytes = stdout_q.get_nowait()
            writable.write(bytes.decode('utf-8'))
        # if we have too many failures, exit the watchdog to propogate the error up
        if len(failure_times) > 10:
            break
        # now loop around: either the master asked us to stop, or the subp died and we relaunch it

    # too many failures, or master asked us to stop, close the writable before exiting thread
    writable.close()

def logrotate_thread_task(writables, tgen_writable, torctl_writable, docroot, nickname, done_ev):
    next_midnight = None

    while not done_ev.wait(1):
        # get time
        utcnow = datetime.datetime.utcnow()

        # setup the next expiration time (midnight tonight)
        if next_midnight is None:
            next_midnight = datetime.datetime(utcnow.year, utcnow.month, utcnow.day, 23, 59, 59)
            # make sure we are not already past the above time today
            if (next_midnight - utcnow).total_seconds() < 0:
                next_midnight -= datetime.timedelta(1)  # subtract 1 day

        # if we are past midnight, launch the rotate task
        if (next_midnight - utcnow).total_seconds() < 0:
            # handle the general writables we are watching
            for w in writables:
                w.rotate_file(filename_datetime=next_midnight)

            # handle tgen and tor writables specially, and do analysis
            if tgen_writable is not None or torctl_writable is not None:
                try:

                    # get our public ip address, do this every night in case it changes
                    public_measurement_ip_guess = util.get_ip_address()

                    # set up the analysis object with our log files
                    anal = analysis.OPAnalysis(nickname=nickname, ip_address=public_measurement_ip_guess)
                    if tgen_writable is not None:
                        anal.add_tgen_file(tgen_writable.rotate_file(filename_datetime=next_midnight))
                    if torctl_writable is not None:
                        anal.add_torctl_file(torctl_writable.rotate_file(filename_datetime=next_midnight))

                    # run the analysis, i.e. parse the files
                    anal.analyze()

                    # save the results in onionperf json format in the www docroot
                    anal.save(output_prefix=docroot, do_compress=True, date_prefix=next_midnight.date())

                    # update the xml index in docroot
                    generate_docroot_index(docroot)
                except Exception as e:
                    logging.warning("Caught and ignored exception in TorPerf log parser: {0}".format(repr(e)))
                    logging.warning("Formatted traceback: {0}".format(traceback.format_exc()))
            # reset our timer
            next_midnight = None

class Measurement(object):

    def __init__(self, tor_bin_path, tgen_bin_path, datadir_path, privatedir_path, nickname, additional_client_conf=None, torclient_conf_file=None, torserver_conf_file=None, single_onion=False, drop_guards_interval_hours=0):
        self.tor_bin_path = tor_bin_path
        self.tgen_bin_path = tgen_bin_path
        self.datadir_path = datadir_path
        self.privatedir_path = privatedir_path
        self.nickname = nickname
        self.threads = None
        self.done_event = None
        self.hs_v3_service_id = None
        self.www_docroot = "{0}/htdocs".format(self.datadir_path)
        self.base_config = os.environ['BASETORRC'] if "BASETORRC" in os.environ else ""
        self.additional_client_conf = additional_client_conf
        self.torclient_conf_file = torclient_conf_file
        self.torserver_conf_file = torserver_conf_file
        self.single_onion = single_onion
        self.drop_guards_interval_hours = drop_guards_interval_hours

    def run(self, do_onion=True, do_inet=True, tgen_model=None, tgen_client_conf=None, tgen_server_conf=None):
        '''
        only `tgen_server_conf.listen_port` are "public" and need to be opened on the firewall.
        if `tgen_client_conf.connect_port` != `tgen_server_conf.listen_port`, then you should have installed a forwarding rule in the firewall.
        all ports need to be unique though, and unique among multiple onionperf instances.

        here are some sane defaults:
        tgen_client_conf.listen_port=58888, tgen_client_conf.connect_port=8080, tgen_client_conf.tor_ctl_port=59050, tgen_client_conf.tor_socks_port=59000,
        tgen_server_conf.listen_port=8080, tgen_server_conf.tor_ctl_port=59051, tgen_server_conf.tor_socks_port=59001
        '''
        self.threads = []
        self.done_event = threading.Event()

        if tgen_client_conf is None:
            tgen_client_conf = TGenConf(listen_port=58888,
                                        connect_ip='0.0.0.0',
                                        connect_port=8080,
                                        tor_ctl_port=59050,
                                        tor_socks_port=59000)
        if tgen_server_conf is None:
            tgen_server_conf = TGenConf(listen_port=8080,
                                        tor_ctl_port=59051,
                                        tor_socks_port=59001)

        # if ctrl-c is pressed, shutdown child processes properly
        try:
            # make sure stem and Tor supports ephemeral HS (version >= 0.2.7.1-alpha)
            # and also the NEWNYM mode that clears descriptor cache (version >= 0.2.7.3-rc)
            if do_onion:
                try:
                    tor_version = get_system_tor_version(self.tor_bin_path)
                    if tor_version < Requirement.ADD_ONION or tor_version < Version('0.2.7.3-rc'):  # ADD_ONION is a stem 1.4.0 feature
                        logging.warning("OnionPerf in onion mode requires Tor version >= 0.2.7.3-rc, you have {0}, aborting".format(tor_version))
                        return
                except:
                    logging.warning("OnionPerf in onion mode requires stem version >= 1.4.0, you have {0}, aborting".format(stem_version))
                    return

            logging.info("Bootstrapping started...")
            logging.info("Log files for the client and server processes will be placed in {0}".format(self.datadir_path))

            general_writables = []
            tgen_client_writable, torctl_client_writable = None, None

            if do_onion or do_inet:
                tgen_model.port = tgen_server_conf.listen_port
                general_writables.append(self.__start_tgen_server(tgen_model))

            if do_onion:
                logging.info("Onion Service private keys will be placed in {0}".format(self.privatedir_path))
                # one must not have an open socks port when running a single
                # onion service.  see tor's man page for more information.
                if self.single_onion:
                    tgen_server_conf.tor_socks_port = 0
                tor_writable, torctl_writable = self.__start_tor_server(tgen_server_conf.tor_ctl_port,
                                                                        tgen_server_conf.tor_socks_port,
                                                                        {tgen_client_conf.connect_port:tgen_server_conf.listen_port})
                general_writables.append(tor_writable)
                general_writables.append(torctl_writable)

            if do_onion or do_inet:
                tor_writable, torctl_client_writable = self.__start_tor_client(tgen_client_conf.tor_ctl_port, tgen_client_conf.tor_socks_port)
                general_writables.append(tor_writable)

            server_urls = []
            if do_onion and self.hs_v3_service_id is not None:
                server_urls.append("{0}.onion:{1}".format(self.hs_v3_service_id, tgen_client_conf.connect_port))
            if do_inet:
                connect_ip = tgen_client_conf.connect_ip if tgen_client_conf.connect_ip != '0.0.0.0' else util.get_ip_address()
                server_urls.append("{0}:{1}".format(connect_ip, tgen_client_conf.connect_port))
            tgen_model.servers = server_urls

            if do_onion or do_inet:
                assert len(server_urls) > 0

                tgen_model.port = tgen_client_conf.listen_port
                tgen_model.socks_port = tgen_client_conf.tor_socks_port
                tgen_client_writable = self.__start_tgen_client(tgen_model)

                self.__start_log_processors(general_writables, tgen_client_writable, torctl_client_writable)

                logging.info("Bootstrapping finished, entering heartbeat loop")
                time.sleep(1)
                while True:
                    if tgen_model.num_transfers:
                        # This function blocks until our TGen client process
                        # terminated on its own.
                        self.__wait_for_tgen_client()
                        break

                    if self.__is_alive():
                        logging.info("All helper processes seem to be alive :)")
                    else:
                        logging.warning("Some parallel components failed too many times or have died :(")
                        logging.info("We are in a broken state, giving up and exiting now")
                        break

                    logging.info("Next main process heartbeat is in 1 hour (helper processes run on their own schedule)")
                    logging.info("press CTRL-C for graceful shutdown...")
                    time.sleep(3600)
            else:
                logging.info("No measurement mode set, nothing to do")

        except KeyboardInterrupt:
            logging.info("Interrupt received, please wait for graceful shutdown")
            self.__is_alive()
        finally:
            logging.info("Cleaning up child processes now...")

            if self.hs_v3_service_id is not None:
                try:
                    with Controller.from_port(port=self.hs_v3_control_port) as torctl:
                        torctl.authenticate()
                        torctl.remove_ephemeral_hidden_service(self.hs_v3_service_id)
                except: pass  # this fails to authenticate if tor proc is dead

#            logging.disable(logging.INFO)
            self.done_event.set()
            for t in self.threads:
                logging.info("Joining {0} thread...".format(t.getName()))
                t.join()
            time.sleep(1)
#            logging.disable(logging.NOTSET)

            logging.info("Child processes terminated")
            logging.info("Child process cleanup complete!")
            logging.info("Exiting")

    def __start_log_processors(self, general_writables, tgen_writable, torctl_writable):
        # rotate the log files, and then parse out the measurement data
        logrotate_args = (general_writables, tgen_writable, torctl_writable, self.www_docroot, self.nickname, self.done_event)
        logrotate = threading.Thread(target=logrotate_thread_task, name="logrotate", args=logrotate_args)
        logrotate.start()
        self.threads.append(logrotate)

    def __start_tgen_client(self, tgen_model_conf):
        return self.__start_tgen("client", tgen_model_conf)

    def __start_tgen_server(self, tgen_model_conf):
        return self.__start_tgen("server", tgen_model_conf)

    def __start_tgen(self, name, tgen_model_conf):
        logging.info("Starting TGen {0} process on port {1}...".format(name, tgen_model_conf.port))
        tgen_datadir = "{0}/tgen-{1}".format(self.datadir_path, name)
        if not os.path.exists(tgen_datadir): os.makedirs(tgen_datadir)

        tgen_confpath = "{0}/tgen.graphml.xml".format(tgen_datadir)
        if os.path.exists(tgen_confpath): os.remove(tgen_confpath)
        
        if tgen_model_conf.socks_port is None:
            model.ListenModel(tgen_port="{0}".format(tgen_model_conf.port)).dump_to_file(tgen_confpath)
            logging.info("TGen server running at 0.0.0.0:{0}".format(tgen_model_conf.port))
        else:
            tgen_model = model.TorperfModel(tgen_model_conf)
            tgen_model.dump_to_file(tgen_confpath)

        tgen_logpath = "{0}/onionperf.tgen.log".format(tgen_datadir)
        tgen_writable = util.FileWritable(tgen_logpath)
        logging.info("Logging TGen {1} process output to {0}".format(tgen_logpath, name))

        tgen_cmd = "{0} {1}".format(self.tgen_bin_path, tgen_confpath)
        # If we're running in "one-shot mode", TGen client will terminate on
        # its own and we don't need our watchdog to restart the process.
        no_relaunch = (name == "client" and tgen_model_conf.num_transfers)
        tgen_args = (tgen_cmd, tgen_datadir, tgen_writable, self.done_event, None, None, None, no_relaunch)
        tgen_watchdog = threading.Thread(target=watchdog_thread_task, name="tgen_{0}_watchdog".format(name), args=tgen_args)
        tgen_watchdog.start()
        self.threads.append(tgen_watchdog)

        return tgen_writable

    def create_tor_config(self, control_port, socks_port, tor_datadir, name):
        """
        This function generates a tor configuration based on a default
        template. This template is appended to any tor configuration inherited
        via the BASETORRC environment variable. Configuration in any additional
        tor client/server config files are then appended depending on whether
        "name" points to client or server. Any additional client configuration
        specified as a string is also added if the client is being configured.

        Finally, if there is no specific mention of either using Entry Guards
        (by default enabled) or bridges (by default disabled) the configurator
        appends an option to override the use of Entry Guards, to avoid
        measuring the guard node multiple times.
        """

        tor_config_template = self.base_config + "RunAsDaemon 0\nORPort 0\nDirPort 0\nControlPort {0}\nSocksPort {1}\nSocksListenAddress 127.0.0.1\nClientOnly 1\n\
WarnUnsafeSocks 0\nSafeLogging 0\nMaxCircuitDirtiness 60 seconds\nDataDirectory {2}\nDataDirectoryGroupReadable 1\nLog INFO stdout\n"
        tor_config = tor_config_template.format(control_port, socks_port, tor_datadir)
        if name == "server" and self.torserver_conf_file:
            with open(self.torserver_conf_file, 'r') as f:
                tor_config += f.read()
        if name == "client" and self.torclient_conf_file:
            with open(self.torclient_conf_file, 'r') as f:
                tor_config = tor_config + f.read()
        if name == "client" and self.additional_client_conf:
            tor_config += self.additional_client_conf
        if not 'UseEntryGuards' in tor_config and not 'UseBridges' in tor_config and self.drop_guards_interval_hours == 0:
            tor_config += "UseEntryGuards 0\n"
        if name == "server" and self.single_onion:
            tor_config += "HiddenServiceSingleHopMode 1\nHiddenServiceNonAnonymousMode 1\n"
        return tor_config

    def start_onion_service(self,
                            control_port,
                            hs_port_mapping,
                            key_path):
        logging.info("Creating ephemeral hidden service...")
    
        with Controller.from_port(port=control_port) as torctl:
            torctl.authenticate()
            if not os.path.exists(key_path):
                response = torctl.create_ephemeral_hidden_service(
                    hs_port_mapping,
                    detached=True,
                    await_publication=True,
                    key_content='ED25519-V3')
                with open(key_path, 'w') as key_file:
                    key_file.write('%s:%s' % (response.private_key_type,
                                              response.private_key))
            else:
                with open(key_path) as key_file:
                    key_type, key_content = key_file.read().split(':', 1)
                response = torctl.create_ephemeral_hidden_service(
                    hs_port_mapping,
                    detached=True,
                    await_publication=True,
                    key_content=key_content,
                    key_type=key_type)
            self.hs_v3_service_id = response.service_id
            self.hs_v3_control_port = control_port

            logging.info("Ephemeral hidden service is available at {0}.onion".format(response.service_id))
        return response.service_id

    def __start_tor_client(self, control_port, socks_port):
        return self.__start_tor("client", control_port, socks_port)

    def __start_tor_server(self, control_port, socks_port, hs_port_mapping):
        return self.__start_tor("server", control_port, socks_port, hs_port_mapping)

    def __start_tor(self, name, control_port, socks_port, hs_port_mapping=None):
        logging.info("Starting Tor {0} process with ControlPort={1}, SocksPort={2}...".format(name, control_port, socks_port))
        tor_datadir = "{0}/tor-{1}".format(self.datadir_path, name)
        key_path_v3 = "{0}/os_key_v3".format(self.privatedir_path)

        if not os.path.exists(tor_datadir): os.makedirs(tor_datadir)
        tor_config = self.create_tor_config(control_port,socks_port,tor_datadir,name)
        tor_confpath = "{0}/torrc".format(tor_datadir)
        with open(tor_confpath, 'wt') as f:
            f.write(tor_config)

        tor_logpath = "{0}/onionperf.tor.log".format(tor_datadir)
        tor_writable = util.FileWritable(tor_logpath)
        logging.info("Logging Tor {0} process output to {1}".format(name, tor_logpath))

        # from stem.process import launch_tor_with_config
        # tor_subp = launch_tor_with_config(tor_config, tor_cmd=self.tor_bin_path, completion_percent=100, init_msg_handler=None, timeout=None, take_ownership=False)
        tor_cmd = "{0} -f -".format(self.tor_bin_path)
        tor_stdin_bytes = str_tools._to_bytes(tor_config)
        tor_ready_str = "Bootstrapped 100"
        tor_ready_ev = threading.Event()
        tor_args = (tor_cmd, tor_datadir, tor_writable, self.done_event, tor_stdin_bytes, tor_ready_str, tor_ready_ev, False)
        tor_watchdog = threading.Thread(target=watchdog_thread_task, name="tor_{0}_watchdog".format(name), args=tor_args)
        tor_watchdog.start()
        self.threads.append(tor_watchdog)

        # wait until Tor finishes bootstrapping
        tor_ready_ev.wait()

        torctl_logpath = "{0}/onionperf.torctl.log".format(tor_datadir)
        torctl_writable = util.FileWritable(torctl_logpath)
        logging.info("Logging Tor {0} control port monitor output to {1}".format(name, torctl_logpath))

        # give a few seconds to make sure Tor had time to start listening on the control port
        time.sleep(3)

        torctl_events = [e for e in monitor.get_supported_torctl_events() if e not in ['DEBUG', 'INFO', 'NOTICE', 'WARN', 'ERR']]
        newnym_interval_seconds = 300
        torctl_args = (control_port, torctl_writable, torctl_events, newnym_interval_seconds, self.drop_guards_interval_hours, self.done_event)
        torctl_helper = threading.Thread(target=monitor.tor_monitor_run, name="torctl_{0}_helper".format(name), args=torctl_args)
        torctl_helper.start()
        self.threads.append(torctl_helper)

        if hs_port_mapping is not None:
            self.start_onion_service(control_port, hs_port_mapping, key_path_v3)

        return tor_writable, torctl_writable

    def __wait_for_tgen_client(self):
        logging.info("Waiting for TGen client to finish.")
        for t in self.threads:
            if t.getName() == "tgen_client_watchdog":
                while t.is_alive():
                    time.sleep(1)
                logging.info("TGen client finished.")

    def __is_alive(self):
        all_alive = True
        for t in self.threads:
            t_name = t.getName()
            if t.is_alive():
                logging.info("{0} is alive".format(t_name))
            else:
                logging.warning("{0} is dead!".format(t_name))
                all_alive = False
        return all_alive
