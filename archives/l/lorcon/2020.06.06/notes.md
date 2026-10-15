# lorcon 2020.06.06 adaptation notes

- Upstream is tag `2020.06.06` of https://github.com/kismetwireless/lorcon
  (commit `7dbf24ee6f7c277240c0fbd988b6902850577772`), a generic library
  for injecting 802.11 frames. Archive SHA256 verified in `conandata.yml`.
- Build system is Autotools (`configure` + hand-written `Makefile.in`,
  libtool `liborcon2.la`). Packet capture needs real libpcap at configure
  time (`AC_CHECK_LIB(pcap)` is a hard error); `libnl` netlink support is
  optional in upstream configure and is left to auto-detect (absent on OHOS
  means mac80211 VAP control is compiled out, packet forge/packasm stay
  fully usable).
- OHOS portability handling (zero committed patches, all in `build()`):
  `umask 077` -> `022` for HMDFS; `config.sub` aarch64 case backfill for
  vintage files; `linux/wireless.h` hard error relaxed to a warning so a
  sysroot without wireless extensions still configures (the mac80211
  driver is already guarded by `SYS_LINUX && HAVE_LINUX_WIRELESS &&
  HAVE_LIBNL`, and `iwcontrol.c` is guarded by `HAVE_LINUX_WIRELESS`).
- Upstream test audit (evidence round, replaces the prior no_tests claim
  falsified by the preflight清单): `Makefile.in` has no `check`/`test`
  target (verified raw targets are only all/install/clean/distclean/
  dep/depend), no `tests/` directory, no CTest/gtest/pytest wiring. The
  only automated suite is `pylorcon2/test.py` with 10 python_def unittests
  (`testGetVersion`, `testListDrivers`, `testFindDriver`, `testAutoDriver`,
  `testInjection`, `testTimeout`, `testVap`, `testGetDriverName`,
  `testChannel`, `testMAC`; upstream `setUp` does
  `PyLorcon2.Context('wlan0')`, 8/10 methods call `open_injmon`/
  `open_monitor`/`send_bytes`/`set_channel`/`set_hwmac`/`auto_driver`).
  `testGetVersion` never touches `Context`/iface (only
  `type(get_version()) == int`, verified against the tag source fetched
  2026-10-15) and executes for real via the packaged `lorcon_test`
  binary (`CHECK-OK: version=` line, `LORCON_TEST_BIN` handoff); the
  other 9 require monitor-mode 802.11 injection hardware absent on
  HarmonyOS PC, so `test_package/upstream_pylorcon2_tests.py` mirrors the
  identical 10 IDs with 1 executed + 9 explicit unittest skips
  (`status: incomplete`, `discovered: 10`, `executed: 1`, `passed: 1`,
  `skipped: 9`, `gaps: [{count: 9, category: ohos_feature}]`), fixing
  the rule4 `executed: 0` incomplete (rule4 requires passed only on
  full execution, so 1/10 must report incomplete, not passed). Remaining
  `pylorcon2/test-multi.py`, `test-packet.py`, `test-packet-filter.py`,
  `test-packet-scapy.py` and `ruby-lorcon/test.rb` are hardware/pcap demos
  with zero assertions, not counted. Hence `upstream_tests_exist: true`,
  `upstream_test_total: 10`, `upstream_test_count_method: python_def`;
  consumer coverage stays in `test_package/test.c`.
- Consumer test (`test_package/test.c`, 4 assertions, no hardware):
  `lorcon_get_version` non-zero; `lcpa_*` init/append/size/freeze/free
  roundtrip; `lcpf_beacon` produces a non-empty frame; and
  `lorcon_parse_ht_channel("6")` parses to `LORCON_CHANNEL_BASIC`.
- Notes on driver listing: upstream `lorcon_list_drivers()` is guarded by
  `USE_DRV_*` macros that upstream never defines, so it always returns
  NULL; the consumer test deliberately does not assert on driver listing.
