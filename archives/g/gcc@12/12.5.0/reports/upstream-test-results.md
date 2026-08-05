# gcc@12 12.5.0 Upstream Test Results

## Scope

- Date: 2026-08-05
- Platform: HarmonyOS aarch64 validation device
- Package under test: `gcc12/12.5.0`
- Package folder: `/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/conan-home/p/b/gcc120ffaca3649874/p`
- Upstream source tree: `/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/conan-home/p/b/gcc12e130de926e59f/b/src`

Full GCC DejaGnu required an on-device Tcl/Expect/DejaGnu bootstrap because
`runtest` and `expect` were not available on the validation device. After
building Tcl 8.6.14, Expect 5.45.4, and DejaGnu 1.6.3 under the validation job
root, a DejaGnu execution probe passed. The full `make -k check
RUNTESTFLAGS="--target_board=ohos-gcc"` run was then attempted from the
completed build cache, but it stopped without a final `rc` file after
`make-check.log` reported `Musl Fortify runtime error: file descriptor 5138 >=
FD_SETSIZE 1024`. The partial `gcc.sum` snapshot had 27266 PASS, 4012 FAIL, and
3992 UNRESOLVED entries. This partial run is recorded only as incomplete
full-suite evidence and is not reported as a full DejaGnu pass rate.

The executed subset uses unmodified GCC upstream tests from the release source
tree. Each test was compiled with the packaged `gcc` or `g++`, linked with the
OHOS sysroot/library flags used by `test_package`, code-signed, and executed on
the device.

## Summary

- Upstream test case pass rate: 32/32 (100.0%)
- GCC C execution subset: 20/20 (100.0%)
- GCC C++ RTTI execution subset: 12/12 (100.0%)
- DejaGnu probe: 16/16 expected passes for
  `gcc.c-torture/execute/20000112-1.c` across compile and execution modes,
  including `-O3 -g`
- Full DejaGnu: attempted but interrupted before complete results; partial
  `gcc.sum` snapshot: PASS=27266, FAIL=4012, UNRESOLVED=3992

## GCC C Execution Subset

Source directory: `gcc/testsuite/gcc.c-torture/execute`

Selection: first 20 `.c` files sorted by file name, compiled with packaged
`gcc` at `-O2` and executed on OHOS.

| Result | Test |
| --- | --- |
| PASS | `20000112-1.c` |
| PASS | `20000113-1.c` |
| PASS | `20000121-1.c` |
| PASS | `20000205-1.c` |
| PASS | `20000217-1.c` |
| PASS | `20000223-1.c` |
| PASS | `20000224-1.c` |
| PASS | `20000225-1.c` |
| PASS | `20000227-1.c` |
| PASS | `20000313-1.c` |
| PASS | `20000314-1.c` |
| PASS | `20000314-2.c` |
| PASS | `20000314-3.c` |
| PASS | `20000402-1.c` |
| PASS | `20000403-1.c` |
| PASS | `20000412-1.c` |
| PASS | `20000412-2.c` |
| PASS | `20000412-3.c` |
| PASS | `20000412-4.c` |
| PASS | `20000412-5.c` |

## GCC C++ RTTI Execution Subset

Source directory: `gcc/testsuite/g++.dg/rtti`

Selection: 12 upstream `dg-do run` files covering RTTI, `typeid`, and
`dynamic_cast`, compiled with packaged `g++` and executed on OHOS.

| Result | Test | Options |
| --- | --- | --- |
| PASS | `cv1.C` | `-O2` |
| PASS | `dyncast2.C` | `-O2` |
| PASS | `dyncast3.C` | `-O2` |
| PASS | `dyncast4.C` | `-O2` |
| PASS | `dyncast7.C` | `-O2` |
| PASS | `pr83534.C` | `-O2 -std=c++17` |
| PASS | `typeid2.C` | `-O2` |
| PASS | `typeid4.C` | `-O2` |
| PASS | `typeid9.C` | `-O2` |
| PASS | `typeid10.C` | `-O2` |
| PASS | `typeid11.C` | `-O2` |
| PASS | `typeid12.C` | `-O2` |

## Commands

The subset runners are archived on the validation device:

```sh
/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/run-upstream-gcc12-subset.sh
/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/run-upstream-gcc12-cxx-run-subset.sh
```

Result logs:

```sh
/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/upstream-gcc12-subset.log
/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/upstream-gcc12-cxx-run-subset.log
```

DejaGnu probe and full-suite run:

```sh
/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/run-dejagnu-probe-ohos.sh
/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/run-dejagnu-full-ohos.sh
/storage/Users/currentUser/ohos-users/codex/gcc12-12.5.0-20260804-192814/dejagnu-full-latest.txt
```
