# libuser 0.64-git20241106-dfsg 适配笔记

## 编译环境

- 构建系统：autotools（configure + make，`admin/` aux 目录）
- 编译日期：2026-09-26（首轮工作树，待 HMBS 真机预检）
- 编译器：clang（OHOS aarch64 原生构建）
- 状态：built（真机验证前；CI upload 成功后方可标 published）

## 上游调研

- 上游：https://pagure.io/libuser/（Red Hat 用户/组账户管理库，pagure 只读快照）
- 本版本为 Debian 快照 `0.64+git20241106~dfsg`（上游 git 2024-11-06 + dfsg 重打包），对应关系见 oaknut 先例
- 源码包：`libuser_0.64+git20241106~dfsg.orig.tar.gz`（724694 字节）
- SHA256 `e383cbdabb782ea8e8f6df1351ecd491f3b62f4f9b171c44e03cce9e1cec4658` 来自 Debian 官方 `.dsc`
 （tracker  dfsg-1 与 pureos dfsg-3 双源一致），与 Ubuntu 源包页 MD5 `a0f584d1bbe6d27dbabc947dc7031454` 同包互证
- `configure.ac` 关键结论（决定配方依赖与开关）：
  - glib 三件套为硬依赖：`PKG_CHECK_MODULES(GLIB/GOBJECT/GMODULE)` → 需 `glib/2.84.0.1` + PkgConfigDeps 提供 `.pc`
  - popt 仅路径参数、无开关，全部 CLI 以 `-lpopt` 链接 → 需 `popt/1.16`
  - `apps/libapputil.la` 无条件链接 `-lpam -lpam_misc` → 需 `linux-pam/1.7.2`（barada-pam/0.5.3 同口径依赖先例）
  - ldap/sasl 默认均为 no（传 `--with-ldap/--with-sasl` 才启用），selinux 默认 no，audit 默认 auto（无 libaudit 则静默关闭，本配方显式 `--without-audit` 求确定性）
  - python 默认 YES（`with_python=yes`），OHOS 无目标 python 开发栈，必须显式 `--without-python`
  - gtk-doc 由 `GTK_DOC_CHECK` 提供开关，Debian/Red Hat 均用 `--enable-gtk-doc=no`
- 上游测试（`Makefile.am` 的 `TESTS`，本配方 LDAP/SASL 禁用时共 5 项）：
  `tests/config_test.sh`、`tests/fs_test`、`tests/files_test`、`tests/pwhash_test`、`tests/utils_test`
  （另有 `tests/default_pw_test`、`tests/ldap_test` 仅在 `--with-ldap` 时注册，本配方不启用）
- 模块加载：`lib/modules.c` 经 `lu_cfg_read_single(ctx, "defaults/moduledir", MODULEDIR)` 定位后端 `.so`；
  `lib/config.c` 允许 `LIBUSER_CONF` 环境变量覆盖配置文件（非 setuid 时）。test_package 靠此机制把模块目录
  指向 Conan 包内 `lib/libuser`，不写死绝对路径。

## 编译步骤

1. `get()` 解包 Debian orig tarball
2. `generate()`：PkgConfigDeps（glib 的 `.pc`）+ AutotoolsDeps（popt/pam 的 `-I/-L/-l`）+ AutotoolsToolchain
  （`--without-python --without-sasl --without-ldap --without-selinux --without-audit --enable-gtk-doc=no --disable-nls`）
3. `build()`：`configure` → `make -j1` → `make check -j1`（best-effort，真实计数解析自 `test-suite.log`
   的 `# TOTAL/# PASS/# FAIL/# SKIP` 汇总块并输出 `HMBS_UPSTREAM_TEST_RESULT`）
4. `package()`：`make install`，删除 `lib/*.la`，复制 `COPYING` 到 `licenses/`，持久化 `res/hmbs_upstream.json`
5. `test_package`：CMake 编译 `test_libuser.c`（6 组真实 API 调用），运行时经 `LIBUSER_CONF`
   把 `defaults/moduledir` 指向包内模块目录，输出 `HMBS_TEST_PACKAGE_RESULT`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 本机无法下载 Debian 源码包（SSL EOF） | 本机出口网络限制 | 改从 Debian/PureOS 官方 `.dsc` 取 SHA256（双源一致），下载与编译留给真机预检验证 |
