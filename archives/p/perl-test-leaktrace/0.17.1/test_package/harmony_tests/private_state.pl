use strict;use warnings;use Cwd qw(abs_path);use Fcntl qw(O_WRONLY O_CREAT O_EXCL S_ISREG);use Test::LeakTrace qw(:util);
my $root=$ENV{TMPDIR};my @r=lstat($root);die "Foreign private root" unless abs_path($root) eq $root && $r[4]==$< && ($r[2]&0777)==0700;
my $path="$root/leaktrace-$$.txt";sysopen(my $fp,$path,O_WRONLY|O_CREAT|O_EXCL,0600) or die $!;
{open local(*STDERR),'>&',$fp or die $!;leaktrace {my @a;push @a,\@a;} -simple;}
close($fp) or die $!;my @s=lstat($path);die "Bad owned inode" unless S_ISREG($s[2]) && $s[4]==$< && ($s[2]&0777)==0600;
open(my $read,'<',$path) or die $!;my $text=do {local $/;<$read>};close($read) or die $!;my $source=__FILE__;die "No actual source trace" unless $text=~/from \Q$source\E line \d+\./;unlink($path)==1 or die $!;die "Leaked file name" if -e $path;
print "HARMONY_TEST_COUNT=1\nHARMONY_NATIVE_LEAKTRACE_OWNED_REPORT=1/1 PASS\nHARMONY_TEST_PASS=1/1\n";
