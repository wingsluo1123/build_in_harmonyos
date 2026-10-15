# libuninum 2.7.1 native test report

Conan create: PASS, RC0, OHOS armv8 Clang 15.0.4, one build job, clean task cache.
Run libuninum-w3-r6-20261012-upstream-assertions, product tree
0360764f476aa79c6e55271c38919dc6a088b85f.

| Source inventory | Executed | Assertions passed | Skipped |
|---|---:|---:|---:|
| TestStringToNumber.tcl original inputs | 26 | 26 | 0 |
| TestNumberToString.tcl original systems | 44 | 44 | 0 |
| Installed API/CLI consumer groups | 8 | 8 | 0 |

The 70 upstream outcomes consist of 60 numeric results and 10 specific
source-defined error returns. An expected invalid-input rejection is not a
successful numeric conversion; neither is it an execution skip. The wrapper
rejects wrong numbers, different errors (including allocation failure), row
loss, stderr and nonzero exit. It does not trim the scripts or retry them.

Raw log SHA256:
4eabbc1b0492b2f7d79be3b8d4738c073a0ac4d9cd1dbee168e95d21c147944b.
Full package:
libuninum/2.7.1#45b3744a9c9e16fc6dc73dcef4ce675c:504014e02a7e90aad722612f5b3526cd5f20316b#999f7f68612b4bdb86466c47a0b20084.
Frozen validator W3_PASS, 12 receipts, runner absent after release.

## Official local CI: r11

Run libuninum-w3-r11-20261012-official-finish-ci-artifact, frozen product tree
a694751610247130c03abbf44d6180312f95b3e5. Runtime closure is unchanged from r6;
later README/report/index additions are metadata only.
Official finish ran unchanged. setup.sh and build_and_test.sh returned RC0,
one package succeeded; upstream 70/70 and installed consumers 8/8. L0/L1/L4/L5
and the destructive dependency check passed. L2 version/help is nonblocking
SKIP, not PASS; the real bidirectional CLI consumer passed.
The task-private copied project has no .git directory; its final Git warning
does not certify repository checkout gates. Host candidate/PR scope is checked
separately by the submission contract.

Official CI result exit_code=0, integrity_hash=4e9a334272f4459b, matching log
SHA256 ef2d290f733ec52bec2aa203f7825773e81d832d139297abf195ad4f8ded0208.
Whole finish native RC1, PARTIAL_POST_W3: only step5b/step8 failed (post-W3
knowledge/legacy readiness). This is not a whole-finish PASS. Current paired
knowledge and PRE_CREATE/POST_CREATE must independently pass before submission.

Collected full log SHA256:
28197d8bead6e80484d130ea1abb84eb7dfa87bc3c5dc0dbdcb89d34bd12b722.
Actual primary CI package:
libuninum/2.7.1#45b3744a9c9e16fc6dc73dcef4ce675c:504014e02a7e90aad722612f5b3526cd5f20316b#db36204a08c15fa8b0d9f6be2476e2ac.
Its numconv SHA256:
576591b1d4dc0f140ce6e51a56c98ce060ea47c8534931ae9a6bce3effa565c3.
Frozen validator returned W3_PASS with 12 receipts, release/postrelease PASS,
runner absent. No result or artifact was borrowed from a different run.

No platform CI/AI Review or release success is claimed by this report.

## 2026-10-14 rule12 native consumer validation

Run: libuninum-rule12-20261014-r2. Full upstream 70/70; original API/CLI groups 8/8; new OHOS installed CLI file-roundtrip flow 1/1. Unique total 79 (not 5 extra record cases or 3 extra process cases). Western -> Arabic_Western -> Devanagari -> Western_Lower, Unicode filenames, full UTF-8 bytes/newlines and a 100-digit record verified. Conan test() invokes this automatically on runnable OHOS.

Native 12-receipt release/postrelease PASS. Full raw log SHA256: ad2e3dd33a7d0030579223ee2ab99a7b2bcf2558f91967e20acdd46dbed3bdeb. Official CI log SHA256: bfc77fda8b08a10d1781abdfb0b2f6d81e1ac007c04c23d02dbfd547cbf6aeed. Whole-finish post-W3 failures remain unchanged; current-head platform CI/review not claimed. Earlier report sections describe historical runs, not the current added-test count.
