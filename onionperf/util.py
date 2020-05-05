'''
  OnionPerf
  Authored by Rob Jansen, 2015
  See LICENSE for licensing information
'''

import sys, os, socket, logging, random, re, shutil, datetime, urllib.request, urllib.parse, urllib.error, gzip, lzma
from threading import Lock
from io import StringIO
from abc import ABCMeta, abstractmethod

LINEFORMATS = "k-,r-,b-,g-,c-,m-,y-,k--,r--,b--,g--,c--,m--,y--,k:,r:,b:,g:,c:,m:,y:,k-.,r-.,b-.,g-.,c-.,m-.,y-."

def make_dir_path(path):
    p = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(p):
        os.makedirs(p)

def find_file_paths(searchpath, patterns):
    paths = []
    if searchpath.endswith("/-"): paths.append("-")
    else:
        for root, dirs, files in os.walk(searchpath):
            for name in files:
                found = False
                fpath = os.path.join(root, name)
                fbase = os.path.basename(fpath)
                for pattern in patterns:
                    if re.search(pattern, fbase): found = True
                if found: paths.append(fpath)
    return paths

def find_file_paths_pairs(searchpath, patterns_a, patterns_b):
    paths = []
    for root, dirs, files in os.walk(searchpath):
        for name in files:
            fpath = os.path.join(root, name)
            fbase = os.path.basename(fpath)

            paths_a = []
            found = False
            for pattern in patterns_a:
                if re.search(pattern, fbase):
                    found = True
            if found:
                paths_a.append(fpath)

            paths_b = []
            found = False
            for pattern in patterns_b:
                if re.search(pattern, fbase):
                    found = True
            if found:
                paths_b.append(fpath)

            if len(paths_a) > 0 or len(paths_b) > 0:
                paths.append((paths_a, paths_b))
    return paths

def find_path(binpath, defaultname, search_path=None):
    # find the path to tor
    if binpath is not None:
        binpath = os.path.abspath(os.path.expanduser(binpath))
    else:
        w = which(defaultname, search_path)
        if w is not None:
            binpath = os.path.abspath(os.path.expanduser(w))
        else:
            logging.error("You did not specify a path to a '{0}' binary, and one does not exist in your PATH".format(defaultname))
            return None
    # now make sure the path exists
    if os.path.exists(binpath):
        logging.info("Using '{0}' binary at {1}".format(defaultname, binpath))
    else:
        logging.error("Path to '{0}' binary does not exist: {1}".format(defaultname, binpath))
        return None
    # we found it and it exists
    return binpath

def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def which(program, search_path=None):
    if search_path is None:
        search_path = os.environ["PATH"]
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in search_path.split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

def timestamp_to_seconds(stamp):  # unix timestamp
    return float(stamp)

def date_to_string(date_object):
    if date_object is not None:
        return "{:04d}-{:02d}-{:02d}".format(date_object.year, date_object.month, date_object.day)
    else:
        return ""

def do_dates_match(date1, date2):
    year_matches = True if date1.year == date2.year else False
    month_matches = True if date1.month == date2.month else False
    day_matches = True if date1.day == date2.day else False
    if year_matches and month_matches and day_matches:
        return True
    else:
        return False

def find_ip_address_url(data):
    """
    Parses a string using a regular expression for identifying IPv4 addressses.
    If more than one IP address is found, only the first one is returned.
    If no IP address is found, the function returns None .

    :param data: string
    :returns: string
    """

    ip_address = None
    if data is not None and len(data) > 0:
        ip_list = re.findall(r'[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}', data)
        if ip_list is not None and len(ip_list) > 0:
            ip_address = ip_list[0]
    return ip_address

def find_ip_address_local():
    """
    Determines the local IP address of the host by opening a socket
    connection to an external address. In doing so, the address used by the
    host for initiating connections can be retrieved and then returned.

    :returns: string
    """

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 53))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address
 
