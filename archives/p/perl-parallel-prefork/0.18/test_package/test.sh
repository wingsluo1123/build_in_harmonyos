#!/bin/sh
# test_package/test.sh — perl-parallel-prefork functional test
# This script documents the test performed by test_package/conanfile.py
#
# Test 1: Verify Parallel::Prefork.pm is installed in the package
#   Checks that the .pm file exists at the expected site_perl path
#
# Test 2: Verify SpareWorkers.pm submodule is installed
#
# Test 3: Verify Scoreboard.pm submodule is installed
#
# Test 4: Verify module version matches 0.18
echo "perl-parallel-prefork test package - functional verification"
