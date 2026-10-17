# ladvd 1.1.2 test report

## Scope

- Target: HarmonyOS PC 6.0, AArch64, Clang 15, Release
- Recipe: `ladvd/1.1.2`
- Direct dependencies: `libevent/2.1.13`, `libpcap/1.10.6`
- Test dependency: `check/0.15.2`
- Source archive SHA256:
  `3391ad591eb6a97b19fdf243f2bb0dc54a93f0f4a3980e8240ac0ffab353d0d4`

## Native clean build

The formal W3 local-CI run exported the final recipe from the official archive
under the `ohos-aarch64` host and build profiles. It completed the quality
gates, clean Conan build, complete upstream suite, package installation, ELF
signing, installed-package test, and HarmonyOS consumer case successfully.
The W3 log and its generated receipt are the sole build evidence cited by this
report; exploratory run logs are not part of the submitted evidence set.

- W3 exit code: 0
- W3 log SHA256:
  `0c60128ad22b7e4f336d55c63eadf52887d4d8772a60887b299ff55b2af4896e`

## Upstream tests

Upstream registers seven Check executables containing 45 `START_TEST` cases.
All were built, signed, and executed by unfiltered `make check -j1`:

| Executable | Cases | Result |
|---|---:|---|
| `check_compat` | 4 | pass |
| `check_proto` | 10 | pass |
| `check_util` | 8 | pass |
| `check_tlv` | 2 | pass |
| `check_parent` | 9 | pass |
| `check_child` | 7 | pass |
| `check_cli` | 5 | pass |
| **Total** | **45** | **45/45 pass** |

No executable or case was filtered. Two test source adaptations are declared
in `test_package/MANIFEST.yml`; neither removes an assertion nor changes a
protocol expectation.

The `check_util` adaptation also has a Path B evidence record. Check 0.12.0
generated the function `test_my`, while Check 0.13.0 and the packaged 0.15.2
generate the internal function `test_my_fn`. The test now derives its expected
function prefix from `__func__` instead of binding the oracle to either
framework implementation. See `path-b-evidence.md` for the three-arm boundary
and the retained device-log hashes. The focused target comparison is 7/8 with
the original hard-coded oracle versus 8/8 after patch 0010; the final complete
suite is 7/7 executables (45 cases), all passing.

## Installed-package tests

`test_package` resolves the tested package's absolute `bin` directory and
checks the installed `ladvd` and `ladvdc` entries. It runs both commands with
`-h` and independently verifies their return code, version text, and usage
text.

- Auxiliary assertions: 13
- Result: 13/13 pass

## HarmonyOS-specific consumer test

One end-to-end consumer case runs the signed installed command as
`ladvd -d -o -s -L` on the native HarmonyOS PC. This is not counted as a set
of assertion-only tests: it is one complete production workflow. The process
initializes the daemon, creates its privilege-separation process pair,
discovers target interfaces, emits the real 24-byte Ethernet pcap stream
header, reports the child exit status, and shuts down the parent cleanly.

- HarmonyOS-specific consumer cases: 1
- Result: 1/1 pass
- Bounded execution: 15 seconds
- Installed artifact: the absolute `bin/ladvd` from the tested Conan package

## Platform capability probe

An independent target probe successfully created both
`AF_UNIX/SOCK_SEQPACKET` and `AF_UNIX/SOCK_STREAM` sockets. Consequently, the
upstream stream fallback is not entered on this target. No Path B claim is
made for fallback framing, short-read reconstruction, or related semantics.
