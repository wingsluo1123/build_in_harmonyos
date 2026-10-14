# poke-elf 1.0 adaptation notes

## Build environment

- Build system: autotools (configure + make, no C compilation; data-only pickles + info + script)
- Compiler: clang 15 (native OHOS aarch64 build; no compiled code, toolchain only provides shell/make)
- Date: 2026-10-13
- Status: built (worktree prepared for HMBS true-device preflight; conan create evidence pending)

## Upstream audit (2026-10-13, tarball poke-elf-1.0.tar.gz, 272395 bytes)

- Homepage: https://www.jemarch.net/poke-elf
- Official source: https://ftp.gnu.org/gnu/poke/poke-elf-1.0.tar.gz
- sha256: 0ab767dafc435454cc98b245fe45aa2178c7c85d7b16308a23434a7d60847a74
- Contents (41 entries): 16 pickles (elf.pk, elf-build.pk, elf-common.pk,
  elf-32.pk, elf-64.pk, elf-config.pk, 7 elf-mach-*.pk, 4 elf-os-*.pk),
  poke-elf.texi + prebuilt poke-elf.info, examples/prelinkr, configure +
  Makefile.in, build-aux (tap-driver, test-driver, install-sh, missing).
- configure.ac: AC_INIT poke-elf 1.0; PK_PROG_POKE([POKE],[4.0]) plus
  PK_CHECK_PICKLE pktest.pk gates AM_CONDITIONAL RUN_TESTS.
- Makefile.am: TESTS = test-elf.pk (single TAP test) with
  TESTS_ENVIRONMENT = POKE_LOAD_PATH=$(top_srcdir); installed via
  dist_pickles_DATA to $(datadir)/poke/pickles, info_TEXINFOS, and
  dist_bin_SCRIPTS examples/prelinkr.
- Upstream test count (official unit): TESTS entries in Makefile.am = 1
  (test-elf.pk); the test itself runs 1 pktest named "load elf pickle".
  Method recorded in test_package/MANIFEST.yml as autotools_tests.
- configure contains 2x `umask 077` (HMDFS E011 risk); build-aux has no
  config.guess/config.sub so no OHOS triplet patch is needed.

## Build steps (recipe-fixed)

```bash
conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 -r ohpcd --build=missing
```

Recipe equivalent:

1. apply patches/0001 (umask 077 -> 022 in configure)
2. prepend poke/5.0 bin/ to PATH (so PK_PROG_POKE finds poke and pktest.pk)
3. sh ./configure --prefix=/
4. pin prebuilt doc timestamps (stamp-vti, version.texi, poke-elf.info)
5. make -j1 MAKEINFO=true
6. make check -j1 (upstream TAP suite; emits HMBS_UPSTREAM_TEST_RESULT from test-suite.log)
7. make install MAKEINFO=true (DESTDIR packaging)

## Issues and fixes

| # | Issue | Root cause | Fix |
|---|-------|------------|-----|
| 1 | config.status temp-dir creation may fail on HMDFS | `(umask 077 && mktemp -d ./confXXXXXX)` makes owner-unwritable setgid dir | patches/0001 relaxes both sites to umask 022 |
| 2 | make may try to rebuild poke-elf.info without makeinfo | patch rewrites configure mtime; stamp-vti rule triggers mdate-sh | _pin_prebuilt_docs() refreshes stamp/version/info mtimes + MAKEINFO=true override |
| 3 | make check needs poke with pktest.pk | RUN_TESTS is false without poke>=4.0 | requirements poke/5.0 plus PATH injection in build() |
| 4 | No config.guess/sub in build-aux | data-only package, no platform probe | no triplet patch; explicit --prefix=/ only |
| 5 | configure re-exec aborts 127 on true device (`configure[139]: /data/service/hnp/bin/bash: inaccessible`) / CI-010 fork failure under /system/bin/sh (`conanautotoolstoolchain.sh[13]: can't fork`, build #90666) | profile pins SHELL/CONFIG_SHELL to CI-worker bash absent on HMBS device (only /bin/sh guaranteed); v2 _pick_shell() preferred $SHELL (/bin/sh) even when profile bash exists, diverging from proven poke/5.0 env | v1 (failed): _fs_env apply only, aggregation盖回stale值. v2 (passed 3rd preflight): generate() save_sh + build()行内CONFIG_SHELL/SHELL前缀. v3: _pick_shell()优先用存在的 /data/service/hnp/bin/bash (CI 与 profile 一致)，缺失时回落 /bin/sh (真机行为不变) |
| 6 | configure poke检查崩溃 (`//share/poke/pkl-rt.pk: No such file`, Signal 6, version "unknown", RUN_TESTS=no → upstream discovered 0) | build()只把poke bin/放PATH，未设POKEDATADIR等重定位变量；poke以--prefix=/构建，默认去//share/poke找stdlib | _poke_runtime_env()导出POKEDATADIR/POKECONFIGDIR/POKEPICKLESDIR/POKEFMTAPPDIR，configure+make check全程嵌套生效 (poke test_package同款变量) |
| 7 | make install Error 64 (`install -c -m 644 <17 pickles> dest`) | HMBS install shim只接受单文件两参 (`[ $# -eq 2 ] \|\| exit 64`)；automake批量拷贝17个pickles必挂 (xeyes/libICE + adms 2.3.7 E182/E188同款) | _write_install_shim()写cp/mkdir shim (chmod容错，多源时mkdir -p目标) + _redirect_install_to_shim()重定向各Makefile INSTALL变量；OHOS分支在build()configure后与package()install前各接一次 (adms先例改编) |

## Dependencies

- poke/5.0 (conan ohpcd; provides the poke binary and pktest.pk for make check and consumer tests)

## Verification

- Upstream: `make check` TAP suite, 1 registered test (test-elf.pk / load elf pickle).
  True-device counts pending HMBS preflight; the recipe parses
  test-suite.log (# TOTAL/# PASS/# FAIL) and emits HMBS_UPSTREAM_TEST_RESULT.
- test_package: test.sh runs 5 consumer checks through the poke binary
  (version, load elf, file-type/class/AArch64 constants) and the conanfile
  emits HMBS_TEST_PACKAGE_RESULT with discovered 5.
  True-device pass counts pending HMBS preflight evidence.
- Falsifiability: checks use exact-output matching and assert propagation
  (poke -c); replacing poke with an exit-1 stub fails every check.

## Deliverables

| File | Note |
|------|------|
| conanfile.py | autotools recipe, application package, R32 guard, HMBS markers |
| conandata.yml | official GNU URL + sha256 + 1 patch |
| patches/0001-configure-umask-022.patch | E011 portability fix |
| test_package/conanfile.py + test.sh + MANIFEST.yml | 5 R34 consumer checks with deterministic counts |
| commands.json | prelinkr tool declaration (software level) |

## Caveats

1. Runtime needs two locations: poke stdlib datadir (POKEDATADIR) and the elf
   pickles via POKE_LOAD_PATH=<pkg>/share/poke/pickles + `load elf;`
   (poke's `-L FILE` is a script-file option, not a load-path directory).
2. GC Warning "Failed to find PT_GNU_RELRO segment" from statically linked
   poke is benign and hidden (2>/dev/null) in test.sh.
3. poke -s assertion failures do not propagate exit codes, so test.sh uses
   exact-output matching per the poke/5.0 precedent.
