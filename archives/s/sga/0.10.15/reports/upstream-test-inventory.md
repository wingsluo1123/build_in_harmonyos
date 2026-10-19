# SGA 0.10.15 upstream test inventory — 2026-10-15

INVENTORY_COUNT=0

The source under review is the official `jts/sga` tag `v0.10.15`, not an
invented test directory. Source archive SHA-256:
`1b18996e6ec47985bc4889a8cbc3cd4dd3a8c7d385ae9f450bd474e36342558b`.

GitHub's complete, non-truncated recursive tag tree has 403 blobs and SHA
`0944b3f163d127ffb6bbfc03bd284a47c6b90018`. Its full file set exactly equals
the archive's 403 regular members. The independently fetched default branch
tree (`229293b2c97777aa015581b6075ed6b60050b34d`) also has these same four
test-substring paths, with no directory named `test` or `tests`:

| Matching path | Actual role | Counted upstream test? |
| --- | --- | --- |
| `Dockerfile.testing` | Installs prerequisites, builds and installs SGA; explicitly build-only | No |
| `src/GraphDiff/VCFTester.cpp` | Production variant-analysis implementation in `libgraphdiff_a_SOURCES` | No |
| `src/GraphDiff/VCFTester.h` | Header of that production class | No |
| `src/Thirdparty/rapidjson/filewritestream.h` | Production JSON stream; `test` occurs inside the name `filewritestream` | No |

All 13 `Makefile.am` files and `src/configure.ac` were inspected. None
registers `TESTS`, `check_PROGRAMS`, `check_SCRIPTS` or `check_LTLIBRARIES`.
The C/C++ and script source inventory has no Boost.Test, GoogleTest or
equivalent registered test suite. `src/examples` contains external-data
example workflows, not four self-contained regression cases. This conclusion
is based on the role and build wiring of each candidate, not merely the
absence of a particular test framework.

Therefore original upstream test count remains **0**, not 4. The six added
functional checks and installed UTF-8-path workflow (two assertions) are
disclosed separately. Their actual native evidence remains the released
`sga-ci-fix-210-20261015-r6` transaction; the original log is not edited.
This documentation-only correction changes no recipe or runtime input.

Reproducible authorities:

- [Official tag tree](https://api.github.com/repos/jts/sga/git/trees/v0.10.15?recursive=1)
- [Default branch tree](https://api.github.com/repos/jts/sga/git/trees/master?recursive=1)
- [Build-only Dockerfile](https://github.com/jts/sga/blob/v0.10.15/Dockerfile.testing)
- [GraphDiff source registration](https://github.com/jts/sga/blob/v0.10.15/src/GraphDiff/Makefile.am)
- [VCF production implementation](https://github.com/jts/sga/blob/v0.10.15/src/GraphDiff/VCFTester.cpp)
- [RapidJSON stream](https://github.com/jts/sga/blob/v0.10.15/src/Thirdparty/rapidjson/filewritestream.h)
