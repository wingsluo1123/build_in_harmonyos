# libxls 1.6.4

The upgrade preserves the published 1.6.3 version and uses its own task branch.
No external Conan library is required: the native libc provides iconv. The
official release tar and SHA-256 are retained. No generated configure file is
edited, and no upstream test or assertion is removed.

The OHOS compiler tuple is obtained from the configured compiler, not invented
as a GNU Linux triplet. Native compiler outputs are signed in the task build
directory. A task-private mktemp wrapper deliberately returns failure so that
Autoconf uses its existing mkdir fallback on HMDFS; it does not manufacture a
successful temporary-directory result or change system permissions.

Both shared and static Conan packages were built in a fresh private native
transaction. The upstream registered `test_libxls` and original C and C++
examples were executed; there is only one Automake TESTS entry, not three.
Consumers validate version, workbook/sheet geometry, invalid-buffer errors,
installed CLI conversion through a Chinese path containing spaces, and missing
input rejection. No compiler-assertion count is treated as a test count.

The CLI always prints `FILE: <input>` on stdout and its actual default separator
is semicolon despite help saying comma. The end-to-end test separately verifies
the filename banner, selects the first actual sheet, compares data bytes and
checks 24 rows / 11 columns using the real separator. Initial consumer-check
failures were retained as failed runs; none was relabeled PASS.

## 编译结束

Official finish ran in libxls-finish-w3-20261015-r9: conan-verify and its actual
W3 CI substep passed; the frozen twelve-phase native transaction also passed
and was released. The aggregate finish remains PARTIAL_POST_W3 (step5b and
step8: existing shared graph completeness/knowledge warnings). The new draft
pair is provided by this candidate and validated separately by Pre-PR; no
shared knowledge file was modified to hide those warnings.

The official CI's exact mirror-list rewrite was restored only after its
original URL/source hash had been proven unchanged. The real CI proof and log
are copied byte-for-byte; they were never generated or rewritten by hand.
An actual `conan cache save` export of the built native package is retained
locally under ignored packaging/, not submitted as a build artifact.

See reports/test-report.md. Pre-PR/Review/platform CI and publication remain
separate later stages; no platform success is claimed here.

## CI checkout transport repair

Build #93393 failed before Conan in checkout-pr: the platform text .diff endpoint
did not include binary patch data for test_package/test2.xls. This is not the
bot's generic source-download timeout or a demonstrated main-branch conflict.
Following existing binary-PR-diff transport knowledge, the required fixture is
now canonical LF Base64 plus an exact manifest, decoded only in the isolated
test build folder. Strict decoding rejects malformed/non-canonical text, wrong
manifest, size/hash drift, linked paths and foreign output files. Original
fixture: 35840 bytes, SHA-256
df7d4e07b72284c17ecca138412b48d4217041e5f81a7c297b331c546a20604a.
No test data, upstream case or consumer assertion was removed or relaxed.

Direct transport checks passed 4/4. Fresh libxls-conan-w3-20261015-r6 passed
both shared/static 3/3 upstream + 2/2 consumers, including exact decoded bytes;
official finish r10 also passed Conan verification/W3 and its complete native
receipt/release chain. Aggregate shared-graph warnings remain separately noted.
This repair reuses existing transport guidance; it does not claim a duplicate
new knowledge topic. E552 retains the distinct output-envelope increment.
