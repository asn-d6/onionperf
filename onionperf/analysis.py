'''
  OnionPerf
  Authored by Rob Jansen, 2015
  See LICENSE for licensing information
'''

import sys, os, re, json, datetime, logging

from multiprocessing import Pool, cpu_count
from signal import signal, SIGINT, SIG_IGN
from socket import gethostname
from abc import ABCMeta, abstractmethod

# stem imports
from stem import CircEvent, CircStatus, CircPurpose, StreamStatus
from stem.response.events import CircuitEvent, CircMinorEvent, StreamEvent, BandwidthEvent, BuildTimeoutSetEvent
from stem.response import ControlMessage, convert

# onionperf imports
from . import util

class Analysis(object):

    def __init__(self, nickname=None, ip_address=None):
        self.nickname = nickname
        self.measurement_ip = ip_address
        self.hostname = gethostname().split('.')[0]
        self.json_db = {'type':'onionperf', 'version':'2.0', 'data':{}}
        self.tgen_filepaths = []
        self.torctl_filepaths = []
        self.date_filter = None
        self.did_analysis = False

    def add_tgen_file(self, filepath):
        self.tgen_filepaths.append(filepath)

    def add_torctl_file(self, filepath):
        self.torctl_filepaths.append(filepath)

    def get_nodes(self):
        return list(self.json_db['data'].keys())

    def get_tor_bandwidth_summary(self, node, direction):
        try:
            return self.json_db['data'][node]['tor']['bandwidth_summary'][direction]
        except:
            return None

    def get_tgen_transfers(self, node):
        try:
            return self.json_db['data'][node]['tgen']['transfers']
        except:
            return None

    def get_tgen_transfers_summary(self, node):
        try:
            return self.json_db['data'][node]['tgen']['transfers_summary']
        except:
            return None

    def analyze(self, do_complete=False, date_filter=None):
        if self.did_analysis:
            return

        self.date_filter = date_filter
        tgen_parser = TGenParser(date_filter=self.date_filter)
        torctl_parser = TorCtlParser(date_filter=self.date_filter)

        for (filepaths, parser, json_db_key) in [(self.tgen_filepaths, tgen_parser, 'tgen'), (self.torctl_filepaths, torctl_parser, 'tor')]:
            if len(filepaths) > 0:
                for filepath in filepaths:
                    logging.info("parsing log file at {0}".format(filepath))
                    parser.parse(util.DataSource(filepath), do_complete=do_complete)

                if self.nickname is None:
                    parsed_name = parser.get_name()
                    if parsed_name is not None:
                        self.nickname = parsed_name
                    elif self.hostname is not None:
                        self.nickname = self.hostname
                    else:
                        self.nickname = "unknown"

                if self.measurement_ip is None:
                    self.measurement_ip = "unknown"

                self.json_db['data'].setdefault(self.nickname, {'measurement_ip': self.measurement_ip}).setdefault(json_db_key, parser.get_data())

        self.did_analysis = True

    def merge(self, analysis):
        for nickname in analysis.json_db['data']:
            if nickname in self.json_db['data']:
                raise Exception("Merge does not yet support multiple Analysis objects from the same node \
                (add multiple files from the same node to the same Analysis object before calling analyze instead)")
            else:
                self.json_db['data'][nickname] = analysis.json_db['data'][nickname]

    def save(self, filename=None, output_prefix=os.getcwd(), do_compress=True, date_prefix=None):
        if filename is None:
            base_filename = "onionperf.analysis.json.xz"
            if date_prefix is not None:
                filename = "{0}.{1}".format(util.date_to_string(date_prefix), base_filename)
            elif self.date_filter is not None:
                filename = "{0}.{1}".format(util.date_to_string(self.date_filter), base_filename)
            else:
                filename = base_filename

        filepath = os.path.abspath(os.path.expanduser("{0}/{1}".format(output_prefix, filename)))
        if not os.path.exists(output_prefix):
            os.makedirs(output_prefix)

        logging.info("saving analysis results to {0}".format(filepath))

        outf = util.FileWritable(filepath, do_compress=do_compress)
        json.dump(self.json_db, outf, sort_keys=True, separators=(',', ': '), indent=2)
        outf.close()

        logging.info("done!")

    @classmethod
    def load(cls, filename="onionperf.analysis.json.xz", input_prefix=os.getcwd()):
        filepath = os.path.abspath(os.path.expanduser("{0}".format(filename)))
        if not os.path.exists(filepath):
            filepath = os.path.abspath(os.path.expanduser("{0}/{1}".format(input_prefix, filename)))
            if not os.path.exists(filepath):
                logging.warning("file does not exist at '{0}'".format(filepath))
                return None

        logging.info("loading analysis results from {0}".format(filepath))

        inf = util.DataSource(filepath)
        inf.open()
        db = json.load(inf.get_file_handle())
        inf.close()

        logging.info("done!")

        if 'type' not in db or 'version' not in db:
            logging.warning("'type' or 'version' not present in database")
            return None
        elif db['type'] != 'onionperf' or str(db['version']) >= '3.':
            logging.warning("type or version not supported (type={0}, version={1})".format(db['type'], db['version']))
            return None
        else:
            analysis_instance = cls()
            analysis_instance.json_db = db
            return analysis_instance

