#!/bin/sh
# test_package/test_deprecationmanager.sh — L1 smoke test wrapper for perl-package-deprecationmanager
# Runs test_deprecationmanager.pl which tests real Package::DeprecationManager API.
set -eu

script_dir=$(dirname "$0")

# Package::Stash (a runtime dependency of Package::DeprecationManager) requires
# Module::Implementation at runtime, which in turn depends on Module::Runtime
# and Try::Tiny. These are pure-Perl modules not available on CI workers.
# Bundle them in test_package/lib/ so the test is self-contained.
perl -I"$script_dir/lib" "$script_dir/test_deprecationmanager.pl"
