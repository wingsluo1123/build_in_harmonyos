# tdbcodbc 1.1.14 适配笔记

## 编译环境
- 构建系统: autotools（TEA — Tcl Extension Architecture，TEA 3.13）
- 编译日期: 2026-10-14
- 编译器: clang 15（OHOS SDK，target `aarch64-linux-ohos`）
- 目标平台: OHOS arm64（CI profile `ci/conan/profiles/ohos-aarch64`）
- 本机验证: macOS 开发机 + `~/.conan2/profiles/ohos-local`（OpenHarmony 5.1.0 macOS SDK native，clang 15）交叉构建
- 状态: built（本机交叉 conan-verify G1/G2/G3/G4 全通过；published 待 OHOS CI 通过后更新）

## 软件简介

tdbcodbc 是 TDBC（Tcl Database Connectivity）的 **ODBC 驱动桥**：把 tdbc 的
connection/statement/resultset 基类接到任意 ODBC 驱动管理器与 ODBC 驱动上。
它本身不含数据库客户端，凡 unixODBC 能驱动的数据库都能通过它访问。

- 上游官网/仓库: https://core.tcl-lang.org/tdbcodbc/ （Fossil）
- 源码: https://prdownloads.sourceforge.net/tcl/tdbcodbc1.1.14.tar.gz
- SHA256: `cac1fdc99a859cf444e1b40bc3a683228a93370007af1331270d8ac4108e79fa`
- `manifest.uuid`: `3da926e4ed4e328c3d1deb3f77be740a42cfbf99898611d8a6861102a541a111`
- 版本核验: tarball 内 `README` 第 3 行 "This is the 1.1.14 source distribution of the bridge between Tcl ..."
- 同族已归档: `archives/t/tdbc/1.1.14`（基础包）、`archives/t/tcl/8.6.16`

### 与 unixODBC 的真实关系（本包最易误判处）

上游 **不在链接期依赖 unixODBC**：

- `generic/fakesql.h` 自带一份 ODBC 类型/常量/句柄声明（不 include `<sql.h>`）；
- `generic/odbcStubInit.c` 在**运行期** dlopen 驱动管理器并用 `Tcl_FindSymbol`
  逐个解析 30 个 `SQL*` 符号填进 stub 表；
- 实测产物 `DT_NEEDED` 只有 `libc.so`（见「验证结果」），无 `libodbc`/`libtcl`/`libtdbc`。

但**运行期硬依赖** unixODBC：首次 ODBC 调用走
`GetHEnv()` → `OdbcInitStubs()`（`generic/tdbcodbc.c:1245`），dlopen 失败即返回
`SQL_NULL_HENV`，所有 `tdbc::odbc::*` 命令随之失败。候选名表
（`generic/odbcStubInit.c:36-56`）在非 Windows/非 Apple/非 OpenBSD 平台为：

```c
"odbc32", "odbc", "libodbc32", "libodbc", "libiodbc"   /* + info sharedlibextension + ABI 后缀 .2/.1/.0 */
"odbccp", "odbccp32", "odbcinst", "libodbccp", "libodbccp32", "libodbcinst", "libiodbcinst"
```

**该表没有 `__OHOS__` 分支**，OHOS 走的是 Linux 路径：由 `libodbc` + `.so` + `.2`
命中制品仓 unixodbc 提供的 soname `libodbc.so.2`。这是本次鸿蒙特有测试的验证目标之一。

## 上游测试清点（先于适配执行）

**唯一计数口径**：上游按 `tests/tdbcodbc.test` 中 tcltest `test` **声明数 = 194** 计；
适配后新增测试按 `test_package/test_tdbcodbc.tcl` 中的**独立检查项数 = 12** 计
（其中鸿蒙特有 4 项）。该口径贯穿本文件 / `test_package/MANIFEST.yml` / 测试日志 /
PR 两张表格。

清点命令与结果：

```bash
$ rg -c '^test ' tests/tdbcodbc.test
194
$ rg -o '\-constraints (\w+)' -r '$1' tests/tdbcodbc.test | sort | uniq -c | sort -rn
   8 jet
   6 sqlserver
   4 sqlite
   1 odbcinst
   1 knownBug
   1 connect
```

测试入口是 TEA Makefile 的三个后端目标（`make test` = 三者串行，各以不同
`TDBCODBC_TEST_TYPE` 跑一遍 `tests/all.tcl`）：

| 后端 | 上游用例数（声明） | 在 OHOS 上可达 | 原因 |
|------|------|------|------|
| `test-jet` | 194（同一份 .test，`jet` 约束 8 项） | 0 | `tests/tdbcodbc.test:32-40` 硬编码 Windows-only，非 Windows 直接 `cleanupTests; return` |
| `test-sqlserver` | 194（同一份 .test，`sqlserver` 约束 6 项） | 0 | 同上 |
| `test-sqlite` | 194（同一份 .test，Unix 默认后端） | 4（3 通过 + 1 跳过） | 需注册进 unixODBC 的 `SQLite3` 驱动，制品仓没有 |

