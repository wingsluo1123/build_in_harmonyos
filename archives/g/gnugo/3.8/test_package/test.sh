#!/bin/sh
# test_package/test.sh — verify gnugo binary works
# Runs gnugo --version and checks output contains "GNU Go"
gnugo --version 2>&1 | grep -q "GNU Go" && echo "PASS: gnugo --version OK" || { echo "FAIL: gnugo not working"; exit 1; }
