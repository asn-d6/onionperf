'''
  OnionPerf
  Authored by Rob Jansen, 2015
  See LICENSE for licensing information
'''

import matplotlib; matplotlib.use('Agg')  # for systems without X11
from matplotlib.backends.backend_pdf import PdfPages
import pylab, numpy, time
from abc import abstractmethod, ABCMeta
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import datetime

'''
pylab.rcParams.update({
    'backend': 'PDF',
    'font.size': 16,
    'figure.max_num_figures' : 50,
    'figure.figsize': (6, 4.5),
    'figure.dpi': 100.0,
    'figure.subplot.left': 0.10,
    'figure.subplot.right': 0.95,
    'figure.subplot.bottom': 0.13,
    'figure.subplot.top': 0.92,
    'grid.color': '0.1',
    'axes.grid' : True,
    'axes.titlesize' : 'small',
    'axes.labelsize' : 'small',
    'axes.formatter.limits': (-4, 4),
    'xtick.labelsize' : 'small',
    'ytick.labelsize' : 'small',
    'lines.linewidth' : 2.0,
    'lines.markeredgewidth' : 0.5,
    'lines.markersize' : 10,
    'legend.fontsize' : 'x-small',
    'legend.fancybox' : False,
    'legend.shadow' : False,
    'legend.ncol' : 1.0,
    'legend.borderaxespad' : 0.5,
    'legend.numpoints' : 1,
    'legend.handletextpad' : 0.5,
    'legend.handlelength' : 1.6,
    'legend.labelspacing' : .75,
    'legend.markerscale' : 1.0,
    'ps.useafm' : True,
    'pdf.use14corefonts' : True,
    'text.usetex' : True,
})
'''

class Visualization(object, metaclass=ABCMeta):

    def __init__(self):
        self.datasets = []

    def add_dataset(self, analysis, label, lineformat):
        self.datasets.append((analysis, label, lineformat))

    @abstractmethod
    def plot_all(self, output_prefix):
        pass

class TorVisualization(Visualization):

    def plot_all(self, output_prefix, relays_only=False):
        self.relays_only = relays_only
        if len(self.datasets) > 0:
            prefix = output_prefix + '.' if output_prefix is not None else ''
            ts = time.strftime("%Y-%m-%d_%H:%M:%S")
            self.page = PdfPages("{0}tor.onionperf.viz.{1}.pdf".format(prefix, ts))
            self.__plot_bytes(direction="bytes_read")
            self.__plot_bytes(direction="bytes_written")
            self.page.close()

    def __plot_bytes(self, direction="bytes_written"):
        mafig = pylab.figure()
        allcdffig = pylab.figure()
        eachcdffig = pylab.figure()

        for (anal, label, lineformat) in self.datasets:
            tput = {}
            pertput = []
            for node in anal.get_nodes():
                if self.relays_only and 'relay' not in node and 'thority' not in node: continue
                d = anal.get_tor_bandwidth_summary(node, direction)
                if d is None: continue
                for tstr in d:
                    mib = d[tstr] / 1048576.0
                    t = int(tstr)
                    if t not in tput: tput[t] = 0
                    tput[t] += mib
                    pertput.append(mib)

            pylab.figure(mafig.number)
            x = sorted(tput.keys())
            y = [tput[t] for t in x]
            y_ma = movingaverage(y, 60)
            pylab.scatter(x, y, s=0.1)
            pylab.plot(x, y_ma, lineformat, label=label)

            pylab.figure(allcdffig.number)
            x, y = getcdf(y)
            pylab.plot(x, y, lineformat, label=label)

            pylab.figure(eachcdffig.number)
            x, y = getcdf(pertput)
            pylab.plot(x, y, lineformat, label=label)

        pylab.figure(mafig.number)
        pylab.xlabel("Tick (s)")
        pylab.ylabel("Throughput (MiB/s)")
        pylab.xlim(xmin=0.0)
        pylab.ylim(ymin=0.0)
        pylab.title("60 second moving average throughput, {0}, all relays".format("write" if direction == "bytes_written" else "read"))
        pylab.legend(loc="lower right")
        self.page.savefig()
        pylab.close()
        del(mafig)

        pylab.figure(allcdffig.number)
        pylab.xlabel("Throughput (MiB/s)")
        pylab.ylabel("Cumulative Fraction")
        pylab.title("1 second throughput, {0}, all relays".format("write" if direction == "bytes_written" else "read"))
        pylab.legend(loc="lower right")
        self.page.savefig()
        pylab.close()
        del(allcdffig)

        pylab.figure(eachcdffig.number)
        # pylab.xscale('log')
        pylab.xlabel("Throughput (MiB/s)")
        pylab.ylabel("Cumulative Fraction")
        pylab.title("1 second throughput, {0}, each relay".format("write" if direction == "bytes_written" else "read"))
        pylab.legend(loc="lower right")
        self.page.savefig()
        pylab.close()
        del(eachcdffig)