`tests/test.mdb` 是 jet 后端用的空 MS Access 模板，非可执行测试（计 0）。
`tests/all.tcl` 是 tcltest 2.2 驱动器，本身不含用例（计 0）。

### sqlite 后端为何只跑到 4 条（真实技术原因，非"没环境"）

1. 连接串在 `tests/tdbcodbc.test:83` 硬编码 `DRIVER=SQLite3;Database=<file>`；
2. W0 依赖探测证明制品仓**没有任何 ODBC 驱动**，只有驱动管理器：

```text
$ conan download sqliteodbc/0.999      -r=ohpcd --only-recipe
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]   # = 配方不存在
$ conan download sqliteodbc/0.100      -r=ohpcd --only-recipe   → 同上
$ conan download libsqliteodbc/0.999   -r=ohpcd --only-recipe   → 同上
$ conan download mdbtools/1.0.1        -r=ohpcd --only-recipe   → 同上
$ conan download unixodbc/2.3.12       -r=ohpcd --only-recipe
      revisions 6878d8258773e5a57d6526e9b29cc5b1 (2026-08-28)  # 存在，但只含
                                                                # libodbc/libodbcinst/libodbccr，无驱动
$ conan download freetds/1.4.23        -r=ohpcd --only-recipe
      revisions 94f88d5e63d6f1da6a9d53485c5c3246 (2026-08-20)  # TDS 驱动，需 TDS 服务端
```

3. 无驱动 → `tests/tdbcodbc.test:139` 的 `tcltest::testConstraint connect` 为假
   → 第 158-163 行 `if {![tcltest::testConstraint connect]} { puts "tests requiring
   a db connection skipped."; cleanupTests; return }` **提前返回**，其后 190 个用例
   连 `test` 声明都不会被执行到；
4. 可达的只有 `tdbc::odbc-1.1 / 1.2 / 1.3`（通过）与 `-1.4`（`connect` 约束跳过）。

因此配方 `_run_upstream_tests()` 里除了"零失败"还加了下限断言
（`total >= 4 且 passed >= 3`），防止测试入口本身坏掉被静默当成"全部跳过"。

> 补齐 SQLite ODBC 驱动属于**另一个三方库的适配**（sqliteodbc），受 W2「一个 PR
> 只允许一个软件」与 R36「依赖先发布再构建下游」约束，不在本次 PR 内捎带。

## W0 依赖发布探测（适配前第一件事）

| 依赖 | 用途 | 探测结果 |
|------|------|---------|
| `tcl/8.6.16` | 构建期 tclConfig.sh/tcl.h/libtclstub8.6.a；运行期 tclsh + libtcl8.6.so | ✅ 已发布 `2b0403fc1121633897928693fa91bfbe (2026-08-15)` |
| `tdbc/1.1.14` | 构建期 tdbcConfig.sh/tdbc.h/libtdbcstub1.1.14.a；运行期 `package require tdbc` | ✅ 已发布 `2e7294798738e876a93322690c4b8b5d (2026-09-28)` |
| `unixodbc/2.3.12` | 运行期 dlopen libodbc.so.2 / libodbcinst.so.2 | ✅ 已发布 `6878d8258773e5a57d6526e9b29cc5b1 (2026-08-28)` |

三者 OHOS aarch64 预编译 binary 均可 `conan download` 成功，无依赖阻塞。

## 编译步骤（真实命令）

配方内实际执行（CI worker 为原生 OHOS 构建；本机为交叉构建，差异见问题表 #5）：

```bash
bash configure --prefix=/usr/local --exec_prefix=/usr/local \
     --with-tcl=${TCL_PKG}/lib \
     --with-tdbc=${TDBC_PKG}/lib/tdbc1.1.14 \
     --enable-shared=yes \
     CC=<clang> tcl_cv_sys_version=Linux-6.6 \
     CPPFLAGS=-I${TDBC_PKG}/include \
     LDFLAGS=-L${TDBC_PKG}/lib/tdbc1.1.14
     # 本机交叉时另加 --host=aarch64-unknown-linux-ohos AR=llvm-ar RANLIB=llvm-ranlib
     #            ac_cv_sizeof_long=8 ac_cv_sizeof_long_long=8
make -j1
make test TESTFLAGS="-verbose pass"     # can_run 为真时执行（CI worker）
make install DESTDIR=<staging>
```

本机验证命令（与仓库 W3 同源的 conan create）：