| 2 | `configure` 是否在 orig tarball 中存在不确定（Debian 曾清理生成文件） | 未亲见 tarball 内容 | 首轮按标准 autotools 流程编写；若真机报缺 `configure`，下一轮加 `autoreconf` 或换 release tarball |
| 3 | PAM 在 OHOS 是否可用 | `apps` 无条件 `-lpam -lpam_misc` | 依赖仓内 `linux-pam/1.7.2`（barada-pam 同口径先例）；制品仓发布状态由真机 L0i 核验 |
| 4 | 模块目录 baked 为构建期绝对路径 | `MODULEDIR` 编译进库 | test_package 生成 `libuser.conf`（`defaults/moduledir` 指向包内）+ `LIBUSER_CONF` 环境变量，上游原生支持，无补丁 |
| 5 | 真机 `pkg-config` 二进制是否存在 | `PKG_CHECK_MODULES` 需要 | acsccid 等 autotools 配方同机制已合入，默认存在；缺失则按真机日志补 `tool_requires` |

## 依赖版本

- `glib/2.84.0.1`（accountsservice 同领域配方同版本依赖，含 meson 实测记录）
- `popt/1.16`
- `linux-pam/1.7.2`

## 验证结果

```bash
# 本轮仅完成未提交工作树；以下待 HMBS 真机预检回填
# conan create archives/l/libuser/0.64-git20241106-dfsg --user=ohpcd --channel=stable
# 预期证据：
#   HMBS_UPSTREAM_TEST_RESULT={"status":..., "framework":"autotools-make-check", "discovered":5, ...}
#   HMBS_TEST_PACKAGE_RESULT={"executed":true, "passed":..., "discovered":6, "passedCount":...}
```

`git rev-parse --verify HEAD` 通过；`ci/conan/profiles/ohos-aarch64` 存在；无 `.git/index.lock` 残留。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 主配方（autotools + 上游测试 best-effort + 双 HMBS 标记） |
| `conandata.yml` | Debian 官方源 URL + SHA256，无补丁 |
| `manifest.yaml` | 版本级 manifest（状态 built，测试数待真机回填） |
| `test_package/` | 6 组真实 API 调用的消费者测试 + MANIFEST.yml（上游 5 项审计） |
| `notes.md` | 本文件 |

## 注意事项

- 本配方默认 `shared=True`（libuser 非系统同名库，无 R26 静态强制；后端模块为 dlopen 插件，必须是 `.so`）
- `package_info.requires` 透传 `glib` 三组件与 `popt::popt`，消费者 `#include <libuser/user.h>` 所需 glib 头文件路径自动跟随
- Python 绑定、LDAP/SASL 后端、SELinux、audit、NLS 在本配方中关闭，属有意裁剪（OHOS 无对应运行时），见 PR 补充说明
- 未提交、未推送，未创建 PR；待真机 rule4 门禁通过后由 HMBS 统一提交

## 2026-09-27 proxy-libintl link fix (uncommitted, pending preflight)

- Blocker (compile/link): `ld.lld: error: undefined symbol: g_libintl_bindtextdomain/textdomain/gettext/dgettext` in `apps/lchfn` and `lib/.libs/libuser.so` (`--no-allow-shlib-undefined`). configure/autoreconf/getcwd/cross/secure_getenv stages all pass.
- Root cause: glib/2.84.0.1 is built with `-Dnls=disabled` and keeps proxy-libintl private, so PkgConfigDeps `glib-2.0.pc` carries no `-lintl`, while glib's `libintl.h` remaps `gettext()->g_libintl_*`. Same class as paps/0.8.0 (extra_ldflags `-lintl`) and wv/1.2.9 (absolute LIBS path).
- Fix (no glib touch, one-PR-one-lib): `requirements()` adds `proxy-libintl/0.5` static; `build()` passes absolute `libintl.a` (fallback `libintl.so`, proxy-libintl first then glib-bundled) via command-line `LIBS=` to `make -j1` and `make check -j1` (global LIBS only, per-target LDADD intact); `package_info()` on OHOS adds `system_libs=intl` plus `-L<proxy-libintl>/lib` link flags (wv pattern). Static archive => no runtime NEEDED/rpath change.

