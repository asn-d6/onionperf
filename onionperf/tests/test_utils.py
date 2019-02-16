import os
import sys
import shutil
import tempfile
import datetime
import hashlib
from onionperf import util
from nose.tools import assert_equals

def test_make_dir():
    """
    Creates a temporary working directory, and then a directory within it.
    The second directory is created using util.make_dir_path.
    Ensures that the path exists, is a directory and is not a symbolic link.
    Removes the temporary working directory only if successful.
    """
    work_dir = tempfile.mkdtemp()
    test_path = os.path.join(work_dir, "test")
    util.make_dir_path(test_path)
    assert(os.path.exists(test_path))
    assert(os.path.isdir(test_path))
    assert(not os.path.islink(test_path))
    shutil.rmtree(work_dir)

def test_find_file_paths():
    """
    Uses util.find_file_paths to find an existing file in the test data directory, given a pattern.
    The function returns the full path to the file.
    """
    data_dir = "data" 
    pattern = ["abcdef"] 
    paths = util.find_file_paths(data_dir, pattern)
    print(paths)
    assert_equals(paths, ["data/dirs/abcdefg.txt"])
     
def test_find_file_paths_with_dash():
    """
    Uses util.find_file_paths to find an existing file in the test data directory, given a
    pattern.  Ensures the path returned by the function defaults to stdin if there
    is a dash detected at the end of the given directory.
    """
    data_dir = "data" 
    pattern = ["abcdef"] 
    paths = util.find_file_paths(data_dir + "/-", pattern)
    assert_equals(paths, ['-'])
 
def test_find_file_paths_pairs():
    """
    Uses util.find_file_paths_pairs to find existing files in the test data
    directory matching either of two given patterns.
    it returns tuples consisting of a list containing matching file and an empty list.
    The position of the empty lists is dependent on which pattern was matched.
    If a file matches the first pattern, the second item in the tuple will be empty.
    If a file matches the second pattern, the first item in the tuple will be empty.
    """
    data_dir = "data" 
    first_pattern = ['.*tgen\.log']
    second_pattern = ['.*torctl\.log']
    paths = util.find_file_paths_pairs(data_dir, first_pattern, second_pattern)
    assert_equals(paths, [([], ['data/logs/onionperf20190101.torctl.log']), ([], ['data/logs/onionperf.torctl.log']), (['data/logs/onionperf.tgen.log'], []), (['data/logs/onionperf20190101.tgen.log'], [])])

def test_find_path_with_binpath():
    """
    Creates a temporary named file, uses util.find_path with a filename to find its
    full path and then compares is to that returned by the tempfile function.
    Removes the created named temporary file only if successful.
    """
    temp_file = tempfile.NamedTemporaryFile()
    work_path = util.find_path(temp_file.name, temp_file.name)
    assert_equals(work_path, temp_file.name)
    temp_file.close()


def test_find_path_with_which():
    """
    Creates a temporary named file, and makes it executable.
    Uses util.find_path with a name and search path to find its full
    path, and then compares is to that returned by the tempfile function.  Removes
    the created named temporary file only if successful.
    """

    temp_file = tempfile.NamedTemporaryFile()
    os.chmod(temp_file.name, 0775)
    work_path = util.find_path(None, temp_file.name, tempfile.tempdir)
    assert_equals(work_path, temp_file.name)
    temp_file.close()

def test_is_exe():
    """
    Uses util.is_exe to test if paths point to executable files.
    Checks an executable file path is accepted 
    Checks a non-executable file path is not accepted
    Checks a directory path is not accepted
    """
    assert(util.is_exe("data/bin/script"))
    assert(not util.is_exe("data/bin/script_no_exe"))
    assert(not util.is_exe("data/bin/"))

def test_which():
    """
    Uses util.which with an executable file and a search path in the test data
    directory. Checks the full path of the file is identified.
    """
    test_binary = util.which("script", search_path="data/bin/")
    assert_equals(test_binary, "data/bin/script")

def test_which_not_executable():
    """
    Uses util.which to test an non-executable file 
    in the test data directory. Checks the non-executable file is not 
    identified as a program to run.
    """
    test_binary = util.which("script_non_exe", search_path="data/bin/")
    assert_equals(test_binary, None)

def test_which_full_path():
    """
    Uses util.which with the full path of an executable file and a  
    search path. 
    Checks the full path of the file is identified.
    """
    test_binary = util.which("data/bin/script", search_path="data/bin/")
    assert_equals(test_binary, "data/bin/script")


def test_date_to_string():
    """
    Uses util.date_to_string with a datetime object.
    Returns a correctly formatted string.
    """
    date_object = datetime.datetime(2018, 11, 27, 11)
    date_string = util.date_to_string(date_object)
    assert_equals(date_string, "2018-11-27")

def test_date_to_string_is_none():
    """
    Uses util.date_to_string with a None object.
    Returns an empty string.
    """
    date_string = util.date_to_string(None)
    assert_equals(date_string, "")

def test_dates_match():
    """
    Uses util.dates_match with two matching datetime objects.
    """
    first_date = datetime.datetime(2018, 11, 27, 10)
    second_date = datetime.datetime(2018, 11, 27, 11)
    assert(util.do_dates_match(first_date, second_date))