```bash
python3 scripts/ohc-run.py conan-verify tdbcodbc 1.1.14 --profile ohos-local
# G1 PASS / G2 PASS / G3 PASS / G4 PASS → 配方验证通过
# 等价于 conan create archives/t/tdbcodbc/1.1.14 -pr:h=ohos-local -pr:b=ohos-local \
#         --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config.status` 生成 `./confXXXXXX/subs1.awk` 时报 Permission denied，configure 以 exit=1 结束并输出 `could not setup config files machinery` | autoconf 生成的 configure/config.status 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录；OHOS HMDFS 权限归一化后该目录不可访问（与 tdbc/1.1.14、tcl/8.6.16 的 E011 同源） | 把 configure 内两处 `umask 077` 改为 `umask 022`（configure 会把模板写进新生成的 config.status，故只需改 configure）→ 固化为 `patches/0001-configure.patch`；配方 `build()` 仅 `apply_conandata_patches` 应用（R6）。补丁经 `track-edit` 基线 + `refresh-patch --auto` 生成（R3） |
| 2 | Makefile 中 `SHLIB_LD` 为空（configure 能过但共享库链接命令残缺） | TEA 的 `tclconfig/tcl.m4` 无 HarmonyOS 分支：`uname -s` 返回含 `HarmonyOS` 的串，`tcl_cv_sys_version` 不匹配 `Linux*\|GNU*\|...` | configure 追加 `tcl_cv_sys_version=Linux-6.6`（autoconf 缓存变量，走官方 Linux 分支，与 tcl/tdbc 配方同法） |
| 3 | `make install DESTDIR=...` 会把 pkglibdir 装进 tcl 依赖包目录 | `TEA_PREFIX` 在未给 `--exec_prefix` 时继承 tclConfig.sh 的 `TCL_EXEC_PREFIX` | configure 显式 `--prefix=/usr/local --exec_prefix=/usr/local`，安装全部经 DESTDIR 落在本包 staging |
| 4 | **（本包新增）** `configure` 报 tdbc 头文件找不到 / 链接期 `-ltdbcstub1.1.14` 找不到库 | `TEA_LOAD_CONFIG(tdbc)` 在 configure 内部 `. ${tdbc_BIN_DIR}/tdbcConfig.sh`，而该文件里记录的是 tdbc **打包时**的 prefix 与 tdbc **构建机**的 conan cache 绝对路径：`tdbc_INCLUDE_SPEC="-I/usr/local/include"`、`tdbc_STUB_LIB_SPEC="-L/usr/local/lib/tdbc1.1.14 -ltdbcstub1.1.14"`、`tdbc_SRC_DIR="/storage/Users/currentUser/.cache/conan2/p/b/tdbc4f3fa0fa53f81/b"`。命令行 `VAR=...` 覆盖会被随后的 source 冲掉，改不了 | 用 `CPPFLAGS=-I${TDBC_PKG}/include` 与 `LDFLAGS=-L${TDBC_PKG}/lib/tdbc1.1.14` 补真实路径：tcl.m4 把 CPPFLAGS 并入 CFLAGS（`COMPILE` 规则含 `$(CPPFLAGS) $(CFLAGS)`），`MAKE_SHARED_LIB` 含 `${LDFLAGS}`。失效的 `/usr/local` 规格成为无害冗余项。`--with-tdbc=${TDBC_PKG}/lib/tdbc1.1.14` 保证 `TEA_PATH_CONFIG` 找得到 tdbcConfig.sh |
| 5 | **（本包新增）** 本机 `conan create` 报 `configure: error: cannot run C compiled programs. If you meant to cross compile, use '--host'.` | ohc 工具链（`conan-verify` / W3 / `ci/conan/build_and_test.sh:315-318`）对 `-pr:h` 与 `-pr:b` 传**同一个** profile，host==build 使 `cross_building()` 恒为 False，无法据此判断"产物能否在本机执行" | 判据改用 `can_run()`：`ohos-local` profile 的 `tools.build.cross_building:can_run=False` 是权威信号（conan `can_run()` 优先读该 conf）。`not can_run()` 时才追加 `--host=aarch64-unknown-linux-ohos`、`AR=llvm-ar`、`RANLIB=llvm-ranlib`、`ac_cv_sizeof_long=8`、`ac_cv_sizeof_long_long=8`（`AC_CHECK_SIZEOF` 无法执行编译产物）。CI worker 用 `ci/conan/profiles/ohos-aarch64`（无该 conf、原生构建）→ `can_run=True` → 本分支不生效，与 tdbc/1.1.14 的原生路径完全一致 |
| 6 | **（本包新增）** `build()` 内 `make test` 若执行，`OdbcInitStubs` 的 dlopen 会失败 | 测试跑在 `conanbuild` 环境；tcl 的 `package_info()` 显式声明了 `LD_LIBRARY_PATH`，而 **unixodbc 没有声明任何 buildenv_info**，因此 conanbuild 环境里没有 unixodbc 的 libdir，`dlopen("libodbc.so.2")` 找不到驱动管理器 | `generate()` 里用 `Environment().prepend_path("LD_LIBRARY_PATH", <unixodbc>/lib)` + `save_script(...)` 注入 build 作用域（再由 `VirtualBuildEnv` 聚合进 conanbuild.sh）。消费侧（test_package）走 `env="conanrun"`，由 VirtualRunEnv 从 libdirs 自动补齐，无需额外处理 |
| 7 | OHOS 上 `make -jN` 报 mkfifo `Operation not permitted` | OHOS 不支持 make jobserver 的命名管道 | 构建统一 `make -j1`（与 tdbc/1.1.14 一致） |

