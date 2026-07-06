#!/bin/sh
# test.sh — CI L0c compliant test for Parallel::ForkManager
perl -MParallel::ForkManager -e 'print qq(Parallel::ForkManager loaded OK\n)'
