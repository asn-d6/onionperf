# Changes in version 0.7 - 2020-??-??

 - Remove the `onionperf measure --oneshot` switch and replace it with
   new switches `--tgen-pause-initial`, `--tgen-pause-between`,
   `--tgen-transfer-size`, and `--tgen-num-transfers ` to further
   configure the generated TGen model.

# Changes in version 0.6 - 2020-??-??

 - Update to TGen 1.0.0, use TGenTools for parsing TGen log files, and
   update analysis results file version to 3.0. Implements #33974.
 - Remove summaries from analysis results files, and remove the
   `onionperf analyze -s/--do-simple-parse` switch. Implements #40005.
 - Add JSON schema for analysis results file format 3.0. Implements
   #40003.
 - Correctly compute the start time of failed streams as part of the
   update to TGen and TGenTools 1.0.0. Fixes #30362.
 - Refine error codes shown in visualizations into TOR or TGEN errors.
   Implements #34218.

# Changes in version 0.5 - 2020-07-02

 - Add new graph showing the cumulative distribution function of
   throughput in Mbps. Implements #33257.
 - Improve `README.md` to make it more useful to developers and
   researchers. Implements #40001.
 - Always include the `error_code` column in visualization CSV output,
   regardless of whether data contains measurements with an error code
   or not. Fixes #40004.
 - Write generated torrc files to disk for debugging purposes.
   Implements #40002.

# Changes in version 0.4 - 2020-06-16

 - Include all measurements when analyzing log files at midnight as
   part of `onionperf measure`, not just the ones from the day before.
   Also add `onionperf analyze -x/--date-prefix` switch to prepend a
   given date string to an analysis results file. Fixes #29369.
 - Add `size`, `last_modified`, and `sha256` fields to index.xml.
   Implements #29365.
 - Add support for single onion services using the switch `onionperf
   measure -s/--single-onion`. Implements #29368.
 - Remove unused `onionperf measure --traffic-model` switch.
   Implements #29370.
 - Make `onionperf measure -o/--onion-only` and `onionperf measure
   -i/--inet-only` switches mutually exclusive. Fixes #34316.
 - Accept one or more paths to analysis results files or directories
   of such files per dataset in `onionperf visualize -d/--data` to
   include all contained measurements in a dataset. Implements #34191.

# Changes in version 0.3 - 2020-05-30

 - Automatically compress logs when rotating them. Fixes #33396.
 - Update to Python 3. Implements #29367.
 - Integrate reprocessing mode into analysis mode. Implements #34142.
 - Record download times of smaller file sizes from partial completion
   times. Implements #26673.
 - Stop generating .tpf files. Implements #34141.
 - Update analysis results file version to 2.0. Implements #34224.
 - Export visualized data to a CSV file. Implements #33258.
 - Remove version 2 onion service support. Implements #33434.
 - Reduce timeout and stallout values. Implements #34024.
 - Remove 50 KiB and 1 MiB downloads. Implements #34023.
 - Remove existing Tor control log visualizations. Implements #34214.
 - Update to Networkx version 2.4. Fixes #34298.
 - Update time to first/last byte definitions to include the time 
   between starting a measurement and receiving the first/last byte. 
   Implements #34215.
 - Update `requirements.txt` to actual requirements, and switch from 
   distutils to setuptools. Fixes #30586.
 - Split visualizations into public and onion service measurements. 
   Fixes #34216.

# Changes from before 2020-04

 - Changes made before 2020-04 are not listed here. See `git log` for
   details.

