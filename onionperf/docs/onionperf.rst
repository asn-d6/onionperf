
What is OnionPerf?
==================
OnionPerf is a utility to track Tor and Onion service performance.

OnionPerf uses multiple processes and threads to download random data through
Tor while tracking the performance of those downloads. The data is served and
fetched on localhost using two TGen (traffic generator) processes, and is
transferred through Tor using Tor client processes and an ephemeral Tor Onion
service. Tor control information and TGen performance statistics are logged to
disk, analyzed once per day to produce a json stats database and files that can
feed into Torperf, and can later be used to visualize changes in Tor client
performance over time.

Installation
============
OnionPerf depends on traffic generator TGen. Instructions for TGen installation can also be found at https://github.com/shadow/tgen.
To install it:

Tgen
----

1. Install dependencies
::

 apt install cmake make build-essential gcc libigraph0-dev libglib2.0-dev

2. Clone repositories
::

 git clone https://github.com/shadow/tgen.git

3. Build and install
::

 mkdir build
 cd build
 cmake .. -DCMAKE_INSTALL_PREFIX=/home/$USER/.local
 make
 ln -s build/tgen /usr/bin/tgen


OnionPerf
---------
Once TGen is installed, follow these instructions to install OnionPerf:

1. Clone repositories
::

 apt install git
 git clone https://git.torproject.org/onionperf.git

2. Install dependencies
::

 apt install tor libxml2-dev python-dev python-lxml python-networkx python-scipy python-matplotlib python-numpy python-netifaces python-ipaddress

Ensure stem is the latest version for v3 Onion services to work, this can be installed from backports:
::

 echo 'deb http://deb.debian.org/debian stretch-backports main' >> /etc/apt/sources.list
 apt update
 apt-get -t stretch-backports install python-stem

3. Install OnionPerf
::

 cd onionperf
 sudo python setup.py install

4. Run an OnionPerf test measurement
::
 
  onionperf measure --oneshot --onion-only

