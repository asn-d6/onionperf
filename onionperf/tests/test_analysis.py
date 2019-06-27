import os
import pkg_resources
from nose.tools import *
from onionperf import analysis, util


def absolute_data_path(relative_path=""):
    """
    Returns an absolute path for test data given a relative path.
    """
    return pkg_resources.resource_filename("onionperf",
                                           "tests/data/" + relative_path)

DATA_DIR = absolute_data_path()
LINE_ERROR = '2019-04-22 14:41:20 1555940480.647663 [message] [shd-tgen-transfer.c:1504] [_tgentransfer_log] [transfer-error] transport TCP,12,localhost:127.0.0.1:46878,localhost:127.0.0.1:43735,dc34og3c3aqdqntblnxkstzfvh7iy7llojd4fi5j23y2po32ock2k7ad.onion:0.0.0.0:8080,state=ERROR,error=READ transfer transfer5m,4,cyan,GET,5242880,(null),0,state=ERROR,error=PROXY total-bytes-read=0 total-bytes-write=0 payload-bytes-read=0/5242880 (0.00%) usecs-to-socket-create=11 usecs-to-socket-connect=210 usecs-to-proxy-init=283 usecs-to-proxy-choice=348 usecs-to-proxy-request=412 usecs-to-proxy-response=-1 usecs-to-command=-1 usecs-to-response=-1 usecs-to-first-byte=-1 usecs-to-last-byte=-1 usecs-to-checksum=-1'

NO_PARSE_LINE = '2018-04-14 21:10:04 1523740204.809894 [message] [shd-tgen-transfer.c:803] [_tgentransfer_log] [transfer-error] transport TCP,17,NULL:37.218.247.40:26006,NULL:0.0.0.0:0,146.0.73.4:146.0.73.4:1313,state=SUCCESS,error=NONE transfer (null),26847,op-nl,NONE,0,(null),0,state=ERROR,error=AUTH total-bytes-read=1 total-bytes-write=0 payload-bytes-write=0/0 (-nan%) usecs-to-socket-create=0 usecs-to-socket-connect=8053676879205 usecs-to-proxy-init=-1 usecs-to-proxy-choice=-1 usecs-to-proxy-request=-1 usecs-to-proxy-response=-1 usecs-to-command=-1 usecs-to-response=-1 usecs-to-first-byte=-1 usecs-to-last-byte=-1 usecs-to-checksum=-1'

def test_transfer_status_event():
    transfer = analysis.TransferStatusEvent(LINE_ERROR)
    assert_equals(transfer.is_success, False)
    assert_equals(transfer.is_error, False)
    assert_equals(transfer.is_complete, False)
    assert_equals(transfer.unix_ts_end, 1555940480.647663)
    assert_equals(transfer.endpoint_local, 'localhost:127.0.0.1:46878')
    assert_equals(transfer.endpoint_proxy, 'localhost:127.0.0.1:43735')
    assert_equals(
        transfer.endpoint_remote,
        'dc34og3c3aqdqntblnxkstzfvh7iy7llojd4fi5j23y2po32ock2k7ad.onion:0.0.0.0:8080'
    )
    assert_equals(
        transfer.endpoint_remote,
        'dc34og3c3aqdqntblnxkstzfvh7iy7llojd4fi5j23y2po32ock2k7ad.onion:0.0.0.0:8080'
    )
    assert_equals(transfer.transfer_id, 'transfer5m:4')
    assert_equals(transfer.hostname_local, 'cyan')
    assert_equals(transfer.method, 'GET')
    assert_equals(transfer.filesize_bytes, 5242880)
    assert_equals(transfer.hostname_remote, '(null)')
    assert_equals(transfer.error_code, 'PROXY')
    assert_equals(transfer.total_bytes_read, 0)
    assert_equals(transfer.total_bytes_write, 0)
    assert_equals(transfer.is_commander, True)
    assert_equals(transfer.payload_bytes_status, 0)
    assert_equals(transfer.unconsumed_parts, [
        'usecs-to-socket-create=11', 'usecs-to-socket-connect=210',
        'usecs-to-proxy-init=283', 'usecs-to-proxy-choice=348',
        'usecs-to-proxy-request=412', 'usecs-to-proxy-response=-1',
        'usecs-to-command=-1', 'usecs-to-response=-1',
        'usecs-to-first-byte=-1', 'usecs-to-last-byte=-1',
        'usecs-to-checksum=-1'
    ])
    assert_equals(transfer.elapsed_seconds, {})


