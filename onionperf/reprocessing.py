from onionperf.analysis import OPAnalysis
from onionperf import util
from functools import partial
from multiprocessing import Pool, cpu_count
import datetime
import fnmatch
import logging
import os
import re
import sys


def collect_logs(dirpath, pattern):
    logs = []
    for root, dirnames, filenames in os.walk(dirpath):
        for filename in fnmatch.filter(sorted(filenames), pattern):
            logs.append(os.path.join(root, filename))
    return logs


def match(tgen_logs, tor_logs, date_filter):
    log_pairs = []
    for tgen_log in tgen_logs:
        m = re.search(r'(\d+-\d+-\d+)', tgen_log)
        if m:
            date = m.group(0)
            fdate = datetime.datetime.strptime(date, "%Y-%m-%d")
            found = False
            if date_filter is None or util.do_dates_match(date_filter, fdate):
                for tor_log in tor_logs:
                    if date in tor_log:
                        log_pairs.append((tgen_log, tor_log, fdate))
                        found = True
                        break
                if not found:
                    logging.warning(
                        'Skipping file {0}, could not find a match for it'.
                        format(tgen_log))

        else:
            logging.warning(
                'Filename {0} does not contain a date'.format(tgen_log))
    if not log_pairs:
        logging.warning(
            'Could not find any log matches. No analyses will be performed')
    return log_pairs


def analyze_func(prefix, nick, pair):
    analysis = OPAnalysis(nickname=nick)
    logging.info('Analysing pair for date {0}'.format(pair[2]))
    analysis.add_tgen_file(pair[0])
    analysis.add_torctl_file(pair[1])
    analysis.analyze(date_filter=pair[2])
    analysis.save(output_prefix=prefix)
    return 1


def multiprocess_logs(log_pairs, prefix, nick=None):
    pool = Pool(cpu_count())
    analyses = None
    try:
        func = partial(analyze_func, prefix, nick)
        mr = pool.map_async(func, log_pairs)
        pool.close()
        while not mr.ready():
            mr.wait(1)
    except KeyboardInterrupt:
        logging.info("interrupted, terminating process pool")
        pool.terminate()
        pool.join()
        sys.exit()
    except Exception as e:
        logging.error(e)
