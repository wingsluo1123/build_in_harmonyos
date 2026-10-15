use strict;
use warnings;
use IO::String;
use POSIX qw(uname);
use File::Temp qw(tempfile);
use Cwd qw(abs_path);

# One Harmony application-sandbox case, not an inflated count of its checks.
my @identity = uname();
die "Not an actual HarmonyOS target\n" unless $identity[0] eq 'HarmonyOS';
my $tmp = $ENV{TMPDIR} // die "Missing explicit task TMPDIR\n";
die "Symlink or unowned task root\n" if -l $tmp || abs_path($tmp) ne $tmp;
my @st = stat($tmp);
die "Foreign task root\n" unless @st && $st[4] == $< && $< == $>;
my ($real, $path) = tempfile('io-string-harmony-XXXXXX', DIR => $tmp, UNLINK => 1);
binmode($real);
my $text = "a\0b\nsecond\n";
print {$real} $text or die "Private filesystem write failed\n";
seek($real, 0, 0) or die "Private filesystem seek failed\n";
my $virtual = IO::String->new($text);
die "Private file/virtual first line differs\n" unless scalar(<$real>) eq $virtual->getline();
die "Private file/virtual offset differs\n" unless tell($real) == $virtual->getpos();
$virtual->setpos(2);
$virtual->print('X');
die "Virtual handle did not modify caller-owned memory\n" unless $text eq "a\0X\nsecond\n";
close($real) or die "Private descriptor close failed\n";
print "HARMONY_TEST_COUNT=1\nHARMONY_PRIVATE_IO_PASS=1/1\nHARMONY_TEST_PASS=1/1\n";