def subproc_analyze_func(analysis_args):
    signal(SIGINT, SIG_IGN)  # ignore interrupts
    a = analysis_args[0]
    do_complete = analysis_args[1]
    a.analyze(do_complete=do_complete)
    return a

class ParallelAnalysis(Analysis):

    def analyze(self, search_path, do_complete=False, nickname=None, tgen_search_expressions=["tgen.*\.log"],
                torctl_search_expressions=["torctl.*\.log"], num_subprocs=cpu_count()):

        pathpairs = util.find_file_paths_pairs(search_path, tgen_search_expressions, torctl_search_expressions)
        logging.info("processing input from {0} nodes...".format(len(pathpairs)))

        analysis_jobs = []
        for (tgen_filepaths, torctl_filepaths) in pathpairs:
            a = Analysis()
            for tgen_filepath in tgen_filepaths:
                a.add_tgen_file(tgen_filepath)
            for torctl_filepath in torctl_filepaths:
                a.add_torctl_file(torctl_filepath)
            analysis_args = [a, do_complete]
            analysis_jobs.append(analysis_args)

        analyses = None
        pool = Pool(num_subprocs if num_subprocs > 0 else cpu_count())
        try:
            mr = pool.map_async(subproc_analyze_func, analysis_jobs)
            pool.close()
            while not mr.ready(): mr.wait(1)
            analyses = mr.get()
        except KeyboardInterrupt:
            logging.info("interrupted, terminating process pool")
            pool.terminate()
            pool.join()
            sys.exit()

        logging.info("merging {0} analysis results now...".format(len(analyses)))
        while analyses is not None and len(analyses) > 0:
            self.merge(analyses.pop())
        logging.info("done merging results: {0} total nicknames present in json db".format(len(self.json_db['data'])))

class TransferStatusEvent(object):

    def __init__(self, line):
        self.is_success = False
        self.is_error = False
        self.is_complete = False

        parts = line.strip().split()
        self.unix_ts_end = util.timestamp_to_seconds(parts[2])

        transport_parts = parts[8].split(',')
        self.endpoint_local = transport_parts[2]
        self.endpoint_proxy = transport_parts[3]
        self.endpoint_remote = transport_parts[4]

        transfer_parts = parts[10].split(',')

        # for id, combine the time with the transfer num; this is unique for each node,
        # as long as the node was running tgen without restarting for 100 seconds or longer
        # #self.transfer_id = "{0}-{1}".format(round(self.unix_ts_end, -2), transfer_num)
        self.transfer_id = "{0}:{1}".format(transfer_parts[0], transfer_parts[1])  # id:count

        self.hostname_local = transfer_parts[2]
        self.method = transfer_parts[3]  # 'GET' or 'PUT'
        self.filesize_bytes = int(transfer_parts[4])
        self.hostname_remote = transfer_parts[5]
        self.error_code = transfer_parts[8].split('=')[1]

        self.total_bytes_read = int(parts[11].split('=')[1])
        self.total_bytes_write = int(parts[12].split('=')[1])

        # the commander is the side that sent the command,
        # i.e., the side that is driving the download, i.e., the client side
        progress_parts = parts[13].split('=')
        self.is_commander = (self.method == 'GET' and 'read' in progress_parts[0]) or \
                            (self.method == 'PUT' and 'write' in progress_parts[0])
        self.payload_bytes_status = int(progress_parts[1].split('/')[0])

        self.unconsumed_parts = None if len(parts) < 16 else parts[15:]
        self.elapsed_seconds = {}

