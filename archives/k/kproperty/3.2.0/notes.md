# KProperty 3.2.0 — target validation complete, submission pending

Task #7917 is assigned to 2501_91199785 on feat/kproperty-3.2.0.
Use repo-kproperty-clean, not the diagnostic failed full Windows clone.

## Dependency and build boundary

Host: released Qt5 qtbase 5.15.2.2, KF5 Config/CoreAddons/GuiAddons/
WidgetsAddons 5.116.0. Build only: ECM 6.20.0 and qttools 6.11.1.1.
W0 resolves 14 distinct recipe/package revisions including build-context
dependencies. Do not replace host Qt5 with Qt6 or rebuild an unpublished
dependency variant. All upstream translation catalogs remain enabled.

## Failure recovery

- r1: ECM lookup before project() could not see a late toolchain variable;
  pass ECM_DIR and prefixes through configure cache arguments.
- r2: CMake 4 rejects CMP0059 OLD, and Qt5Core metadata referenced missing
  producer-build mkspecs. Use supported NEW policy and shadow only CMake
  metadata in this build, pointing to the provider's real package mkspecs.
  Never mutate the provider cache or signed ELF.
- r3: no released Qt5LinguistTools provider; use actual released Qt6
  lconvert/lrelease executables through an explicitly labelled command
  adapter, then verify their QM output with real Qt5 QTranslator.
- r4: test subprocesses lacked this build/package's shared lib directories;
  the header-test child configure also lacked the native toolchain/prefixes.
- r5: header test passed but GUILESS tests aborted creating an error dialog.
  r6/r7 temporarily tried QApplication; this only changed abort to timeout.
  Source inspection traced the modal fallback to missing library RCC lookup.
- r8: restore the original GUILESS sources and prepend installed package
  share to XDG_DATA_DIRS. All three original upstream entries now pass.
  runenv_info exports the same resource root for installed consumers.
- r8 consumer configure separately failed because released KF5 recipes opt
  out of CMakeDeps. The aggregate Conan consumer enables config generation
  for their actual cpp_info interfaces instead of requesting missing
  generic config files or changing dependency packages.
- r9: native Conan create RC0, upstream 3/3 entries and installed consumer
  5/5 assertions including French QM -> Général. Complete 12-receipt W3_PASS
  after release. Every earlier failed transaction remains FAIL.

## Evidence and remaining work

See reports/test-report.md. W3 log SHA256:
0de754bbcc306f2bd21f8953da597db94b81a9e0282c5e85d6a7189fd60f41a0.
Knowledge draft pair: E551-draft-BAS1. Formal finish, current classification,
unique Issue/Pre-PR contracts, PR creation, platform review and CI remain
pending. Headless library validation does not prove native desktop UI support.

## Formal W3 closure

kproperty-formal-20261014-r2: official verification/W3 passed with 3/3 complete
registered entries and all 5/5 installed consumers, including Qt5 loading
the real French QM. All 12 receipts passed and released.
Tested tree e1ded30622007fa03242991db491b849bb486f49.
Official W3 log SHA256: 6cb50364d1aac8f5ad028a48440c03e88224a62603775fdeae209d06dd3a1dd8.
Aggregate finish remains PARTIAL_POST_W3 RC1 for step5b,step8 only, not full
finish PASS. The actual released package/cache backup, not hand packaging,
backs the legacy local submit check. Runtime control/artifact files stay ignored.

**编译结束**：正式原生 W3 已通过；平台 Review/CI 与发布仍待 PR 后执行。