## 2026-09-27 secure-getenv回退修复（未提交，待真机复检）

- 本轮阻断（compile）：sgml 修复已生效（docs/ 通过），新阻断在 lib/config.c:48 `#error Neither secure_getenv ...`，configure 明确 `__secure_getenv...no / secure_getenv...no`，clang 将隐式声明的 safe_getenv 当错误。
- 根因：OHOS/musl 无 secure_getenv/__secure_getenv；上游无回退直接 #error。
- 方案（Yocto Khem Raj issetugid 先例 + 无 issetugid 时 uid/gid 回退）：configure.ac 追加 AC_CHECK_FUNCS([issetugid])；lib/config.c 加 HAVE_ISSETUGID 分支并把 #error 改为 safe_getenv_uidcheck（getuid/geteuid/getgid/getegid 不等回 NULL，否则 getenv），补 unistd.h 与 helpers 定义；autoreconf 前改写，无新补丁文件。

## 2026-09-27 sgml文档禁用修复（未提交，待真机复检）

- 本轮阻断（compile）：make 在 docs/ 失败：sgml2txt not found（Error 127），此前 autoreconf/getcwd 与 CC 检查均已通过。
- 根因：docs/Makefile.am 的 all 强制调用 linuxdoc-tools，OHOS 真机无此工具；与库功能无关的纯文档依赖。
- 方案（Yocto disable-sgml-doc.patch / Gentoo nodocs.patch 同类先例）：build() 在 autoreconf 前改写 docs/Makefile.am——all 改为仅依赖 libuser.conf.5，含 sgml2txt/sgml2html 的 recipe 行改为 @: 空操作；man 页规则保留。

## 2026-09-27 getcwd换路修复（未提交，待真机复检）

- 上轮浅层修复无效证据：layout已设 build="."，真机仍执行 `.../p/b/.../b/configure`（helper异地构建目录）并复现 `configure: error: working directory cannot be determined`+级联getcwd；且popt默认多层目录+helper可通过，故“少一层目录”非决定因素。
- 本轮换路：不再依赖helper改layout字符串，改为源码树内手动构建（libcitadel/917已验证路线）：configure/make/check/install一律 `cwd=source_folder` 经 `self.run` 直接调用；新增 `_pick_shell`（优先HMBS注入SHELL/CONFIG_SHELL，其次/system/bin/sh）并显式导出SHELL/CONFIG_SHELL后调用configure；`--build/--host=aarch64-unknown-linux-gnu`（OHOS时）与 `--prefix=/` 手动传入；标记落盘改到source树。TMPDIR可写+umask022+mktemp门禁保留。

## 2026-09-27 cross声明修复（未提交，待真机复检）

- 进展确认：上轮换路有效，真机已越过autoreconf/getcwd（本轮日志无shell-init/getcwd报错），新阻断在configure的CC可用性检查：cannot run C compiled programs + use --host，位于手动configure调用处。
- 根因判断：预检/CI均以OHOS同时作为host与build上下文，原--build与--host传相同三元组，autoconf判为native并试图执行刚编出的a.out，在沙箱内执行失败；OHOS SDK clang本就是带sysroot的交叉工具链，声明cross才诚实。
- 修改：OHOS时改传--build=x86_64-pc-linux-gnu --host=aarch64-unknown-linux-gnu（均为老config.sub可识别），强制cross跳过执行类检查；CC_FOR_BUILD构建期工具仍在本机aarch64原生运行，make check不受cross影响照常实跑。

## 2026-09-27 gmodule-no-export alias fix (uncommitted, pending preflight)

- New blocker (different domain from getcwd/cross, those are now passed):
  configure aborts at `checking for glib-2.0 gmodule-no-export-2.0... no`
  with `No package 'gmodule-no-export-2.0' found`. autoreconf/getcwd and
  CC sanity stages already pass, so prior in-source + cross routes hold.
