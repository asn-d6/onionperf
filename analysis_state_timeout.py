#!/usr/bin/env python3

import os
import math
import sys

import numpy

from scipy.stats import pareto
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt

numpy.seterr('raise')

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

def extract_data(state_fname):
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

    return data

def plot_state_file(data):

    # Make the bins for the histogram
    bins = list(range(0, max(data), 100)) # bins should be every 100ms
    bins.append(max(data)) # also include the last one

    # Plot the histogram
    fig, ax = plt.subplots()
    plt.hist(data, bins=bins, density=True, facecolor='green', alpha=1)

    # Try to fit a Pareto distribution to the data
    shape, loc, scale = pareto.fit(data, 1, loc=0, scale=1)
    y = pareto.pdf(bins, shape, loc=loc, scale=scale)
    # Plot the pareto
    l = plt.plot(bins, y, 'r--', linewidth=2)

    # Set up the graph metadata
    plt.xticks((0,500, 1000, 1500) + tuple(range(2500, max(data), 5000)), rotation=90)
    ax.grid(alpha=0.3)
    plt.xlabel('Miliseconds')
    plt.ylabel('Probability')
    plt.title("Histogram of %d circuit timeout values fitted against Pareto with shape=%.3f, loc=%.3f and scale=%.3f" %(len(data), shape, loc, scale))
    plt.grid(True)

    # Plot it! :)
    plt.show()
    #basename=os.path.splitext(sys.argv[1])[0]
    #plt.savefig(basename + "_pareto.png", dpi=300)

def plot_all(state_fnames_list):
    for state_fname in state_fnames_list:
        data = extract_data(state_fname)
        plot_state_file(data)

def main():
    if len(sys.argv) < 2:
        print("Usage:\n $ ./analysis_state_timeout.py state-1.txt state-2.txt state-3.txt")
        sys.exit(1)

    state_fnames_list = sys.argv[1:]
    plot_all(state_fnames_list)

if __name__ == '__main__':
    main()
