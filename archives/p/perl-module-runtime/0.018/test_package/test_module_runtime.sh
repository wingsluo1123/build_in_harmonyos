#!/bin/bash
# test_module_runtime.sh — Module::Runtime consumer test
# Exercises core API: is_module_name, require_module, use_module
# Usage: PERL5LIB=<path> bash test_module_runtime.sh
set -e

perl -e '
use Module::Runtime qw(require_module use_module is_module_name);
die "not a valid module name" unless is_module_name("Cwd");
require_module("Cwd");
use_module("Cwd");
print Cwd::getcwd(), "\n";
print "OK\n";
'
