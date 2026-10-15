# DRAFT-libklibc-2.0.14-ohos-clang-malloc-builtins — Clang builtins in libc upstream tests

> **Contributor**: iKalous_OscarP | **Status**: DRAFT | **Updated**: 2026-10-15
> **Scope**: libklibc 2.0.14, HarmonyOS PC AArch64, Clang 15

## Problem and scope

The upstream `usr/klibc/tests/malloctest3.c` checks allocator edge cases directly. Its unchanged assertions require `malloc(0)` to return NULL (line 15), reject allocations near `SIZE_MAX`, allow a 4 GiB + 1 allocation (line 31), and reject overflowing `calloc` products (lines 38 and 42).

When Clang compiles this test with its malloc/calloc builtins enabled, `malloctest3` fails even though the test is linked to klibc. The first failing assertion is the zero-size `malloc` check. This is a test compilation issue: the calls must reach the target allocator for the test to measure its behavior.

## Evidence and diagnosis

| Experiment | Test source | Compiler flags | Observed result |
|---|---|---|---|
| Initial device suite | Unmodified upstream source | Clang defaults | 38/39 upstream programs pass; `malloctest3` first fails at `malloc(0)` line 15 |
| Isolate malloc builtin | Unmodified source | `-fno-builtin-malloc` | The line 15 assertion advances; the next failure is the `calloc` overflow assertion at line 38 |
| Disable both allocator builtins | Unmodified source | `-fno-builtin-malloc -fno-builtin-calloc` | Every `malloctest3` assertion passes |
| Allocator control | Unmodified source and original klibc mmap flags | Both test-only flags above | `malloctest3` passes without an allocator `MAP_NORESERVE` patch |

The staged assertion failures isolate each builtin: disabling only malloc changes the first failure to the calloc overflow check; disabling both makes the same test source pass. A separate run with the allocator patch removed also passes, so this failure does not justify changing klibc's mmap behavior.

## Recommended fix

Pass `-fno-builtin-malloc -fno-builtin-calloc` only to the upstream test build. Keep the upstream C sources and their assertions unchanged, then run every discovered upstream test and count all results. In this task, the recipe keeps a strict 39-program denominator and treats the upstream `testrand48` vector printer as passing only when its expected output matches, despite its intentional return code of 1.

Do not skip `malloctest3`, disable assertions, or patch the test source. Do not add an allocator workaround before checking whether the compiler rewrote the test calls.

## Distinction from existing malloc knowledge

This entry is separate from `DRAFT-ohos-autotools-rpl-malloc` and E568. Those entries cover the **configure-time** `AC_FUNC_MALLOC` run probe in a cross build, which can select an unavailable `rpl_malloc` replacement. This entry covers **test-compilation-time** Clang builtins changing calls in an actual upstream allocator test. The phases, symptoms, and fixes differ: use an Autoconf cache value for the former, and test-only compiler flags for this case.

As independent evidence that zero-size allocation behavior varies across C libraries, the repository's Xlib compatibility header at `archives/x/xeyes/1.3.1/x11include/X11/Xlibint.h:450-453` notes that some systems do not return a valid pointer for `malloc(0)`, while Xlib expects one. This corroborates the need for tests to observe the target allocator; it is not evidence for the Clang-builtin root cause itself.

## Verification record

The complete final no-`MAP_NORESERVE` package run is recorded in the accompanying `archives/l/libklibc/2.0.14/notes.md`. It requires all 39 upstream programs, zero failures, zero not-built programs, and zero skips, plus both consumer and HarmonyOS-specific package tests.



## Final device run

The final package recipe, without the discarded allocator patch, completed Conan create with exit code 0. The upstream suite reported **39 passed, 0 failed, 0 not-built, 0 skipped**. Both package programs passed: the klibc consumer probe and the HarmonyOS system-libc 4 GiB + 1 sparse-map probe. The device create used `tools.build:jobs=2`; Kbuild cleared inherited `MAKEFLAGS` and ran the library and test targets at `-j1` because HMDFS rejects jobserver FIFO creation.
