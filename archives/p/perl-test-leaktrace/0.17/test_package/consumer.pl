use strict;use warnings;use Cwd qw(abs_path);use Test::LeakTrace;
my $root=abs_path($ENV{PACKAGE_ROOT});my $loaded=abs_path($INC{'Test/LeakTrace.pm'});die "Foreign module" unless index($loaded,$root.'/')==0;
sub normal {my %a;my %b;$a{b}=1;$b{a}=2;}
sub leaked {my %a;my %b;$a{b}=\%b;$b{a}=\%a;}
die "Normal scope leaks" unless leaked_count(\&normal)==0;
die "Cycle not detected" unless leaked_count(\&leaked)>0;
print "CONSUMER_TEST_PASS=2/2\n";
