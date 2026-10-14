BEGIN {
    @INC = split /:/, $ENV{PERL5LIB};
    my @roots = split /:/, $ENV{BINDING_ROOTS};
    die "unbound include" if grep { my $p = $_; !grep { index($p, "$_/") == 0 } @roots } @INC;
}
use strict;
use warnings;
use Module::Runtime qw(is_module_name module_notional_filename use_module);
die "genuine module version mismatch" unless $Module::Runtime::VERSION eq '0.018';
die "valid module rejected" unless is_module_name('Data::Dumper');
die "module filename mismatch" unless module_notional_filename('Data::Dumper') eq 'Data/Dumper.pm';
my $module = use_module('Data::Dumper');
die "real core module not loaded" unless $module eq 'Data::Dumper' && $INC{'Data/Dumper.pm'};
for my $invalid ('../outside', 'Name/Component', 'Name;die') {
    die "invalid module accepted" if is_module_name($invalid);
}
print "CONSUMER_TEST_PASS=2/2; actual module mapping/loading and invalid-name rejection
";
