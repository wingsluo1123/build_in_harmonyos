# jdim 0.10.1 适配笔记

**编译结束**：2026-10-18
**最终状态**：published

- 上游：https://github.com/JDimproved/JDim ，tag `JDim-v0.10.1`（注意前缀，不是 `v0.10.1`）
- 归档：`archives/j/jdim/0.10.1/`（Conan recipe `jdim/0.10.1@ohpcd/stable`）
- 形态：C++ / Autotools（`configure.ac` + `Makefile.am`，`LT_INIT` 化），产物是**应用**
  `bin/jdim`（GTK3 2ch 浏览器），因此 `package_type = "application"` + 软件级 `commands.json`（R38）。
- 构建系统选择说明：上游 tarball **同时带 `meson.build` 与 `configure.ac`**；本适配走 **Autotools**，
  因为 (a) 本项目驱动 `scripts/ohc/driver.py:_detect_build_system()` 先判 `meson.build`，
  在无 meson 的设备上 `ohc-run.py build` 会在 Step3 直接 HANDOFF（首错原文
  `zsh:1: command not found: meson`），(b) tag archive **不带 `configure`**，Autotools 侧
  用 `autoreconf` 自举在本平台已验证可行（见下）。

## 编译环境

- 构建系统: autotools（`autoreconf -fi` 自举 + `configure` + `make`）
- 编译日期: 2026-10-18
- 编译器: clang / clang++ 15.0.4（`/data/service/hnp/bin/clang{,++}`）
- 目标: OHOS aarch64，profile `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / cppstd=17）
- Conan: 2.29.1（OHOS 适配版），`CONAN_HOME=~/tmp/ch/home-zhuli7-jdim`
- 作业数: `tools.build:jobs=4`（CONAN_HOME `global.conf`）

## 环境前置（属 worker 环境，未进仓库，入库无痕）

1. **meson 启动器缺失（worker 环境缺陷）**。`conan create` 会 `--build=missing` 重建
   `cairomm/1.14.5.1` 与 `pangomm/2.46.5`（ohpcd 已发布 binary 绑 `libsigc/2.12.Z`，
   而 gtkmm/3.24.11 把全图钉到 `libsigc/2.10.8`），这两个包是 Meson 工程，而本 worker
   `/data/service/hnp/bin` 与各前缀里**都没有 meson**（`/bin/sh: meson: inaccessible or not found`；
   cmd-pkgs 的 meson 资产 404，`install_prebuilt` 还报了假成功）。
   处置（**worker 环境修复，不改任何配方**）：从社区 PyPI 装 `meson 1.11.1` 到
   `~/usr/local/lib/meson-python`，并在 `~/usr/local/bin/meson` 放 shim：

   ```sh
   #!/bin/sh
   export PYTHONPATH=/storage/Users/currentUser/usr/local/lib/meson-python${PYTHONPATH:+:$PYTHONPATH}
   exec /storage/Users/currentUser/.harmonybrew/bin/python3 -m mesonbuild.mesonmain "$@"
   ```

   ⚠ **必须用 `-m mesonbuild.mesonmain`，禁止 `python -c`**：meson 会把 `argv[0]` 记进
   `mesonlib.meson_command`，生成共享库符号文件时会自我重入
   `--internal symbolextractor`；写成 `python -c` 会变成
   `<builddir>/-c: inaccessible or not found`（127）。修完 `meson --version` = 1.11.1，
   `meson setup && ninja` 最小共享库探针 rc=0。
2. `pkg-config 0.29.2` 在 `/data/service/hnp/bin`，其 `pkg.m4` 位于
   `<prefix>/pkg-config.org/pkg-config_0.29.2/share/aclocal/`（**不在 Conan 工具图里**，
   漏了它 `PKG_CHECK_MODULES` 不展开）。

## 编译步骤

```bash
conan create archives/j/jdim/0.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

1. `source()`：`get()` 官方 tag tarball（sha256 `884fef563c0ff314426d3b35887ad5dafe9456e1ace6792f5772794937cf7a17`，1478051 B）。
2. `generate()`：
   - `TMPDIR=~/tmp`；探测一个 `pwd` 能用的 shell 写进 `SHELL`/`CONFIG_SHELL`
     （profile 钉的是 hnp bash，HMDFS 下 getcwd 可能挂，E386 家族）；
   - 收集 `libtool`/`automake`/`autoconf-archive` 的 `share/aclocal` **以及 SDK 的 `pkg.m4` 目录**，
     **一次 `define_path("ACLOCAL_PATH", …)` 写全量**（否则 autoconf-archive 的 `define_path`
     会顶掉 libtool 的 `append_path`，见"遇到的问题"#1）；
   - `_fix_dependency_components()`：把 atkmm 的根 `cpp_info` 镜像成 gtkmm 引用的
     `atkmm-1.6` component（**绝对路径** dirs）；
   - `PkgConfigDeps(self).generate()`（本次 61 个 `.pc`）+ 必要时补 `gtest_main.pc`；
   - 各依赖 `lib` 目录追加进 `LD_LIBRARY_PATH`（`make check` 要能加载整条 gtk 共享栈）；
   - `AutotoolsToolchain` + `AutotoolsDeps`，configure 参数见下。
