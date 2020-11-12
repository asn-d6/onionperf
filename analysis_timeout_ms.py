#!/usr/bin/env python3

import os
import math
import sys

import numpy

from scipy.stats import pareto
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt

# Read data from a Tor state file
fname = sys.argv[1]
data = []

def parse_torctl_line(line):
    """
    Parse a line from a Tor state line and return the data that we should plot in the histogram

    For example if it's (CircuitBuildTimeBin 342 4) return (342, 342, 342, 342)
    """
    items = line.split()

    # We only use CircuitBuildTimeBin lines
    if len(items) < 5:
        return None

    if items[4] == "BUILDTIMEOUT_SET":
        timeout_ms_string = items[7]
        xm_string = items[8]
    else:
        return None

    timeout_ms = int(timeout_ms_string.split("=")[1])
    xm = int(xm_string.split("=")[1])

    return [timeout_ms]

# Extract data from state file
data = []
for line in open(fname,'r'):
    values = parse_torctl_line(line)
    if values:
        data.extend(values)

# Now replace abandoned circuits with maximum timeout
for i, value in enumerate(data):
    if math.isnan(value):
        data[i] = max(data)

print(data)

fig, ax = plt.subplots()

# Plot the histogram
bins = list(range(min(data), max(data), 5)) # bins should be every 100ms
bins.append(max(data)) # also include the last one

#print(bins)
plt.hist(data, bins=bins, density=True, facecolor='green', alpha=1)

numpy.seterr('raise')

# Try to fit a Pareto in the data
# shape is b (alpha in wikipedia), scale is x (x_b in wikipedia)
#shape, loc, scale = pareto.fit(data)
#y = pareto.pdf(bins, shape, loc=loc, scale=scale)

# Plot the Pareto on top of the bins
#l = plt.plot(bins, y, 'r--', linewidth=2)

#plt.xticks((0,500, 1000, 1500) + tuple(range(2500, max(data), 5000)), rotation=90)
plt.xticks(range(min(data), max(data), 5))
ax.grid(alpha=0.3)

#plot
plt.xlabel('Miliseconds')
plt.ylabel('Occurences')
#plt.title("Histogram of %d circuit timeout values fitted against Pareto with shape=%.3f, loc=%.3f and scale=%.3f" %(len(data), shape, loc, scale))
plt.grid(True)

#plt.show()
basename=os.path.splitext(sys.argv[1])[0]
plt.savefig(basename + "_pareto.png", dpi=300)