def test_dates_match_false():
    """
    Uses util.dates_match with two non-matching datetime objects.
    """
    first_date = datetime.datetime(2018, 11, 27, 10)
    second_date = datetime.datetime(2016, 11, 27, 11)
    assert_equals(util.do_dates_match(first_date, second_date), False)

def test_find_ip_address_url():
    """
    Uses util.find_ip_address_url with a string containing an IPv4 address.
    The ip address is returned as a string.
    """
    ip_address =  util.find_ip_address_url("Your IP address appears to be: 70.70.70.70")
    assert_equals(ip_address, "70.70.70.70")

def test_find_ip_address_url_none():
    """
    Uses util.find_ip_address_url with a string containing no IPv4 address.
    This should return None.
    """
    ip_address =  util.find_ip_address_url("Your IP address appears to be")
    assert_equals(ip_address, None)

def test_get_random_free_port():
    """
    Uses util.get_random_free_port to get a port number.
    Asserts the port exists, and it is a high-numbered port
    between 10000 and 60000.
    """ 
    port = util.get_random_free_port()
    assert(port is not None)
    assert(port < 60000)
    assert(port >= 10000)

def test_data_source_stdin():
    """
    Creates a new util.DataSource object with stdin input.  When calling
    util.DataSource.open(), this should set stdin as the DataSource.source
    for this object.
    """
    test_data_source = util.DataSource("-")
    test_data_source.open()
    assert_equals(test_data_source.source, sys.stdin)

def test_data_source_file():
    """
    Creates a new util.DataSource object with an uncompressed input file.  When calling
    util.DataSource.open(), this should set the file handle as the DataSource.source
    for this object. 
    DataSouce.source is verified against the contents of the input file.
    """
    test_data_source = util.DataSource("data/simplefile")
    test_data_source.open()
    data_source_file_handle = test_data_source.source
    data_source_contents = data_source_file_handle.read()
    assert_equals(data_source_contents, "onionperf")

def test_data_source_compressed_file():
    """
    Creates a new util.DataSource object with a compressed input file.  When
    calling util.DataSource.open(), this should set the output of an xzprocess (an
    uncompressed file handle) as the DataSource.source for this object, and set
    DataSource.compress to True. 
    Verifies DataSource.compress is set to True. 
    DataSouce.source is verified against the contents of the input file.
    """
    test_data_source = util.DataSource("data/simplefile.xz")
    test_data_source.open()
    data_source_file_handle = test_data_source.source
    data_source_contents = data_source_file_handle.read()
    assert_equals(data_source_contents, "onionperf")
    assert(test_data_source.compress)

def test_file_writable():
    """
    Creates a new util.FileWritable object using a temporary filename.
    Writes a string to it using util.FileWritable.write(). 
    The checksum of this file is compared to a good known checksum.    
    The temporary file is only removed if the test is successful.
    """
    temp_file = tempfile.NamedTemporaryFile()
    test_writable = util.FileWritable(temp_file.name)
    test_writable.write("onionperf")
    test_writable.close()
    expected_checksum = "5001ed4ab25b52543946fa63da829d4eeab1bd254c89ffdad0877186e074b385"
    with open(temp_file.name) as f:
        file_bytes = f.read()
        file_checksum = hashlib.sha256(file_bytes).hexdigest()
    assert_equals(file_checksum, expected_checksum)
    temp_file.close()

def test_file_writable_compressed():
    """
    Creates a new util.FileWritable object using a temporary filename and
    compression. Writes a string to it using util.FileWritable.write(). 
    The checksum of this file is compared to a good known checksum.    
    The temporary file is only removed if the test is successful.
    """

    temp_file = tempfile.NamedTemporaryFile(suffix=".xz")
    test_writable = util.FileWritable(temp_file.name, True)
    test_writable.write("onionperf")
    test_writable.close()
    expected_checksum = "66a6256bc4b04529c7123fa9573d30de659ffaa0cce1cc9b189817c8bf30e813"
    with open(temp_file.name) as f:
        file_bytes = f.read()
        file_checksum = hashlib.sha256(file_bytes).hexdigest()
    assert_equals(file_checksum, expected_checksum)
    temp_file.close()

def test_file_writable_with_stout():
    """
    Creates a new util.FileWritable object using stdout.
    Checks the util.FileWritable.file attribute is set to stdout.
    """
    test_writable = util.FileWritable("-")
    assert_equals(test_writable.file, sys.stdout)

def test_file_writable_rotate_file():
    """
    Creates a temporary working directory.
    Creates a new util.FileWritable object in the working directory.
    Rotates file using util.FileWritable.rotate_file with a fixed date and time.
    Checks path log_archive has been created in the working directory.
    Checks path log_archive is a directory.
    Checks file with the appropiate name has been rotated in the log_archive directory.
    Removes working directory only if successful.
    """
    work_dir = tempfile.mkdtemp()
    test_writable = util.FileWritable(os.path.join(work_dir, "logfile"))
    test_writable.write("onionperf")
    test_writable.rotate_file(datetime.datetime(2018, 11, 27, 0, 0, 0))
    created_dir = os.path.join(work_dir, "log_archive")
    rotated_file = os.path.join(created_dir, "logfile_2018-11-27_00:00:00")
    assert(os.path.exists(created_dir))
    assert(os.path.isdir(created_dir))
    assert(os.path.exists(rotated_file))
    shutil.rmtree(work_dir)
