use strict;use warnings;use Cwd qw(abs_path);use Fcntl qw(O_WRONLY O_CREAT O_EXCL S_ISREG);use Lingua::EN::Inflect qw(PL_N NUMWORDS);
my $root=$ENV{TMPDIR};my @r=lstat($root);die "Foreign private POSIX root" unless abs_path($root) eq $root && $r[4]==$< && ($r[2]&0777)==0700;
my $payload=PL_N('octopus')."\n".NUMWORDS(21)."\n";my $path="$root/lingua-$$.txt";sysopen(my $fp,$path,O_WRONLY|O_CREAT|O_EXCL,0600) or die $!;
my $offset=0;while($offset<length($payload)){my $n=syswrite($fp,$payload,length($payload)-$offset,$offset);defined($n)&&$n>0 or die $!;$offset+=$n;}close($fp) or die $!;
my @s=lstat($path);die "Bad actual owned inode" unless S_ISREG($s[2]) && $s[4]==$< && ($s[2]&0777)==0600;open(my $read,'<',$path) or die $!;binmode($read);my $raw=do {local $/;<$read>};close($read) or die $!;
die "Actual inflected private state differs" unless $raw eq "octopuses\ntwenty-one\n";unlink($path)==1 or die $!;die "Leaked file name" if -e $path;
print "HARMONY_TEST_COUNT=1\nHARMONY_LINGUA_OWNED_STATE=1/1 PASS\nHARMONY_TEST_PASS=1/1\n";
