# Native HarmonyOS test report

Date: 2026-10-12. HarmonyOS 6.0 AArch64, Clang 15, OHOS Conan 2.29.1.

Upstream suite: zero formal cases; not applicable.

Added consumer cases: 2/2 passed (100%).
- Installed-program exact versions: 1/1 passed.
- HarmonyOS-specific loopback TCP/UDP experiment in user storage: 1/1 passed, 5 finite nonnegative samples.

W3: L0/L1/L2/L4/L5 pass. Full log: w3-local-ci.log. Original tool-generated log SHA256: f2dedfc240b21bd9233344f52178ec5ae02210d84b66eea7cc4bcdb43a0acec4

Initial failures were caused by upstream fixed 100-byte parameter writes, fixed by the portability patch. Pre-download helper reported missing curl and fell back to Conan; Conan successfully downloaded and verified the source archive. Main-branch junk markers caused whole-tree checks to fail; after a feature commit, the unchanged check passed for this PR scope.
