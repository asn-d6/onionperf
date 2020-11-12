#!/usr/bin/env python3

import os
import math
import sys
import random

import numpy

from scipy.stats import pareto
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt

numpy.seterr('raise')

SUBSAMPLING_SIZES = [100, 500, 1000]

def parse_state_line(line):
    """
    Parse a line from a Tor state line and return the data that we should plot in the histogram

    For example if it's (CircuitBuildTimeBin 342 4) return (342, 342, 342, 342)
    """
    items = line.split()

    # We only use CircuitBuildTimeBin lines
    if len(items) < 1:
        return None
    if items[0] == "CircuitBuildTimeBin":
        value = int(items[1])
        occurences = int(items[2])
    elif items[0] == "CircuitBuildAbandonedCount":
        value = float("NaN")
        occurences = int(items[1])
    else:
        return None

    return ([value] * occurences)

def extract_data(state_fname, subsampling_n):
    # Extract data from state file
    data = []
    for line in open(state_fname,'r'):
        values = parse_state_line(line)
        if values:
            data.extend(values)

    # For each abandoned circuits turn it into a circuit that has reached the
    # maximum timeout
    for i, value in enumerate(data):
        if math.isnan(value):
            data[i] = max(data)

    data = random.sample(data, subsampling_n)

    return data

def plot_state_file(state_fname, data, ax):

    # Make the bins for the histogram
    bins = list(range(0, max(data), 100)) # bins should be every 100ms
    bins.append(max(data)) # also include the last one

    # Plot the histogram
    ax.hist(data, bins=bins, density=True, facecolor='green', alpha=1)

    # Try to fit a Pareto distribution to the data
    shape, loc, scale = pareto.fit(data, 1, loc=0, scale=1)
    y = pareto.pdf(bins, shape, loc=loc, scale=scale)
    # Plot the pareto
    l = ax.plot(bins, y, 'r--', linewidth=2)

    # Set up the graph metadata
    plt.xticks((0,500, 1000, 1500) + tuple(range(2500, max(data), 5000)), rotation=90)
    ax.grid(alpha=0.3)
    ax.set_xlabel('Miliseconds')
    ax.set_ylabel('Probability')

    basename=os.path.splitext(os.path.basename(state_fname))[0]
    ax.set_title("%s [%d timeouts: Pareto(shape=%.3f, loc=%.3f, scale=%.3f)]" %(basename, len(data), shape, loc, scale))

    ax.grid(True)

    # Plot it! :)
    #plt.show()
    #basename=os.path.splitext(sys.argv[1])[0]
    #plt.savefig(basename + "_pareto.png", dpi=300)

def plot_all(state_fnames_list):
    n_states = len(state_fnames_list)
    fig, (ax_list) = plt.subplots(nrows=len(SUBSAMPLING_SIZES), ncols=n_states)

    for i, state_fname in enumerate(state_fnames_list):
        for s, subsampling_n in enumerate(SUBSAMPLING_SIZES):
            data = extract_data(state_fname, subsampling_n)
            plot_state_file(state_fname, data, ax_list[s][i])


    plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=0.4)
    plt.show()

def main():
    if len(sys.argv) < 2:
        print("Usage:\n $ ./analysis_state_timeout.py state-1.txt state-2.txt state-3.txt")
        sys.exit(1)

    state_fnames_list = sys.argv[1:]
    plot_all(state_fnames_list)

if __name__ == '__main__':
    main()
