# mrtgutils

`mrtgutils` is a small collection of command-line helpers that produce
MRTG-compatible counters from local system data:

- `mrtg-load` reports Linux-style load averages.
- `mrtg-uptime` reports uptime and idle-time counters.
- `mrtg-ip-acct` reports byte or packet counters from `/proc/net/dev`.
- `mrtg-apache` reads Apache `server-status` counters.
- `mrtg-sensors` reports a named hardware-monitor reading through libsensors.

All five upstream programs are built. `mrtg-sensors` needs libsensors,
which the recipe takes from the published `lm-sensors/3.6.0` package;
that package ships a static `libsensors.a`, so the installed binary has
no extra shared-library dependency.

## OHOS Adaptation

The upstream 0.8.4 archive contains `configure.ac` and `Makefile.am`, but
no generated `configure` script. The Conan recipe compiles the five
programs directly with the compiler supplied by the profile.

Two source fixes are applied:

- `mrtg-ip-acct` changes the non-standard `%Lu` integer conversion to the
  standard `%llu` conversion. The musl-based OHOS libc does not expose the
  GNU `%Lu` behavior and would otherwise omit the counter lines.
- `mrtg-load` passes the caller's average variable address to `setPos()`
  instead of storing the address of a by-value temporary. This removes the
  dangling pointer used by the `-l` selection path.

No platform macros or process-local stubs are introduced.

## Source

Source archive: `https://salsa.debian.org/debian/mrtgutils/-/archive/upstream%2F0.8.4/mrtgutils-upstream-0.8.4.tar.gz`

SHA256: `f72e31dd88abc82437b6407dfbda1d95a06681d96bca82ab2cec733668ca7f6e`

## Verification

The upstream 0.8.4 source has no automated test suite. The consumer test
checks all five packaged executables and exercises the deterministic
runtime paths for uptime, load, IP accounting, and argument validation,
including the argument path of the libsensors-linked `mrtg-sensors`.
A real Apache status request is intentionally not part of the test because
it needs an external Apache server.
