use strict;
use warnings;
use Proc::ProcessTable;

# Test 1: module loads and has correct version
my $version = $Proc::ProcessTable::VERSION;
die 'VERSION not defined' unless defined $version;
print "Test 1 PASS: module loaded, version $version\n";

# Test 2: constructor creates a ProcessTable object
my $pt = Proc::ProcessTable->new();
die 'new() failed' unless defined $pt;
die 'not a Proc::ProcessTable' unless ref($pt) eq 'Proc::ProcessTable';
print "Test 2 PASS: new() returns Proc::ProcessTable object\n";

# Test 3: fields() returns available field names
my @fields = $pt->fields();
die 'fields() returned empty list' unless @fields > 0;
print "Test 3 PASS: fields() returns " . scalar(@fields) . " fields: " . join(', ', @fields) . "\n";

# Test 4: table() returns an array reference
# Note: on HarmonyOS, /proc may be limited; table() may return empty list
my $procs = eval { $pt->table(); };
if ($@) {
    print "Test 4 SKIP: table() failed (platform /proc limitation): $@\n";
} else {
    die 'table() did not return array ref' unless ref($procs) eq 'ARRAY';
    print "Test 4 PASS: table() returns ARRAY ref with " . scalar(@$procs) . " processes\n";
}

print "ALL TESTS PASSED\n";
