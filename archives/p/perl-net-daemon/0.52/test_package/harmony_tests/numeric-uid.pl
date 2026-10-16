BEGIN { @INC=split /:/,$ENV{PERL5LIB}; }
use strict;
use warnings;
use POSIX qw(uname);
use IO::Socket::INET;
use Net::Daemon;
my @uname=uname();die "not actual HarmonyOS" unless $uname[0] eq 'HarmonyOS';
die "wrong installed module" unless index($INC{'Net/Daemon.pm'},$ENV{NET_DAEMON_MODULE_ROOT}.'/')==0;
my $uid=$>;die "root is outside this capability fixture" unless $uid>0 && $<==$uid;
my $name=getpwuid($uid);die "NSS capability changed; reassess original boundary" if defined $name;
my $socket=IO::Socket::INET->new(LocalAddr=>'127.0.0.1',LocalPort=>0,Proto=>'tcp',Listen=>1,Reuse=>1) or die "actual socket: $!";
my $daemon=bless {user=>"$uid",pidfile=>'none',mode=>'single',catchint=>1,done=>1,socket=>$socket},'Net::Daemon';
local $SIG{ALRM}=sub {die "Bind timeout\n"};alarm 10;
$daemon->Bind();alarm 0;
die "actual UID changed" unless $>==$uid && $<==$uid;
close $socket;
print "HARMONY_TEST_COUNT=1\nHARMONY_TEST_PASS=1/1\nactual numeric UID=$uid without named NSS; same-UID Bind; root privileges not granted\n";
