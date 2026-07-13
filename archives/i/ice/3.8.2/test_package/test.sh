#!/bin/sh
set -eu

icebox --version
slice2cpp "$1"
test -f Test.cpp
test -f Test.h
