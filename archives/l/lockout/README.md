# lockout

`lockout` is a Perl command-line utility that can impose a temporary
self-restriction by changing the root password and running administrator-
provided hooks.

## Features

- Reports the scheduled unlock time with `lockout status`.
- Provides lock, unlock, and usage flows through one self-contained Perl script.
- Uses cron or administrator-provided scripts for unlock automation.

## HarmonyOS adaptation

- The installed script uses the target Perl interpreter discovered during
  packaging rather than `/usr/bin/env` or a fixed system path.
- The recipe runs `perl -c` before packaging.
- The consumer test only exercises `status` and the usage path. It deliberately
  never calls `lock`, `unlock`, password changes, or user modification.

## Dependencies

- Runtime: Perl 5 and core modules `Fcntl`, `POSIX`, and `Getopt::Long`.

## References

- Upstream: http://thomer.com/lockout/
- Source package: https://packages.debian.org/source/sid/lockout
