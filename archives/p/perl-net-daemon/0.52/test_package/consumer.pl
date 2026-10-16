BEGIN {
 @INC=split /:/,$ENV{PERL5LIB};
 my @roots=split /:/,$ENV{BINDING_ROOTS};
 die "unbound include" if grep {my $p=$_;!grep {index($p,"$_/")==0} @roots} @INC;
}
use strict;
use warnings;
use Net::Daemon;
use Net::Daemon::Log;
use File::Temp qw(tempfile);
die "module version drift" unless $Net::Daemon::VERSION eq '0.52';
die "source tree module selected" unless index($INC{'Net/Daemon.pm'},$ENV{NET_DAEMON_MODULE_ROOT}.'/')==0;
my $daemon=Net::Daemon->new({localport=>0,proto=>'tcp',mode=>'single'},['--listen','20']);
die "real options not applied" unless $daemon->{'listen'}==20 && exists Net::Daemon->Options()->{'listen'};
{
 package NativeClone;
 our @ISA=('Net::Daemon');
 sub post_clone { $_[0]->{'hook_seen'}=1; }
}
bless $daemon,'NativeClone';
my $clone=$daemon->Clone(undef);
die "clone hook or parent identity lost" unless $clone->{'hook_seen'} && $clone->{'parent'}==$daemon && $clone!=$daemon;
my ($fh,$path)=tempfile(DIR=>$ENV{TMPDIR},UNLINK=>1);close $fh;
my $logger=bless {logfile=>$path},'Net::Daemon::Log';
$logger->Log('notice','native installed module logfile roundtrip');
close $logger->{'logfile'} if ref($logger->{'logfile'});
open my $read,'<',$path or die "open log: $!";
my $text=do {local $/;<$read>};close $read;
die "installed logger did not write message" unless $text=~/native installed module logfile roundtrip/;
print "CONSUMER_TEST_PASS=3/3\n";
