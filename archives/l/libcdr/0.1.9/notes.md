# libcdr 0.1.9 native adaptation notes

Shared-library scope, docs/tools disabled. Upstream CppUnit testRead/testSeek: 2/2. Installed consumer executes actual CDR recognition/parsing and SVG generation, with HarmonyOS identity and TMPDIR file lifecycle: 14 assertions.

Dependencies: librevenge/0.0.5, full-header boost/1.90.0.3, icu/76.1, lcms/2.19.1, zlib/1.3.1; test cppunit/1.15.1. Downloaded ohpcd binary graph, no missing-dependency source builds.
Use task-private .la-free copies of the three librevenge static archives, scoped REVENGE/STREAM flags and explicit ICU/LCMS/ZLIB/CPPUNIT provider flags. Do not modify published dependency caches.

r1 failed due to a mechanical package-version replacement corrupting Boost into 1.90.1.9. Recipe corrected to 1.90.0.3. r2 actual build/tests passed, but frozen dependency metadata still contained that wrong Boost reference; it is not the final submission evidence. r3 corrected the metadata before freezing and repeated complete build/testing with unchanged recipe candidate. Old controllers and receipts were not rewritten.

Official LibreOffice/core sample writerperfect/qa/unit/data/draw/libcdr/pass/fdo65220-2.cdr; immutable blob aff705ffa5eefa8f98d7fbfa49c4f6793d2c3732, 10755 bytes, SHA256 88e62beb7a7ebe812f6ce06238017d07d215de9dbf76323dde93200f2d5dd348. Git blob identity independently verified. Fixture attribution/licensing closure remains a pre-submission check.

Final run libcdr-conan-20261011T0638Z-r3: Conan RC0, 2/2 upstream cases, consumer SVG pages=1, all 12 receipts/release/postrelease PASS.
Candidate SHA256 9abf7619887882f441ca8d8f16d87b7010230f2a5db6dd43c8373bf75f47814b.
Log SHA256 37f31a315a0583facf5b88c40e5ec0bd2bb62019022ff8a722361558bcfc8931.

## Formal validation and submission preparation

Official config.guess patch candidate passed `libcdr-finish-20261011-r1`: conan-verify and embedded W3 PASS, CppUnit 2/2, installed consumer 14 assertions and one SVG page. Raw W3 SHA-256 9085fa15deb78850b7e8d1e0e5d431eb3d4777c9afbbd9695133c779639eb2cc; integrity 3c8fb0d9599e2874. All 12 receipts and release/postrelease PASS. Aggregate finish RC1 only legacy step5b/step8 post-W3 readiness/staging; not whole-finish or worker-CI PASS.

Fixture source/identity and project-level licensing caveat are recorded in test_package/FIXTURE-NOTICE.md; no invented individual binary-file license. Registration inventory, immutable-log-derived summary, HD reassessment and E545-draft-CD11 are ready; remote submission still requires PRE/POST contract validation. No executable/recipe/patch or fixture changes after this formal run.
