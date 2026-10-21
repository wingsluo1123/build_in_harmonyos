# SGA

String Graph Assembler 0.10.15, implemented in C++.

## OHOS adaptation

Build with the archived Conan recipe. All getopt_long return values retain
int; help/version success alone cannot verify this parser boundary. The
functional driver tests both indexes and exact inverse-BWT data roundtrips.
Upstream registers no test suite; supplemental checks are labelled separately.

## Dependencies

bamtools 2.5.3, sparsehash 2.0.4 and zlib 1.3.1.1 must be released first.

## Validation

See 0.10.15/reports/test-report.md for the native data-path W3 result.
Formal finish, Pre-PR, platform review and CI are not yet complete.
