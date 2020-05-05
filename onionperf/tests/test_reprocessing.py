import os
import pkg_resources
import datetime
import tempfile
import shutil
from nose.tools import *
from onionperf import analysis
from onionperf import reprocessing


def absolute_data_path(relative_path=""):
    """
    Returns an absolute path for test data given a relative path.
    """
    return pkg_resources.resource_filename("onionperf",
                                           "tests/data/" + relative_path)


DATA_DIR = absolute_data_path()

def test_log_collection_tgen():
    log_list = reprocessing.collect_logs(DATA_DIR, '*tgen.log')
    well_known_list = [ DATA_DIR + 'logs/onionperf.tgen.log', DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.tgen.log' ]
    assert_equals(log_list, well_known_list )

def test_log_collection_torctl():
    log_list = reprocessing.collect_logs(DATA_DIR, '*torctl.log')
    well_known_list = [ DATA_DIR + 'logs/onionperf.torctl.log', DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.torctl.log' ]
    assert_equals(log_list, well_known_list )

def test_log_match():
    tgen_logs = reprocessing.collect_logs(DATA_DIR, '*tgen.log')
    torctl_logs = reprocessing.collect_logs(DATA_DIR, '*torctl.log')
    log_pairs =  reprocessing.match(tgen_logs, torctl_logs, None)
    well_known_list = [(DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.tgen.log', DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.torctl.log', datetime.datetime(2019, 1, 10, 0, 0))]
    assert_equals(log_pairs, well_known_list)

def test_log_match_no_log_date():
    tgen_logs = reprocessing.collect_logs(DATA_DIR, '*perf.tgen.log')
    torctl_logs = reprocessing.collect_logs(DATA_DIR, '*perf.torctl.log')
    log_pairs =  reprocessing.match(tgen_logs, torctl_logs, None)
    well_known_list = []
    assert_equals(log_pairs, well_known_list)

def test_log_match_with_filter_date():
    tgen_logs = reprocessing.collect_logs(DATA_DIR, '*tgen.log')
    torctl_logs = reprocessing.collect_logs(DATA_DIR, '*torctl.log')
    test_date = datetime.date(2019, 1, 10)
    log_pairs =  reprocessing.match(tgen_logs, torctl_logs, test_date)
    well_known_list = [(DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.tgen.log', DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.torctl.log', datetime.datetime(2019, 1, 10, 0, 0))]
    assert_equals(log_pairs, well_known_list)

def test_log_match_with_wrong_filter_date():
    tgen_logs = reprocessing.collect_logs(DATA_DIR, '*tgen.log')
    torctl_logs = reprocessing.collect_logs(DATA_DIR, '*torctl.log')
    test_date = datetime.date(2017, 1, 1)
    log_pairs =  reprocessing.match(tgen_logs, torctl_logs, test_date)
    well_known_list = []
    assert_equals(log_pairs, well_known_list)

def test_analyze_func_json():
    pair = (DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.tgen.log', DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.torctl.log', datetime.datetime(2019, 1, 10, 0, 0))
    work_dir = tempfile.mkdtemp()
    reprocessing.analyze_func(work_dir, None, pair)
    json_file = os.path.join(work_dir, "2019-01-10.onionperf.analysis.json.xz")
    assert(os.path.exists(json_file))
    for i in ['51200',  '5242880', '1048576']: 
       torperf_file = os.path.join(work_dir, "op-ab-{0}-2019-01-10.tpf".format(i))
       assert(os.path.exists(torperf_file))
    shutil.rmtree(work_dir)

def test_multiprocess_logs():
    pairs = [(DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.tgen.log', DATA_DIR + 'logs/onionperf_2019-01-10_23:59:59.torctl.log', datetime.datetime(2019, 1, 10, 0, 0))]
    work_dir = tempfile.mkdtemp()
    reprocessing.multiprocess_logs(pairs, work_dir)
    json_file = os.path.join(work_dir, "2019-01-10.onionperf.analysis.json.xz")
    assert(os.path.exists(json_file))
    for i in ['51200',  '5242880', '1048576']: 
       torperf_file = os.path.join(work_dir, "op-ab-{0}-2019-01-10.tpf".format(i))
       assert(os.path.exists(torperf_file))
    shutil.rmtree(work_dir)

def test_end_to_end():
    tgen_logs = reprocessing.collect_logs(DATA_DIR, '*tgen.log')
    torctl_logs = reprocessing.collect_logs(DATA_DIR, '*torctl.log')
    log_pairs =  reprocessing.match(tgen_logs, torctl_logs, None)
    work_dir = tempfile.mkdtemp()
    reprocessing.multiprocess_logs(log_pairs, work_dir)
    json_file = os.path.join(work_dir, "2019-01-10.onionperf.analysis.json.xz")
    assert(os.path.exists(json_file))
    for i in ['51200',  '5242880', '1048576']: 
       torperf_file = os.path.join(work_dir, "op-ab-{0}-2019-01-10.tpf".format(i))
       assert(os.path.exists(torperf_file))
    shutil.rmtree(work_dir)
