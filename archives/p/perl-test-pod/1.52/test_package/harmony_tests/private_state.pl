use strict;use warnings;use Cwd qw(abs_path);use POSIX qw(uname);use Fcntl qw(O_WRONLY O_CREAT O_EXCL S_ISREG);use Test::More tests=>1;use Test::Pod;
my ($sysname)=uname();die "Actual HarmonyOS runtime required" unless $sysname eq 'HarmonyOS';
my $root=$ENV{TMPDIR};my @r=lstat($root);die "Foreign private root" unless abs_path($root) eq $root && $r[4]==$< && ($r[2]&0777)==0700;
my $path="$root/testpod-$$.pod";sysopen(my $fp,$path,O_WRONLY|O_CREAT|O_EXCL,0600) or die $!;print $fp "=pod\n\n=head1 NAME\n\nNative owned HarmonyOS POD state\n\n=cut\n";close($fp) or die $!;
my @s=lstat($path);die "Bad owned inode" unless S_ISREG($s[2]) && $s[4]==$< && ($s[2]&0777)==0600;pod_file_ok($path,'POD validation in actual HarmonyOS UID-owned storage') or die "Actual native parser";
unlink($path)==1 or die $!;die "Leaked private state" if -e $path;print "HARMONY_TEST_COUNT=1\nHARMONY_TESTPOD_OWNED_STATE=1/1 PASS\nHARMONY_TEST_PASS=1/1\n";
