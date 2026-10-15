use strict;use warnings;use Cwd qw(abs_path);use Lingua::EN::Inflect qw(PL_N NUMWORDS);
my $root=abs_path($ENV{PACKAGE_ROOT});my $loaded=abs_path($INC{'Lingua/EN/Inflect.pm'});die "Foreign installed module" unless defined($root) && defined($loaded) && index($loaded,$root.'/')==0;
die "Wrong upstream module version" unless $Lingua::EN::Inflect::VERSION eq '1.905';
die "Actual plural API" unless PL_N('octopus') eq 'octopuses';
die "Actual number API" unless NUMWORDS(21) eq 'twenty-one';
print "CONSUMER_TEST_PASS=2/2\n";
