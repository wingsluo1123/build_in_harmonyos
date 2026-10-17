use common::sense;use Cwd qw(abs_path);use POSIX qw(uname);use Encode qw(encode);use Fcntl qw(O_WRONLY O_CREAT O_EXCL S_ISREG);use Test::More tests=>1;
my ($sysname)=uname();die "Actual HarmonyOS required" unless $sysname eq 'HarmonyOS';my $root=$ENV{TMPDIR};my @r=lstat($root);die "Foreign private root" unless abs_path($root) eq $root && $r[4]==$< && ($r[2]&0777)==0700;my $leaf="sense-汉-$$.txt";die "UTF8 lexical hint mismatch" unless length("汉")==1;my $path=$root.'/'.encode('UTF-8',$leaf);sysopen(my $f,$path,O_WRONLY|O_CREAT|O_EXCL,0600) or die $!;print $f "actual native generated lexical hints
";close($f) or die $!;my @s=lstat($path);ok(S_ISREG($s[2]) && $s[4]==$< && ($s[2]&0777)==0600,'Generated target lexical hints with actual UID-owned Unicode native state') or die "Wrong native inode";unlink($path)==1 or die $!;die "Leaked state" if -e $path;print "HARMONY_TEST_COUNT=1
HARMONY_SENSE_GENERATED_HINT_STATE=1/1 PASS
HARMONY_TEST_PASS=1/1
";
