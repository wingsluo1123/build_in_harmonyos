# KProperty 3.2.0 — native validation

Date: 2026-10-14. Target: OHOS 6.0 arm64, Clang 15, C++17, one build job.
Official native verification/W3 passed in kproperty-formal-20261014-r2;
all 12 receipts passed and released. Official W3 log SHA256:
6cb50364d1aac8f5ad028a48440c03e88224a62603775fdeae209d06dd3a1dd8.
Aggregate finish is PARTIAL_POST_W3 RC1 (step5b,step8), not full finish PASS.
Independent W5/Pre-PR and platform review/CI govern subsequent stages.

| Upstream registered entry | Real scope | Result |
| --- | --- | --- |
| KPropertyTest | Original testNull method and all its assertions | PASS |
| KPropertySetTest | Original testEmpty and testGroupNameForProperty | PASS |
| HeadersTest | Original generated independent public-header compilation | PASS |

The denominator is three registered entries, containing three QtTest methods
plus the generated header compilation group. It is not four or six tests
created by counting QtTest initialization/cleanup hooks. All original test
methods and GUILESS entry points are preserved in the final candidate.

Installed consumer: 5/5 assertion groups: construction, mutation, insertion,
clear, and Qt5 QTranslator loading the installed French QM and checking
General -> Général. All upstream translation catalogs are built with released
Qt6 lconvert/lrelease tools used only in the build context. No Qt6 library is
substituted for the Qt5/KF5 host ABI.

Frozen run: kproperty-w3-20261014-r9. Tested candidate tree:
`b94c60a58cf6e5c61c9d40b565da9c7b7030bf40`.
Conan create RC0; all 12 transaction receipts validated; release W3_PASS.
Log SHA256: `0de754bbcc306f2bd21f8953da597db94b81a9e0282c5e85d6a7189fd60f41a0`.
Primary installed core library SHA256:
`5fcde093ab0c6f50a1850e99005b0af97cca0a661d54c0c20f28e9b422a06e5b`.
This is headless library validation, not proof of native desktop interaction.
