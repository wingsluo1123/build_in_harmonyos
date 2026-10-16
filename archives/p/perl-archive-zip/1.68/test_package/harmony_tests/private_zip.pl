use strict;
use warnings;
use POSIX qw(uname);
use File::Temp qw(tempdir);
use Cwd qw(getcwd abs_path);
use Archive::Zip qw(:ERROR_CODES);
my @u=uname();die "actual target" unless $u[0] eq 'HarmonyOS' && $u[4] eq 'aarch64';my $base=$ENV{TMPDIR}//die 'TMPDIR';my @b=stat($base);die "private app UID root" unless @b && $b[4]==$< && ($b[2]&0777)==0700 && !-l $base && abs_path($base) eq $base;my $old=getcwd();my $root=tempdir('harmony-zip-XXXXXX',DIR=>$base,CLEANUP=>1);chdir $root or die $!;my $z=Archive::Zip->new();$z->addString("native\0bytes"=>'owned.dat') or die 'member';die 'write' unless $z->writeToFileNamed('owned.zip')==AZ_OK;my @s=stat('owned.zip');die 'actual app UID owner' unless @s && $s[4]==$<;my $r=Archive::Zip->new();die 'read' unless $r->read('owned.zip')==AZ_OK;die 'contents' unless $r->memberNamed('owned.dat')->contents eq "native\0bytes";chdir $old or die $!;print "HARMONY_TEST_COUNT=1\nHARMONY_TEST_PASS=1/1\n";
