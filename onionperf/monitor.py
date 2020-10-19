'''
  OnionPerf
  Authored by Rob Jansen, 2015
  Copyright 2015-2020 The Tor Project
  See LICENSE for licensing information
'''

import datetime
import time
import os

from time import sleep
from socket import gethostname
from functools import partial

import shutil
import pathlib

# stem imports
from stem.control import EventType, Controller, Signal

def get_supported_torctl_events():
    return list(EventType)

class TorMonitor(object):

    def __init__(self, tor_ctl_port, writable, events=get_supported_torctl_events()):
        self.tor_ctl_port = tor_ctl_port
        self.writable = writable
        self.events = events

    def run(self, newnym_interval_seconds=None, drop_guards_interval_hours=0, done_ev=None):
        with Controller.from_port(port=self.tor_ctl_port) as torctl:
            torctl.authenticate()

            vers_str = "Starting torctl program on host {2} using Tor version {0} status={1}\n".format(torctl.get_info('version'), torctl.get_info('status/version/current'), gethostname())
            self.__log(self.writable, vers_str)

            boot_str = "{0}\n".format(torctl.get_info('status/bootstrap-phase'))
            self.__log(self.writable, boot_str)

            # register for async events!
            # some events are only supported in newer versions of tor, so ignore errors from older tors
            event_handler = partial(TorMonitor.__handle_tor_event, self, self.writable,)
            for e in self.events:
                if e in EventType:
                    # try to add all events that this stem supports
                    # silently ignore those that our Tor does not support
                    try:
                        torctl.add_event_listener(event_handler, EventType[e])
                    except:
                        self.__log(self.writable, "[WARNING] event %s is recognized by stem but not by tor\n" % e)
                        pass
                else:
                    try:
                        torctl.add_event_listener(event_handler, e)
                    except:
                        self.__log(self.writable, "[ERROR] unrecognized event %s in tor\n" % e)
                        return

            # let stem run its threads and log all of the events, until user interrupts
            try:
                interval_count = 0
                if newnym_interval_seconds is not None:
                    next_newnym = newnym_interval_seconds
                next_drop_guards = 0
                while done_ev is None or not done_ev.is_set():
                    # if self.filepath != '-' and os.path.exists(self.filepath):
                    #    with open(self.filepath, 'rb') as sizef:
                    #        msg = "tor-ctl-logger[port={0}] logged {1} bytes to {2}, press CTRL-C to quit".format(self.tor_ctl_port, os.fstat(sizef.fileno()).st_size, self.filepath)
                    #        logging.info(msg)
                    if drop_guards_interval_hours > 0 and interval_count >= next_drop_guards:
                        next_drop_guards += drop_guards_interval_hours * 3600
                        torctl.drop_guards()
                        drop_timeouts_response = torctl.msg("DROPTIMEOUTS")
                        if not drop_timeouts_response.is_ok():
                            self.__log(self.writable, "[WARNING] unrecognized command DROPTIMEOUTS in tor\n")

                        self.__log(self.writable, "Dropping guards %s" % os.getcwd())
                        pathlib.Path("tor-client/onionperf_state_history/").mkdir(parents=True, exist_ok=True)
                        shutil.copy("tor-client/state", "tor-client/onionperf_state_history/state_%s" % time.strftime("%Y%m%d-%H%M%S"))

                    sleep(1)
                    interval_count += 1
                    if newnym_interval_seconds is not None and interval_count >= next_newnym:
                        next_newnym += newnym_interval_seconds
                        torctl.signal(Signal.NEWNYM)

            except KeyboardInterrupt:
                pass  # the user hit ctrl+c

        self.writable.close()

    def __handle_tor_event(self, writable, event):
        self.__log(writable, event.raw_content())

    def __log(self, writable, msg):
        now = datetime.datetime.now()
        utcnow = datetime.datetime.utcnow()
        epoch = datetime.datetime(1970, 1, 1)
        unix_ts = (utcnow - epoch).total_seconds()
        writable.write("{0} {1:.02f} {2}".format(now.strftime("%Y-%m-%d %H:%M:%S"), unix_ts, msg))

def tor_monitor_run(tor_ctl_port, writable, events, newnym_interval_seconds, drop_guards_interval_hours, done_ev):
    torctl_monitor = TorMonitor(tor_ctl_port, writable, events)
    torctl_monitor.run(newnym_interval_seconds=newnym_interval_seconds, drop_guards_interval_hours=drop_guards_interval_hours, done_ev=done_ev)
