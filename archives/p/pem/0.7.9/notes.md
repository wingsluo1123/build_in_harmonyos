# GNU Pem 0.7.9 adaptation notes

GNU Pem is a single Perl script.  The installed command is renamed from
`pem.pl` to `pem`, and its shebang is rewritten to the target Perl interpreter.
The build runs `perl -c` before packaging.

The consumer checks create a temporary HOME so that records are written below
that directory.  The shell smoke test exercises the installed CLI, while the
independent Python consumer case persists an income and a categorized expense,
parses the generated CSV directly, and then validates daily, monthly, and
category reports.  No data in the caller's real `$HOME/.pem` is touched.
