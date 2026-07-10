#!/bin/sh
# test_package/test_variant.sh — smoke test for Package::Variant (pure Perl module)
# Verifies that Package::Variant can be loaded and its version matches expectation.
set -eu

echo "[test] Loading Package::Variant..."
perl -e 'use Package::Variant; print "Package::Variant loaded OK\n"' || {
    echo "❌ Failed to load Package::Variant"
    exit 1
}

echo "[test] Checking version..."
perl -e 'use Package::Variant; my $v = $Package::Variant::VERSION; die "No version\n" unless $v; print "Version: $v\n"; die "Version mismatch\n" unless $v eq "1.003002";' || {
    echo "❌ Version check failed"
    exit 1
}

echo "[test] Verifying core API (build_variant_of)..."
perl -e '
use Package::Variant;
# build_variant_of is the core method; build_variant is exported to caller
no strict "refs";
die "build_variant_of not defined\n" unless defined &{"Package::Variant::build_variant_of"};
print "build_variant_of method: OK\n";
die "build_variant_package_name not defined\n" unless defined &{"Package::Variant::build_variant_package_name"};
print "build_variant_package_name method: OK\n";
' || {
    echo "❌ API verification failed"
    exit 1
}

echo "✅ All Package::Variant tests passed"
