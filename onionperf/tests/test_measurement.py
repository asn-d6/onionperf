import os
import pkg_resources
from nose.tools import assert_equals
from onionperf import measurement


def absolute_data_path(relative_path=""):
    """
    Returns an absolute path for test data given a relative path.
    """
    return pkg_resources.resource_filename("onionperf",
                                           "tests/data/" + relative_path)


DATA_DIR = absolute_data_path()


def test_create_tor_config_env_var():
    """
    This test uses Measurement.create_tor_config to 
    create a configuration string for tor when the BASETORRC env variable is set. 
    It first sets the environment variable, then initializes an empty
    measurement and then calls create_tor_config with a series of well known
    variables. The resulting config is tested against the expected config for
    both client and server. Also
    this tests if the contents of the env variable are correctly recorded in
    the class attribute base_config.
    The environment variable is unset only if the test is successful.
    """

    os.environ["BASETORRC"] = "UseBridges 1\n"
    meas = measurement.Measurement(None, None, None, None, None, None, None, None,
                                   None)
    known_config = "UseBridges 1\nRunAsDaemon 0\nORPort 0\nDirPort 0\nControlPort 9001\nSocksPort 9050\nSocksListenAddress 127.0.0.1\nClientOnly 1\n\
WarnUnsafeSocks 0\nSafeLogging 0\nMaxCircuitDirtiness 60 seconds\nDataDirectory /tmp/\nDataDirectoryGroupReadable 1\nLog INFO stdout\n"

    config_client = meas.create_tor_config(9001, 9050, "/tmp/", "client")
    config_server = meas.create_tor_config(9001, 9050, "/tmp/", "server")
    assert_equals(config_client, known_config)
    assert_equals(config_server, known_config)
    assert_equals(meas.base_config, "UseBridges 1\n")
    del os.environ["BASETORRC"]


def test_create_tor_config_client_lines():
    """
    This test uses Measurement.create_tor_config to create a configuration
    string for tor when additional client config is specified.
    It initializes an empty measurement, setting the additional_client_config
    parameter. The resulting configuration is then tested against the expected
    configuration for both client and server.
    """

    known_config = "RunAsDaemon 0\nORPort 0\nDirPort 0\nControlPort 9001\nSocksPort 9050\nSocksListenAddress 127.0.0.1\nClientOnly 1\n\
WarnUnsafeSocks 0\nSafeLogging 0\nMaxCircuitDirtiness 60 seconds\nDataDirectory /tmp/\nDataDirectoryGroupReadable 1\nLog INFO stdout\nUseBridges 1\n"

    known_config_server = "RunAsDaemon 0\nORPort 0\nDirPort 0\nControlPort 9001\nSocksPort 9050\nSocksListenAddress 127.0.0.1\nClientOnly 1\n\
WarnUnsafeSocks 0\nSafeLogging 0\nMaxCircuitDirtiness 60 seconds\nDataDirectory /tmp/\nDataDirectoryGroupReadable 1\nLog INFO stdout\nUseEntryGuards 0\n"

    meas = measurement.Measurement(None, None, None, None, None, None,
                                   "UseBridges 1\n", None, None)
    config_client = meas.create_tor_config(9001, 9050, "/tmp/", "client")
    config_server = meas.create_tor_config(9001, 9050, "/tmp/", "server")
    assert_equals(config_client, known_config)
    assert_equals(config_server, known_config_server)


def test_create_tor_config_client_file():
    """
    This test uses Measurement.create_tor_config to create a configuration
    string for tor when additional client config is specified.
    It initializes an empty measurement, setting the additional_client_config
    parameter. The resulting configuration is then tested against the expected
    configuration for both client and server.
    """

    known_config_server = "RunAsDaemon 0\nORPort 0\nDirPort 0\nControlPort 9001\nSocksPort 9050\nSocksListenAddress 127.0.0.1\nClientOnly 1\n\
WarnUnsafeSocks 0\nSafeLogging 0\nMaxCircuitDirtiness 60 seconds\nDataDirectory /tmp/\nDataDirectoryGroupReadable 1\nLog INFO stdout\nUseEntryGuards 0\n"

    known_config = "RunAsDaemon 0\nORPort 0\nDirPort 0\nControlPort 9001\nSocksPort 9050\nSocksListenAddress 127.0.0.1\nClientOnly 1\n\
WarnUnsafeSocks 0\nSafeLogging 0\nMaxCircuitDirtiness 60 seconds\nDataDirectory /tmp/\nDataDirectoryGroupReadable 1\nLog INFO stdout\nUseBridges 1\n"

    meas = measurement.Measurement(None, None, None, None, None, None, None,
                                   absolute_data_path("config"), None)
    config_client = meas.create_tor_config(9001, 9050, "/tmp/", "client")
    config_server = meas.create_tor_config(9001, 9050, "/tmp/", "server")
    assert_equals(config_client, known_config)
    assert_equals(config_server, known_config_server)


def test_create_tor_config_server_file():
    """
    This test uses Measurement.create_tor_config to create a configuration
    string for tor when additional server config is specified in a file.
    It initializes an empty measurement, setting the additional_client_config
    parameter. The resulting configuration is then tested against the expected
    configuration for both client and server.
    """

    known_config_server = "RunAsDaemon 0\nORPort 0\nDirPort 0\nControlPort 9001\nSocksPort 9050\nSocksListenAddress 127.0.0.1\nClientOnly 1\n\
WarnUnsafeSocks 0\nSafeLogging 0\nMaxCircuitDirtiness 60 seconds\nDataDirectory /tmp/\nDataDirectoryGroupReadable 1\nLog INFO stdout\nUseBridges 1\n"

    known_config = "RunAsDaemon 0\nORPort 0\nDirPort 0\nControlPort 9001\nSocksPort 9050\nSocksListenAddress 127.0.0.1\nClientOnly 1\n\
WarnUnsafeSocks 0\nSafeLogging 0\nMaxCircuitDirtiness 60 seconds\nDataDirectory /tmp/\nDataDirectoryGroupReadable 1\nLog INFO stdout\nUseEntryGuards 0\n"

    meas = measurement.Measurement(None, None, None, None, None, None, None, None,
                                   absolute_data_path("config"))
    config_client = meas.create_tor_config(9001, 9050, "/tmp/", "client")
    config_server = meas.create_tor_config(9001, 9050, "/tmp/", "server")
    assert_equals(config_client, known_config)
    assert_equals(config_server, known_config_server)
