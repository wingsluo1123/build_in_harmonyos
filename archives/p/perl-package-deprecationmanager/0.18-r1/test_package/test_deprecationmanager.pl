#!/usr/bin/env perl
# test_package/test_deprecationmanager.pl — L1 smoke test for perl-package-deprecationmanager
# Tests real Package::DeprecationManager API: import with -deprecations,
# deprecated() function, custom message, feature-based deprecation, warning capture.
#
# R34/L1e: This test verifies that the module is loaded from the Conan
# package cache path (.conan2), not from a system Perl installation.
# When CI sabotages the package's lib/ directory, the module will be
# found from system paths, but the path check will fail the test.
use strict;
use warnings;
use Package::DeprecationManager -deprecations => {
    'TestModule::old_method' => '0.01',
    'feature_x'              => '0.05',
};

my $pass = 0;
my $total = 0;

# Test 1: module loads
$total++; $pass++ if defined $INC{'Package/DeprecationManager.pm'};

# Test 2: module loaded from Conan cache (R34/L1e negative test defense)
# When CI moves the package lib/ away, the module may be found from system
# paths. This check ensures the test fails in that case, proving real dependency.
my $module_path = $INC{'Package/DeprecationManager.pm'} // '';
$total++; $pass++ if $module_path =~ /\.conan2/;

# Test 3: deprecated() function is exported to caller
$total++; $pass++ if defined *main::deprecated{CODE};

# Test 4: deprecated() with no args produces a warning
{
    my $warning_caught = 0;
    local $SIG{__WARN__} = sub { $warning_caught = 1 if $_[0] =~ /deprecated/ };
    deprecated();
    $total++; $pass++ if $warning_caught;
}

# Test 5: deprecated() with custom message produces that message
{
    my $msg_caught = '';
    local $SIG{__WARN__} = sub { $msg_caught = $_[0] };
    deprecated('custom deprecation message');
    $total++; $pass++ if $msg_caught =~ /custom deprecation message/;
}

# Test 6: deprecated() with message and feature parameters
{
    my $msg_caught = '';
    local $SIG{__WARN__} = sub { $msg_caught = $_[0] };
    deprecated(
        message => 'Feature X is deprecated',
        feature => 'feature_x',
    );
    $total++; $pass++ if $msg_caught =~ /Feature X is deprecated/;
}

# Test 7: deprecated() for a feature triggers the correct deprecation version
{
    my $msg_caught = '';
    local $SIG{__WARN__} = sub { $msg_caught = $_[0] };
    deprecated(
        message => 'old_method is removed',
        feature => 'TestModule::old_method',
    );
    $total++; $pass++ if $msg_caught =~ /old_method is removed/;
}

# Test 8: import() function is exported
$total++; $pass++ if defined *main::import{CODE};

# Test 9: Package::DeprecationManager version is defined
$total++; $pass++ if defined $Package::DeprecationManager::VERSION;

print "test perl-package-deprecationmanager 0.18-r1: $pass/$total OK\n";
die "FAILED: $pass/$total tests passed\n" if $pass != $total;
