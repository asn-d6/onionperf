#!/bin/sh

PYTHONPATH=. python -m nose --with-coverage --cover-package=onionperf
