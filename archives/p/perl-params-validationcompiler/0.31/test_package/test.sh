#!/bin/sh
# test.sh — CI L0c compliant test for Params::ValidationCompiler
perl -e 'use Params::ValidationCompiler qw(validation_for); use Params::ValidationCompiler::Exceptions; my $validator = validation_for( params => { foo => 1 } ); die "test failed" unless $validator; print "Params::ValidationCompiler test OK\n";'
