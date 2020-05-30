#!/usr/bin/env python3

from setuptools import setup

with open('requirements.txt') as f:
    install_requires = f.readlines()

setup(name='OnionPerf',
      version='0.3',
      description='A utility to monitor, measure, analyze, and visualize the performance of Tor and Onion Services',
      author='Rob Jansen',
      url='https://github.com/robgjansen/onionperf/',
      packages=['onionperf'],
      scripts=['onionperf/onionperf'],
      install_requires=install_requires
     )
