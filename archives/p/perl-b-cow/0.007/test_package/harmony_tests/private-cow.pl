BEGIN { @INC=split /:/,$ENV{PERL5LIB}; }
use strict;
use warnings;
use File::Temp qw(tempdir);
use File::Spec;
use B::COW qw(is_cow cowrefcnt);
my $system=`/system/bin/uname -s`;
die "actual OHOS identity required" unless $?==0 && $system eq "HarmonyOS\n";
my $root=tempdir('cow-ohos-XXXXXX',DIR=>$ENV{TMPDIR},CLEANUP=>1);
die "task POSIX root identity denied" if -l $root || (lstat $root)[4]!=$<;
my $original='Harmony private POSIX COW binary fixture' . "\0";my $copy=$original;
die "genuine COW state missing" unless is_cow($original) && cowrefcnt($original)>0;
$copy.='changed';my $file=File::Spec->catfile($root,'actual-cow-state.bin');
open my $out,'>:raw',$file or die "create: $!"; print {$out} $copy or die "write: $!";close $out or die "close: $!";
die "foreign output inode" if -l $file || (lstat $file)[4]!=$<;
open my $in,'<:raw',$file or die "read: $!";local $/;my $actual=<$in>;close $in or die "close: $!";
die "private OHOS inode bytes or COW isolation drift" unless $actual eq $copy && $original eq 'Harmony private POSIX COW binary fixture'."\0" && $copy ne $original;
die "foreign XS" unless grep {index($_,$ENV{B_COW_XS_ROOT}.'/auto/B/COW/')==0 && /\/COW\.so$/} @DynaLoader::dl_shared_objects;
print "HARMONY_TEST_PASS=1/1\nactual OHOS owned POSIX inode and same-ABI COW state\n";
