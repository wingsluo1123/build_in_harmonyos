# libplist 2.8.0

Upgrade task 15225; preserve earlier published recipes. The upstream bundled
libcnary is part of this source, not a missing external dependency. The C and
C++ libraries and plistutil CLI are delivered; optional Cython bindings are not
enabled because this task adapts the C/C++ library.

The native compiler proves its own OHOS tuple. Signing applies only to newly
linked ELFs inside the task build directory. A private mktemp failure wrapper
selects Autoconf's own mkdir fallback on HMDFS. The generated configure script,
system tools, UID, SSH and other tasks are untouched.

All 43 original Automake tests remain enabled, including C++, timezone, integer,
binary/XML/JSON/OpenStep and CLI-stream cases. Automake removes the configured
`.test` suffix when naming `.trs` files; accounting therefore maps each original
test identity to its actual stem instead of incorrectly requesting `.test.trs`.
The first run had 43 PASS results but failed this accounting check; it is retained
as a failed transaction, not reused as a full successful run.

The fresh corrected native run passed both shared and static Conan builds with
43/43 original tests and 2/2 packaged consumers in each mode. The installed CLI
performs JSON→binary→XML→JSON through Chinese/space filenames and checks exact
Unicode keys/values, uint64, arrays, binary header, and malformed-input failure.
The C API consumer independently verifies binary encode/decode values.

## 编译结束

Official finish ran in libplist-finish-w3-20261015-r4: conan-verify and actual
W3 CI substep passed, followed by frozen twelve-phase validation and release.
The aggregate finish remains PARTIAL_POST_W3 for shared pre-existing knowledge
warnings (step5b/step8). This candidate supplies its own new draft pair, checked
separately by the blocking Pre-PR contract. No shared graph entry was modified.
The exact official mirror-list rewrite was restored to candidate conandata
bytes; original source hash and all other recipe inputs were unchanged. CI
proof/log are retained byte-for-byte, not hand-written. A real Conan cache save
export is retained locally under ignored packaging/, not committed as a binary.
See reports/test-report.md. Platform Review/CI and publication are later stages;
no published status is claimed.
