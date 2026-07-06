#!/bin/sh
# test.sh — CI L0c compliant test for Parallel::Pipes
cat > /tmp/test_parallel_pipes.pl << 'PERL'
use Parallel::Pipes;
use Parallel::Pipes::App;
my $pipes = Parallel::Pipes->new(3);
print "OK\n";
PERL
perl /tmp/test_parallel_pipes.pl
