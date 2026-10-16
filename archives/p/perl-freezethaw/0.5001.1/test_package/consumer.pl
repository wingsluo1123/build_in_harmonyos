use strict;use warnings;use Cwd qw(abs_path);use FreezeThaw qw(freeze thaw);
my $root=abs_path($ENV{PACKAGE_ROOT});my $loaded=abs_path($INC{'FreezeThaw.pm'});die "Foreign module" unless index($loaded,$root.'/')==0;
my $shared=[1,'two'];my $a={x=>$shared,y=>$shared};$a->{self}=$a;my ($b)=thaw(freeze($a));die "Roundtrip alias/cycle" unless $b->{x}==$b->{y} && $b->{self}==$b && $b->{x}[1] eq 'two';
{package LocalObject;sub new {bless {answer=>42},shift}}
my ($object)=thaw(freeze(LocalObject->new));die "Object state" unless ref($object) eq 'LocalObject' && $object->{answer}==42;
print "CONSUMER_TEST_PASS=2/2\n";
