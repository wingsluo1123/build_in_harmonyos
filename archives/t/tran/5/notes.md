# tran 5 adaptation notes

`tran` is a single Perl filter plus a directory of character conversion tables.
The recipe preserves the upstream shebang flags, replaces the interpreter with
the target Perl path, and adds a core `FindBin` import.

The upstream `$DATA="data"` path is relative to the current working directory.
The packaged copy changes it to `$FindBin::RealBin/data` and installs the data
directory next to the executable.  This keeps `tran list` and transliteration
working regardless of the caller's directory.

The task directory and branch keep the upstream release number `5`. Conan
requires a version of at least two characters, so `set_version()` publishes the
artifact as `tran/5.0`; this matches the repository's single-character-version
adaptation pattern while keeping L0m and the task branch aligned.
