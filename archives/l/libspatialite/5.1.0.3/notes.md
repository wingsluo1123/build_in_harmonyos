# GUI data-format prerequisite restoration

This revision restores FreeXL/VirtualXL and MiniZIP required by the original
spatialite-gui import and virtual-table paths. It preserves the predecessor's
GEOS, PROJ, RTTOPO, XML, GeoPackage, native signing and HMDFS layout fixes.
Published Expat/2.8.5 is the selected current transitive XML parser baseline.
Native r1 built the real library and passed all108 original tests (zero skips),
then failed package_info before the consumer because force=True made Expat a
direct unused public dependency. It is now an override-only version selection,
matching the actual FreeXL-owned parser edge. r1 remains FAIL, fully released
with9 receipts; its108/108 is not carried into the new target transaction.

Claim: exact libspatialite/5.1.0.3 row, activity dependency, owner
2301_80739235, feat/libspatialite-5.1.0.3. No duplicate import/Issue/PR.
Source is official stable libspatialite 5.1.0 with adaptation suffix 3.

Original source changes inherited from the current archive will be replayed
onto a fresh official source tree and regenerated only by refresh-patch --auto.
No .patch file is hand-written/copied to this revision. The source/configure
repairs are described by the predecessor's exact eight patches; no source
conditional macro containing OHOS is introduced.

Native build, complete original tests, restored XLS/VirtualXL data consumers,
Harmony-specific test, official finish and new PR have not run yet. Do not
reuse historical 108/108 or consumer17/17 as this revision's result.

## Current verified result

Formal r4 finish RC0 and exact automatic marker/log hashes are archived in reports/current-test-evidence.json. Original108/108, consumer1 program with20 assertions and Harmony1 command passed. Old r1/r2/r3 failures retained; platform/GUI/release separate.

## Current CI checkout transport repair

Platform request118625/build105453 failed before build on omitted binary XLS diff payload. Canonical text carries the same6656-byte original fixture; the actual consumer materializer validates and invokes unchanged data tests. Fresh formal r6 completed original108/108, consumer1 program20 assertions and Harmony1/1; current complete local CI SHA256 3955e48f35977608ff8f38ca2c2805179f19d451219884281fcd23a05f78afce. Old target runs and failed platform build remain immutable. New platform HEAD/Review/CI/submission remain pending.
