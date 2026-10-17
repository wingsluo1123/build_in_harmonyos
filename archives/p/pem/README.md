# pem

GNU Pem is a small command-line tool for recording personal income and
expenses and producing daily, monthly, and category reports.

## Features

- Records income and expense entries with optional categories.
- Produces daily and monthly summaries.
- Produces category-wise totals from locally stored CSV data.
- Keeps records under `$HOME/.pem` without requiring a database.

## HarmonyOS adaptation

- The installed `pem` command uses the target Perl interpreter discovered during
  packaging instead of the upstream `/usr/bin/env perl` shebang.
- The recipe runs `perl -c` before installation.
- The consumer test uses a temporary `HOME`, adds real income and expense
  records through the installed CLI, and validates daily, monthly, and category
  reports.

## Dependencies

- Runtime: Perl 5 with `POSIX` core support.

## References

- Upstream: https://www.gnu.org/software/pem/
- Source package: https://packages.debian.org/source/sid/pem
