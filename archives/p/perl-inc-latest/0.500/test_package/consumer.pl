use strict;
use warnings;
use File::Temp qw(tempdir);
use File::Path qw(make_path);
use Cwd qw(getcwd abs_path);
use inc::latest ();
use inc::latest::private ();
my $package = $ENV{INC_LATEST_PACKAGE} // die "Missing declared package root";
my $installed = abs_path($INC{'inc/latest.pm'});
die "Unexpected inc::latest source $installed" unless index($installed, abs_path($package).'/') == 0;
die "Wrong module version" unless $inc::latest::VERSION eq '0.500';
my $start=getcwd();
my $root=tempdir('inc-latest-consumer-XXXXXX', TMPDIR=>1, CLEANUP=>1);
chdir $root or die $!;
inc::latest->write('inc');
inc::latest->bundle_module('inc::latest','inc');
for my $rel ('latest.pm','latest/private.pm') {
    my $original="$package/lib/perl5/inc/$rel";
    my $copy="inc/inc_inc-latest/inc/$rel";
    open my $a,'<',$original or die $!;binmode $a;local $/;my $av=<$a>;
    open my $b,'<',$copy or die $!;binmode $b;my $bv=<$b>;
    die "Real packlist bundle differs: $rel" unless $av eq $bv;
}
die "Stub was not generated" unless -f 'inc/latest.pm' && -f 'inc/latest/private.pm';
print "CONSUMER_CASE_PASS=author-write-and-real-installed-packlist-bundle\n";
sub write_probe {
    my ($path,$version,$value)=@_;
    open my $fh,'>',$path or die $!;
    print {$fh} "package Task::Selection;\n".'our $VERSION = '."'$version';\n".'our $imported; sub import { $imported=caller().":".$_[1]; } sub value { '."'$value'".' } 1;' or die $!;
    close $fh or die $!;
    require ExtUtils::MakeMaker;
    my $parsed=ExtUtils::MM->parse_version($path);
    die "Fixture metadata not parseable: $parsed versus $version" unless $parsed eq $version;
}
make_path('inc/inc_Task-Selection/Task','installed/Task');
write_probe('inc/inc_Task-Selection/Task/Selection.pm','2.0','bundled');
write_probe('installed/Task/Selection.pm','1.0','installed');
my $check='use strict; use warnings; use inc::latest "Task::Selection", "sentinel"; die "wrong import" unless $Task::Selection::imported eq "main:sentinel"; my ($expected,$fragment)=@ARGV; die "wrong value" unless Task::Selection::value() eq $expected; die "wrong source" unless index($INC{"Task/Selection.pm"},$fragment)>=0;';
my $rc=system {$^X} $^X,'-I.','-Iinstalled','-e',$check,'bundled','inc/inc_Task-Selection';
die "Bundled newer selection failed: $rc" if $rc;
print "CONSUMER_CASE_PASS=bundled-newer-version-and-caller-import\n";
write_probe('inc/inc_Task-Selection/Task/Selection.pm','1.0','bundled');
write_probe('installed/Task/Selection.pm','3.0','installed');
$rc=system {$^X} $^X,'-I.','-Iinstalled','-e',$check,'installed','installed/Task';
die "Installed newer selection failed: $rc" if $rc;
print "CONSUMER_CASE_PASS=installed-newer-version-and-caller-import\n";
chdir $start or die $!;
print "CONSUMER_TEST_PASS=3/3\n";
