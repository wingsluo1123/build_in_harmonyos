#!/data/service/hnp/bin/bash
# test_package/test.sh — sixtunnel (6tunnel) consumer smoke test.
# Runs under bash in the conanrun env (PATH includes the installed bin/).
# Real on-device verification: the packaged 6tunnel binary must execute and
# print its version string "6tunnel 0.14".  This is the single real consumer
# test case (discovered=1).  On failure it exits non-zero so self.run() in
# conanfile.py raises and the HMBS_TEST_PACKAGE_RESULT marker is not emitted.
set -eu

out="$(6tunnel -V 2>&1)" || {
    echo "[test] FAIL: 6tunnel -V returned rc=$?"
    exit 1
}
echo "[test] 6tunnel -V -> $out"
case "$out" in
  6tunnel*0.14*)
    echo "[test] PASS: packaged 6tunnel printed expected version"
    ;;
  *)
    echo "[test] FAIL: unexpected version output: $out"
    exit 1
    ;;
esac
exit 0