class TransferCompleteEvent(TransferStatusEvent):
    def __init__(self, line):
        super(TransferCompleteEvent, self).__init__(line)
        self.is_complete = True

        i = 0
        elapsed_seconds = 0.0
        # match up self.unconsumed_parts[0:11] with the events in the transfer_steps enum
        for k in ['socket_create', 'socket_connect', 'proxy_init', 'proxy_choice', 'proxy_request',
                  'proxy_response', 'command', 'response', 'first_byte', 'last_byte', 'checksum']:
            # parse out the elapsed time value
            keyval = self.unconsumed_parts[i]
            i += 1

            val = float(int(keyval.split('=')[1]))
            if val >= 0.0:
                elapsed_seconds = val / 1000000.0  # usecs to secs
                self.elapsed_seconds.setdefault(k, elapsed_seconds)

        self.unix_ts_start = self.unix_ts_end - elapsed_seconds
        del(self.unconsumed_parts)

class TransferSuccessEvent(TransferCompleteEvent):
    def __init__(self, line):
        super(TransferSuccessEvent, self).__init__(line)
        self.is_success = True

class TransferErrorEvent(TransferCompleteEvent):
    def __init__(self, line):
        super(TransferErrorEvent, self).__init__(line)
        self.is_error = True

class Transfer(object):
    def __init__(self, tid):
        self.id = tid
        self.last_event = None
        self.payload_progress = {decile:None for decile in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]}
        self.payload_bytes = {partial:None for partial in [10240, 20480, 51200, 102400, 204800, 512000, 1048576, 2097152, 5242880]}

    def add_event(self, status_event):
        progress_frac = float(status_event.payload_bytes_status) / float(status_event.filesize_bytes)
        progress = float(status_event.payload_bytes_status)
        for partial in sorted(self.payload_bytes.keys()):
            if progress >= partial and self.payload_bytes[partial] is None:
                self.payload_bytes[partial] = status_event.unix_ts_end
        for decile in sorted(self.payload_progress.keys()):
            if progress_frac >= decile and self.payload_progress[decile] is None:
                self.payload_progress[decile] = status_event.unix_ts_end
        self.last_event = status_event

    def get_data(self):
        e = self.last_event
        if e is None or not e.is_complete:
            return None
        d = e.__dict__
        if not e.is_error:
            d['elapsed_seconds']['payload_progress'] = {decile: round(self.payload_progress[decile] - e.unix_ts_start, 6) for decile in self.payload_progress if self.payload_progress[decile] is not None}
            d['elapsed_seconds']['payload_bytes'] = {partial: round(self.payload_bytes[partial] - e.unix_ts_start, 6) for partial in self.payload_bytes if self.payload_bytes[partial] is not None}
        return d

class Parser(object, metaclass=ABCMeta):
    @abstractmethod
    def parse(self, source, do_complete):
        pass
    @abstractmethod
    def get_data(self):
        pass
    @abstractmethod
    def get_name(self):
        pass