> 无 `#ifdef __OHOS__` 类源码改动；唯一的源码树改动是 configure 内两处 umask
> （已固化为补丁）。其余全部是构建参数 / Conan 环境层面的最小修改。

## 源码修改

| 补丁 | 文件 | 改动 |
|------|------|------|
| `patches/0001-configure.patch` | `configure` | 第 11008、11013 行 `umask 077` → `umask 022`（+2/-2） |

生成方式：`ohc-run.py track-edit`（基线指纹 31 个文件）+ `refresh-patch --auto tdbcodbc 1.1.14`
（`orig hash 6cfbb05af3294306` / `work hash b85ab0eb11ad3466`），已用
`patch --dry-run -p1` 在 pristine 源码上验证可干净应用。

> `configure` 是 autoconf 生成文件，`refresh-patch --auto` 的规则扫描会把它判为
> "generated" 而跳过；因此必须先用 `track-edit` 建立基线，走精准模式（R6 的
> `track-edit` 例外路径）。同族 `archives/t/tdbc/1.1.14/patches/0001-configure.patch`
> 是同一处 umask 改动的既有先例。

## 依赖版本

- `tcl/8.6.16`（build + run）：tclConfig.sh（`${TCL_ROOT}` 占位由其 buildenv 注入）、
  `tcl.h`/`tclDecls.h`、`libtclstub8.6.a`、`tclsh8.6`、`libtcl8.6.so`、`tcl8.6` 脚本库（TclOO 内置）
- `tdbc/1.1.14`（build + run）：tdbcConfig.sh、`tdbc.h`/`tdbcDecls.h`、
  `libtdbcstub1.1.14.a`、`lib/tdbc1.1.14/{pkgIndex.tcl,tdbc.tcl}`
- `unixodbc/2.3.12`（**仅 run**）：`libodbc.so.2`（驱动管理器）、`libodbcinst.so.2`
  （安装器库，提供 `SQLConfigDataSource*` / `SQLInstallerError`）、`libodbccr.so.2`
- 测试期 `tcltest`：由 tcl 包提供
- 链接期不需要 unixODBC（fakesql.h + dlopen 符号表），产物 `DT_NEEDED` 只有 `libc.so`

## 验证结果

### 本机交叉构建（macOS + ohos-local profile）

```bash
$ python3 scripts/ohc-run.py conan-verify tdbcodbc 1.1.14 --profile ohos-local
  G1: PASS   # 配方完整性（name/version/source/build/package/package_info/
             #              export_sources/补丁调用/conandata/test_package/MANIFEST）
  G2: PASS   # conan create 干净构建
  G3: PASS   # R26 系统同名库隔离
  G4: PASS   # 产物完整性
✅ 配方验证通过: tdbcodbc 1.1.14
```

conan create 关键日志（`reports/conan-create.log`）：

```text
tdbcodbc/1.1.14@ohpcd/stable: Apply patch (portability): ... umask 077→022 ...
checking TEA configuration... ok (TEA 3.13)
checking system version... (cached) Linux-6.6
checking for Tcl configuration... found <tcl pkg>/lib/tclConfig.sh
...
<ohos clang> -shared -L<tdbc pkg>/lib/tdbc1.1.14 -Wl,--export-dynamic \
    -o tdbcodbc1.1.14.so tdbcodbc.o odbcStubInit.o \
    -ltdbcstub1.1.14 "<tcl pkg>/lib/libtclstub8.6.a"
tdbcodbc/1.1.14@ohpcd/stable: L1_UPSTREAM_RESULT: skipped=can_run_false（本机交叉构建）
tdbcodbc/1.1.14@ohpcd/stable: package(): Packaged 1 '.so' file: tdbcodbc1.1.14.so
======== Launching test_package ========
tdbcodbc/1.1.14@ohpcd/stable (test package): Running test()
WARN: test_package 未执行：交叉构建（can_run=False），断言在原生 OHOS 构建上运行
```

产物核验（`llvm-readelf` / `llvm-nm`）：

