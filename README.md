# OnionPerf
 * [Overview](#overview)
    + [What does OnionPerf do?](#what-does-onionperf-do-)
    + [What does OnionPerf *not* do?](#what-does-onionperf--not--do-)
  * [Installation](#installation)
    + [Tor](#tor)
    + [TGen](#tgen)
    + [OnionPerf](#onionperf-1)
  * [Measurement](#measurement)
    + [Starting and stopping measurements](#starting-and-stopping-measurements)
    + [Output directories and files](#output-directories-and-files)
    + [Changing Tor configurations](#changing-tor-configurations)
    + [Changing the TGen traffic model](#changing-the-tgen-traffic-model)
    + [Sharing measurement results](#sharing-measurement-results)
    + [Troubleshooting](#troubleshooting)
  * [Analysis](#analysis)
    + [Analyzing measurement results](#analyzing-measurement-results)
    + [Visualizing measurement results](#visualizing-measurement-results)
    + [Interpreting the PDF output format](#interpreting-the-pdf-output-format)
    + [Interpreting the CSV output format](#interpreting-the-csv-output-format)
  * [Contributing](#contributing)

## Overview

### What does OnionPerf do?

OnionPerf measures performance of bulk file downloads over Tor. Together with its predecessor, Torperf, OnionPerf has been used to measure long-term performance trends in the Tor network since 2009. It is also being used to perform short-term performance experiments to compare different Tor configurations or implementations.

OnionPerf uses multiple processes and threads to download random data through Tor while tracking the performance of those downloads. The data is served and fetched on localhost using two TGen (traffic generator) processes, and is transferred through Tor using Tor client processes and an ephemeral Tor onion service. Tor control information and TGen performance statistics are logged to disk and analyzed once per day to produce a JSON analysis file that can later be used to visualize changes in Tor client performance over time.

### What does OnionPerf *not* do?

OnionPerf does not attempt to simulate complex traffic patterns like a web-browsing user or a voice-chatting user. It measures a very specific user model: a bulk 5 MiB file download over Tor.

OnionPerf does not interfere with how Tor selects paths and builds circuits, other than setting configuration values as specified by the user. As a result it cannot be used to measure specific relays nor to scan the entire Tor network.

## Installation

OnionPerf has several dependencies in order to perform measurements or analyze and visualize measurement results. These dependencies include Tor, TGen (traffic generator), and a few Python packages.

The following description was written with a Debian system in mind but should be transferable to other Linux distributions and possibly even other operating systems.

### Tor

OnionPerf relies on the `tor` binary to start a Tor client process on the client side and a server side process to host onion services.

The easiest way to satisfy this dependency is to install the `tor` package, which puts the `tor` binary into the `PATH` where OnionPerf will find it. Optionally, systemd can be instructed to make sure that `tor` is never started as a service:

```shell
sudo apt install tor
sudo systemctl stop tor.service
sudo systemctl mask tor.service
```

Alternatively, Tor can be built from source:

```shell
sudo apt install automake build-essential libevent-dev libssl-dev zlib1g-dev
cd ~/
git clone https://git.torproject.org/tor.git
cd tor/
./autogen.sh
./configure --disable-asciidoc
make
```

In this case the resulting `tor` binary can be found in `~/tor/src/app/tor` and needs to be passed to OnionPerf's `--tor` parameter when doing measurements.

### TGen

OnionPerf uses TGen to generate traffic on client and server side for its measurements. Installing dependencies, cloning TGen to a subdirectory in the user's home directory, checking out version 0.0.1, and building TGen is done as follows:

```shell
sudo apt install cmake libglib2.0-dev libigraph0-dev make
cd ~/
git clone https://github.com/shadow/tgen.git
cd tgen/
git checkout -b v0.0.1 v0.0.1
mkdir build
cd build/
cmake ..
make
```

The TGen binary will be contained in `~/tgen/build/tgen`, which is also the path that needs to be passed to OnionPerf's `--tgen` parameter when doing measurements.

### OnionPerf

OnionPerf is written in Python 3. The following instructions assume that a Python virtual environment is being used, even though installation is also possible without that.

The virtual environment is created, activated, and tested using:

```shell
sudo apt install python3-venv
cd ~/
python3 -m venv venv
source venv/bin/activate
which python3
```

The last command should output something like `~/venv/bin/python3` as the path to the `python3` binary used in the virtual environment.

The next step is to clone the OnionPerf repository and install its requirements:

```shell
git clone https://git.torproject.org/onionperf.git
pip3 install --no-cache -r onionperf/requirements.txt
```

The final step is to install OnionPerf and print out the usage information to see if the installation was successful:

```shell
cd onionperf/
python3 setup.py install
cd ~/
onionperf --help
```

The virtual environment is deactivated with the following command:

```shell
deactivate
```

However, in order to perform measurements or analyses, the virtual environment needs to be activated first. This will ensure all the paths are found.


## Measurement

Performing measurements with OnionPerf is done by starting an `onionperf` process that itself starts several other processes and keeps running until it is interrupted by the user. During this time it performs new measurements every 5 minutes and logs measurement results to files.

Ideally, OnionPerf is run detached from the terminal session using tmux, systemd, or similar, except for the most simple test runs. The specifics for using these tools are not covered in this document.

### Starting and stopping measurements

The most trivial configuration is to measure onion services only. In that case, OnionPerf runs without needing any additional configuration. For direct measurements via exit nodes, firewall rules or port forwarding may be required to allow inbound connections to the TGen server.

Starting these measurements is as simple as:

```shell
cd ~/
onionperf measure --onion-only --tgen ~/tgen/build/tgen --tor ~/tor/src/app/tor
```

OnionPerf logs its main output on the console and then waits indefinitely until the user presses `CTRL-C` for graceful shutdown. It does not, however, print out measurement results or progress on the console, just a heartbeat message every hour.

OnionPerf's `measure` mode has several command-line parameters for customizing measurements. See the following command for usage information:

```shell
onionperf measure --help
```

### Output directories and files

OnionPerf writes several files to two subdirectories in the current working directory while doing measurements:

- `onionperf-data/` is the main directory containing measurement results.
  - `htdocs/` is created at the first UTC midnight after starting and contains measurement analysis result files that can be shared via a local web server.
    - `$date.onionperf.analysis.json.xz` contains extracted metrics in OnionPerf's analysis JSON format.
    - `index.xml` contains a directory index with file names, sizes, last-modified times, and SHA-256 digests.
  - `tgen-client/` is the working directory of the client-side `tgen` process.
    - `log_archive/` is created at the first UTC midnight after starting and contains compressed log files from previous UTC days.
    - `onionperf.tgen.log` is the current log file.
    - `tgen.graphml.xml` is the traffic model file generated by OnionPerf and used by TGen.
  - `tgen-server/` is the working directory of the server-side `tgen` process with the same structure as `tgen-client/`.
  - `tor-client/` is the working directory of the client-side `tor` process.
    - `log_archive/` is created at the first UTC midnight after starting and contains compressed log files from previous UTC days.
    - `onionperf.tor.log` is the current log file containing log messages by the client-side `tor` process.
    - `onionperf.torctl.log` is the current log file containing controller events obtained by OnionPerf connecting to the control port of the client-side `tor` process.
    - `[...]` (several other files written by the client-side `tor` process to its data directory)
  - `tor-server/` is the working directory of the server-side `tor` process with the same structure as `tor-client/`.
- `onionperf-private/` contains private keys of the onion services used for measurements and potentially other files that are not meant to be published together with measurement results.

### Changing Tor configurations

OnionPerf generates Tor configurations for both client-side and server-side `tor` processes. There are a few ways to add Tor configuration lines:

- If the `BASETORRC` environment variable is set, OnionPerf appends its own configuration options to the contents of that variable. Example:

  ```shell
  BASETORRC=$'Option1 Foo\nOption2 Bar\n' onionperf ...
  ```

- If the `--torclient-conf-file`  and/or  `--torserver-conf-file`  command-line arguments are given, the contents of those files are appended to the configurations of client-side and/or server-side `tor` process.
- If the `--additional-client-conf` command-line argument is given, its content is appended to the configuration of the client-side  `tor`  process.

These options can be used, for example, to change the default measurement setup use bridges (or pluggable transports) by passing bridge addresses as additional client configuration lines as follows:

```shell
onionperf measure --additional-client-conf="UseBridges 1\nBridge 72.14.177.231:9001 AC0AD4107545D4AF2A595BC586255DEA70AF119D\nBridge 195.91.239.8:9001 BA83F62551545655BBEBBFF353A45438D73FD45A\nBridge 148.63.111.136:35577 768C8F8313FF9FF8BBC915898343BC8B238F3770"
```

### Changing the TGen traffic model

OnionPerf is a relatively simple tool that can be adapted to do more complex measurements beyond what can be configured on the command line.

For example, the hard-coded traffic model generated by OnionPerf and executed by the TGen processes is to send a small request from client to server and receive a relatively large response of 5 MiB of random data back. This model can be changed by editing `~/onionperf/onionperf/model.py`, rebuilding, and restarting measurements. For specifics, see the [TGen
documentation](https://github.com/shadow/tgen/blob/master/doc/TGen-Overview.md)
and [TGen traffic model examples](https://github.com/shadow/tgen/blob/master/tools/scripts/generate_tgen_config.py).

### Sharing measurement results

Measurement results can be further analyzed and visualized on the measuring host. But in many cases it's more convenient to do analysis and visualization on another host, also to compare measurements from different hosts to each other.

There are at least two common ways of sharing measurement results:

1. Creating a tarball of the `onionperf-data/` directory; and
2. Using a local web server to serve the contents of the `onionperf-data/` directory.

The details of doing either of these two methods are not covered in this document.

### Troubleshooting

If anything goes wrong while doing measurements, OnionPerf typically informs the user in its console output. This is also the first place to look for investigating any issues.

The second place would be to check the log files in `~/onionperf-data/tgen-client/` or `~/onionperf-data/tor-client/`.

The most common configuration problems are probably related to firewall and port forwarding for doing direct (non onion-service) measurements. The specifics for setting up the firewall are out of scope for this document.

Another class of common issues of long-running measurements is that one of the `tgen` or `tor` processes dies for reasons or hints (hopefully) to be found in their respective log files.

In order to avoid extended downtimes it is recommended to deploy monitoring tools that check whether measurement results produced by OnionPerf are fresh. The specifics are, again, out of scope for this document.

## Analysis

The next steps after performing measurements are to analyze and optionally visualize measurement results.

### Analyzing measurement results

While performing measurements, OnionPerf writes quite verbose log files to disk. The first step in the analysis is to parse these log files, extract key metrics, and write smaller and more structured measurement results to disk. This is done with OnionPerf's `analyze` mode.

For example, the following command analyzes current log files of a running (or stopped) OnionPerf instance (as opposed to log-rotated, compressed files from previous days):

```shell
onionperf analyze --tgen ~/onionperf-data/tgen-client/onionperf.tgen.log --torctl ~/onionperf-data/tor-client/onionperf.torctl.log
```

The output analysis file is written to `onionperf.analysis.json.xz` in the current working directory. The file format is described in more detail in `README_JSON.md`.

The same analysis files are written automatically as part of ongoing measurements once per day at UTC midnight and can be found in `onionperf-data/htdocs/`.

OnionPerf's `analyze` mode has several command-line parameters for customizing the analysis step:

```shell
onionperf analyze --help
```

### Visualizing measurement results

Step two in the analysis is to process analysis files with OnionPerf's `visualize` mode which produces CSV and PDF files as output.

For example, the analysis file produced above can be visualized with the following command, using "Test Measurements" as label for the data set:

```shell
onionperf visualize --data onionperf.analysis.json.xz "Test Measurements"
```

As a result, two files are written to the current working directory:

- `onionperf.viz.$datetime.csv` contains visualized data in a CSV file format; and
- `onionperf.viz.$datetime.pdf` contains visualizations in a PDF file format.

Similar to the other modes, OnionPerf's `visualize` mode has command-line parameters for customizing the visualization step:

```shell
onionperf visualize --help
```

### Interpreting the PDF output format

The PDF output file contains visualizations of the following metrics:

- Time to download first (last) byte, which is defined as elapsed time between starting a measurement and receiving the first (last) byte of the HTTP response.
- Throughput, which is computed from the elapsed time between receiving 0.5 and 1 MiB of the response.
- Number of downloads.
- Number and type of failures.

### Interpreting the CSV output format

The CSV output file contains the same data that is visualized in the PDF file. It contains the following columns:

- `transfer_id` is the identifier used in the TGen client logs which may be useful to look up more details about a specific measurement.
- `error_code`  is an optional error code if a measurement did not succeed.
- `filesize_bytes` is the requested file size in bytes.
- `label` is the data set label as given in the `--data/-d` parameter to the `visualize` mode.
- `server` is set to either `onion` for onion service measurements or `public` for direct measurements.
- `start` is the measurement start time.
- `time_to_first_byte` is the time in seconds (with microsecond precision) to download the first byte.
- `time_to_last_byte` is the time in seconds (with microsecond precision) to download the last byte.

## Contributing

The OnionPerf code is developed at https://gitlab.torproject.org/tpo/metrics/onionperf.

Contributions to OnionPerf are welcome and encouraged!

