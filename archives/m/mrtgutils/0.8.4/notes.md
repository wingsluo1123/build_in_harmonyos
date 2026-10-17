# mrtgutils 0.8.4 adaptation notes

## Upstream identity

- Software: mrtgutils, five MRTG helper commands.
- Version: 0.8.4.
- Upstream source: the Debian-maintained `upstream/0.8.4` tag on salsa.debian.org, commit `6e830b74b96ed350884a3c95518d189058ba6582` (2022-04-01).
- License: GPL-2.0-or-later, recorded by the Debian source package and the upstream project.
- The release archive contains `Makefile.am` and `configure.ac` but no generated `configure` script.

## Build approach

The upstream Makefile.am compiles the MRTG helpers and links each with the common `uptime.c` and `util.c` translation units. The recipe does the same direct compilation with the Conan-provided clang, so the CI worker does not need autoreconf, Automake, Libtool, pod2man, or a host pkg-config setup.

The `mrtg-sensors` command needs libsensors, which is not part of the OHOS base image. The recipe therefore requires the `lm-sensors/3.6.0` package from the artifact repository and links its `libsensors.a` into the program, which keeps the installed binary free of an extra shared-library dependency. All five upstream programs are packaged.

## OHOS/musl fixes

### 1. `%Lu` is not a portable integer format

`mrtg-ip-acct.c` uses the GNU extension `%Lu` for `unsigned long long` values in both `sscanf()` and `printf()`. GNU libc accepts it, but the musl-based OHOS libc does not provide the same integer conversion: the `%Lu` output path produced no counter lines in a musl test. The patch changes all four occurrences to the standard C99 `%llu` spelling.

This is a real runtime regression, not a cosmetic warning. The consumer test asserts that `mrtg-ip-acct lo` emits two numeric lines before its uptime and hostname output.

### 2. `mrtg-load` kept a dangling pointer

`setPos()` accepted `double i` by value and stored `&i` in the caller's selected pointer. That object ceases to exist when `setPos()` returns, so `mrtg-load -l 1` dereferenced dangling storage. The patch passes a pointer to the caller's actual `avg1`, `avg5`, or `avg15` variable and preserves the original two-selection semantics. The consumer test runs `mrtg-load -l 1` and checks the two numeric output lines.

No platform macro is introduced. Both changes are plain C and remain correct on glibc.

## Upstream tests

The upstream 0.8.4 tag has no `tests/` directory, no test driver, and no `check`/`test`/`verify` target in `Makefile.am`. The Debian packaging branch of the same project contains a downstream packaging test, but that is not part of the upstream release source and is not presented here as upstream coverage.

## Consumer test

`test_package/test_mrtgutils.sh` performs six checks against the installed binaries:

1. all five executables are present and executable;
2. `mrtg-uptime -t sys -u s` emits two numeric values;
3. `mrtg-load -l 1` emits two numeric values, covering the dangling-pointer fix;
4. `mrtg-ip-acct lo` emits two numeric values, covering the `%llu` fix;
5. `mrtg-apache` with no hostname fails and prints usage;
6. `mrtg-sensors` with no chip/label arguments fails and prints usage.

The test does not claim to run a real Apache status endpoint. That requires a configured Apache server and is outside the deterministic CI surface.

## Known limitations

- `mrtg-sensors` needs a readable hwmon device and a configured sensor label before it can print a reading; the packaged test therefore covers its argument/usage path only.
- `mrtg-apache` needs a reachable Apache status endpoint for its real data path. The packaged test covers its argument/usage path only.
- `mrtg-uptime` and `mrtg-load` read Linux-style `/proc` files; OHOS provides the required procfs interfaces for these commands.
