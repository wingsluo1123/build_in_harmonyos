use strict;use warnings;use Cwd qw(abs_path);use Test::More tests=>2;use Canary::Stability ();
my $root=abs_path($ENV{PACKAGE_ROOT});my $loaded=abs_path($INC{'Canary/Stability.pm'});die "Foreign module" unless index($loaded,$root.'/')==0;
sub actual_check {my ($minimum)=@_;my $out='';open(my $f,'>',\$out) or die $!;{local *STDOUT=$f;local $ENV{PERL_CANARY_STABILITY_DISABLE}=0;local $ENV{PERL_CANARY_STABILITY_NOPROMPT}=1;local $ENV{PERL_CANARY_STABILITY_COLOUR}=0;Canary::Stability->import('native-consumer',$minimum,5.008002);}close($f) or die $!;return $out;}
is($Canary::Stability::VERSION,2013,'Actual installed version') or die "Installed version";
my $out=actual_check(2014);like($out,qr/Canary::Stability.*too old/s,'Actual unsupported canary version warning is retained') or die "Missing real diagnostic";
print "CONSUMER_TEST_PASS=2/2\n";