Watch out for any projects in the log. The output of the measurement should look similar to the following:
::

 2019-03-05 17:57:02 1551805022.995195 [onionperf] [INFO] Using 'tor' binary at /usr/bin/tor
 2019-03-05 17:57:02 1551805022.995359 [onionperf] [INFO] Using 'tgen' binary at /home/ana/Work/shadow/src/plugin/shadow-plugin-tgen/build/tgen
 2019-03-05 17:57:03 1551805023.005096 [onionperf] [INFO] Bootstrapping started...
 2019-03-05 17:57:03 1551805023.005265 [onionperf] [INFO] Log files for the client and server processes will be placed in /home/ana/onionperf-data
 2019-03-05 17:57:03 1551805023.005340 [onionperf] [INFO] Starting TGen server process on port 8080...
 2019-03-05 17:57:03 1551805023.012559 [onionperf] [INFO] TGen server running at 0.0.0.0:8080
 2019-03-05 17:57:03 1551805023.012727 [onionperf] [INFO] Logging TGen server process output to /home/ana/onionperf-data/tgen-server/onionperf.tgen.log
 2019-03-05 17:57:03 1551805023.013463 [onionperf] [INFO] Starting Tor server process with ControlPort=26984, SocksPort=17674...
 2019-03-05 17:57:03 1551805023.016020 [onionperf] [INFO] Logging Tor server process output to /home/ana/onionperf-data/tor-server/onionperf.tor.log
 2019-03-05 17:57:18 1551805038.183236 [onionperf] [INFO] Logging Tor server control port monitor output to /home/ana/onionperf-data/tor-server/onionperf.torctl.log
 2019-03-05 17:57:53 1551805073.334130 [onionperf] [INFO] Creating ephemeral hidden service...
 2019-03-05 17:57:55 1551805075.847095 [onionperf] [INFO] Ephemeral hidden service is available at p3d2xcwjevqkiwtyejjbjxwadp5ces7v4k4hhrsheqwbbokuismkiyad.onion
 2019-03-05 17:57:55 1551805075.851187 [onionperf] [INFO] Starting Tor client process with ControlPort=18843, SocksPort=18397...
 2019-03-05 17:57:55 1551805075.851770 [onionperf] [INFO] Logging Tor client process output to /home/ana/onionperf-data/tor-client/onionperf.tor.log
 2019-03-05 17:58:49 1551805129.399007 [onionperf] [INFO] Logging Tor client control port monitor output to /home/ana/onionperf-data/tor-client/onionperf.torctl.log
 2019-03-05 17:58:52 1551805132.401905 [onionperf] [INFO] Starting TGen client process on port 14785...
 2019-03-05 17:58:52 1551805132.408057 [onionperf] [INFO] Logging TGen client process output to /home/ana/onionperf-data/tgen-client/onionperf.tgen.log
 2019-03-05 17:58:52 1551805132.414970 [onionperf] [INFO] Bootstrapping finished, entering heartbeat loop
 2019-03-05 17:58:53 1551805133.416607 [onionperf] [INFO] Onionperf is running in Oneshot mode. It will download a 5M file and shut down gracefully...
 2019-03-05 17:59:24 1551805164.697978 [onionperf] [INFO] Onionperf has downloaded a 5M file in oneshot mode, and will now shut down.
 2019-03-05 17:59:24 1551805164.698091 [onionperf] [INFO] Cleaning up child processes now...
 2019-03-05 17:59:24 1551805164.707111 [onionperf] [INFO] Joining tgen_server_watchdog thread...
 2019-03-05 17:59:25 1551805165.094310 [onionperf] [INFO] Joining tor_server_watchdog thread...
 2019-03-05 17:59:25 1551805165.094690 [onionperf] [INFO] Joining torctl_server_helper thread...
 2019-03-05 17:59:25 1551805165.113840 [onionperf] [INFO] command '/home/ana/Work/shadow/src/plugin/shadow-plugin-tgen/build/tgen /home/ana/onionperf-data/tgen-client/tgen.graphml.xml' finished as expected
 2019-03-05 17:59:25 1551805165.493231 [onionperf] [INFO] Joining tor_client_watchdog thread...
 2019-03-05 17:59:25 1551805165.493633 [onionperf] [INFO] Joining torctl_client_helper thread...
 2019-03-05 17:59:25 1551805165.538060 [onionperf] [INFO] Joining tgen_client_watchdog thread...
 2019-03-05 17:59:25 1551805165.538464 [onionperf] [INFO] Joining logrotate thread...
 2019-03-05 17:59:26 1551805166.539878 [onionperf] [INFO] Child processes terminated
 2019-03-05 17:59:26 1551805166.540305 [onionperf] [INFO] Child process cleanup complete!
 2019-03-05 17:59:26 1551805166.540603 [onionperf] [INFO] Exiting
 
Deployment
==========

Deployment options
------------------
There are
various options available for deployment of measurements. These options can be
passed to OnionPerf via command line arguments, as follows:

::

 --onion-only  

Only download files through an Onion service (default: disabled) ::

 --inet-only 

Only download files through the Internet (default: disabled) ::

 --single-onion

Use a single Onion service, which uses a direct circuit between the Onion
service and the introduction and rendezvous point. ::

 --torclient-conf-file FILE

Download files using specified configuration file for the Tor client (default: disabled) ::

 --torserver-conf-file FILE

In addition to specifying configuration files, you can pass newline-separated
Tor configuration options to the Tor process by adding them to the
:code:`BASETORRC` environment variable. These options are prepended to all other
configuration options.  Here is an example which prepends the options
:code:`Option1 Foo` and :code:`Option2 Bar` to Tor's configuration file: ::

 BASETORRC=$'Option1 Foo\nOption2 Bar' onionperf ...

Download files using specified configuration file for the Tor server  (default: disabled) ::

 --additional-client-conf STRING

Download files using specified configuration lines (default: disabled)

By default, OnionPerf downloads files using both the Internet and Onion services, using a v3 Onion address.
It uses publicly available relays, but by specifying additional configuration files it can be configured to run
on test Tor networks, or using bridges with or without pluggable transports.
::

 --oneshot 

Only download a 5M file and then shut down gracefully (default: disabled)

