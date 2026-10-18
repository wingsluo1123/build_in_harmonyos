use strict;use warnings;use Cwd qw(abs_path);use Test::More tests=>2;use Test::Pod;
my $root=abs_path($ENV{PACKAGE_ROOT});my $loaded=abs_path($INC{'Test/Pod.pm'});die "Foreign module" unless index($loaded,$root.'/')==0;
my $path="$ENV{TMPDIR}/consumer.pod";open(my $f,'>',$path) or die $!;print $f "=pod\n\n=head1 NAME\n\nTestPod consumer fixture\n\n=cut\n";close($f) or die $!;
pod_file_ok($path,'Actual installed parser validates POD') or die "POD validation";
my @found=Test::Pod::all_pod_files($ENV{TMPDIR}); @found=sort @found;is_deeply(\@found,[$path],'Actual POD file discovery') or die "POD discovery";
unlink($path)==1 or die $!;print "CONSUMER_TEST_PASS=2/2\n";