class TGenParser(Parser):

    def __init__(self, date_filter=None):
        ''' date_filter should be given in UTC '''
        self.state = {}
        self.transfers = {}
        self.transfers_summary = {'time_to_first_byte':{}, 'time_to_last_byte':{}, 'errors':{}}
        self.name = None
        self.date_filter = date_filter

    def __is_date_valid(self, date_to_check):
        if self.date_filter is None:
            # we are not asked to filter, so every date is valid
            return True
        else:
            # we are asked to filter, so the line is only valid if the date matches the filter
            # both the filter and the unix timestamp should be in UTC at this point
            return util.do_dates_match(self.date_filter, date_to_check)

    def __parse_line(self, line, do_complete):
        if self.name is None and re.search("Initializing traffic generator on host", line) is not None:
            self.name = line.strip().split()[11]

        if self.date_filter is not None:
            parts = line.split(' ', 3)
            if len(parts) < 4: # the 3rd is the timestamp, the 4th is the rest of the line
                return True
            unix_ts = float(parts[2])
            line_date = datetime.datetime.utcfromtimestamp(unix_ts).date()
            if not self.__is_date_valid(line_date):
                return True

        if do_complete and re.search("state\sRESPONSE\sto\sstate\sPAYLOAD", line) is not None:
            # another run of tgen starts the id over counting up from 1
            # if a prev transfer with the same id did not complete, we can be sure it never will
            parts = line.strip().split()
            transfer_parts = parts[7].strip().split(',')
            transfer_id = "{0}:{1}".format(transfer_parts[0], transfer_parts[1])  # id:count
            if transfer_id in self.state:
                self.state.pop(transfer_id)

        elif do_complete and re.search("transfer-status", line) is not None:
            status = TransferStatusEvent(line)
            xfer = self.state.setdefault(status.transfer_id, Transfer(status.transfer_id))
            xfer.add_event(status)

        elif re.search("transfer-complete", line) is not None:
            complete = TransferSuccessEvent(line)

            if do_complete:
                xfer = self.state.setdefault(complete.transfer_id, Transfer(complete.transfer_id))
                xfer.add_event(complete)
                self.transfers[xfer.id] = xfer.get_data()
                self.state.pop(complete.transfer_id)

            filesize, second = complete.filesize_bytes, int(complete.unix_ts_end)
            fb_secs = complete.elapsed_seconds['first_byte'] - complete.elapsed_seconds['command']
            lb_secs = complete.elapsed_seconds['last_byte'] - complete.elapsed_seconds['command']

            fb_list = self.transfers_summary['time_to_first_byte'].setdefault(filesize, {}).setdefault(second, [])
            fb_list.append(fb_secs)
            lb_list = self.transfers_summary['time_to_last_byte'].setdefault(filesize, {}).setdefault(second, [])
            lb_list.append(lb_secs)

        elif re.search("transfer-error", line) is not None:
            error = TransferErrorEvent(line)

            if do_complete:
                xfer = self.state.setdefault(error.transfer_id, Transfer(error.transfer_id))
                xfer.add_event(error)
                self.transfers[xfer.id] = xfer.get_data()
                self.state.pop(error.transfer_id)

            err_code, filesize, second = error.error_code, error.filesize_bytes, int(error.unix_ts_end)

            err_list = self.transfers_summary['errors'].setdefault(err_code, {}).setdefault(second, [])
            err_list.append(filesize)

        return True

    def parse(self, source, do_complete=False):
        source.open()
        for line in source:
            # ignore line parsing errors
            try:
                if not self.__parse_line(line, do_complete):
                    break
            except:
                logging.warning("TGenParser: skipping line due to parsing error: {0}".format(line))
                continue
        source.close()

    def get_data(self):
        return {'transfers':self.transfers, 'transfers_summary': self.transfers_summary}

    def get_name(self):
        return self.name

class Stream(object):
    def __init__(self, sid):
        self.stream_id = sid
        self.circuit_id = None
        self.unix_ts_start = None
        self.unix_ts_end = None
        self.failure_reason_local = None
        self.failure_reason_remote = None
        self.source = None
        self.target = None
        self.elapsed_seconds = []
        self.last_purpose = None

    def add_event(self, purpose, status, arrived_at):
        if purpose is not None:
            self.last_purpose = purpose
        key = "{0}:{1}".format(self.last_purpose, status)
        self.elapsed_seconds.append([key, arrived_at])

    def set_circ_id(self, circ_id):
        if circ_id is not None:
            self.circuit_id = circ_id

    def set_start_time(self, unix_ts):
        if self.unix_ts_start is None:
            self.unix_ts_start = unix_ts

    def set_end_time(self, unix_ts):
        self.unix_ts_end = unix_ts

    def set_local_failure(self, reason):
        self.failure_reason_local = reason

    def set_remote_failure(self, reason):
        self.failure_reason_remote = reason

    def set_target(self, target):
        self.target = target

    def set_source(self, source):
        self.source = source

    def get_data(self):
        if self.unix_ts_start is None or self.unix_ts_end is None:
            return None
        d = self.__dict__
        for item in d['elapsed_seconds']:
            item[1] = item[1] - self.unix_ts_start
        del(d['last_purpose'])
        if d['failure_reason_local'] is None: del(d['failure_reason_local'])
        if d['failure_reason_remote'] is None: del(d['failure_reason_remote'])
        if d['source'] is None: del(d['source'])
        if d['target'] is None: del(d['target'])
        return d

    def __str__(self):
        return('stream id=%d circ_id=%s %s' % (self.id, self.circ_id,
               ' '.join(['%s=%s' % (event, arrived_at)
               for (event, arrived_at) in sorted(self.elapsed_seconds, key=lambda item: item[1])])))

