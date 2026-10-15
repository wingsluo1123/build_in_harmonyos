# Native HarmonyOS test report — tlsrpt 0.5.0

Date: 2026-10-15. Target: HarmonyOS PC aarch64, OHOS SDK Clang 15.0.4,
Conan 2.29.1. Isolated task worktree and Conan home.

```text
CREATE_RC=0
tlsrpt/0.5.0@ohpcd/stable#c765feb8a3b87072e9480594c2412c64:6b129b068851896169fae42d399fa922d239ce8a#a6d0fddd8f1e7f6d94fe97900f5d673d
```

Upstream test audit: no test directory or automated test registration in the
official v0.5.0 archive. `make -j1 check` executed:

```text
make: Nothing to be done for 'check'.
HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}
```

Installed artifacts: `lib/libtlsrpt.a` (28292 bytes), `include/tlsrpt.h`,
`include/tlsrpt_version.h`, `licenses/COPYING`. Both archive members report
`ELF64` / `AArch64` through the SDK's llvm-readelf.

CMake consumer linked the installed `tlsrpt::tlsrpt` target and executed:

```text
PASS version
PASS errors
PASS allocator
PASS no_connection
PASS long_path
PASS connection
PASS success
PASS failure
PASS multiple
PASS cancel
PASS no_policies
PASS nested
PASS unfinished
PASS missing_receiver
tlsrpt 0.5.0: 14/14 functional cases passed
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"consumer_total":14,"consumer_passed":14}
```

The success, failure and multiple-policy cases receive real datagrams and
compare their complete decoded JSON objects. No tests were skipped.

Platform capability probe:

```text
bind relative.sock rc=-1 errno=1
bind /storage/Users/currentUser/work/frj__/tlsrpt.sock rc=-1 errno=1
bind /data/local/tmp/tlsrpt.sock rc=-1 errno=13
bind /tmp/tlsrpt.sock rc=-1 errno=30
bind @tlsrpt-probe-050 rc=0 errno=0
```

Negative control using the exact unpatched upstream C sources and the same
success-scenario consumer, compiled natively:

```text
tlsrpt_finish_policy(dr, TLSRPT_FINAL_SUCCESS) returned 35009: TLSRPT error in call to fprintf in finishpolicy
UNPATCHED_RC=1
CONTROL_EXPECTED_FAILURE_CONFIRMED
```

Path A only. Existing E461 explains the socket restriction; the existing
`libtlsrpt/0.5.1` recipe documents the memory-stream close behavior.
