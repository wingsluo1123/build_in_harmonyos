# Test Report - asterisk-odbc 22.10.1

**Status:** the configured device runner has completed its isolated category
campaign. The upstream inventory has 125 entries that were not registered by
this test configuration, so the source-inventory result remains partial.

## Test scopes

| Scope | Inventory | PASS | FAIL | SKIP | Not executed | Result basis |
|---|---:|---:|---:|---:|---:|---|
| Asterisk upstream internal tests | 724 | 559 | 26 | 14 | 125 | `559/724` (77.21%). The 14 skips are 9 runtime `NOT RUN` results plus 5 protected framework self-tests. |
| Current device registration | 599 | 559 | 26 | 14 | 0 | 594 normal entries ran in clean categories; the remaining 5 are deliberately protected or intentionally failing self-tests. |
| Package consumer probe | 1 | 1 | 0 | 0 | 0 | Official CI #42701 at `a23d26ee75`; current-device `conan test` also passed for mutex recipe rrev `a744e096...`. |

The source-inventory row is not a claim that all 724 tests executed: 125 were
not registered by the current full-runner configuration. The package probe is
an independent product check and must not be added to upstream counts.

## Observed environment causes

- [Case-level evidence](upstream-test-failure-matrix.md) maps every one of
  the 26 failures to its result XML and repair boundary. It reconciles the
  25 category failures plus one separately executed explicit-only WebSocket
  test, and it records five items whose root causes still require minimal
  device probes rather than treating a hypothesis as a conclusion.
- The device `/tmp` is read-only. Several failures use fixed `/tmp` paths;
  device-only preload workarounds are test harness inputs and are not recipe
  changes.
- `test_strings` hits musl fortify aborts for a deliberately undersized test
  buffer. A temporary test-module rebuild with `-U_FORTIFY_SOURCE` passed the
  single test; source and packaged ODBC modules remain unchanged.
- The initial serial command stopped during `more_destruction`; the clean
  `/main/threadpool/` category subsequently passed 16/16. The final count uses
  80 root categories so nested category prefix matching is not double-counted.
- The failure matrix assigns a device-verified cause to each of the 26
  failures: 19 runner-fixture, two full-PBX WebSocket module-graph, one
  full-PBX timezone-data path, one HarmonyOS `/dev/null` poll-semantics case,
  and three test-capture pipe-drain cases. They are not evidence against the
  packaged ODBC modules.

## Package validation

- Current-device `conan create` package build: passed at recipe rrev
  `a744e096929b9b22842d211bdaa90fc1`, package revision
  `16c0f27d84febbcce59e43a387cdf1a7`.
- Current-device `conan test`: passed after the probe learned the device's
  `llvm-readobj` fallback; checked 7 modules and 6 sample configuration files.
- Official CI #42701: passed at `a23d26ee75`.

The current OHOS recursive-mutex source patch is covered by the package build
and consumer test above. The initial automatic test step exposed only a probe
tool-discovery assumption and did not invalidate the built package.