class Circuit(object):
    def __init__(self, cid):
        self.circuit_id = cid
        self.unix_ts_start = None
        self.unix_ts_end = None
        self.failure_reason_local = None
        self.failure_reason_remote = None
        self.buildtime_seconds = None
        self.build_timeout = None
        self.build_quantile = None
        self.elapsed_seconds = []
        self.path = []

    def add_event(self, event, arrived_at):
        self.elapsed_seconds.append([str(event), arrived_at])

    def add_hop(self, hop, arrived_at):
        self.path.append(["${0}~{1}".format(hop[0], hop[1]), arrived_at])

    def set_launched(self, unix_ts, build_timeout, build_quantile):
        if self.unix_ts_start is None:
            self.unix_ts_start = unix_ts
        self.build_timeout = build_timeout
        self.build_quantile = build_quantile

    def set_end_time(self, unix_ts):
        self.unix_ts_end = unix_ts

    def set_local_failure(self, reason):
        self.failure_reason_local = reason

    def set_remote_failure(self, reason):
        self.failure_reason_remote = reason

    def set_build_time(self, unix_ts):
        if self.buildtime_seconds is None:
            self.buildtime_seconds = unix_ts

    def get_data(self):
        if self.unix_ts_start is None or self.unix_ts_end is None:
            return None
        d = self.__dict__
        for item in d['elapsed_seconds']:
            item[1] = item[1] - self.unix_ts_start
        for item in d['path']:
            item[1] = item[1] - self.unix_ts_start
        if d['buildtime_seconds'] is None:
            del(d['buildtime_seconds'])
        else:
            d['buildtime_seconds'] = self.buildtime_seconds - self.unix_ts_start
        if len(d['path']) == 0: del(d['path'])
        if d['failure_reason_local'] is None: del(d['failure_reason_local'])
        if d['failure_reason_remote'] is None: del(d['failure_reason_remote'])
        if d['build_timeout'] is None: del(d['build_timeout'])
        if d['build_quantile'] is None: del(d['build_quantile'])
        return d

    def __str__(self):
        return('circuit id=%d %s' % (self.id, ' '.join(['%s=%s' %
               (event, arrived_at) for (event, arrived_at) in
               sorted(self.elapsed_seconds, key=lambda item: item[1])])))