- Dependency investigation (3 preflight rounds, all failing in conancenter
  `m4/1.4.19` with `configure[139]: /data/service/hnp/bin/bash:
  inaccessible`): round-1 shell hardening only covers lorcon's own build;
  round-2 pin `1.10.6` -> `1.10.1` was FALSIFIED (preflight downloaded
  conancenter RREV `a695cc40` for 1.10.1; CCI `config.yml` hosts
  1.10.6/1.10.5/1.10.4/1.10.1 under one `all` recipe with unconditional
  `bison/3.8.2` + `flex/2.6.4` tool_requires), and was reverted.
  `ci/conan/setup.sh:130-133` disables conancenter on CI ("private CI
  builds"), but preflight queries it, so every shared libpcap version
  resolves to the CCI autotools recipe that cannot build in the container.
- 2nd-strategy cycle (this round): prior root-cause assumption ("fix the
  shell" / "pick another shared version") is abandoned as proven invalid
  above -- no shell patch inside lorcon can fix a conancenter m4 build,
  and no shared version escapes the CCI `all` recipe. Different route:
  remove the Conan-level libpcap requirement entirely and build the
  official libpcap 1.10.6 sources privately with CMake inside lorcon's
  `build()` (same URL/SHA as published `archives/l/libpcap/1.10.6`, zero
  committed patches; build-time `cmake_minimum_required` bump for CMake
  4.4.3 and `pcap-linux.c` sockaddr_storage guard, mirroring the 1.10.1
  recipe). The private static archive is shipped in this package as
  `libpcap.a` (`cpp_info.libs = ["orcon2", "pcap"]`, no
  `libpcap::libpcap` transitive requirement), so neither CI nor preflight
  enters the conancenter bison/flex/m4 chain. Upstream `configure` still
  sees a REAL libpcap (headers + `pcap_open_live`), so this is not a stub:
  capture/inject symbols resolve and the forge/packasm consumer test links
  both archives. `test_package` accordingly requires only the tested
  reference.
- OHOS shell/TMPDIR hardening (retained from round 1, defense-in-depth for
  lorcon's own configure): profile `CONFIG_SHELL/SHELL` may point at an
  inaccessible `/data/service/hnp/bin/bash`; `generate()`/`build()` select
  an actually executable shell (preferring HMBS `SHELL=/bin/sh`, mirroring
  `archives/m/m4/1.4.19`) and use a private `build_folder/tmp` TMPDIR.
- Lex-shim fix (this round, fixes preflight `checking for lex output file
  root... unknown` + `Neither flex nor lex was found`): root cause in our
  shim, not the environment. The shim ignored flex's default-output
  protocol: autoconf's root probe runs `$LEX conftest.l` with no `-o`
  and looks for `lex.yy.c`/`leyy.c`, but the shim wrote `scanner.c`,
  so the probe found nothing. It also answered `-t` with empty stdout.
  Fix: parse `-o`/`--header-file`/`-t` properly; with no `-o` emit
  `lex.yy.c` (real flex behaviour); `-t` emits generated C to stdout;
  tiny autoconf probes get a minimal compilable stub re-using the
  probe's own trailing C code (with FLEX_SCANNER markers), while only
  real `scanner.l` inputs (name or >8KB + `pcap_` marker) replay the
  committed flex 2.6.4 bytes. Verified locally: probe creates
  `lex.yy.c` with `yylex`/`yywrap`, `-t` emits >200 bytes, replay is
  byte-identical (229035 bytes).
- 4th-strategy cycle (this round, fixes preflight
  `configure: error: Neither flex nor lex was found` in
  `_build_vendored_libpcap`): the vendoring route is abandoned as
  proven unbuildable on the worker. Evidence: (1) the libpcap-1.10.6
  release tarball contains only `scanner.l`/`grammar.y.in` (verified by
  listing the 311-entry archive: no `scanner.c`/`grammar.c` shipped),
  so Autotools AND CMake builds both mandate real flex 2.5.31+ and
  bison (`AC_PROG_LEX` hard error + capable-lex functional test +
  `AC_CHECK_PROGS(BISON_BYACC, bison)` hard error; CMake
  `find_program(LEX_EXECUTABLE ... FATAL_ERROR)` likewise); (2) the
  worker has neither (`checking for flex... no`, `checking for lex...
  no`); (3) `grammar.y` is generated by config.status at configure
  time, so even touching shipped files cannot skip the bison step in
  an out-of-source build. Different route: `requirements()` now
  declares `libpcap/1.10.6` (team-published, status published,
  identical official tarball+SHA) from the ohpcd remote; CI disables
  conancenter so it resolves to the prebuilt OHOS binary with no
  source build and no flex/bison chain. lorcon's own configure needs
  no generators (verified: its `configure.ac` has no
  `AC_PROG_LEX`/`YACC` checks; only libpcap/libm hard deps + optional
  libnl), so it configures cleanly once AutotoolsDeps supplies the
  libpcap flags. `conandata.yml` drops the vendored source entry
  (also removes the flaky tcpdump.org download + IncompleteRead retry
  noise); `package()`/`package_info()` no longer ship/link a private
  `libpcap.a` (`cpp_info.libs = ["orcon2"]`, pcap arrives
  transitively). Download headline note: both lorcon (github) and
  libpcap (tcpdump.org) URLs in the failing log show `Sources
  correctly downloaded`; the IncompleteRead was retried successfully,
  so no mirror swap was made (SHA unchanged per R39).
- Vendored-build fix (this round): the first vendored attempt failed inside
  `_build_vendored_libpcap` with `Could not find toolchain file:
  .../conan/conantoolchain.cmake` plus `CMAKE_MAKE_PROGRAM is not set` /
  `CMAKE_C_COMPILER not set`. Root causes in our code, not the environment:
  (1) hardcoded the stale `conantoolchain.cmake` name while Conan 2.x
  generates `conan_toolchain.cmake` (log confirms); now located dynamically
  via `*toolchain*.cmake` glob with legacy fallbacks and a hard error
  listing the generators dir when absent; (2) bare `self.run(cmake)` does
  not source conanbuild env, so the HMBS tools dir is not on PATH for the
  "Unix Makefiles" generator; now `-DCMAKE_MAKE_PROGRAM` is passed
  explicitly from `HMBS_MAKE` / `user.hmbs:make_path` / `which make`, and
  cmake path also honors `user.hmbs:cmake_path`. No test assertions or
  dependency set changed.
- Compiler fix (this round): with the toolchain file resolved, vendored
  CMake configure failed at `project()` with `The CMAKE_C_COMPILER:
  /data/service/hnp/bin/clang` (check program cannot run) -- the same
  "profile absolute path inaccessible in container" class as the SHELL
  failure, with in-repo precedent (`archives/l/libnids/1.26` probes CC the
  same way). Different route from last round (which fixed file names/make
  program): `build()` now really execs `<exe> --version` over the conf
  compiler, `$CC`/`$CXX`, the HNP absolute path and PATH `clang/cc/gcc`
  candidates, keeps the first with exit 0, and pins it via explicit
  `-DCMAKE_C_COMPILER/-DCMAKE_CXX_COMPILER` (command line wins over the
  toolchain file) for the vendored build plus `CC=/CXX=` configure args
  for lorcon itself. Empty probe result keeps the toolchain default so the
  genuine error still surfaces.
- 5th-strategy cycle (this round, fixes preflight CCI m4/1.4.19
  `configure[139]: /data/service/hnp/bin/bash: inaccessible`): the
  `requires("libpcap/1.10.6")` route is abandoned as proven
  unresolvable on preflight. Root cause, verified against evidence:
  every requireable libpcap version (1.10.6 published, 1.10.1 built)
  is also hosted on conancenter under one `all` recipe whose
  `build_requirements()` unconditionally tool_requires bison/3.8.2 +
  flex/2.6.4 (fetched current CCI conanfile.py to confirm); the
  preflight dual-remote resolution selects the CCI recipe, its bison
  pulls CCI m4/1.4.19, and CCI m4 honors the profile's bad SHELL with
  no workaround possible from this package. The multimail/0.52
  pin-to-ohpcd-only-version trick cannot apply: no ohpcd-only libpcap
  version exists (CCI hosts 1.10.6/1.10.5/1.10.4/1.10.1/1.10.0).
  Different route: zero Conan requirements; official libpcap 1.10.6
  sources (same URL/SHA as published archives/l/libpcap/1.10.6)
  build privately via Autotools configure with deterministic flags
  (--disable-shared/dbus/rdma/bluetooth/usb, --with-snf=no,
  --without-dpdk, --without-libnl) and the same toolchain CFLAGS/
  LDFLAGS lorcon itself uses (persisted at generate() time, so the
  OHOS sysroot travels along). Worker has no flex/bison (both are
  hard gates: AC_PROG_LEX + capable-lex `$LEX ... -t` probe +
  `bison -V` version parse, confirmed in configure.ac): vendor/
  commits the four generator outputs produced offline by REAL flex
  2.6.4 + GNU Bison 3.8.2 (winflexbison v2.5.25, the exact CCI
  toolchain versions) from this tag's scanner.l/grammar.y.in
  (@REENTRANT_PARSER@ -> %define api.pure) with upstream's own flags;
  vendor/tools shims replay them through LEX/BISON_BYACC as
  `python3 shim.py ...` (no +x needed on the chmod-less fs). Verified
  locally: 28/28 grammar tokens in grammar.h, bison silent under
  %expect 38, all shim invocation forms byte-identical to the
  committed files. libpcap.a + pcap headers ship inside this package
  (cpp_info.libs = ["orcon2", "pcap"]); pcap-linux.c sockaddr guard
  replicates team 1.10.6 patch 0003 at build time, zero committed
  patches. Capture backend stays auto-detected (V_PCAP=linux when the
  sysroot provides linux/socket.h); consumer tests never open a
  device, so backend choice cannot affect evidence.
- Lex-library probe fix (this round, fixes preflight `checking for lex
  library... not found` + `library containing yywrap... no` +
  `Neither flex nor lex was found`): different strategy from last round
  (which fixed the shim's default-output protocol -- that worked, the
  root probe now reports `lex.yy`). Root cause of the new failure:
  modern AC_PROG_LEX links its conftest scanner, which calls plain
  `yywrap()`, against `-lfl`/`-ll`; the worker ships neither library,
  so configure sets `LEX=:` and libpcap hard-errors. The real build
  genuinely needs no lex library: the committed flex-2.6.4 scanner is
  reentrant with `#define yywrap pcap_wrap` (vendor/pcap_gen/scanner.h
  lines 258-261), and make consumes the replayed scanner.c/h directly.
  Fix: pass autoconf cache override `ac_cv_lib_lex='none needed'` on
  the vendored configure command line (documented autoconf mechanism,
  correctly quoted as one argv), so LEXLIB is empty and LEX stays valid.
- Yacc-slot fix (this round, fixes preflight `checking for byacc... no`
  + `checking for yacc... no` + `Neither bison, byacc, nor yacc was
  found`): different strategy from the last two rounds (shim protocol,
  then lex-library cache). Root cause in our recipe, not the worker:
  libpcap's configure locates the parser generator via AC_PROG_YACC,
  i.e. the YACC variable with byacc/yacc program fallback, and never
  consults BISON_BYACC (the CMake-slot name this recipe exported
  alone); configure therefore searched PATH, found nothing, and
  hard-errored. Fix: export YACC plus BISON/BYACC/BISON_BYACC aliases
  through the same env(1) prefix, all pointing at the validated
  bison replay shim.
- Own-configure SHELL scrub (this round, fixes preflight `.../b/configure[157]: /data/service/hnp/bin/bash: inaccessible or not found` on lorcon's own configure): different layer from all prior rounds (which fixed only the vendored libpcap configure -- that one now succeeds and installs man pages/libpcap.a). Root cause in our recipe, not the worker: lorcon's own configure ran via the Autotools helper, which re-exports the profile buildenv CONFIG_SHELL/SHELL through conanbuild, while the vendored configure ran under an env(1) scrub that wins over conanbuild; additionally _select_shell() accepted the bad bash on isfile+X_OK alone (the path exists with +x in the shared-fs view but exec fails in the isolated namespace). Fix: (1) _select_shell() really execs `shell -c true` and keeps the first with exit 0 (HMBS SHELL=/bin/sh first, profile bash last); (2) new _run_lorcon_configure_and_make() runs lorcon configure under `env CONFIG_SHELL=<good> SHELL=<good>` with the same prefix/triplet/shared flags the helper used, plus `make SHELL=<good> -j1`; (3) package() runs `make install ... DESTDIR=<package_folder>` with the same SHELL override. No test or dependency change.
- In-source build fix (this round, fixes `clang-15: error: no such file or directory` for all 15 lorcon sources + `Makefile:114: .depend: No such file` after the SHELL scrub let configure succeed): different layer from last round (SHELL re-exec). Root cause in upstream build files, not the worker: lorcon's hand-written Makefile.in has no VPATH/srcdir indirection and its .depend rule expands bare `*.c` names, so the out-of-source Makefile generated in the default build-folder cwd cannot find any source. Fix: run lorcon's own configure and make with cwd=source_folder, and run package() install from source_folder as well; vendored libpcap stays out-of-source in its private build dir. No test or dependency change.
- ifcontrol include fix (this round, fixes 12 errors `variable has incomplete type 'struct ifreq'` + `use of undeclared identifier 'IFNAMSIZ'/'IFF_UP'` + implicit `rindex` in ifcontrol_linux.c): different layer from last round (in-source build -- that worked, compilation now starts). Root cause in upstream sources, not the worker: ifcontrol_linux.c declares almost none of what it uses, relying on glibc transitive includes, and ifcontrol_linux.h provides struct ifreq only via <linux/if.h> under HAVE_LINUX_WIRELESS, which is undefined on OHOS. Fix: build-time insert of direct headers (stdio/string/strings/errno/sys/socket/sys/ioctl/netinet/in + <net/if.h> guarded by #ifndef HAVE_LINUX_WIRELESS so wireless-enabled glibc builds keep <linux/if.h>). Zero committed patches. No test or dependency change.

- madwifing include fix (this round, fixes 9 errors `variable has incomplete type 'struct ifreq'` + `use of undeclared identifier 'IFNAMSIZ'` in madwifing_control.c): different file from last round (ifcontrol_linux.c -- that fix worked, build progressed to the next object madwifing_control.lo). Root cause is the same OHOS sysroot class but a second translation unit: madwifing_control.c already includes sys/socket + sys/ioctl yet struct ifreq/IFNAMSIZ live only in <net/if.h> on OHOS (glibc provides them transitively). Fix extends the same build-time helper to also insert guarded `#ifndef HAVE_LINUX_WIRELESS / #include <net/if.h> / #endif` + netinet/in.h after `#include "ifcontrol_linux.h"` in madwifing_control.c (fallback after errno.h). Zero committed patches. No test or dependency change.

- Bison-slot fix (this round, fixes preflight \`checking for byacc... no\` + \`checking for yacc... no\` + \`Neither bison, byacc, nor yacc was found\`): different route from last round (YACC/BISON_BYACC env exports -- proven ineffective). Root cause in upstream configure, not the worker: libpcap 1.10.6 configure.ac hard-codes BISON_BYACC="" before AC_CHECK_PROGS(BISON_BYACC, bison) / (byacc yacc) (fetched upstream tag to confirm), so every env export is discarded and configure always searches PATH, where the worker has nothing. Fix: build-time patch of the generated configure replacing BISON_BYACC="" with BISON_BYACC=<python3 bison_shim.py>, taking the bison branch; shim -V reports 3.8.2 so %define api.pure is selected, matching the committed grammar.c. LEX stays on the env channel (AC_PROG_LEX honours it). No PATH executables needed (worker fs lacks chmod).
- packasm u_char fix (this round, fixes 2 errors unknown type u_char in lorcon_packasm.h:168 + lorcon_packasm.c:220): different symbol/file from the last two rounds (ifcontrol/madwifing ifreq -- both worked, build progressed to lorcon_packasm.lo). Root cause is the same glibc-transitive class but a BSD alias: upstream uses u_char with only stdint.h, relying on glibc sys/types.h; OHOS musl-like sysroot provides no u_char. Fix is a build-time insert in lorcon_packasm.h of sys/types.h plus typedef unsigned char u_char guarded by ifndef __GLIBC__. Zero committed patches.

- drv_tuntap include isolation (prior round, fixed `redefinition of 'sockaddr_storage'` in drv_tuntap.lo via linux/if.h -> linux/socket.h vs sys/socket.h): single-file conditional exclusion of the linux triplet under HAVE_LINUX_WIRELESS; that fix worked (build progressed past drv_tuntap.lo), so the exclusion route itself is validated.

- drv driver sweep (prior round, generalized the tuntap single-file exclusion to a sweep over every *.c TU for the exact linux triplet, skipping wireless-struct consumers; build progressed past drv_tuntap.lo and drv_madwifing.lo).

- Manual staging (this round, fixes package() `Makefile:67: install, Error 64` after all 15 objects compile green): new failure domain, not the header-conflict fingerprint -- compilation is done, installation is the blocker. Root cause in upstream's install target, not the worker: it runs `install -o root` (chown as non-root), a trailing `$(LDCONFIG)` (OHOS has no ldconfig; libpri/1.6.0 precedent passes LDCONFIG=true), and libtool --mode=install re-chmod/relink (worker fs reports chmod:0/hardlink:0). Flag tweaks cannot converge on three independent causes, so the strategy is different: zero `make install` invocation, replicate its layout with pure-python conan copy() (liborcon2.a/.so* from .libs, five headers + ieee80211.h renamed to lorcon_ieee80211.h under include/lorcon2, lorcon.3 man page). Zero committed patches. No test or dependency change.

- test_package compiler pin (this round, fixes `CMAKE_C_COMPILER: /data/service/hnp/bin/clang ... identification is unknown` after all 15 objects + manual staging succeed): new failure domain, not the header/install fingerprint -- main build/package are green, only test_package configure dies. Prior header-exclusion and manual-staging assumptions are validated (build progressed past them) and therefore abandoned for this domain; different route. Root cause in test_package toolchain, not upstream: CMakeToolchain bakes the profile absolute compiler which the container reports as "not a file, skip" (main recipe CC probe log), while the main build already pins a probed-good harmonybrew clang via CC=. Fix mirrors the main probe in test_package: generate() really execs --version over conf/CC/HNP-PATH candidates and pins CMAKE_C_COMPILER/CMAKE_CXX_COMPILER via cache_variables, plus build() re-probes under conanbuild PATH and passes -D variables (command line wins over toolchain file). Empty probe keeps toolchain default so genuine errors still surface. No test assertions or dependency set changed.
- test_package exhaustive compiler scan (this round, fixes repeat of the same identification-unknown fingerprint where only CMAKE_CXX_COMPILER got pinned): prior single-which probe is falsified -- log shows `pin CMAKE_CXX_COMPILER=.../clang++` alone, C stays on the dead HNP path, so configure still dies at line 129. Root cause of the partial pin: shutil.which returns only the first PATH hit, and on this worker that hit is the dead /data/service/hnp/bin/clang shadowing the working harmonybrew clang later in PATH (C++ escaped by luck). Different route, not a repeat: scan every PATH dir for each tool name plus ~/.harmonybrew/bin independent of PATH order, keep exec-probing past dead hits with diagnostics, and derive C from the validated C++ sibling (clang++ -> clang in the same dir) when the C scan is empty. No test assertions or dependency set changed.
- test_package never-dead-default (this round, fixes third repeat where C still pins nothing: 20:00 preflight shows CXX-only pin again at line 204 despite the exhaustive scan). Two probe-or-default rounds falsified -- whenever the C exec probe finds nothing in the test_package context the dead HNP default survives. Different route: never leave the dead default; resolver tiers are probe (exec-validated, dead-HNP hits explicitly descended) -> sibling by existence only (CMake validates) -> bare `clang`/`clang++` resolved by CMake under the conanbuild PATH (which the main build proves resolves clang to harmonybrew). Both generate() cache and build() -D always pin; per-candidate fork storm is gone, only advisory probes remain (low-fork direction). No test assertions or dependency set changed.
- rindex link fix (this round, fixes `ld.lld: error: undefined symbol: rindex` referenced by ifcontrol_linux.o at test_package lorcon_test link): new failure domain, not the header/install/compiler fingerprint -- all 15 objects, manual staging and test C compile are green, only the final link dies. Root cause in upstream source, not the worker: ifcontrol_linux.c calls BSD-deprecated rindex() (== strrchr) in ifconfig_get_sysdriver, declared via strings.h on glibc but absent from the OHOS musl-like sysroot (linker itself suggests only `index` exists). Fix is a build-time sweep mapping rindex->strrchr with string.h include guarded by ifndef __GLIBC__ (glibc builds byte-identical). Zero committed patches. No test or dependency change.
