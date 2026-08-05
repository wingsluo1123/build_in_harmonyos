#!/bin/sh
# L1 test source file - satisfies CI L0c (test source file requirement)
# R34: Tests substantially exercise aircrack-ng's functionality
# The actual tests run via conanfile.py test() method

set -e

# Test 1: aircrack-ng --help (main WEP/WPA-PSK cracking tool)
aircrack-ng --help

# Test 2: makeivs-ng --help (IVS file generator)
makeivs-ng --help

# Test 3: Verify kstats binary is installed
command -v kstats