3. `build()`：`apply_conandata_patches()`（本版无补丁）→ `autoreconf -fi -I <每个 m4 目录>`
   → 把生成的 `configure` 里 `umask 077` 改成 `umask 022` → `configure` → `make`
   → **`make check`（上游 gtest 套件真跑）**。
4. `package()`：`autotools.install()`（`DESTDIR=package_folder`，`--prefix=/`），产物
   `bin/jdim` + `share/{applications,icons,metainfo}`，`COPYING` → `licenses/`。

configure 关键参数：

```
--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos
--with-sessionlib=xsmp --with-tls=gnutls --with-migemo --with-alsa
PKG_CONFIG_PATH=<build>/build-release/conan
```

- **三元组必须显式**：本机 `config.guess` 直接失败
  （`./config.guess[1612]: can't create …/cgXXXXXX/dummy.c: Permission denied`，HMDFS E011 家族）。
- `--host` 写 **`…-linux-ohos`**（build 写 gnu）是**有意**：这样 configure 走 cross 分支，
  跳过运行期探测；若走 native 分支，`AC_RUN_IFELSE` 的 conftest 会经 AutotoolsDeps 的 `LIBS`
  链上整条 gtk 共享栈，运行时报 `Error loading shared library libgtkmm-3.0.so.1 …`，
  configure 判 `cannot run C compiled programs` 而失败。jdim 的 `configure.ac` 自身
  不含显式 `AC_RUN_IFELSE`，cross 分支无副作用。

## 遇到的问题与解决方案

| # | 问题（首条真实错误原文） | 根因 | 解决方案 |
|---|------------------------|------|----------|
| 1 | `src/article/Makefile.am:1: error: library used but 'RANLIB' is undefined` … `autoreconf: error: …/automake failed with exit status: 1` | `autoconf-archive/2024.10.16` 用 `buildenv_info.define_path("ACLOCAL_PATH", …)`（**赋值**）把 `libtool/2.5.4` 用 `append_path` 追加的目录**顶掉**，最终 env 里只剩 autoconf-archive 一项 ⇒ `aclocal.m4` 里 `AC_DEFUN([LT_INIT]` 计数 **0**（`AX_CXX_COMPILE_STDCXX` 34）⇒ automake 不认 `LT_INIT` ⇒ 每个 `noinst_LIBRARIES` 报 RANLIB 未定义 | 收集三个工具包的 `share/aclocal` **一次 define_path 写全量** + `autoreconf -fi -I <dir>…` 双保险；同时把 SDK 的 `pkg.m4` 目录也纳入（否则 `PKG_CHECK_MODULES` 不展开 → `syntax error near unexpected token 'GTKMM,'`）。已沉淀为草稿 `DRAFT-jdim-0.10.1-aclocal-path-libtool-m4-clobber` + Issue #4225 |
| 2 | `./config.status: line 887: ./confXXXXXX/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery` | autoconf 模板里 `(umask 077 && mkdir)` 在 HMDFS 上产出不可写目录（E011/E114） | `build()` 内 `autoreconf` 之后把生成的 `configure` 里 `umask 077` → `umask 022`（本次 2 处） |
| 3 | `configure: error: Package requirements (gtkmm-3.0 >= 3.24.0) were not met: No package 'gtkmm-3.0' found` | 没有把 PkgConfigDeps 的输出目录交给 `configure`（conan 不导出 `PKG_CONFIG_PATH` 到 conanbuild env） | `configure` 命令行显式传 `PKG_CONFIG_PATH=<generators 目录>`（abiword-plugin-docbook/3.0.8 先例） |
| 4 | `Package 'libpcre2-8', required by 'glib-2.0', not found`（其后依次 `libffi`、`graphite2`） | 曾改用"各依赖包自带的 `lib/pkgconfig`"方案：上游 `.pc` 的 `Requires.private` 会追到**构建机上的**私有依赖（`harfbuzz.pc` 要 `graphite2`，而图中 graphite2 的 binary 被 conan "Skipped binaries" 跳过、`.pc` 落不了地） | 改回 **PkgConfigDeps 生成全图 `.pc`**（61 个，只引用图内节点），`PKG_CONFIG_PATH` 收窄到 generators 目录 |
| 5 | `ConanException: Component 'atkmm::atkmm-1.6' not found in 'atkmm' package requirement` | `gtkmm/3.24.11` 的 `components["gtkmm-3.0"].requires` 里写了 `atkmm::atkmm-1.6`，而 ohpcd `atkmm/2.28.4` 只有根 `cpp_info`（`pkg_config_name=atkmm-1.6`）、无 components | 在 `generate()` 里把 atkmm 根 `cpp_info` **镜像**成 `atkmm-1.6` component（libs + **绝对路径** dirs）；**不改 atkmm/gtkmm 配方本体**。⚠ 首次实现漏了 dirs，LDFLAGS 里 atkmm 位置退化成字面量 `-Llib` ⇒ `ld.lld: error: unable to find library -latkmm-1.6`；改为绝对路径 dirs 后消失 |
| 6 | `configure: error: C compiler cannot create executables`（exit 77），`config.log` 里 `Error loading shared library libgtkmm-3.0.so.1: (needed by ./conftest)` | native 分支下 `AC_RUN_IFELSE` 的 conftest 链上整条 gtk 共享栈，运行时找不到 `.so` | `--host=…-linux-ohos`（cross 分支跳过运行期探测）+ 各依赖 `lib` 目录进 conanbuild 的 `LD_LIBRARY_PATH`（后者同时供 `make check` 运行用） |
| 7 | 缺 `gnutls.pc` / 其 `prefix` 指向构建机 | ohpcd `gnutls/3.8.10` 把 `gnutls.pc` 放在 `lib/`（不是 `lib/pkgconfig/`），且 `prefix=` 是构建机安装前缀 | 配方按需补写 `gnutls.pc`（指向包内 `lib`/`include`）；`gtest_main.pc` 同理兜底（上游 googletest 自带该 `.pc`，仅在缺失时写 shim） |