```text
$ find <package folder>
/include/fakesql.h
/include/odbcStubs.h
/lib/tdbcodbc1.1.14/pkgIndex.tcl
/lib/tdbcodbc1.1.14/tdbcodbc.tcl
/lib/tdbcodbc1.1.14/tdbcodbc1.1.14.so
/share/man/mann/tdbc_odbc.n

$ llvm-readelf -h lib/tdbcodbc1.1.14/tdbcodbc1.1.14.so
  Class:   ELF64      Type: DYN (Shared object file)      Machine: AArch64
$ llvm-readelf -d lib/tdbcodbc1.1.14/tdbcodbc1.1.14.so | grep NEEDED
  0x0000000000000001 (NEEDED)  Shared library: [libc.so]     # 纯 stub 链接，无 libtcl/libtdbc/libodbc
$ llvm-nm -D --defined-only lib/tdbcodbc1.1.14/tdbcodbc1.1.14.so | grep ' T '
0000000000003b74 T Tdbcodbc_Init                              # Tcl load 入口
```

### 测试脚本静态验证（本机可做的部分）

OHOS 产物无法在 macOS 执行，故对本机可验证的部分做了实测（`/usr/bin/tclsh`）：

```text
info_complete(test_tdbcodbc.tcl) = 1                       # 语法完整（括号/引号配平）
elf_header(<本机交叉产物 .so>) = 7f454c46 / 02 / 183        # 断言 10 的解析逻辑对真实产物成立
regexp {/libodbc\.so\.2(\.[0-9.]+)?(\s|$)} <合成 maps 行> = 1
regexp {/libodbcinst\.so\.2(\.[0-9.]+)?(\s|$)} <合成 maps 行> = 1
libodbc 正则对 "libodbcinst.so.2" 行 = 0                    # 无误判
lib_mapped(无 procfs) = -1                                  # 降级路径正确
check 计数器 pass=1 fail=1                                  # 计数与退出码逻辑正确
```

### 待 OHOS CI 回填

- `make test`（jet/sqlserver/sqlite 三后端）实测汇总行与通过率
- `test_package/test_tdbcodbc.tcl` 12 项独立检查（含 4 项鸿蒙特有）实测结果
- 远程 HarmonyOS CI 构建编号

## 鸿蒙特有测试（rule12，N = 4）

| 检查项 | 验证的 HarmonyOS 适配点 |
|--------|------------------------|
| `ohos-platform` | `uname -s` 与 `$tcl_platform(os)` 均含 harmony —— 锁住"确实在鸿蒙上运行"这一前提（TEA 无 HarmonyOS 分支，全靠 `tcl_cv_sys_version=Linux-6.6`） |
| `ohos-elf-aarch64` | 已加载的本包共享库（OHOS 上为 `libtdbcodbc1.1.14.so`）是 ELF64 / AArch64(machine=183)。TEA 缺 HarmonyOS 分支时 `SHLIB_LD`/`SHLIB_SUFFIX` 为空、根本产不出共享库，故此断言直接验证问题 #2 的修复生效 |
| `ohos-odbc-manager-mapped` | `info sharedlibextension` 为 `.so`，且 `/proc/self/maps` 中出现 `libodbc.so.2` 映射 —— 证明 `odbcStubInit.c` 那条**没有 `__OHOS__` 分支**的 Linux 候选名 + ABI 后缀路径在鸿蒙 musl 加载器上按 soname dlopen 成功（不是文件存在性检查，是进程实际映射） |
| `ohos-odbcinst-mapped` | `/proc/self/maps` 中出现 `libodbcinst.so.2` 映射 —— 第二个可选库的 dlopen + `Tcl_FindSymbol(SQLConfigDataSource*/SQLInstallerError)` 在鸿蒙上成功；与第 7 项 `::tdbc::odbc::datasource` 命令是否被创建互为印证 |

## 交付物

| 文件 | 说明 |
------|------|
| `lib/tdbcodbc1.1.14/libtdbcodbc1.1.14.so` | Tcl 扩展共享库（tclsh 经 pkgIndex.tcl dlopen）。OHOS 原生构建带 `lib` 前缀（tcl.m4 unix 分支 `PACKAGE_LIB_PREFIX8="lib"`）；本机带 `--host` 的交叉构建得到无前缀的 `tdbcodbc1.1.14.so`，pkgIndex.tcl 与产物名由同一次 configure 生成，两侧各自自洽 |
| `lib/tdbcodbc1.1.14/{pkgIndex.tcl,tdbcodbc.tcl}` | Tcl 包索引 / ODBC 桥的 TclOO 类定义 |
| `include/{fakesql.h,odbcStubs.h}` | 上游声明安装的公共头（自带 ODBC 类型声明与 stub 表结构） |
| `share/man/mann/tdbc_odbc.n` | 参考手册 |

无 `bin/` 可执行产物 → 库类型，不需要 `commands.json`（R38 / CI L0k）。
无 stub 静态库（`TEA_ADD_STUB_SOURCES()` 为空）→ 不声明 `cpp_info.libs`
（共享库名无 `lib` 前缀，声明会产生无法解析的 `-ltdbcodbc1.1.14`）。

