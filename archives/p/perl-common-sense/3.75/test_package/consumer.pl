use strict;use warnings;use Cwd qw(abs_path);use Test::More tests=>2;use common::sense ();
my $root=abs_path($ENV{PACKAGE_ROOT});my $loaded=abs_path($INC{'common/sense.pm'});die "Foreign generated module" unless index($loaded,$root.'/')==0;
my $bad=eval q{use common::sense; deliberately_unquoted_native_bareword; 1;};ok(!defined($bad) && $@ =~ /Bareword.*not allowed/s,'Actual generated strict-subs hints reject a bareword') or die "Missing strict hints";
my $good=eval q{use common::sense; my $text="汉"; sub actual_native_state {state $n=0; ++$n}; length($text)==1 && actual_native_state()==1 && actual_native_state()==2;};ok($good && !$@,'Actual generated UTF8 and state feature hints match target Perl') or die "Wrong generated target hints: $@";
print "CONSUMER_TEST_PASS=2/2
";
