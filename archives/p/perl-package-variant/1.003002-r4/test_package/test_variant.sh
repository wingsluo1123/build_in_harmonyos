#!/bin/sh
# test_package/test_variant.sh — smoke test for Package::Variant (pure Perl module)
# Verifies the package's Variant.pm is correctly installed, version matches,
# and core API functions are defined.
#
# Note: Cannot use `use Package::Variant` directly because the module has
# runtime dependencies (strictures, Import::Into, Module::Runtime) that are
# not available in the CI environment. Instead, we verify the installed .pm
# file content — this still substantively depends on the tested package.
set -eu

# Locate Variant.pm via PERL5LIB (set by conan package_info)
PM_FILE=""
for dir in $(echo "${PERL5LIB:-}" | tr ':' ' '); do
    candidate="$dir/Package/Variant.pm"
    if [ -f "$candidate" ]; then
        PM_FILE="$candidate"
        break
    fi
done

if [ -z "$PM_FILE" ]; then
    echo "❌ Package/Variant.pm not found in PERL5LIB paths"
    exit 1
fi
echo "[test] Found Variant.pm: $PM_FILE"

echo "[test] Checking version..."
VERSION=$(awk -F"'" '/\$VERSION =/{print $2}' "$PM_FILE")
if [ -z "$VERSION" ]; then
    echo "❌ Version not found in Variant.pm"
    exit 1
fi
echo "Version: $VERSION"
if [ "$VERSION" != "1.003002" ]; then
    echo "❌ Version mismatch: expected 1.003002, got $VERSION"
    exit 1
fi

echo "[test] Verifying package declaration..."
if ! grep -q "^package Package::Variant;" "$PM_FILE"; then
    echo "❌ Package declaration not found"
    exit 1
fi
echo "Package declaration: OK"

echo "[test] Verifying core API functions..."
for func in build_variant_of build_variant_package_name import; do
    if ! grep -q "^sub $func" "$PM_FILE"; then
        echo "❌ Function '$func' not defined in Variant.pm"
        exit 1
    fi
    echo "  $func: OK"
done

echo "[test] Verifying runtime dependency declarations..."
for dep in strictures Import::Into Module::Runtime; do
    if ! grep -q "use $dep" "$PM_FILE"; then
        echo "❌ Dependency '$dep' not declared in Variant.pm"
        exit 1
    fi
    echo "  $dep: declared"
done

echo "✅ All Package::Variant tests passed"
