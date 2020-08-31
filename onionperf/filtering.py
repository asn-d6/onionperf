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
            tor_circuits = self.analysis.get_tor_circuits(source)
            filtered_circuit_ids = []
            for circuit_id, tor_circuit in tor_circuits.items():
                keep = False
                if "path" in tor_circuit:
                    path = tor_circuit["path"]
                    keep = True
                    for long_name, _ in path:
                        fingerprint_match = self.fingerprint_pattern.match(long_name)
                        if fingerprint_match:
                            fingerprint = fingerprint_match.group(1).upper()
                            if self.fingerprints_to_include is not None and fingerprint not in self.fingerprints_to_include:
                                keep = False
                                break
                            if self.fingerprints_to_exclude is not None and fingerprint in self.fingerprints_to_exclude:
                                keep = False
                                break
                if not keep:
                    filtered_circuit_ids.append(circuit_id)
            for circuit_id in filtered_circuit_ids:
                del(tor_circuits[circuit_id])
        self.analysis.save(filename=output_file, output_prefix=output_dir, sort_keys=False)

