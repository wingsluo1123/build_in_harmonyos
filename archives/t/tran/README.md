# tran

`tran` is a Perl command-line filter that transliterates text between
character scripts using configurable data tables.

## Features

- Converts text read from stdin between Latin and several historical or
  alternative scripts.
- Lists available scripts with `tran list`.
- Supports aliases and user-supplied data directories.
- Includes data tables for Greek, Cyrillic, Devanagari, full-width forms, and
  other scripts.

## HarmonyOS adaptation

- The installed script uses the target Perl interpreter discovered during
  packaging.
- The upstream relative `data` directory is anchored to the installed script
  location with `FindBin`, so the tool works from any current directory.
- The consumer test verifies script discovery and real Greek transliteration.

## Dependencies

- Runtime: Perl 5 and its core `FindBin` module.

## References

- Upstream: https://github.com/kilobyte/tran
- Source package: https://packages.debian.org/source/sid/tran
