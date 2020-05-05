#!/bin/sh

PYTHONPATH=. python3 -m nose --with-coverage --cover-package=onionperf