def get_ip_address():
    """
    Determines the public IPv4 address of the vantage point using the
    check.torproject.org service. If it is not possible to reach the service,
    or to parse the result recieved, it will fall back to determining the local
    IP address used for outbound connections.

    :returns: string
    """
    ip_address = None
    try:
        data = urllib.request.urlopen('https://check.torproject.org/').read().decode('utf-8')
        ip_address = find_ip_address_url(data)
        if not ip_address:
            logging.error(
                "Unable to determine IP address from check.torproject.org. "
                "The site was successfully contacted but the result could "
                "not be parsed. Maybe the service is down? Falling back to "
                "finding your IP locally...")
            ip_address = find_ip_address_local()
    except IOError:
        logging.warning(
            "An IOError occured attempting to contact check.torproject.org. "
            "This will affect measurements unless your machine has a public "
            "IP address. Falling back to finding your IP locally...")
        ip_address = find_ip_address_local()
    return ip_address

def get_random_free_port():
    """
    Picks a random high port and checks its availability by opening a
    socket connection to localhost on this port. If this raises an exception
    the process is repeated until a free port is found.

    :returns: int
    """

    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = random.randint(10000, 60000)
        rc = s.connect_ex(('127.0.0.1', port))
        s.close()
        if rc != 0: # error connecting, port is available
            return port

class DataSource(object):
    def __init__(self, filename, compress=False):
        self.filename = filename
        self.compress = compress
        self.source = None

    def __iter__(self):
        if self.source is None:
            self.open()
        return self.source

    def __next__(self):
        return next(self.source) if self.source is not None else None

    def open(self):
        if self.source is None:
            if self.filename == '-':
                self.source = sys.stdin
            elif self.compress or self.filename.endswith(".xz"):
                self.compress = True
                self.source = lzma.open(self.filename, mode='rt')
            elif self.filename.endswith(".gz"):
                self.compress = True
                self.source = gzip.open(self.filename, 'rt')
            else:
                self.source = open(self.filename, 'rt')

    def get_file_handle(self):
        if self.source is None:
            self.open()
        return self.source

    def close(self):
        if self.source is not None: self.source.close()


class Writable(object, metaclass=ABCMeta):
    @abstractmethod
    def write(self, msg):
        pass

    @abstractmethod
    def close(self):
        pass

class FileWritable(Writable):

    def __init__(self, filename, do_compress=False, do_truncate=False):
        self.filename = filename
        self.do_compress = do_compress
        self.do_truncate = do_truncate
        self.file = None
        self.lock = Lock()

        if self.filename == '-':
            self.file = sys.stdout
        elif self.do_compress or self.filename.endswith(".xz"):
            self.do_compress = True
            if not self.filename.endswith(".xz"):
                self.filename += ".xz"

    def write(self, msg):
        self.lock.acquire()
        if self.file is None: self.__open_nolock()
        if self.file is not None: self.file.write(msg)
        self.lock.release()

    def open(self):
        self.lock.acquire()
        self.__open_nolock()
        self.lock.release()

    def __open_nolock(self):
        if self.do_compress:
            self.file = lzma.open(self.filename, mode='wt')
        else:
            self.file = open(self.filename, 'wt' if self.do_truncate else 'at', 1)

    def close(self):
        self.lock.acquire()
        self.__close_nolock()
        self.lock.release()

    def __close_nolock(self):
        if self.file is not None:
            self.file.close()
            self.file = None

    def rotate_file(self, filename_datetime=datetime.datetime.now()):
        self.lock.acquire()

        # build up the new filename with an embedded timestamp and ending in .gz
        base = os.path.basename(self.filename)
        base_noext = os.path.splitext(os.path.splitext(base)[0])[0]
        ts = filename_datetime.strftime("%Y-%m-%d_%H:%M:%S")
        new_base = base.replace(base_noext, "{0}_{1}".format(base_noext, ts))
        new_filename = self.filename.replace(base, "log_archive/{0}.gz".format(new_base))

        make_dir_path(os.path.dirname(new_filename))

        # close and copy the old file, then truncate and reopen the old file
        self.__close_nolock()
        with open(self.filename, 'rb') as f_in, gzip.open(new_filename, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        with open(self.filename, 'ab') as f_in:
            f_in.truncate(0)
        self.__open_nolock()

        self.lock.release()
        # return new file name so it can be processed if desired
        return new_filename

class MemoryWritable(Writable):

    def __init__(self):
        self.str_buffer = StringIO()

    def write(self, msg):
        self.str_buffer.write()

    def readline(self):
        return self.str_buffer.readline()

    def close(self):
        self.str_buffer.close()