## 注意事项

- **与 tcl 内置版本的关系**：`tcl/8.6.16` 包内已带 `lib/tdbcodbc1.1.10/`（只有
  `libtdbcodbc1.1.10.so`，**没有 pkgIndex.tcl**，不构成可发现的 Tcl 包），因此不会
  与本包 1.1.14 争抢 `package require tdbc::odbc`。`lib/tdbc1.1.10/` 同理。
  即便如此，测试与消费方仍使用 `package require tdbc::odbc 1.1.14` 精确匹配。
- `library/tdbcodbc.tcl` 里是 `package require tdbc`（不带版本）；Tcl 的
  `package require` 在无版本约束时取已注册的最高版本，1.1.14 > 1.1.10，解析正确。
- OHOS 不支持 make jobserver 的 mkfifo，构建统一 `-j1`。
- `make test` 需要 `ODBCSYSINI` 指向含 `odbcinst.ini` 的目录才能让
  `SQLDriversW`/`SQLDataSourcesW` 行为确定；`test_package/conanfile.py` 已显式指向
  unixodbc 包自带的 `etc/`（内容为空配置）。

## 路径 B 候选评估

问题 #4（TEA `*Config.sh` 记录的是**打包时** prefix 与**构建机** cache 绝对路径，
下游 TEA 扩展 configure 时 source 到的是失效路径）具备跨库复用价值：
`tdbcmysql` / `tdbcpostgres` / `tdbcsqlite3` 以及任何以已发布 TEA 扩展为依赖的
下游包都会撞上同一问题。已用 `ohc-run.py engine` 撞库，
`knowledge/graph/index.tsv` 中无 `*Config.sh` / TEA 相关条目（E221/E538 的命中为
关键词误配，与 TEA 无关）。是否立为路径 B 草稿见 PR 说明与后续评估。

## 远程 HarmonyOS CI 第一轮（构建 #91604，PR #15791）

worker `OpenHarmonyPCDeveloper-CI-020`，SHA `4804813f`，`conan-build-test` 步骤失败
（elapsedTime=58.57s）。步骤结果：worker_preparation / worker-prep / git-clone /
checkout-pr / conan-setup / cleanup 全 ✅，`conan-build-test` ❌。

### ✅ 配方与构建在真机上完全通过（第一轮即验证）

```text
checking for tclsh... /storage/Users/currentUser/.cache/conan2/p/tcla4d5206af411b/p/bin/tclsh8.6
config.status: creating pkgIndex.tcl
rm -f libtdbcodbc1.1.14.so
/data/service/hnp/bin/clang -fPIC -O2 -pipe ... -I<tdbc pkg>/include -shared \
    -L<tdbc pkg>/lib/tdbc1.1.14 -Wl,--export-dynamic -o libtdbcodbc1.1.14.so \
    tdbcodbc.o odbcStubInit.o -ltdbcstub1.1.14 -L<tcl pkg>/lib -ltclstub8.6
tdbcodbc/1.1.14: package(): Packaged 1 '.so' file: libtdbcodbc1.1.14.so
tdbcodbc/1.1.14: package(): Packaged 2 '.tcl' files: tdbcodbc.tcl, pkgIndex.tcl
tdbcodbc/1.1.14: package(): Packaged 2 '.h' files: fakesql.h, odbcStubs.h
tdbcodbc/1.1.14: package(): Packaged 1 '.n' file: tdbc_odbc.n
```

即：umask 补丁生效、`tcl_cv_sys_version=Linux-6.6` 让共享库分支生效、
`--with-tdbc` + `CPPFLAGS`/`LDFLAGS` 修正 tdbcConfig.sh 失效路径全部有效，
`KC_ERRORS=0`、`JC_ERRORS=0`。

> **产物名与本机不同**：真机（原生构建）产物是 `libtdbcodbc1.1.14.so`，本机带
> `--host` 的交叉构建产物是 `tdbcodbc1.1.14.so`。差异来自 tcl.m4
> `TEA_MAKE_LIB` 的 `PACKAGE_LIB_PREFIX8`（`TEA_PLATFORM=unix` → `"lib"`）。
> `pkgIndex.tcl` 与产物名都由**同一次 configure** 生成，两侧各自自洽，
> `package()` 的断言只检查目录与 pkgIndex.tcl，与文件名无关。

### ✅ 上游测试在真机上的实测结果（与预测完全一致）

```text
tdbcodbc/1.1.14: L1_UPSTREAM_RESULT: backends=3 total=4 passed=3 skipped=1 failed=0 cases=3
```

三个后端（jet / sqlserver / sqlite）各输出一条 tcltest 汇总，合计 Total 4 /
Passed 3 / Skipped 1 / Failed 0，逐项通过的 3 个 case 即 `tdbc::odbc-1.1 / 1.2 / 1.3`，
第 4 项 `-1.4` 因 `connect` 约束跳过。与「上游测试清点」一节的推导逐字吻合。

