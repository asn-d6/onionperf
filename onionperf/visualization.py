'''
  OnionPerf
  Authored by Rob Jansen, 2015
  See LICENSE for licensing information
'''

import matplotlib; matplotlib.use('Agg')  # for systems without X11
from matplotlib.backends.backend_pdf import PdfPages
import time
from abc import abstractmethod, ABCMeta
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import datetime
import numpy as np

class Visualization(object, metaclass=ABCMeta):

    def __init__(self):
        self.datasets = []

    def add_dataset(self, analysis, label):
        self.datasets.append((analysis, label))

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
            self.__plot_downloads_count()
            self.__plot_errors_count()
            self.__plot_errors_time()
            self.page.close()

    def __extract_data_frame(self):
        transfers = []
        for (analysis, label) in self.datasets:
            for client in analysis.get_nodes():
                tgen_transfers = analysis.get_tgen_transfers(client)
                for transfer_id, transfer_data in tgen_transfers.items():
                    transfer = {"transfer_id": transfer_id, "label": label,
                                "filesize_bytes": transfer_data["filesize_bytes"]}
                    transfer["server"] = "onion" if ".onion:" in transfer_data["endpoint_remote"] else "public"
                    if "elapsed_seconds" in transfer_data:
                        s = transfer_data["elapsed_seconds"]
                        if "first_byte" in s:
                            transfer["time_to_first_byte"] = s["first_byte"]
                        if "last_byte" in s:
                            transfer["time_to_last_byte"] = s["last_byte"]
                    if "error_code" in transfer_data and transfer_data["error_code"] != "NONE":
                        transfer["error_code"] = transfer_data["error_code"]
                    if "unix_ts_start" in transfer_data:
                        transfer["start"] = datetime.datetime.utcfromtimestamp(transfer_data["unix_ts_start"])
                    transfers.append(transfer)
        self.data = pd.DataFrame.from_records(transfers, index="transfer_id")

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

    def __plot_downloads_count(self):
        for bytes in np.sort(self.data["filesize_bytes"].unique()):
            for server in self.data["server"].unique():
                self.__draw_countplot(x="label",
                                     data=self.data[(self.data["server"] == server) & (self.data["filesize_bytes"] == bytes)],
                                     xlabel="Data set", ylabel="Downloads completed (#)",
                                     title="Number of downloads of {0} bytes completed from {1} service".format(bytes, server))

    def __plot_errors_count(self):
        for server in self.data["server"].unique():
            if "error_code" in self.data.columns and self.data[self.data["server"] == server]["error_code"].count() > 0:
                self.__draw_countplot(x="error_code", hue="label", hue_name="Data set",
                                      data=self.data[self.data["server"] == server],
                                      xlabel="Error code", ylabel="Downloads failed (#)",
                                      title="Number of downloads failed from {0} service".format(server))

    def __plot_errors_time(self):
        for server in self.data["server"].unique():
            if "error_code" in self.data.columns and self.data[self.data["server"] == server]["error_code"].count() > 0:
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
        sns.despine()
        self.page.savefig()
        plt.close()