- Root cause: upstream glib ships gmodule-no-export-2.0.pc alongside
  gmodule-2.0.pc, but the Conan glib/2.84.0.1 recipe only declares
  gmodule-2.0 component, so PkgConfigDeps never emits the -no-export pc.
  Verified: glib recipe components are glib/gobject/gmodule/gthread/gio only,
  no gmodule-no-export string anywhere under archives/g/glib.
- Fix (libuser-local, no glib recipe touch, one-PR-one-lib): generate() now
  calls _alias_gmodule_no_export() right after PkgConfigDeps: copy
  gmodule-2.0.pc to gmodule-no-export-2.0.pc (Name rewritten) in generators
  folder (+ glib package pkgconfig dirs as fallback). Extra --export-dynamic
  is harmless for shared libuser. Precedent: babeltrace2/2.1.2 same copy,
  ayatana-indicator-session hand-written gio-unix pc.

## 2026-09-27 install-man1 Error 64 fix (uncommitted, pending preflight)

- Blocker (package): `make install` fails at `install-man1` with `Error 64`
  while `install -c -m 644` copies 12 man pages in one batch; single-file
  libtool `.so` installs just above it pass.
- Root cause: HMBS runtime install shim accepts only single-file two-arg
  calls (`[ $# -eq 2 ] || exit 64`, EX_USAGE); automake batches ALL man_MANS
  files into one `$(INSTALL_DATA)` call. Same family as lzop 1.04
  dist_docDATA / cronolog install-man / torsocks / viennarna / cxxtools.
- Fix (no doc loss, one-PR-one-lib): package() now drives `make install`
  with MKDIR_P/INSTALL/INSTALL_PROGRAM/INSTALL_DATA pointed at the
  automake-bundled install-sh (via literal /bin/sh, old-libtool parsing
  requirement; viennarna/cracklib2/cyrus-sasl precedent). Helper
  _find_install_sh() prefers real admin/install-sh and skips the 2-line
  root placeholder this recipe creates for libtoolize.

## 2026-09-27 package_info requires fix (uncommitted, pending preflight)

- Blocker (package_info gate): `ERROR: package_info(): The direct
  dependency 'linux-pam' is not used by any '(cpp_info/components).requires'`;
  install-sh route already holds (package created, headers/pc installed).