### ❌ 唯一失败点：test_package 的 TCLLIBPATH 分隔符

```text
tdbcodbc/1.1.14 (test package): RUN: ODBCSYSINI="..." ODBCINI="..." sh ".../test_tdbcodbc.sh"
can't find package tdbc::odbc 1.1.14
    while executing "package require tdbc::odbc 1.1.14"
ERROR: tdbcodbc/1.1.14 (test package): Error in test() method, line 48
L1_RESULT=fail: conan create failed
```

**根因（已实测确认，非推测）**：Tcl 把 `TCLLIBPATH` 当 **Tcl 列表（空格分隔）**
解析 —— `init.tcl` 里就是 `set auto_path $env(TCLLIBPATH)`；而 Conan 的
`runenv_info.prepend_path` 用 `os.pathsep`（Linux 为 `:`）拼接，且
`conan/tools/env/environment.py` 的 `_EnvValue.get_str()` 对 path 型变量
`return pathsep.join(values)`、**忽略** per-variable separator（即改用
`prepend(..., separator=" ")` 也无效）。本包依赖图里有**两个** Tcl 扩展
（`tdbcodbc` 与 `tdbc`）各自前置 `lib/`，于是 Tcl 拿到
`"<tdbcodbc>/lib:<tdbc>/lib"` 这**一个**不存在的目录名，`tclPkgUnknown` 的
`glob -directory $dir */pkgIndex.tcl` 扫不到任何 pkgIndex.tcl →
`package require` 报 can't find package。

`tdbc/1.1.14` 自己的 test_package 只有一个 TCLLIBPATH 贡献者，不产生 `:`，
所以同样写法在那边能过 —— 该坑只在「依赖图里有 >= 2 个 Tcl 扩展包」时暴露。

**修复**：`test_package/conanfile.py` 从依赖图取出 `tdbcodbc` 与 `tdbc` 两个
`lib/` 目录，按 Tcl 语义用**空格**拼成 `TCLLIBPATH` 显式注入运行命令；并对
「取不到恰好 2 个目录」抛 `ConanException`，避免退化成难懂的 can't find package。
配方 `package_info()` 的 `prepend_path` 保持不变（与已发布的 tdbc 一致，单包
消费方仍然可用），消费方注意事项写进软件级 README.md。

### 其他 CI 观察

- `[fail] [Errno 2] No such file or directory: 'curl'` ×3：worker 的 pre-download
  探测阶段缺 curl，随后日志显示 `Pre-download: conandata.yml 已还原为官方 URL`，
  conan 自行下载源码成功，与本包无关，未导致本次失败。
- `L2_RESULT=skip: not run`（因 L1 fail 而跳过）。

## 远程 HarmonyOS CI 第二轮（构建 #91605 系列，SHA 5ac4e908，PR #15791）

TCLLIBPATH 修复生效，`test_package` 前三项断言在真机通过：

```text
RUN: TCLLIBPATH="<tdbcodbc pkg>/lib <tdbc pkg>/lib" ODBCSYSINI="..." ODBCINI="..." sh ".../test_tdbcodbc.sh"
++++ tdbcodbc-version PASSED
++++ tdbcodbc-superclass PASSED superclass={::tdbc::connection}
++++ tdbcodbc-solib-loaded PASSED <tdbcodbc pkg>/lib/tdbcodbc1.1.14/libtdbcodbc1.1.14.so
key "varchar" not known in dictionary
    while executing "dict get $::tdbc::odbc::sqltypes varchar"
ERROR: tdbcodbc/1.1.14 (test package): Error in test() method, line 67
L1_RESULT=fail: conan create failed
```

上游测试仍全绿：`L1_UPSTREAM_RESULT: backends=3 total=4 passed=3 skipped=1 failed=0 cases=3`。

**失败根因（本次是测试脚本自身的断言写错，不是适配缺陷）**：
`library/tdbcodbc.tcl` 里的 `variable sqltypes [dict create 1 char 2 numeric ... 12 varchar ... -5 bigint ... -11 guid]`
方向是**「SQL 类型号 → 名称」**，而我按名称反查（`dict get ... varchar`）→ Tcl 报
`key "varchar" not known in dictionary`。已对上游原文实测：
`dict get $sqltypes 12` = `varchar`、`dict get $sqltypes -5` = `bigint`、`dict size` = 24。

**修复**：改为正向查并加 `dict size == 24` 断言（比原断言更强）。

**同轮一并加固的两处判定（避免再烧一轮 CI）**：

