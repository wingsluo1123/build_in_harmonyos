# mblaze

mblaze is a set of C command-line utilities and shell scripts for processing messages in Maildir folders. The upstream 1.1 release builds with GNU make and uses POSIX APIs. This Conan archive builds and installs all 20 compiled commands, six shell scripts, four command aliases, manual pages, and the upstream license text.

The source is the [upstream v1.1 tag archive](https://github.com/leahneukirchen/mblaze/archive/refs/tags/v1.1.tar.gz), pinned by SHA256 in `1.1/conandata.yml`. The core C tools have no external Conan dependencies. Some shell commands require an external mail sender or terminal tools at runtime; the Conan consumer tests cover local Maildir and MIME operations, not delivery to an external mail service.

The upstream `make check` target uses Perl `prove` to run 12 TAP shell scripts. This archive runs the same scripts sequentially with terminal stdin and checks all 135 TAP assertions using a Python standard-library runner. This preserves `isatty(0)` behavior and avoids depending on Perl in the target environment. Following registered knowledge `knowledge/graph/E413.kv`, skipped or TODO assertions are not counted as passes. The test suite and installed-command consumer checks passed on WSL Linux x86_64 and in official OHOS armv8 Buildbot #75007 for code commit be070f52.
