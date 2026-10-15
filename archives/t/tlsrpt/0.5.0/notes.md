# tlsrpt 0.5.0 — HarmonyOS PC adaptation

Task **11185**, path **A**, branch `feat/tlsrpt-0.5.0`.
The task name `tlsrpt` refers to upstream **sys4/libtlsrpt v0.5.0**.
It is a C library for generating and sending TLSRPT datagrams; the report
collector/reporter daemon is a separate application.

## Source and build

- Official release: <https://github.com/sys4/libtlsrpt/releases/tag/v0.5.0>
- Archive: `libtlsrpt-0.5.0.tar.gz`, SHA256
  `90a266d6be3dc3390342614e1f54e1eddf13b0ea208b900740ec01f28f30cd9f`.
- Native upstream Autotools `configure` + `make -j1` + `make -j1 check`.
  The release includes generated configure; no autoreconf is needed.
- OHOS SDK Clang 15.0.4, aarch64, Conan 2.29.1, HarmonyOS PC.
- Static `libtlsrpt.a`, upstream `tlsrpt.h` + generated `tlsrpt_version.h`,
  upstream LGPL COPYING; zero third-party runtime dependencies.
- `configure` identifies its platform through a Linux-compatible host triplet
  because bundled config.sub predates OHOS. The actual compiler remains the
  OHOS SDK compiler from `tools.build:compiler_executables`.
- Writable build-local temporary directories, an executable configure shell,
  and `umask 022` handle the existing HMDFS/Autoconf environment constraint.
- Validation used a private Conan home and worktree because another build
  was active in the shared cache. Only this task's private download cache was
  seeded with the hash-verified official archive when direct GitHub timed out.
  The committed recipe retains the official URL and checksum for CI.

## Two portability patches

1. **Flush memory streams before close.** OHOS memory streams need `fflush`
   to publish the JSON buffer before `fclose`, which can report `EBADF`.
   The helper always closes the stream, preserves a real flush error and its
   errno, and tolerates only the known close-time EBADF after successful flush.
   It covers all three policy substreams and the main report stream.
   The unpatched 0.5.0 success scenario fails in `tlsrpt_finish_policy` with
   error **35009**; the patched package passes the same functional scenario.
   The existing `libtlsrpt/0.5.1` recipe documents this libc behavior.
2. **Abstract Unix datagram endpoints.** The tested execution domain rejects
   HMDFS pathname `bind` with `EPERM`; `/data/local/tmp` returns `EACCES` and
   `/tmp` returns `EROFS`. Binding an abstract endpoint succeeds. Existing
   knowledge **E461** covers this platform boundary. Additive `@name` syntax
   selects the abstract namespace and uses the exact sockaddr length for
   `sendto`. Ordinary pathname addresses retain their previous behavior.
   The connection structure is opaque; public function signatures are unchanged.

On HarmonyOS use `tlsrpt_open(&con, "@collector-name")` with a collector bound
to the same abstract name. The separate reporter must support/configure this
namespace. The tests use a real in-process Unix datagram receiver and do not
substitute a fake sendto implementation or accept failed sends as success.

## Test inventory and results

Upstream automated cases: **0**. Audit `Makefile.am` for `TESTS`,
`check_PROGRAMS`, `check_LTLIBRARIES` and test targets, and inspect the release
file list for test directories. None are present. The generated `make check`
target executes successfully with `Nothing to be done for 'check'`; it is not
counted as an upstream test case. There are no removed/skipped upstream tests.

New functional consumer cases: **14/14 passed, 0 skipped**:

1. Exact version plus compatible/incompatible version requests.
2. Internal/libc error classification, errno extraction and descriptions.
3. Connection and request allocation failure plus allocator restoration.
4. Rejection and cleanup of a request without a connection.
5. Rejection of a socket name exceeding sockaddr_un capacity.
6. Connection lifecycle, socket descriptor and blocking-mode API calls.
7. STS success report, with exact decoded JSON equality after real reception.
8. Failure report including quote/backslash/newline/tab escaping.
9. Multiple STS/TLSA/no-policy entries, failure counters and optional fields.
10. Cancellation suppresses transmission and clears the request handle.
11. Empty requests fail with NOPOLICIES and transmit no report.
12. Nested policies fail with NESTEDPOLICY and transmit no report.
13. Unfinished policies fail with UNFINISHEDPOLICY and transmit no report.
14. An absent receiver produces the real sendto error, not a successful report.

`test_package` uses CMakeDeps `find_package(tlsrpt)` / `tlsrpt::tlsrpt`,
compiles the C consumer against the installed static library, and runs all
cases with per-process timeouts. Python decodes the three successful datagrams
and compares their complete objects. No external daemon/network is required.

```sh
conan create archives/t/tlsrpt/0.5.0 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing \
  --user=ohpcd --channel=stable -c tools.build:jobs=1
```

Result: **CREATE_RC=0**. Evidence is in `reports/test-report.md` and the
machine-readable HMBS markers in the build/test output. This is path A;
the portability issues are covered by existing knowledge, with no B/C claim.