class TorCtlParser(Parser):

    def __init__(self, date_filter=None):
        ''' date_filter should be given in UTC '''
        self.do_complete = False
        self.bandwidth_summary = {'bytes_read':{}, 'bytes_written':{}}
        self.circuits_state = {}
        self.circuits = {}
        self.circuits_summary = {'buildtimes':[], 'lifetimes':[]}
        self.streams_state = {}
        self.streams = {}
        self.streams_summary = {'lifetimes':{}}
        self.name = None
        self.boot_succeeded = False
        self.build_timeout_last = None
        self.build_quantile_last = None
        self.date_filter = date_filter

    def __handle_circuit(self, event, arrival_dt):
        # first make sure we have a circuit object
        cid = int(event.id)
        circ = self.circuits_state.setdefault(cid, Circuit(cid))
        is_hs_circ = True if event.purpose in (CircPurpose.HS_CLIENT_INTRO, CircPurpose.HS_CLIENT_REND, \
                                   CircPurpose.HS_SERVICE_INTRO, CircPurpose.HS_SERVICE_REND) else False

        # now figure out what status we want to track
        key = None
        if isinstance(event, CircuitEvent):
            if event.status == CircStatus.LAUNCHED:
                circ.set_launched(arrival_dt, self.build_timeout_last, self.build_quantile_last)

            key = "{0}:{1}".format(event.purpose, event.status)
            circ.add_event(key, arrival_dt)

            if event.status == CircStatus.EXTENDED:
                circ.add_hop(event.path[-1], arrival_dt)
            elif event.status == CircStatus.FAILED:
                circ.set_local_failure(event.reason)
                if event.remote_reason is not None and event.remote_reason != '':
                    circ.set_remote_failure(event.remote_reason)
            elif event.status == CircStatus.BUILT:
                circ.set_build_time(arrival_dt)
                if is_hs_circ:
                    key = event.hs_state
                    if event.rend_query is not None and event.rend_query != '':
                        key = "{0}:{1}".format(key, event.rend_query)
                    circ.add_event(key, arrival_dt)

            if event.status == CircStatus.CLOSED or event.status == CircStatus.FAILED:
                circ.set_end_time(arrival_dt)
                started, built, ended = circ.unix_ts_start, circ.buildtime_seconds, circ.unix_ts_end

                data = circ.get_data()
                if data is not None:
                    if built is not None and started is not None and len(data['path']) == 3:
                        self.circuits_summary['buildtimes'].append(built - started)
                    if ended is not None and started is not None:
                        self.circuits_summary['lifetimes'].append(ended - started)
                    if self.do_complete:
                        self.circuits[cid] = data
                self.circuits_state.pop(cid)

        elif self.do_complete and isinstance(event, CircMinorEvent):
            if event.purpose != event.old_purpose or event.event != CircEvent.PURPOSE_CHANGED:
                key = "{0}:{1}".format(event.event, event.purpose)
                circ.add_event(key, arrival_dt)

            if is_hs_circ:
                key = event.hs_state
                if event.rend_query is not None and event.rend_query != '':
                    key = "{0}:{1}".format(key, event.rend_query)
                circ.add_event(key, arrival_dt)

    def __handle_stream(self, event, arrival_dt):
        sid = int(event.id)
        strm = self.streams_state.setdefault(sid, Stream(sid))

        if event.circ_id is not None:
            strm.set_circ_id(event.circ_id)

        strm.add_event(event.purpose, event.status, arrival_dt)
        strm.set_target(event.target)

        if event.status == StreamStatus.NEW or event.status == StreamStatus.NEWRESOLVE:
            strm.set_start_time(arrival_dt)
            strm.set_source(event.source_addr)
        elif event.status == StreamStatus.FAILED:
            strm.set_local_failure(event.reason)
            if event.remote_reason is not None and event.remote_reason != '':
                strm.set_remote_failure(event.remote_reason)

        if event.status == StreamStatus.CLOSED or event.status == StreamStatus.FAILED:
            strm.set_end_time(arrival_dt)
            stream_type = strm.last_purpose
            started, ended = strm.unix_ts_start, strm.unix_ts_end

            data = strm.get_data()
            if data is not None:
                if self.do_complete:
                    self.streams[sid] = data
                self.streams_summary['lifetimes'].setdefault(stream_type, []).append(ended - started)
            self.streams_state.pop(sid)

    def __handle_bw(self, event, arrival_dt):
        self.bandwidth_summary['bytes_read'][int(arrival_dt)] = event.read
        self.bandwidth_summary['bytes_written'][int(arrival_dt)] = event.written

    def __handle_buildtimeout(self, event, arrival_dt):
        self.build_timeout_last = event.timeout
        self.build_quantile_last = event.quantile

    def __handle_event(self, event, arrival_dt):
        if isinstance(event, (CircuitEvent, CircMinorEvent)):
            self.__handle_circuit(event, arrival_dt)
        elif isinstance(event, StreamEvent):
            self.__handle_stream(event, arrival_dt)
        elif isinstance(event, BandwidthEvent):
            self.__handle_bw(event, arrival_dt)
        elif isinstance(event, BuildTimeoutSetEvent):
            self.__handle_buildtimeout(event, arrival_dt)

    def __is_date_valid(self, date_to_check):
        if self.date_filter is None:
            # we are not asked to filter, so every date is valid
            return True
        else:
            # we are asked to filter, so the line is only valid if the date matches the filter
            # both the filter and the unix timestamp should be in UTC at this point
            return util.do_dates_match(self.date_filter, date_to_check)

    def __parse_line(self, line):
        if not self.boot_succeeded:
            if re.search("Starting\storctl\sprogram\son\shost", line) is not None:
                parts = line.strip().split()
                if len(parts) < 11:
                    return True
                self.name = parts[10]
            if re.search("Bootstrapped\s100", line) is not None:
                self.boot_succeeded = True
            elif re.search("BOOTSTRAP", line) is not None and re.search("PROGRESS=100", line) is not None:
                self.boot_succeeded = True

        if self.do_complete or (self.do_complete is False and re.search("650\sBW", line) is not None):
            # parse with stem
            timestamps, sep, raw_event_str = line.partition(" 650 ")
            if sep == '':
                return True

            # event.arrived_at is also available but at worse granularity
            unix_ts = float(timestamps.strip().split()[2])

            # check if we should ignore the line
            line_date = datetime.datetime.utcfromtimestamp(unix_ts).date()
            if not self.__is_date_valid(line_date):
                return True

            event = ControlMessage.from_str("{0} {1}".format(sep.strip(), raw_event_str))
            convert('EVENT', event)
            self.__handle_event(event, unix_ts)
        return True

    def parse(self, source, do_complete=False):
        self.do_complete = do_complete
        source.open(newline='\r\n')
        for line in source:
            # ignore line parsing errors
            try:
                if self.__parse_line(line):
                    continue
                else:
                    break
            except:
                continue
        source.close()

    def get_data(self):
        return {'circuits': self.circuits, 'circuits_summary': self.circuits_summary,
                'streams':self.streams, 'streams_summary': self.streams_summary,
                'bandwidth_summary': self.bandwidth_summary}

    def get_name(self):
        return self.name
