use strict;
use warnings;
use String::Random;

my $sr = String::Random->new();
my $s = $sr->randpattern("Ccnc");
die "too short" unless length($s) == 4;
print "OK: String::Random version $String::Random::VERSION works\n";