class TGenVisualization(Visualization):

    def plot_all(self, output_prefix):
        if len(self.datasets) > 0:
            prefix = output_prefix + '.' if output_prefix is not None else ''
            ts = time.strftime("%Y-%m-%d_%H:%M:%S")
            self.__extract_data_frame()
            self.data.to_csv("{0}tgen.onionperf.viz.{1}.csv".format(prefix, ts))
            sns.set_context("paper")
            self.page = PdfPages("{0}tgen.onionperf.viz.{1}.pdf".format(prefix, ts))
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
        for (analysis, label, lineformat) in self.datasets:
            for client in analysis.get_nodes():
                tgen_transfers = analysis.get_tgen_transfers(client)
                for transfer_id, transfer_data in tgen_transfers.items():
                    transfer = {"transfer_id": transfer_id, "label": label,
                                "filesize_bytes": transfer_data["filesize_bytes"]}
                    if "elapsed_seconds" in transfer_data:
                        s = transfer_data["elapsed_seconds"]
                        if "command" in s:
                            if "first_byte" in s:
                                transfer["time_to_first_byte"] = s["first_byte"] - s["command"]
                            if "last_byte" in s:
                                transfer["time_to_last_byte"] = s["last_byte"] - s["command"]
                    if "error_code" in transfer_data and transfer_data["error_code"] != "NONE":
                        transfer["error_code"] = transfer_data["error_code"]
                    if "unix_ts_start" in transfer_data:
                        transfer["start"] = datetime.datetime.utcfromtimestamp(transfer_data["unix_ts_start"])
                    transfers.append(transfer)
        self.data = pd.DataFrame.from_records(transfers, index="transfer_id")

    def __plot_firstbyte_ecdf(self):
        self.__draw_ecdf(x="time_to_first_byte", hue="label", hue_name="Data set",
                         data=self.data, title="Time to download first byte",
                         xlabel="Download time (s)", ylabel="Cumulative Fraction")

    def __plot_firstbyte_time(self):
        for bytes in self.data["filesize_bytes"].unique():
            self.__draw_timeplot(x="start", y="time_to_last_byte", hue="label", hue_name="Data set",
                                 data=self.data[self.data["filesize_bytes"]==bytes],
                                 title="Time to download first of {0} bytes over time".format(bytes),
                                 xlabel="Download start time", ylabel="Download time (s)")

    def __plot_lastbyte_ecdf(self):
        for bytes in self.data["filesize_bytes"].unique():
            self.__draw_ecdf(x="time_to_last_byte", hue="label", hue_name="Data set",
                             data=self.data[self.data["filesize_bytes"]==bytes],
                             title="Time to download last of {0} bytes".format(bytes),
                             xlabel="Download time (s)", ylabel="Cumulative Fraction")

    def __plot_lastbyte_box(self):
        for bytes in self.data["filesize_bytes"].unique():
            self.__draw_boxplot(x="label", y="time_to_last_byte",
                                data=self.data[self.data["filesize_bytes"]==bytes],
                                title="Time to download last of {0} bytes".format(bytes),
                                xlabel="Data set", ylabel="Download time (s)")

    def __plot_lastbyte_bar(self):
        for bytes in self.data["filesize_bytes"].unique():
            self.__draw_barplot(x="label", y="time_to_last_byte",
                                data=self.data[self.data["filesize_bytes"]==bytes],
                                title="Mean time to download last of {0} bytes".format(bytes),
                                xlabel="Data set", ylabel="Downloads time (s)")

    def __plot_lastbyte_time(self):
        for bytes in self.data["filesize_bytes"].unique():
            self.__draw_timeplot(x="start", y="time_to_last_byte", hue="label", hue_name="Data set",
                                 data=self.data[self.data["filesize_bytes"] == bytes],
                                 title="Time to download last of {0} bytes over time".format(bytes),
                                 xlabel="Download start time", ylabel="Download time (s)")

    def __plot_downloads_count(self):
        for bytes in self.data["filesize_bytes"].unique():
            self.__draw_countplot(x="label",
                                 data=self.data[self.data["filesize_bytes"] == bytes],
                                 xlabel="Data set", ylabel="Downloads completed (#)",
                                 title="Number of downloads of {0} bytes completed".format(bytes))

    def __plot_errors_count(self):
        if "error_code" in self.data.columns:
            self.__draw_countplot(x="error_code", hue="label", hue_name="Data set", data=self.data,
                                  xlabel="Error code", ylabel="Downloads failed (#)",
                                  title="Number of downloads failed")

    def __plot_errors_time(self):
        if "error_code" in self.data.columns:
            self.__draw_stripplot(x="start", y="error_code", hue="label", hue_name="Data set",
                                 data = self.data,
                                 xlabel="Download start time", ylabel="Error code",
                                 title="Downloads failed over time")

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

# helper - compute the window_size moving average over the data in interval
def movingaverage(interval, window_size):
    window = numpy.ones(int(window_size)) / float(window_size)
    return numpy.convolve(interval, window, 'same')

# # helper - cumulative fraction for y axis
def cf(d): return pylab.arange(1.0, float(len(d)) + 1.0) / float(len(d))

# # helper - return step-based CDF x and y values
# # only show to the 99th percentile by default
def getcdf(data, shownpercentile=0.99, maxpoints=10000.0):
    data.sort()
    frac = cf(data)
    k = len(data) / maxpoints
    x, y, lasty = [], [], 0.0
    for i in range(int(round(len(data) * shownpercentile))):
        if i % k > 1.0: continue
        assert not numpy.isnan(data[i])
        x.append(data[i])
        y.append(lasty)
        x.append(data[i])
        y.append(frac[i])
        lasty = frac[i]
    return x, y