1. `odbc-drivers` / `odbc-datasources` 原断言要求 `rc == 0`。unixODBC 对空
   `odbcinst.ini` / `odbc.ini` 的 `SQLDriversW`/`SQLDataSourcesW` 返回随版本而异，
   让它决定成败等于把判定押在配置文件行为上。改为：**成功且返回偶数长度字典，
   或失败但 `errorCode` 以 `TDBC` 开头**（`TransferSQLError` 所设）—— 两者都证明
   `OdbcInitStubs()` 已 dlopen 驱动管理器并解析出 `SQL*` 符号表；只有「库根本没
   加载起来」才会给出非 TDBC 的普通 Tcl 错误，那才判失败。已用三种情形
   （rc=0 / rc=1+TDBC / rc=1+NONE）实测该 expr 真值分别为 1/1/0，非恒真。
2. `ohos-odbc-manager-mapped` / `ohos-odbcinst-mapped` 的 `/proc/self/maps` 正则
   原为 `{/libodbc\.so\.2(\.[0-9.]+)?(\s|$)}`，依赖行尾格式；简化为
   `{libodbc\.so\.2}` / `{libodbcinst\.so\.2}`，并实测 `libodbc` 正则对
   `libodbcinst.so.2` 行无误判。

**教训（写入本 notes 以免重犯）**：跨机构建下 `test_package` 的运行期断言在本机
无法执行，因此对**每一条**依赖上游数据结构的断言，都必须先在本机用上游原文做
静态实测（本次 `sqltypes` 方向、`dict size`、正则、expr 真值表都已实测），
不能靠读源码推断。

### 第四轮（SHA 511b008367）：`$::errorCode` 未定义

第三轮为 `checkout-pr` 的 CI 基础设施故障（worker 下载 `pull/15791.diff` 超时，
`elapsedTime=20.89s`，未进入 `conan-build-test`），非代码问题。第四轮实测：
第 4 项断言已修复通过（`++++ tdbcodbc-sqltypes PASSED 12=varchar -5=bigint size=24`），
第 5 项前的 `set drivers_code $::errorCode` 报
`can't read "::errorCode": no such variable` —— Tcl 的 `errorCode` 只在发生过错误
之后才存在，而前 4 项断言一路无错，该变量尚未创建。这是第二轮加固时引入的自身缺陷。

修复：加 `proc error_code {}`，用 `info exists ::errorCode` 守卫，无错误时返回 `{}`；
第 5/6/8 项统一改用它。本机实测：无错误时 `[error_code]` = `{}`（不抛异常）、
`catch {error boom}` 后 = `NONE`；第 5/6 项 expr 在 rc=0 / rc=1+TDBC / rc=1+NONE
三种情形下真值为 1/1/0（非恒真）；`info complete` = 1。

## 状态

- 本机交叉验证: ✅ conan-verify G1/G2/G3/G4 全通过（`reports/conan-verify-report.md`）
- manifest status: `built`（未上传制品仓；R30 要求 conan-verify 通过 + 发布后才可标 published）
- 远程 HarmonyOS CI 第一轮（#91604）: 配方/构建/上游测试全通过，test_package 因
  TCLLIBPATH 分隔符失败 → 已修复（提交 e16ced2cd9）
- 远程 HarmonyOS CI 第二轮（SHA 5ac4e908）: TCLLIBPATH 修复生效、前 3 项断言真机通过，
  第 4 项因 sqltypes 字典方向写反失败 → 已修复
- 远程 HarmonyOS CI 第三轮: checkout-pr 基础设施故障（worker 下载 pull/15791.diff 超时，
  elapsedTime=20.89s，未进入 conan-build-test），非代码问题
- 远程 HarmonyOS CI 第四轮（SHA 511b008367）: 第 4 项已通过，失败于 set drivers_code
  $::errorCode（errorCode 未定义）→ 已用 info exists 守卫修复
- 远程 HarmonyOS CI **第五轮 #91833（SHA 74a30119e6）: ✅ 全部通过**
  （worker OpenHarmonyPCDeveloper-CI-034；conan-build-test ✅、Conan test_package 通过、
   L0 门禁通过、L1 门禁通过）
- atomgit-bot AI 代码检视: ✅ 未发现问题（0 条意见）
- 制品仓: `conan download tdbcodbc/1.1.14 -r=ohpcd --only-recipe` 仍为「配方不存在」——
  PR CI 不上传制品，上传在合并后的 release 流水线；故 manifest 状态保持 `built`（R29/R30）
- 真机测试终态: 上游 backends=3 total=4 passed=3 skipped=1 failed=0（3/3，100%）；
  test_package 12 项独立检查全通过（含鸿蒙特有 4 项，rule12 N=4）
- atomgit-bot AI 代码检视: ✅ 未发现问题（0 条意见，rule6/rule11 满足）
- 待办: push 修复 → /rebuild 触发第二轮 CI → 按 CI 终态回填本文件与 PR 正文
---

**编译结束**: 2026-10-14 21:00
**最终状态**: built
