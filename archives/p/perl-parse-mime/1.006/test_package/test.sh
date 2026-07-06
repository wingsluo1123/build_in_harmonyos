#!/bin/sh
# test.sh — CI L0c compliant test for Parse::MIME
perl -e 'use Parse::MIME qw( best_match ); my $m = best_match( [ qw( application/xbel+xml text/xml ) ], '"'"'text/*;q=0.5,*/*; q=0.1'"'"' ); die "test failed" unless $m eq "text/xml"; print "Parse::MIME test OK\n";'
