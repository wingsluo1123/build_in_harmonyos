#!/data/service/hnp/bin/bash
# test_ipc_run3.sh — Test IPC::Run3 module functionality on OpenHarmony
# Called by conan test_package conanfile.py via self.run()

set -eu
set -o pipefail

# PERL5LIB is set by conan environment (package_info runenv_info)
export PERL5LIB="${PERL5LIB:-}"
export PATH="/data/service/hnp/bin:${PATH:-}"

PERL=/data/service/hnp/bin/perl

echo "=== Test 1: Load IPC::Run3 and check version ==="
RESULT=$($PERL -MIPC::Run3 -e 'print "IPC::Run3 version: ", $IPC::Run3::VERSION, "\n"' 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL: IPC::Run3 load test failed: $RESULT"
    exit 1
fi
echo "PASS: $RESULT"

echo "=== Test 2: Capture stdout from subprocess ==="
RESULT=$($PERL -MIPC::Run3 -e 'my @cmd=("echo","hello"); my $out; run3 \@cmd, undef, \$out; print "stdout: ", $out' 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL: stdout capture test failed: $RESULT"
    exit 1
fi
echo "PASS: $RESULT"

echo "=== Test 3: Pipe stdin to subprocess ==="
RESULT=$($PERL -MIPC::Run3 -e 'my $in="test data"; my $out; run3 ["cat"], \$in, \$out; print "piped: ", $out' 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL: stdin pipe test failed: $RESULT"
    exit 1
fi
echo "PASS: $RESULT"

echo "=== Test 4: Capture stderr from subprocess ==="
RESULT=$($PERL -MIPC::Run3 -e 'my $err; run3 ["sh","-c","echo error_msg >&2"], undef, undef, \$err; print "stderr: ", $err' 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL: stderr capture test failed: $RESULT"
    exit 1
fi
echo "PASS: $RESULT"

echo "=== Test 5: Non-zero return code handling ==="
RESULT=$($PERL -MIPC::Run3 -e 'my $out; run3 ["sh","-c","exit 42"], undef, \$out; print "exit code: ", ($? >> 8), "\n"' 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL: return code test failed: $RESULT"
    exit 1
fi
echo "PASS: $RESULT"

echo "=== All tests passed ==="