- Root cause: every direct requires must appear in cpp_info.requires under
  Conan 2; the list only covered glib/popt while apps/* link -lpam
  -lpam_misc -lpamc and proxy-libintl/0.5 is a direct static requires.
- Fix: extend cpp_info.requires with linux-pam::pam, linux-pam::pam_misc,
  linux-pam::pamc (all three, per link line) and
  proxy-libintl::proxy-libintl (libpeas2/libsecret style). The existing OHOS
  system_libs=intl plus -L block is kept for the static-archive closure.

## 2026-09-27 stale_runtime_library fix (uncommitted, pending preflight)

- Blocker (evidence/rule4): make check 4 failed + 1 skip, test_package 0/6. test-suite.log tail: lib/.libs/libuser.so.1 g_str_equal/g_ascii_table symbol not found; apps/.libs/lgroupadd g_libintl_* symbol not found; FAIL tests/utils_test exit 127. HMBS diagnosis stale_runtime_library.
- Root cause: check/consumer processes resolved system old .so instead of current tree + Conan glib; recipe ran make check with env=conanbuild and no LD_LIBRARY_PATH, and test_package preloaded only packaged libuser.so, leaving glib to LD_LIBRARY_PATH which OHOS loader ignores.
- Fix (runtime-only, no link change; ykclient/irqbalance/xz precedent, xmlsec caution respected): conanfile adds _runtime_libdirs (all build-tree .libs + all dep libdirs) and _check_preloads (fresh lib/.libs/libuser.so* + Conan libglib/libgobject/libgmodule versioned .so), runs make check with inline LD_LIBRARY_PATH + LD_PRELOAD; test_package extends LD_PRELOAD from single libuser to libuser + glib trio for capture run and final self.run gate. Static proxy-libintl LIBS link unchanged (no .so to preload).

## 2026-09-27 round-2 intl-provider preload fix (uncommitted, pending preflight)

- New evidence (different failure signature from round-1): Conan libglib-2.0.so.0.8400.0 itself reports g_libintl_gettext/dcgettext/dngettext symbol not found (pwhash_test exit 1); round-1 preload of libuser+glib trio could not help because the preloaded glib is the object missing symbols. utils_test separately exits 2 on group.lock Operation not permitted (filesystem lock domain, kept running, honest gaps).
- Root cause: glib package keeps proxy-libintl private; its shared lib needs a runtime g_libintl_* provider. proxy-libintl/0.5 is static-only on OHOS, but the glib package ships shared libintl.so (wv/1.2.9 _glib_proxy_libintl_path precedent).
- Strategy change (not repeating round-1): LD_PRELOAD chain now starts with the ELF-verified shared libintl.so from the glib package, then built libuser, then glib trio; plain .so linker-script stubs rejected via ELF magic check. test_package mirrors the same intl-first chain. Link-time LIBS static archive unchanged; suite still fully executed.

## 2026-09-27 round-3 link-time fix (uncommitted, pending preflight)

- New evidence: libgobject/libgmodule fail with Error loading shared library libglib-2.0.so.0 (needed by ...), utils_test still group.lock Operation not permitted exit 2; test_package 0/6 without gaps (rule4 evidence incomplete for新增测试).
- Strategy change (no repeat of runtime-preload rounds): link-time fixes per wv/1.2.9 precedent: build() scrubs stale *.la from dep libdirs before autoreconf/configure; LIBS now carries libtool -R RUNPATH flags for dep libdirs plus -Wl,--whole-archive around libintl.a so libuser.so and test binaries DEFINE g_libintl_* (plain archive path left them undefined, relocation failed at runtime). Toolchain LDFLAGS untouched (OHOS sysroot). Added _diagnose_link one-shot probes (dep libdir listing, nm defined g_libintl count, readelf NEEDED/RUNPATH) for next-round ground truth.
- Evidence quality: test_package marker now emits gaps on shortfall (loader vs lock classification, count equals discovered-passedCount); upstream marker splits the utils_test lock failure into ohos_feature with its own evidence when the full test-suite.log contains the lock signature.

## 2026-09-27 autopoint缺失修复（未提交，待真机/CI复检）

- Blocker (CI conan-build-test): autoreconf -fi 在 configure.ac 扫描后报 Can't exec autopoint ... exit status 2，真机曾通过但 CI worker 的 autoconf 套件缺 autopoint。
- 根因：Debian 快照只有 configure.ac（AM_GNU_GETTEXT），bootstrap 必须有 autopoint；配方 build_requirements 只声明了 automake/libtool，未声明提供 autopoint 的 gettext。
- 方案（authselect/avahi 同类先例）：build_requirements 新增 tool_requires gettext/0.22.5.1；不改 autoreconf 命令与 --disable-nls 语义。

## 2026-09-27 autopoint datadir fix (uncommitted, pending preflight)

- Blocker (compile): autoreconf fails at autopoint: can't open
  //share/gettext/archive.dir.tar.xz, gettext-0.18.2 not found in archive,
  autopoint Stop; configure never generated.
- Root cause: gettext/0.22.5.1 tool package bakes prefix "/" (datarootdir
  //share), so autopoint looks under //share instead of the relocatable Conan
  package share/gettext. Same class as avahi/libzbar/libxklavier.
- Fix: generate() defines gettext_datadir to the Conan gettext share/gettext
  via Environment and prepends share/aclocal to ACLOCAL_PATH; autoreconf
  command unchanged.

## 2026-09-28 CI#62950 python-exec + consumer-conf fix (uncommitted, pending preflight)

- Blocker (CI conan-build-test #62950): upstream 0/5 (files_test/pwhash_test `./tests/*.py: can't execute: Permission denied`, utils_test `group.lock: Operation not permitted`, fs_test SKIP fakeroot) + test_package 0/6 (`FAIL: context_start`).
- Root cause (harness, verified from local tarball audit): recipe passes `--without-python`, so configure leaves `PYTHON` empty via `AM_TESTS_ENVIRONMENT`; drivers run `$PYTHON "$srcdir"/xxx.py` as direct exec of the .py, needing +x/shebang that the worker FS denies. `files/pwhash/config/fs` drivers also `import libuser` (bindings disabled) — next log will show ImportError vs pass. Consumer `lu_start` failed on minimal `[defaults]`-only LIBUSER_CONF (no user/group defaults, no files/shadow sections).
- Fix (harness-only, no lib change): build() adds `_pick_python()` (HMBS_PYTHON3/system python3) + `_chmod_test_drivers()` best-effort chmod and runs `make check -j1 PYTHON=<interp>`; marker/MANIFEST command updated. test_package `_write_libuser_conf()` now mirrors upstream `tests/utils.conf.in` (defaults/userdefaults/groupdefaults/files+shadow with temp files dir + empty db files); `test_libuser.c` prints `lu_strerror`/code + LIBUSER_CONF head on `lu_start` failure for next-round ground truth. utils_test lock domain untouched this round pending new evidence.

## 2026-10-14 CI#91463 PYTHON-make-arg + conf-percent fix (uncommitted, pending preflight)

- Progress (CI #91463 vs #62950): consumer 0/6 -> 4/6 (context_start/modules/ent_id/moduledir PASS); upstream still 0/5. L1 fail now only `consumer test failed: rc=1 ok=4/6`.
- Fix 1 (deterministic): PYTHON was passed as env prefix (`PYTHON=... make check`), which never becomes the make variable $(PYTHON) without -e, so AM_TESTS_ENVIRONMENT stayed empty and shebang-less .py were exec'd as shell (`import: inaccessible`, `syntax error: unexpected '('`). Moved to make argument (`make check -j1 PYTHON=... LIBS=...`).
- Fix 2 (deterministic): test conf wrote literal `%%n`/`%%u` (printf-style over-escape in plain file write); libuser warned `Invalid default value of field userdefaults/LU_GIDNUMBER` and user_default/group_default failed. Changed to upstream spelling `%n`/`%u`.
- Upstream python drivers will next show honest ImportError (bindings disabled by design) instead of shell-misexec; lock/SKIP domains untouched.

## 2026-10-14 rule4 python绑定补齐修复（未提交，待真机复检）
- 本轮阻断（evidence/rule4 incomplete）：上游 5 发现、4 执行、0 通过、1 跳过；test-suite.log 尾部 4 FAIL 中至少 pwhash/files 等驱动报 ModuleNotFoundError: No module named libuser，随后 Invalid MD5 hash 等连锁失败；门判定为缺依赖未补齐（missing_dependency 不得包装成环境豁免）。
- 根因（源码实证）：Makefile.am 的 5 项 TESTS 中 config/fs/files/pwhash 均经 PYTHONPATH=\$(pwd)/python/.libs 做 import libuser（pwhash.py 首行、files_test.py 首行、fs_test.py 首行、config_test.py 首行），而配方 generate()/build() 传 --without-python，pyexec_LTLIBRARIES 条件关闭，python/.libs 下无 libuser.so，PYTHON 再正确也无模块可载。
- 方案（补齐依赖再测，非跳过）：generate() 与 _manual_configure_args() 改 --without-python 为 --with-python；build() 在 configure 前用 _pick_python() 选同一 worker 解释器并同时以 PYTHON 环境变量与命令行前缀传入 configure（AM_PATH_PYTHON），PYINCLUDEDIR 取自该解释器 sysconfig 头文件（eigenpy 先例：worker HNP python 含 Python.h，原生 aarch64 构建可直接 import）；make check 保持 PYTHON=<worker> make 参数与 PYTHONPATH 机制不变。LDAP/SASL/SELinux/audit/NLS 裁剪保持；utils_test 文件锁 ohos_feature 与 fs_test fakeroot SKIP 缺口保持原样如实上报。

## 2026-10-15 getusershell 回退修复（未提交，待真机复检）

- 本轮阻断（compile）：--with-python 启用后新阻断在 python/libusermodule.c：setusershell/getusershell/endusershell 隐式声明，getusershell 被当作 int（incompatible integer to pointer conversion，-Wint-conversion 升格为 error），make -j1 停在 python/python_libuser_la-libusermodule.lo。
- 根因：该三函数是 BSD shells API（glibc 经 <unistd.h> 声明），OHOS libc 无此家族；此前 --without-python 时该 TU 不编译故未暴露，补齐绑定后首次触达。
- 方案（in-recipe 文本补丁，无新补丁文件）：configure.ac 追加 AC_CHECK_FUNCS([getusershell setusershell endusershell])（复用 issetugid 补丁锚点）；python/libusermodule.c 在 #include "common.h" 后插入 #ifndef HAVE_GETUSERSHELL 回退实现——最小 /etc/shells 读取器（跳过空行/# 注释，剥离换行），文件缺失或不可读时按 glibc 语义回退 /bin/sh + /bin/csh；三函数为同一家族共用同一 guard。上游 lchsh 明确忽略 /etc/shells，库内他处无此家族调用，本轮只补该 TU。

## 2026-10-15 rm fork OOM round2: revert -g0, keep neutral dep-tracking off (uncommitted, pending preflight)

- Input shares the round-1 fingerprint (compile: sh: /storage/Users/currentUser/.harmonybrew/bin/rm: Out of memory; upstream 0/0/0) with the same commentId/timestamp, so no new preflight evidence that compiler peak is the driver.
- Round-1 review: -g0 on the configure/make command lines plus --disable-dependency-tracking did not change the fingerprint. rm has a tiny resident footprint; exec-time ENOMEM points at system-level pressure at fork time, not at debug-info size of one TU. The make-line env CFLAGS is additionally shadowed by automake Makefile assignments, so its effective surface was configure-time only.
- Different strategy this round (no verbatim repeat): reverted the artifact-changing -g0 (toolchain default debug info restored, less review surface and no masking of the real signal); kept only behavior-neutral --disable-dependency-tracking (skips .deps/.Po generation, no product or test-scope change, incidentally fewer automake rm/mv temp ops per compile). Single-job make -j1, full 5 upstream TESTS, and --with-python (needed by 4 drivers via import libuser) unchanged.
- Next-step reading: a pass on a quiet worker supports transient system pressure; a stable repeat of the identical line needs HMBS-side full logs around the failing point to find the real memory hog (candidates: autoreconf/autopoint phase or the Python.h-heavy TU) before any targeted split.

## 2026-10-15 CI#93801 autoreconf m4/autoconf 缺口修复（未提交，待真机/CI复检）

- Blocker (CI conan-build-test #93801): autoreconf -fi 报 autom4te: need GNU m4 1.4 or later: m4，随后 autopoint 以 exit 1 中止；真机预检通过，CI 必现。
- 根因：配方 build_requirements 只声明 automake/libtool/gettext，而 archives/a/automake 的 requirements() 为空，不会传递 autoconf/m4；真机有 HNP 系统 m4 故通过，CI 工作机无系统 m4 故失败。属真 Conan 依赖缺口，非瞬时 fork 压力（bwm/0.6.3 同款全链先例）。
- 方案：补 tool_requires m4/1.4.19 + autoconf/2.72（libdill/burp2 全链先例），其余 autoreconf/gettext_datadir 逻辑不变。

## 2026-10-16 preflight perl single-interpreter fix (uncommitted, pending preflight)

- Blocker (compile): autoreconf still dies at .aclocal-real line 31 with Can't load conan Cwd.so: Perl_my_cxt_init symbol not found; the 10-15 all-conan attempt (PERL=conan perl + absolute autoreconf path) did not change the fingerprint.
- Root cause: bootstrap mixes two perl ABIs: the runner resolves to system perl while conanbuild PERL5LIB points at conan perl/5.42.2 XS dirs, so system perl loads an incompatible Cwd.so. Same signature as ytnef/2.1.2 and zzuf/0.15.
- Fix (single-Perl route, ytnef _bootstrap_configure + zzuf precedent): build() pins system perl (/data/service/hnp/bin/perl first, then OS fallbacks) via PERL, sets PERL5LIB to Conan automake share/automake-* + autoconf share/autoconf pure-perl dirs only (never conan perl XS dirs), keeps conan tool bindirs (minus perl) on PATH, pins M4 to conan m4, creates source m4 dir via os.makedirs. No new tool_requires; test scope unchanged.
