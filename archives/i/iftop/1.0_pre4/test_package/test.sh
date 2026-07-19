#!/bin/sh
set -eu

iftop -h 2>&1 | grep -q "iftop, version 1.0pre4"