## 源码修改

**无补丁**（`patches/` 为空，`conandata.yml` 的 `patches: {}`）。所有平台适配都在
`conanfile.py` 的 `generate()`/`build()` 里完成，未改上游任何源文件、未改任何依赖配方。

## 依赖版本

`gtkmm/3.24.11`、`libx11/1.8.13`、`libsm/1.2.6`、`libice/1.1.2`、`alsa-lib/1.2.16`、
`gnutls/3.8.10`、`libxcrypt/4.5.2`、`zlib/1.3.1.1`、`cmigemo/1.2-gh0.20220623`；
`test_requires gtest/1.17.0`；`tool_requires automake/1.18`、`libtool/2.5.4`、`autoconf-archive/2024.10.16`。
全部经 `conan download --only-recipe -r=ohpcd` 逐个复核（10/10 REMOTE_OK + 3 个工具包 REMOTE_OK）。
⚠ `zlib` 必须取 `1.3.1.1`：`glib/2.84.0.1` 钉 `zlib/1.3.1.1`，取 `1.3.1` 直接
`ERROR: Version conflict: Conflict between zlib/1.3.1.1 and zlib/1.3.1 in the graph. Conflict originates from glib/2.84.0.1`。

## 验证结果

### 测试五维账本（上游 gtest 套件，真机真跑）

| 维度 | 读数 | 说明 |
|---|---|---|
| `N_static` | **531** | 静态声明：`test/` 下 12 个 `gtest_*.cpp` 的 `TEST_F()` 逐文件计数 8+34+7+13+4+20+109+12+13+261+15+35 |
| `N_registered` / `N_executed` | **526 / 526** | 其中 5 条（`test/gtest_jdlib_misctime.cpp` 第 61–134 行的 `TEST_F(MISC_TimetToStrTest, …)`）被 **`#ifdef _POSIX_C_SOURCE`** 圈住，本配置未定义该宏 ⇒ **未编译进二进制**（不是跳过、不是失败）。gtest 注册即执行，526 全跑 |
| 通过 | **522** | `[  PASSED  ] 522 tests.` |
| 失败 | **4** | 逐条见下，全部为**字符集/库能力墙** |
| 跳过 | **0** | 无 `GTEST_SKIP`、无资源缺失 |
| `N_consumer` | **1** | `test_package`（执行 `bin/jdim --version`，5 条断言） |

