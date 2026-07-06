#!/bin/sh
# test.sh — CI L0c compliant wrapper for test.pl
# CI accepts .sh extension but not .pl; this wrapper bridges the gap.
exec perl "$(dirname "$0")/test.pl"
