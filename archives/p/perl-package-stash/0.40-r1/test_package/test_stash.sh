#!/bin/sh
# test_package/test_stash.sh — L1 smoke test wrapper for perl-package-stash
# Runs test_stash.pl which tests real Package::Stash API.
set -eu

script_dir=$(dirname "$0")
perl "$script_dir/test_stash.pl"
