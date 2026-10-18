# mergedeep 1.3.4 preparation record

2026-10-14 author update / orrkri / task8806 / feat/mergedeep-1.3.4. Work is private and unpublished; the original unbudgeted native Goal remains blocked. No external software action lease.

Fixed v1.3.4 commit ab871aff9eccb5e1bf0ea237c3cff8f6787ebc56 and archive SHA9710916ed71b5b872fbdf3e221da3e8bf4e70da892aff5f85e0390d64308d221. Original source and test hashes match binding. Five added source lines enforce the existing concrete-type check before Mapping recursion. Original test bytes unchanged.

Actual Windows results: original suite14/14 PASS; setup.py install0 and installed consumer0 (1 program/20 functional vectors/20 public merge calls/2 identity checks). First bdist_wheel1 was missing host wheel command, preserved. Host Python3.12.14 consumer; existing Python3.11.0rc2 setuptools installer. No environment recreated. Actual new consumer on unpatched fixed source rejects at first strict conflict as expected; this qualifies the new consumer/signature, not a new original-suite run or old probe replay.

Conan unavailable on host; host evidence remains separate. H1-003 exact input cd0f5d5b22799f32f91be012155ddb0165ca86dcc757d9bfa77c8f76c8653d08 ran one official conan-verify on base f6a25613daaf1aec7170321c249d6ccf3f329593, Conan2.29.1, OHOS6.0/armv8/clang15/Release with supplied Python3.12.9. Real source/build/package/test_package PASS: unchanged upstream14/14 and package consumer1/1,20 vectors,20 merge calls,2 identity checks. Actual package module SHA a3fa951ba5ae9ed0c23751e8d45f8894794920e29c5fbc013b9a31a529f6fb2b and original test SHA47d076198f5990292158a6fa27830442cc9cc8b9d450faa70c2af5ff1ecb24bf match. Official temporary ghfast recipe export was restored to the original source data; its verification RREV is not a final publication RREV.

Native patch name is 0001-mergedeep-mergedeep.py.patch, SHA7601e3a7fbd613e825ceb39611b71cccc4ea7a9b9931d0f8132120ae8799bd63. The five added source lines and tests are unchanged. H1-002 missing-patch export failure and old inputs remain preserved. H1-003 finish/W3 calls0; H1-002 configure127 and full-tree JC1/JC5 failure remain. G4 reported PASS but returned on missing cache package ID; L2/L4/L5 skipped. Real package evidence supplements G4; no bin/ELF supports scoped CLI/ELF N/A, not a blanket L5 or W3 exemption.

W3-004 later completed the first missing whole W3 on the same fixed source and candidate004 input: official setup/build0, L0/L1 pass, L2 skip(no bin), L4 pass(patches clean), L5 pass(lib content), upstream14/14 and installed consumer1/1/20 vectors inside that W3. Official ci-result/log hashes match; owned PID/PGID3843 naturally gone. No extra manual Conan or whole finish was called. Old003 verifier skips and old002 failures remain distinct.

The official fixed-base mirror fallback changed post-W3 conandata from the original GitHub URL to [gh-proxy + URL, original URL], input SHA a2a5d4ff23f3754c5e61335d26e75fc526447b1a0ac1ab3b105ad55e8622cb09 versus post-W3 SHA0e04b78e700dcf107e8f2104fc24a3df758d60e761146e57d1b1d2b8dac5bc01. Archive SHA, patch fields, actual module and original tests are unchanged. Public candidate preserves the original source data; generated recipe revision is not falsely bound to original input bytes.

Manifest status=built means verified Conan build without upload; publication remains NOT_READY. Concrete PF9/software-metadata support and Conan pure-library submission-material applicability still need the original supported handling. No formal W4, AtomCode/comment, PR/Issue, CI, panel linkage, submission, merge, knowledge acceptance or points. Knowledge remains a draft without index changes. Author prepares exact Git base/head/tree/full12 diff and real report without validation replay; coordinator continues the original review/publication chain. All original evidence is indexed in private ENTRY.md.

---

**编译结束**: 2026-10-14T05:06:24.438595+00:00（W3-004原自然终态；北京时间2026-10-14T13:06:24.438595+08:00，本条为据原件补记）
**最终状态**: built（Conan及完整W3已验证，未upload；正式审阅、发布与有效提审按各自真实回执单列，本记录不表示整体完成）