**运行方式**：`build()` 内 `make check`（在 **build 目录**，树是 out-of-source），automake 并行测试框架构建
`check_PROGRAMS = gtest_jdim` 并执行；命令前缀 `LD_LIBRARY_PATH=<全部依赖 libdir>`（profile 的
`[buildenv]` 会覆盖 `buildenv_info` 的同名变量，必须写在命令行上）。原始日志行：

```
[==========] Running 526 tests from 64 test suites.
[==========] 526 tests from 64 test suites ran. (37 ms total)
[  PASSED  ] 522 tests.
[  FAILED  ] 4 tests, listed below:
```

**4 条失败逐条技术原因（均非本适配引入、非代码缺陷）**：

1. `MISC_UrlEncodeWithEncodingTest.encoded_to_eucjp`
2. `MISC_UrlEncodePlusWithEncodingTest.encoded_to_eucjp`
   —— 日志逐字：`can't open iconv coding = UTF-8 to EUCJP-MS`。jdim 目标是 **EUCJP-MS**
   （Microsoft 的 EUC-JP 变体，非标准 EUC-JP），本平台 libc 的 iconv **没有该字符集**
   ⇒ 转换返回空串（期望 `%A4%A2`，实得 `""`）。
3. `Iconv_ToAsciiFromUtf8.hiragana`
4. `Iconv_ToAsciiFromUtf8.subdivision_flag`
   —— 期望 `&#12354;…`（数值字符引用），实得 `*****`。独立探针定因：
   `iconv_open("EUC-JP","UTF-8")` = OK、**`iconv_open("ASCII//TRANSLIT","UTF-8")` = 失败**、
   而 `iconv("ASCII","UTF-8")` 对不可映射字符**用 `*` 替换**（`out='**'`、rc=2）**而不返回
   `EILSEQ`** ⇒ jdim "转换失败 → 输出数值字符引用" 的回退分支永不触发。

⇒ 配方按**文档化基线**断言（`经验库 §12.58③` 口径）：`REGISTERED=526`、`PASS_BASELINE=522`、
`KNOWN_PLATFORM_FAILURES` 四条具名；**只有通过数 <522 或出现名单外失败才 FAIL**，
从而"真跑 + 不堵打包 + 通过集缩水立刻红"。**未做任何删用例 / `DISABLED_` / FAIL 计 SKIP 的操作。**



## 上游测试真跑（R51 三步法）

- **① 清点**：`test/Makefile.am` 里 `check_PROGRAMS = gtest_jdim`、`TESTS = gtest_jdim`，
  `gtest_jdim_SOURCES` 列出 **12 个** `gtest_*.cpp`；逐文件 `TEST_F(` 静态计数
  8/34/7/13/4/20/109/12/13/261/15/35 = **531 个原子用例**，无 `TEST_P`/条件注册。
  ⇒ 静态总数 `N_static = 531`，构建系统注册的可执行目标 `N_registered = 1`（`gtest_jdim`），
  `TESTS` 条目 = 1。**"上游 12 个用例"的说法是把 12 个源文件数当成了用例数**，实为 531。
- **② 真跑**：配方 `build()` 内 `make check`（automake 测试框架），gtest 二进制
  `test/gtest_jdim` 链接 jdim 全部内部静态库，需要能加载整条 gtk 共享栈（故 `LD_LIBRARY_PATH`）。
- **③ 回填**：见"验证结果"与 `test_package/MANIFEST.yml`，四处同源。

## 注意事项

- 上游 README 明说 **Autotools 支持自 2023-07 起弃用**（`configure: WARNING: JDim will drop
  ./configure support in the future release.`），但 0.10.1 tag 的 Autotools 路径完整可用；
  本适配按任务口径走 Autotools。
- `src/jdversion.h` 把版本硬编码为 `0.10.1`，`--version` 输出形如
  `JDim 0.10.1-20230723`（后缀来自 buildinfo/git 的缺省回退），`test_package` 据此断言版本号
  与 configure 开关。
- 产物未额外做 OHOS codesign：实测本设备 clang 产出的 ELF 自带 `.note.ohos.ident`/`.codesign`
  且可直接执行（探针 `int main(){return 42;}` → rc=42），故本轮不加签名步骤（如后续 CI 报
  执行被拒，再按"OHOS 签名"清单补 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool`）。
- 未执行项：无。静态 531 条中 526 条注册并执行（5 条被 `#ifdef _POSIX_C_SOURCE` 条件编译排除），执行项 522 通过 / 4 平台字符集能力墙失败（逐条见「验证结果」）。
---

**编译结束**: 2026-10-18 10:25
**最终状态**: published
