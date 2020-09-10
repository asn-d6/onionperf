'''
  OnionPerf
  Authored by Rob Jansen, 2015
  Copyright 2015-2020 The Tor Project
  See LICENSE for licensing information
'''

import re
from onionperf.analysis import OPAnalysis
from collections import defaultdict

class Filtering(object):

    def __init__(self):
        self.fingerprints_to_include = None
        self.fingerprints_to_exclude = None
        self.fingerprint_pattern = re.compile("\$?([0-9a-fA-F]{40})")
        self.filters = defaultdict(list)

    def include_fingerprints(self, path):
        self.fingerprints_to_include = []
        self.fingerprints_to_include_path = path
        with open(path, 'rt') as f:
            for line in f:
                fingerprint_match = self.fingerprint_pattern.match(line)
                if fingerprint_match:
                    fingerprint = fingerprint_match.group(1).upper()
                    self.fingerprints_to_include.append(fingerprint)

    def exclude_fingerprints(self, path):
        self.fingerprints_to_exclude = []
        self.fingerprints_to_exclude_path = path
        with open(path, 'rt') as f:
            for line in f:
                fingerprint_match = self.fingerprint_pattern.match(line)
                if fingerprint_match:
                    fingerprint = fingerprint_match.group(1).upper()
                    self.fingerprints_to_exclude.append(fingerprint)

    def filter_tor_circuits(self, analysis):
        if self.fingerprints_to_include is None and self.fingerprints_to_exclude is None:
            return
        self.filters["tor/circuits"] = []
        if self.fingerprints_to_include:
           self.filters["tor/circuits"].append({"name": "include_fingerprints", "filepath": self.fingerprints_to_include_path })
        if self.fingerprints_to_exclude:
           self.filters["tor/circuits"].append({"name": "exclude_fingerprints", "filepath": self.fingerprints_to_exclude_path })
        for source in analysis.get_nodes():
            tor_circuits = analysis.get_tor_circuits(source)
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
                    tor_circuits[circuit_id]["filtered_out"] = True
                    tor_circuits[circuit_id] = dict(sorted(tor_circuit.items()))

    def apply_filters(self, input_path, output_dir, output_file):
        self.analysis = OPAnalysis.load(filename=input_path)
        self.filter_tor_circuits(self.analysis)
        self.analysis.json_db["filters"] = self.filters
        self.analysis.json_db["version"] = '4.0'
        self.analysis.json_db = dict(sorted(self.analysis.json_db.items()))
        self.analysis.save(filename=output_file, output_prefix=output_dir, sort_keys=False)

