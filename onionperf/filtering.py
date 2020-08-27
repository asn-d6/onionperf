'''
  OnionPerf
  Authored by Rob Jansen, 2015
  Copyright 2015-2020 The Tor Project
  See LICENSE for licensing information
'''

import re
from onionperf.analysis import OPAnalysis

class Filtering(object):

    def __init__(self):
        self.fingerprints_to_include = None
        self.fingerprints_to_exclude = None
        self.fingerprint_pattern = re.compile("\$?([0-9a-fA-F]{40})")

    def include_fingerprints(self, path):
        self.fingerprints_to_include = []
        with open(path, 'rt') as f:
            for line in f:
                fingerprint_match = self.fingerprint_pattern.match(line)
                if fingerprint_match:
                    fingerprint = fingerprint_match.group(1).upper()
                    self.fingerprints_to_include.append(fingerprint)

    def exclude_fingerprints(self, path):
        self.fingerprints_to_exclude = []
        with open(path, 'rt') as f:
            for line in f:
                fingerprint_match = self.fingerprint_pattern.match(line)
                if fingerprint_match:
                    fingerprint = fingerprint_match.group(1).upper()
                    self.fingerprints_to_exclude.append(fingerprint)

    def apply_filters(self, input_path, output_dir, output_file):
        self.analysis = OPAnalysis.load(filename=input_path)
        if self.fingerprints_to_include is None and self.fingerprints_to_exclude is None:
            return
        for source in self.analysis.get_nodes():
            tor_streams_by_source_port = {}
            tor_streams = self.analysis.get_tor_streams(source)
            for tor_stream in tor_streams.values():
                if "source" in tor_stream and ":" in tor_stream["source"]:
                    source_port = tor_stream["source"].split(":")[1]
                    tor_streams_by_source_port.setdefault(source_port, []).append(tor_stream)
            tor_circuits = self.analysis.get_tor_circuits(source)
            tgen_streams = self.analysis.get_tgen_streams(source)
            tgen_transfers = self.analysis.get_tgen_transfers(source)
            retained_tgen_streams = {}
            retained_tgen_transfers = {}
            while tgen_streams or tgen_transfers:
                stream_id = None
                transfer_id = None
                source_port = None
                unix_ts_end = None
                keep = False
                if tgen_streams:
                    stream_id, stream_data = tgen_streams.popitem()
                    if "local" in stream_data["transport_info"] and len(stream_data["transport_info"]["local"].split(":")) > 2:
                        source_port = stream_data["transport_info"]["local"].split(":")[2]
                    if "unix_ts_end" in stream_data:
                        unix_ts_end = stream_data["unix_ts_end"]
                elif tgen_transfers:
                    transfer_id, transfer_data = tgen_transfers.popitem()
                    if "endpoint_local" in transfer_data and len(transfer_data["endpoint_local"].split(":")) > 2:
                        source_port = transfer_data["endpoint_local"].split(":")[2]
                    if "unix_ts_end" in transfer_data:
                        unix_ts_end = transfer_data["unix_ts_end"]
                if source_port and unix_ts_end:
                    for tor_stream in tor_streams_by_source_port[source_port]:
                        if abs(unix_ts_end - tor_stream["unix_ts_end"]) < 150.0:
                            circuit_id = tor_stream["circuit_id"]
                if circuit_id and str(circuit_id) in tor_circuits:
                    tor_circuit = tor_circuits[circuit_id]
                    path = tor_circuit["path"]
                    keep = True
                    for long_name, _ in path:
                        fingerprint_match = self.fingerprint_pattern.match(long_name)
                        if fingerprint_match:
                            fingerprint = fingerprint_match.group(1).upper()
                            if self.fingerprints_to_include and fingerprint not in self.fingerprints_to_include:
                                keep = False
                                break
                            if self.fingerprints_to_exclude and fingerprint in self.fingerprints_to_exclude:
                                keep = False
                                break
                if keep:
                    if stream_id:
                        retained_tgen_streams[stream_id] = stream_data
                    if transfer_id:
                        retained_tgen_transfers[transfer_id] = transfer_data
            self.analysis.set_tgen_streams(source, retained_tgen_streams)
            self.analysis.set_tgen_transfers(source, retained_tgen_transfers)
        self.analysis.save(filename=output_file, output_prefix=output_dir)