By default, OnionPerf runs continuously and appends measurement information to
log files as they happen. At midnight, the log files are rotated and the measurement continues.
A oneshot measurement will run only until one successful download has completed.

::

 --nickname STRING  

The 'SOURCE' STRING to use in stats files produced by OnionPerf (default: hostname of the current machine)
::

 --prefix PATH

A directory PATH prefix where OnionPerf will run (default: current directory)
::

 --tor PATH

A file PATH to a Tor binary (default: looks in $PATH)
::

 --tgen PATH 

A file PATH to a TGen binary (default: looks in $PATH)

Example vanilla Tor deployment
------------------------------

The following command will download files continuously using a Tor client through Onion service version 3 and via the Internet until it is stopped:
::

 onionperf --measure 


Example vanilla bridge deployment
---------------------------------
The following command will download files continuously using a Tor client through Onion service version 3 and via the Internet until it is stopped.
The Tor client will always pick one of the bridges provided in this configuration to be the first hop in the circuits it builds:

::

 onionperf --measure --additional-client-conf="UseBridges 1
 Bridge 72.14.177.231:9001 AC0AD4107545D4AF2A595BC586255DEA70AF119D
 Bridge 195.91.239.8:9001 BA83F62551545655BBEBBFF353A45438D73FD45A
 Bridge 148.63.111.136:35577 768C8F8313FF9FF8BBC915898343BC8B238F3770"

Note: a new line must be added at the end of each configuration directive. 

A second way of passing this configuration to OnionPerf would be to create a file called tor_conf in a directory of your choice, containing the lines:
::

 UseBridges 1
 Bridge 148.63.111.136:35577 768C8F8313FF9FF8BBC915898343BC8B238F3770
 Bridge 195.91.239.8:9001 BA83F62551545655BBEBBFF353A45438D73FD45A
 Bridge 148.63.111.136:35577 768C8F8313FF9FF8BBC915898343BC8B238F3770

This file is then passed to the client configurator in OnionPerf:

::

 onionperf --measure --torclient-config-file=/path/to/tor_conf 

If we want to use vanilla Tor for the client, but download the files through an Onion service accessible via a bridge, the same configuration file containing the bridge lines can be passed to the server:

::

 onionperf --measure --torserver-config-file=/path/to/tor_conf 


Note that bridge lines for configuration can be downloaded from https://bridges.torproject.org.

Example bridge with Pluggable Transport deployment
--------------------------------------------------
Similarly to the above, the Tor client can use Pluggable Transports (PT) with bridges. Here we present examples for meek and obfs4proxy.

You must have the meek and/or obfs4proxy binaries installed. The binaries can
be obtained by downloading the latest version of Tor browser bundle, or they
can be installed from source.  In the example file that follows, directive "ClientTransportPlugin"
needs to point to the path of the binary corresponding to the wanted PT. Finally, both meek and
obfs4 enabled bridges can be obtained from the bridge database.

Example file torrc1:
::

 UseBridges 1
 # Example meek bridge line - meek bridge lines can be downloaded from https://bridges.torproject.org
 Bridge meek 0.0.2.0:1 url=https://at-b2.erg.abdn.ac.uk
 # meek configuration
 ClientTransportPlugin meek exec /usr/bin/meek

Example file torrc2:
::

 # Example obfs4 bridge - meek bridge lines can be downloaded from bridges.torproject.org
 Bridge obfs4 137.50.19.19:5001 AE77C35CAC66C2F207319939029D6D22945BDA84 cert=kwpT6sHRa80CnoSCGzelo2wl4RU7cC+mjBCihj2gAJAnvNyTWD3Pk9Ae05+fGpiGzHleOw iat-mode=0
 # obfs4 configuration
 ClientTransportPlugin obfs2,obfs3,obfs4,scramblesuit exec /usr/bin/obfs4proxy

Then, the configuration files containing the required bridge and PT lines can be passed to the either the Tor server or client:

::

 onionperf --measure --torserver-config-file=/path/to/torrc1  --torclient-config-file=/path/to/torrc2

In this example, the Onion services uses the obfs4 bridge configured in file torrc2 to connect to the Tor network, while the client uses the meek bridge configured in file torrc1 to connect to the Tor network.
