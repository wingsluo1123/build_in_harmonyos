# POA 2.0-20060928

Official source: https://downloads.sourceforge.net/project/poamsa/poamsa/2.0/poaV2.tar.gz
SHA-256: d98d8251af558f442d909a6527694825ef6f79881b7636cad4925792559092c2.
Byte-identical to Debian poa_2.0+20060928.orig.tar.gz; the task version uses a hyphen.
License: GPL-2.0-or-later, attributed by Debian copyright because upstream omits a
license file. Copyright metadata, provenance and the official GPL-2.0 text are packaged.

CMake builds the complete upstream library/CLI scope, including the public
matrix_scoring_function callback. Three patches add build/install rules, CLI help/version
and standard extern declarations. No upstream alignment behavior is changed.

Upstream has no registered test suite or check/test target. Tests retain its README
example and six Debian downstream scenarios, plus ten CLI and eight API scenarios.
See reports/test-report.md for results and environment limits.
