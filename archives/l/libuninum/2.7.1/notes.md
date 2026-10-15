# libuninum upstream 2.7, adaptation repair 2.7.1

Task #15063 is a claimed dependency repair for msort. The suffix denotes an
adaptation repair, not a new upstream release. Issue #3918 is the single OPEN
issue. The public UTF32=unsigned long ABI remains unchanged.

The published 2.7 CLI patches are retained. The new fix replaces five internal
wcs* casts with typed UTF32 operations, preventing short length calculations
and undersized Chinese-normalization buffers on LP64. The temporary normalized
heap string is checked and released. It was not an escaping alloca pointer;
the early hypothesis was rejected by inspecting the returned malloc copy.

Native config.guess uses the actual configured compiler's -dumpmachine.
Configure binds /bin/sh after Conan activation, and OHOS uses installed LLVM
archive tools rather than an absent GNU ar. GMP headers and libraries propagate
to consumers because public uninum.h exposes mpz_t.

Two original Tcl scripts contain 26 input vectors and 44 output systems.
upstream.py executes all of them and asserts every printed outcome, retaining
the original unsupported/invalid-input/non-BMP return semantics. Unexpected
errors are not waived. r6 native Conan create RC0, upstream 70/70 assertions,
installed API/CLI consumers 8/8, full receipt/release validation W3_PASS.
Log SHA256: 4eabbc1b0492b2f7d79be3b8d4738c073a0ac4d9cd1dbee168e95d21c147944b.

r11 official finish now completed with local CI RC0, 70/70 upstream assertions,
8/8 consumers and all 12 W3 receipts released PASS. Whole finish remains native
RC1 because step5b/step8 post-W3 knowledge/legacy readiness failed; these are
handled independently by current knowledge and two-stage submission contracts,
not relabelled whole-finish success. Reports preserve the exact result/log and
actual primary CI package identity. Published Bash/Git were provisioned only
inside the task cache; no framework or shared device state enters this PR.
No artifact upload or downstream dependency substitution has occurred.
Knowledge E15063-draft-2501 is submitted with this software only.

2026-10-12 CI86351 first failed in config.status confstat directory creation,
then make reported no Makefile. OHOS now binds both creation branches to a
fresh .autoconf-tmp directory, mkdir under umask007, and preserves cleanup.
r12 official local CI exit0, upstream70/70 and installed consumers8/8;
all12 receipts and release/postrelease PASS. Full finish RC1 retains only
step5b/step8 failures; conan-verify cache-path skips are not execution passes.
Full log SHA256 5d52f7d79d2a872701d33300a33ca77f30736b8a377da04e03d88c59f8d011c9.
E15163 adds causal diagnosis of swallowed generation errors, not another
claim to invent the already documented HMDFS permission repair.