def test_transfer_complete_event_init():
    complete = analysis.TransferCompleteEvent(LINE_ERROR)
    assert_equals(complete.is_complete, True)
    assert_equals(
        complete.elapsed_seconds, {
            'proxy_init': 0.000283,
            'proxy_request': 0.000412,
            'proxy_choice': 0.000348,
            'socket_connect': 0.00021,
            'socket_create': 1.1e-05
        })
    assert_equals(complete.unix_ts_start, 1555940480.6472511)


def test_transfer_error_event():
    error = analysis.TransferErrorEvent(LINE_ERROR)
    assert_equals(error.is_error, True)
    assert_equals(error.is_success, False)


def test_transfer_success_event_init():
    success = analysis.TransferSuccessEvent(LINE_ERROR)
    assert_equals(success.is_success, True)


def test_transfer_object_init():
    error = analysis.TransferErrorEvent(LINE_ERROR)
    t = analysis.Transfer(error.transfer_id)
    assert_equals(t.id, 'transfer5m:4')
    assert_equals(t.last_event, None)
    assert_equals(
        t.payload_progress, {
            0.0: None,
            0.1: None,
            0.2: None,
            0.3: None,
            0.4: None,
            0.5: None,
            0.6: None,
            0.7: None,
            0.8: None,
            0.9: None,
            1.0: None
        })


def test_transfer_object_add_event():
    error = analysis.TransferErrorEvent(LINE_ERROR)
    t = analysis.Transfer(error.transfer_id)
    t.add_event(error)
    assert_equals(t.last_event, error)
    assert_equals(
        t.payload_progress, {
            0.0: 1555940480.647663,
            0.1: None,
            0.2: None,
            0.3: None,
            0.4: None,
            0.5: None,
            0.6: None,
            0.7: None,
            0.8: None,
            0.9: None,
            1.0: None
        })


@raises(KeyError)
def test_transfer_object_get_data_error():
    error = analysis.TransferErrorEvent(LINE_ERROR)
    t = analysis.Transfer(error.transfer_id)
    t.add_event(error)
    t.get_data()['elapsed_seconds']['payload_progress']


def test_transfer_object_get_data_no_error():
    success = analysis.TransferSuccessEvent(LINE_ERROR)
    t = analysis.Transfer(success.transfer_id)
    t.add_event(success)
    assert_true(
        t.get_data()['elapsed_seconds']['payload_progress'] is not None)


def test_transfer_object_end_to_end():
    error = analysis.TransferErrorEvent(LINE_ERROR)
    t = analysis.Transfer(error.transfer_id)
    t.add_event(error)
    assert_equals(
        t.get_data(), {
            'is_error':
            True,
            'endpoint_local':
            'localhost:127.0.0.1:46878',
            'total_bytes_read':
            0,
            'error_code':
            'PROXY',
            'unix_ts_end':
            1555940480.647663,
            'hostname_local':
            'cyan',
            'endpoint_remote':
            'dc34og3c3aqdqntblnxkstzfvh7iy7llojd4fi5j23y2po32ock2k7ad.onion:0.0.0.0:8080',
            'elapsed_seconds': {
                'proxy_init': 0.000283,
                'proxy_request': 0.000412,
                'proxy_choice': 0.000348,
                'socket_connect': 0.00021,
                'socket_create': 1.1e-05
            },
            'method':
            'GET',
            'is_commander':
            True,
            'total_bytes_write':
            0,
            'unix_ts_start':
            1555940480.6472511,
            'hostname_remote':
            '(null)',
            'transfer_id':
            'transfer5m:4',
            'is_success':
            False,
            'payload_bytes_status':
            0,
            'endpoint_proxy':
            'localhost:127.0.0.1:43735',
            'is_complete':
            True,
            'filesize_bytes':
            5242880
        })


@raises(ZeroDivisionError)
def test_transfer_status_parse_error():
    transfer = analysis.TransferStatusEvent(NO_PARSE_LINE)
    t = analysis.Transfer(transfer.transfer_id)
    t.add_event(transfer)

def test_parsing_parse_error():
    parser = analysis.TGenParser()
    parser.parse(util.DataSource(DATA_DIR + 'parse_error'))
