'''
  OnionPerf
  Authored by Rob Jansen, 2015
  Copyright 2015-2020 The Tor Project
  See LICENSE for licensing information
'''

import matplotlib; matplotlib.use('Agg')  # for systems without X11
from matplotlib.backends.backend_pdf import PdfPages
import time
from abc import abstractmethod, ABCMeta
import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import register_matplotlib_converters
import seaborn as sns
import datetime
import numpy as np

class Visualization(object, metaclass=ABCMeta):

    def __init__(self):
        self.datasets = []
        register_matplotlib_converters()

    def add_dataset(self, analyses, label):
        self.datasets.append((analyses, label))

    @abstractmethod
    def plot_all(self, output_prefix):
        pass

class TGenVisualization(Visualization):

    def plot_all(self, output_prefix):
        if len(self.datasets) > 0:
            prefix = output_prefix + '.' if output_prefix is not None else ''
            ts = time.strftime("%Y-%m-%d_%H:%M:%S")
            self.__extract_data_frame()
            self.data.to_csv("{0}onionperf.viz.{1}.csv".format(prefix, ts))
            sns.set_context("paper")
            self.page = PdfPages("{0}onionperf.viz.{1}.pdf".format(prefix, ts))
            self.__plot_firstbyte_ecdf()
            self.__plot_firstbyte_time()
            self.__plot_lastbyte_ecdf()
            self.__plot_lastbyte_box()
            self.__plot_lastbyte_bar()
            self.__plot_lastbyte_time()
            self.__plot_throughput_ecdf()
            self.__plot_downloads_count()
            self.__plot_errors_count()
            self.__plot_errors_time()
            self.page.close()

    def __extract_data_frame(self):
        streams = []
        for (analyses, label) in self.datasets:
            for analysis in analyses:
                for client in analysis.get_nodes():
                    tor_streams_by_source_port = {}
                    tor_streams = analysis.get_tor_streams(client)
                    for tor_stream in tor_streams.values():
                        if "source" in tor_stream and ":" in tor_stream["source"]:
                            source_port = tor_stream["source"].split(":")[1]
                            tor_streams_by_source_port.setdefault(source_port, []).append(tor_stream)
                    tor_circuits = analysis.get_tor_circuits(client)
                    tgen_streams = analysis.get_tgen_streams(client)
                    tgen_transfers = analysis.get_tgen_transfers(client)
                    while tgen_streams or tgen_transfers:
                        error_code = None
                        source_port = None
                        unix_ts_end = None
                        # Explanation of the math below for computing Mbps: For 1 MiB and 5 MiB
                        # downloads we can extract the number of seconds that have elapsed between
                        # receiving bytes 524,288 and 1,048,576, which is a total amount of 524,288
                        # bytes or 4,194,304 bits or 4.194304 megabits. We want the reciprocal of
                        # that value with unit megabits per second.
                        if tgen_streams:
                            stream_id, stream_data = tgen_streams.popitem()
                            stream = {"id": stream_id, "label": label,
                                      "filesize_bytes": int(stream_data["stream_info"]["recvsize"]),
                                      "error_code": None}
                            stream["server"] = "onion" if ".onion:" in stream_data["transport_info"]["remote"] else "public"
                            if "time_info" in stream_data:
                                s = stream_data["time_info"]
                                if "usecs-to-first-byte-recv" in s:
                                    stream["time_to_first_byte"] = float(s["usecs-to-first-byte-recv"])/1000000
                                if "usecs-to-last-byte-recv" in s:
                                    stream["time_to_last_byte"] = float(s["usecs-to-last-byte-recv"])/1000000
                            if "elapsed_seconds" in stream_data:
                                s = stream_data["elapsed_seconds"]
                                if stream_data["stream_info"]["recvsize"] == "5242880" and "0.2" in s["payload_progress_recv"]:
                                     stream["mbps"] = 4.194304 / (s["payload_progress_recv"]["0.2"] - s["payload_progress_recv"]["0.1"])
                            if "error" in stream_data["stream_info"] and stream_data["stream_info"]["error"] != "NONE":
                                error_code = stream_data["stream_info"]["error"]
                            if "local" in stream_data["transport_info"] and len(stream_data["transport_info"]["local"].split(":")) > 2:
                                source_port = stream_data["transport_info"]["local"].split(":")[2]
                            if "unix_ts_end" in stream_data:
                                unix_ts_end = stream_data["unix_ts_end"]
                            if "unix_ts_start" in stream_data:
                                stream["start"] = datetime.datetime.utcfromtimestamp(stream_data["unix_ts_start"])
                        elif tgen_transfers:
                            transfer_id, transfer_data = tgen_transfers.popitem()
                            stream = {"id": transfer_id, "label": label,
                                      "filesize_bytes": transfer_data["filesize_bytes"],
                                      "error_code": None}
                            stream["server"] = "onion" if ".onion:" in transfer_data["endpoint_remote"] else "public"
                            if "elapsed_seconds" in transfer_data:
                               s = transfer_data["elapsed_seconds"]
                               if "payload_progress" in s:
                                   if transfer_data["filesize_bytes"] == 1048576 and "1.0" in s["payload_progress"]:
                                       stream["mbps"] = 4.194304 / (s["payload_progress"]["1.0"] - s["payload_progress"]["0.5"])
                                   if transfer_data["filesize_bytes"] == 5242880 and "0.2" in s["payload_progress"]:
                                       stream["mbps"] = 4.194304 / (s["payload_progress"]["0.2"] - s["payload_progress"]["0.1"])
                               if "first_byte" in s:
                                   stream["time_to_first_byte"] = s["first_byte"]
                               if "last_byte" in s:
                                   stream["time_to_last_byte"] = s["last_byte"]
                            if "error_code" in transfer_data and transfer_data["error_code"] != "NONE":
                                error_code = transfer_data["error_code"]
                            if "endpoint_local" in transfer_data and len(transfer_data["endpoint_local"].split(":")) > 2:
                                source_port = transfer_data["endpoint_local"].split(":")[2]
                            if "unix_ts_end" in transfer_data:
                                unix_ts_end = transfer_data["unix_ts_end"]
                            if "unix_ts_start" in transfer_data:
                                stream["start"] = datetime.datetime.utcfromtimestamp(transfer_data["unix_ts_start"])
                        tor_stream = None
                        tor_circuit = None
                        if source_port and unix_ts_end:
                            if source_port not in tor_streams_by_source_port:
                                print("skipping")
                                continue
                            for s in tor_streams_by_source_port[source_port]:
                                if abs(unix_ts_end - s["unix_ts_end"]) < 150.0:
                                    tor_stream = s
                                    break
                        if tor_stream and "circuit_id" in tor_stream:
                            circuit_id = tor_stream["circuit_id"]
                            if str(circuit_id) in tor_circuits:
                                tor_circuit = tor_circuits[circuit_id]
                        if error_code:
                            if error_code == "PROXY":
                                error_code_parts = ["TOR"]
                            else:
                                error_code_parts = ["TGEN", error_code]
                            if tor_stream:
                                if "failure_reason_local" in tor_stream:
                                    error_code_parts.append(tor_stream["failure_reason_local"])
                                    if "failure_reason_remote" in tor_stream:
                                        error_code_parts.append(tor_stream["failure_reason_remote"])
                            stream["error_code"] = "/".join(error_code_parts)

                        if "filters" in analysis.json_db.keys() and analysis.json_db["filters"]["tor/circuits"]:
                           if tor_circuit and "filtered_out" not in tor_circuit.keys():
                               streams.append(stream)
                        else:
                           streams.append(stream)
        self.data = pd.DataFrame.from_records(streams, index="id")

    def __plot_firstbyte_ecdf(self):
        for server in self.data["server"].unique():
            self.__draw_ecdf(x="time_to_first_byte", hue="label", hue_name="Data set",
                             data=self.data[self.data["server"] == server],
                             title="Time to download first byte from {0} service".format(server),
                             xlabel="Download time (s)", ylabel="Cumulative Fraction")

    def __plot_firstbyte_time(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_timeplot(x="start", y="time_to_first_byte", hue="label", hue_name="Data set",
                                     data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                     title="Time to download first of {0} bytes from {1} service over time".format(bytes, server),
                                     xlabel="Download start time", ylabel="Download time (s)")

    def __plot_lastbyte_ecdf(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_ecdf(x="time_to_last_byte", hue="label", hue_name="Data set",
                                 data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                 title="Time to download last of {0} bytes from {1} service".format(bytes, server),
                                 xlabel="Download time (s)", ylabel="Cumulative Fraction")

    def __plot_lastbyte_box(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_boxplot(x="label", y="time_to_last_byte",
                                    data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                    title="Time to download last of {0} bytes from {1} service".format(bytes, server),
                                    xlabel="Data set", ylabel="Download time (s)")

    def __plot_lastbyte_bar(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_barplot(x="label", y="time_to_last_byte",
                                    data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                    title="Mean time to download last of {0} bytes from {1} service".format(bytes, server),
                                    xlabel="Data set", ylabel="Downloads time (s)")

    def __plot_lastbyte_time(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_timeplot(x="start", y="time_to_last_byte", hue="label", hue_name="Data set",
                                     data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                     title="Time to download last of {0} bytes from {1} service over time".format(bytes, server),
                                     xlabel="Download start time", ylabel="Download time (s)")

    def __plot_throughput_ecdf(self):
        for server in self.data["server"].unique():
            self.__draw_ecdf(x="mbps", hue="label", hue_name="Data set",
                             data=self.data[self.data["server"] == server],
                             title="Throughput when downloading from {0} server".format(server),
                             xlabel="Throughput (Mbps)", ylabel="Cumulative Fraction")

    def __plot_downloads_count(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_countplot(x="label",
                                     data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                     xlabel="Data set", ylabel="Downloads completed (#)",
                                     title="Number of downloads of {0} bytes completed from {1} service".format(bytes, server))

    def __plot_errors_count(self):
        for server in self.data["server"].unique():
            if self.data[self.data["server"] == server]["error_code"].count() > 0:
                self.__draw_countplot(x="error_code", hue="label", hue_name="Data set",
                                      data=self.data[self.data["server"] == server],
                                      xlabel="Error code", ylabel="Downloads failed (#)",
                                      title="Number of downloads failed from {0} service".format(server))

    def __plot_errors_time(self):
        for server in self.data["server"].unique():
            if self.data[self.data["server"] == server]["error_code"].count() > 0:
                self.__draw_stripplot(x="start", y="error_code", hue="label", hue_name="Data set",
                                     data=self.data[self.data["server"] == server],
                                     xlabel="Download start time", ylabel="Error code",
                                     title="Downloads failed over time from {0} service".format(server))

    def __draw_ecdf(self, x, hue, hue_name, data, title, xlabel, ylabel):
        data = data.dropna(subset=[x])
        p0 = data[x].quantile(q=0.0, interpolation="lower")
        p99 = data[x].quantile(q=0.99, interpolation="higher")
        ranks = data.groupby(hue)[x].rank(pct=True)
        ranks.name = "rank_pct"
        result = pd.concat([data[[hue, x]], ranks], axis=1)
        result = result.append(pd.DataFrame({hue: data[hue].unique(),
                       x: p0 - (p99 - p0) * 0.05, "rank_pct": 0.0}),
                       ignore_index=True, sort=False)
        result = result.append(pd.DataFrame({hue: data[hue].unique(),
                       x: p99 + (p99 - p0) * 0.05, "rank_pct": 1.0}),
                       ignore_index=True, sort=False)
        result = result.rename(columns={hue: hue_name})
        plt.figure()
        g = sns.lineplot(data=result, x=x, y="rank_pct",
                         hue=hue_name, drawstyle="steps-post")
        g.set(title=title, xlabel=xlabel, ylabel=ylabel,
              xlim=(p0 - (p99 - p0) * 0.03, p99 + (p99 - p0) * 0.03))
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_timeplot(self, x, y, hue, hue_name, data, title, xlabel, ylabel):
        plt.figure()
        data = data.dropna(subset=[y])
        data = data.rename(columns={hue: hue_name})
        xmin = data[x].min()
        xmax = data[x].max()
        ymax = data[y].max()
        g = sns.scatterplot(data=data, x=x, y=y, hue=hue_name, alpha=0.5)
        g.set(title=title, xlabel=xlabel, ylabel=ylabel,
              xlim=(xmin - 0.03 * (xmax - xmin), xmax + 0.03 * (xmax - xmin)),
              ylim=(-0.05 * ymax, ymax * 1.05))
        plt.xticks(rotation=10)
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_boxplot(self, x, y, data, title, xlabel, ylabel):
        plt.figure()
        data = data.dropna(subset=[y])
        g = sns.boxplot(data=data, x=x, y=y, sym="")
        g.set(title=title, xlabel=xlabel, ylabel=ylabel, ylim=(0, None))
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_barplot(self, x, y, data, title, xlabel, ylabel):
        plt.figure()
        data = data.dropna(subset=[y])
        g = sns.barplot(data=data, x=x, y=y, ci=None)
        g.set(title=title, xlabel=xlabel, ylabel=ylabel)
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_countplot(self, x, data, title, xlabel, ylabel, hue=None, hue_name=None):
        plt.figure()
        if hue is not None:
            data = data.rename(columns={hue: hue_name})
        g = sns.countplot(data=data.dropna(subset=[x]), x=x, hue=hue_name)
        g.set(xlabel=xlabel, ylabel=ylabel, title=title)
        sns.despine()
        self.page.savefig()
        plt.close()

    def __draw_stripplot(self, x, y, hue, hue_name, data, title, xlabel, ylabel):
        plt.figure()
        data = data.rename(columns={hue: hue_name})
        xmin = data[x].min()
        xmax = data[x].max()
        data = data.dropna(subset=[y])
        g = sns.stripplot(data=data, x=x, y=y, hue=hue_name)
        g.set(title=title, xlabel=xlabel, ylabel=ylabel,
              xlim=(xmin - 0.03 * (xmax - xmin), xmax + 0.03 * (xmax - xmin)))
        plt.xticks(rotation=10)
        plt.yticks(rotation=80)
        sns.despine()
        self.page.savefig()
        plt.close()
