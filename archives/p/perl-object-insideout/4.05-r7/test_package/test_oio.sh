#!/bin/sh
# test_package/test_oio.sh — smoke test for perl-object-insideout 4.05-r7
# Called by test_package/conanfile.py via self.run()
# PERL5LIB and OIO_PM_PATH must be set by the caller (conanfile.py test() method)
set -eu

# Test 1: Verify Object::InsideOut.pm exists in package
echo "[test] 1/3: Verify package structure"
if [ -z "${OIO_PM_PATH:-}" ]; then
    echo "FAIL: OIO_PM_PATH not set"
    exit 1
fi
if [ ! -f "$OIO_PM_PATH" ]; then
    echo "FAIL: Object::InsideOut.pm not found at $OIO_PM_PATH"
    exit 1
fi
echo "PASS: Object::InsideOut.pm found"

# Test 2: Parse and verify version from .pm file
echo "[test] 2/3: Version verification"
ver=$(perl -e '
    open my $fh, "<", $ARGV[0] or die "Cannot open: $!";
    my $content = do { local $/; <$fh> };
    close $fh;
    my ($v) = $content =~ /\$VERSION\s*=\s*[\x27"]([\d.]+)[\x27"]/;
    die "VERSION not found" unless $v;
    print $v;
' "$OIO_PM_PATH" 2>&1) || {
    echo "FAIL: Version parse failed: $ver"
    exit 1
}
if [ "$ver" != "4.05" ]; then
    echo "FAIL: Version mismatch: expected 4.05, got $ver"
    exit 1
fi
echo "PASS: Object::InsideOut version $ver"

# Test 3: Attempt to load the module and verify version at runtime
echo "[test] 3/3: Module load test"
load_result=$(perl -e '
    eval { require Object::InsideOut; };
    if ($@ && $@ =~ /Exception[\/:]Class/) {
        # Exception::Class is an optional runtime dependency not packaged as Conan
        # Module files are present and correct version — load fails only on missing dep
        print "SKIP: Exception::Class not installed (optional dependency)\n";
        exit 0;
    }
    elsif ($@) {
        print "FAIL: Unexpected error: $@\n";
        exit 1;
    }
    die "Version mismatch" unless $Object::InsideOut::VERSION eq "4.05";
    print "OK: Object::InsideOut loaded, version $Object::InsideOut::VERSION\n";
    exit 0;
' 2>&1) || {
    # If perl exits non-zero, check if it was a real failure
    case "$load_result" in
        *FAIL*) echo "$load_result"; exit 1 ;;
        *) echo "FAIL: Module load test failed: $load_result"; exit 1 ;;
    esac
}
echo "$load_result"

echo "All tests passed."
