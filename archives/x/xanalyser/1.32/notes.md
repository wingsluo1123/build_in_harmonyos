# xanalyser 1.32 适配笔记（OHOS PC aarch64）

## 编译环境

- 构建系统: autotools（上游 2008 年生成的 configure + automake 1.9 Makefile.in，**in-source** 构建）
- 编译日期: 2026-10-14
- 编译器: clang / clang++ 15.0.4（`/data/service/hnp/bin/clang`）
- 目标平台: OHOS 6.0 / armv8（aarch64），profile `ci/conan/profiles/ohos-aarch64`（host = build）
- Conan: 2.29.1（OHOS 适配版）
- 状态: built（conan-verify G0-G4 通过；L2/L4/L5 对纯可执行包无 cache 路径，工具如实标注为跳过；未 upload）

## 源码与来源核验（OBSERVED）

```bash
$ curl -sSL -O http://arvin.schnell-web.net/xanalyser/xanalyser-1.32.tar.bz2
$ sha256sum xanalyser-1.32.tar.bz2
8ca3f65bcaad92b1421912311da47e4aa1741a4bb1f422eaf85d75e5996f7946   # 与 conandata.yml 一致
$ tar tjf xanalyser-1.32.tar.bz2 | head
xanalyser-1.32/{doc,src}/...
$ cat xanalyser-1.32/VERSION
1.32
$ cat xanalyser-1.32/configure.in | grep -E "AC_INIT|AM_INIT"
AC_INIT(src/main.cc)
AM_INIT_AUTOMAKE(xanalyser, $VERSION)
```

### 源 URL 说明（R39 官方托管例外）

作者官方站点 `arvin.schnell-web.net` **只提供 http 分发**：该域名 443 端口返回的是托管商
证书（`CN = *.kasserver.com`，SAN 只有 `*.kasserver.com`/`kasserver.com`），与域名不匹配，
`https://arvin.schnell-web.net/...` 在 TLS 校验阶段即失败（`SSL: no alternative certificate
subject name matches target host name`），无法用于自动化下载；`index.html` 返回 500 而
`xanalyser-1.32.tar.bz2` 返回 200，说明站点/文件均在线，只是不提供可校验的 https。

因此 `conandata.yml` 使用**官方 http 直链**（域名即作者官网，非镜像、非 fork、非网盘），
并以 `sha256` 固定内容防篡改。这是 R39「官方源」的托管例外，需要在 PR 说明中登记。

## R51 上游测试清点（census，raw commands + outputs）

`build()` 内原样执行并落 `upstream-test.log`（同时写进 conan create 日志）：

```text
$ grep -nE "^(check|test):" Makefile.in src/Makefile.in doc/Makefile.in
Makefile.in:501:check: check-recursive
src/Makefile.in:372:check: check-am
doc/Makefile.in:260:check: check-am

$ grep -rnE "^(TESTS|check_PROGRAMS)" Makefile.in src/Makefile.in doc/Makefile.in
NO TESTS/check_PROGRAMS DECLARED

$ find . -iname '*test*' -not -path './conan/*' -not -name 'upstream-test.log'
# 无输出（0 个文件）

$ make -n check                 -> check-target: PRESENT
$ make check                    -> CHECK_EXIT=0（"Nothing to be done for 'check'"）
$ make test                     -> make: *** No rule to make target 'test'.  Stop. TEST_EXIT=2
```

**结论**：上游 0 个自动化用例。`check` 目标是 automake 递归生成的空壳（`check-am: all-am`），
没有 `TESTS`/`check_PROGRAMS`；没有 `test` 目标。上游唯一的可运行入口是程序本体（GUI，
需要 X display）。本包不伪造上游测试：`make check` 每次构建都真实执行、原样记录。

## 编译步骤（配方内部）

1. `_restore_helper_modes()` — HMDFS 不保留 tarball 里的可执行位，先把 `configure` /
   `install-sh` / `missing` / `depcomp` 补回 `+x`（G0 预扫命中 E490，方案一致）。
2. `_patch_configure_umask()` — `umask 077` → `umask 022`（E011，见下）。
3. `autotools.configure()` — 参数只有 `--prefix=/`、`--x-includes=<libx11>/include`、
   `--x-libraries=<libx11>/lib`（AC_PATH_X）；依赖 `-I/-L/-Wl,-rpath-link` 由 R49
   私有构建目录注入 `CPPFLAGS/LDFLAGS`（`self.dependencies.host` 各自的 `include`/`lib`）。
4. `_move_version_out_of_include_root()` — 见「问题 2」。
5. `autotools.make(args=["-j1", "VERSION=1.32"])` — 沙箱无 mkfifo，jobserver 必须 `-j1`。
6. `_run_upstream_tests()` — 上游清点 + `make check` 原样执行（见上）。
7. `package()` — `make -j1 VERSION=1.32 install DESTDIR=<package_folder>`，随后
   归位 app-defaults（见「问题 5」）、拷 `COPYING`、按清单校验四个产物。

## 打包（package）说明

上游 `install` 装三样东西：`bin/xanalyser`、`share/man/man1/xanalyser.1`，以及
`install-data-hook` 写死的 `$(DESTDIR)/usr/share/X11/app-defaults/XAnalyser`。
第 3 项与仓库约定 `<pkg>/share/...` 不一致 → 安装后 `os.rename` 归位并删除空 `usr/`。
`package()` 末尾用硬清单校验（缺任何一个就抛 `ConanException`，不允许静默残缺包）：

```text
bin/xanalyser
share/man/man1/xanalyser.1
share/X11/app-defaults/XAnalyser
licenses/COPYING
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status -> ./confXXXXXX/out: Permission denied`，configure 产物全部写不出来 | E011：configure 用 `umask 077` 建临时目录，HMDFS 忽略 chmod 且权限位固定，0700 目录内不可写 | 构建期把 `configure` 中 `umask 077` 改为 `umask 022`（`replace_in_file`，零补丁） |
| 2 | 每个 TU 都报 `../version:1:1: error: expected unqualified-id` | 源码根有纯文本 `VERSION` 文件，而 `DEFAULT_INCLUDES = -I. -I$(srcdir) -I$(top_builddir)` 把顶层目录放进 `-I`；HMDFS 大小写不敏感，C++17 libc++ 头传递引入的 `#include <version>` 命中了这个文本文件 | `configure` 之后把 `VERSION` 移出 include 根（改名 `VERSION.txt`，文件不删除），所有 make 调用用命令行变量 `VERSION=1.32` 覆盖 `VERSION = $(shell cat ./VERSION)`。**不使用** `-isystem`/`-iquote` 掩盖（知识草稿 DRAFT-srcroot-plain-file-shadows-std-header 的禁忌） |
| 3 | `error: non-constant-expression cannot be narrowed from type 'unsigned int' to 'unsigned short' in initializer list [-Wc++11-narrowing]`（Analyser.cc 15 处） | 1998-2008 年的 C++ 用 `XRectangle rect = { marker[m], 0, 1, height };` 这种赋值语义的列表初始化；C++11 起列表初始化窄化是 hard error，profile `cppstd=17` | `tc.extra_cxxflags.append("-Wno-c++11-narrowing")`（零补丁；仓内既有先例：ballandpaddle/0.8.1 等 8 个配方的 conanfile.py 使用同款处置） |
| 4 | `Xm/Xm.h:1514: ISO C++17 does not allow 'register' storage class specifier [-Wregister]`（**motif 依赖头**里的 11 处） | Motif 的公开头是 1990 年代代码，参数声明带 `register`；C++17 移除该关键字，clang 直接报错 | `tc.extra_cxxflags.append("-Wno-error=register")`（E293 同族处置；关键字只是存储类提示，无语义影响） |
| 5 | app-defaults 落到 `<pkg>/usr/share/X11/app-defaults/` | 上游 `install-data-hook` 写死绝对路径，不带 `$(prefix)` | `package()` 里归位到 `<pkg>/share/X11/app-defaults/` 并删除空 `usr/` 树 |
| 6 | `make -j2` → `jobserver mkfifo: Operation not permitted` | OHOS 沙箱不支持 mkfifo | 一律 `make -j1` |

### 依赖轨冲突（重点关注）

仓库里存在两条并行 X11 轨：

| 轨 | 成员 | 说明 |
|----|------|------|
| 1.8.13 轨 | `libx11/1.8.13` + `libxt/1.3.1` + `libxext/6.4.0.1` + `motif/2.3.8` + `libxmu/1.3.1.1` + `libsm/1.2.6` + `libice/1.1.2` | Motif 家族；motif/libxt/libxmu 均 `force` libx11/1.8.13 |
| 6.4.0 轨 | `libx11/6.4.0` + `libxext/6.4.0` + `libxpm/3.5.17` | cmd-pkgs 家族；libxpm 已发布二进制建在这条轨上 |

`arvin.schnell` xanalyser 同时需要 `-lXm`（轨 1）与 `-lXpm`（轨 2）。制品仓实测：

```bash
$ conan list "libxpm/3.5.17:*" -r=ohpcd
libxpm/3.5.17  packages e647863c... requires: libx11/6.4.Z, libxcb/1.16.Z ...   # 只有 6.4.0 轨二进制

$ conan graph info --requires=motif/2.3.8 --requires=libxpm/3.5.17 ... --format=json
Missing libxpm/3.5.17#e08a81954eab886de9acc314b8bcd8bd                          # 1.8.13 轨缺二进制
```

处理方式沿用已合并的 `xmhtml/1.1.10`：**force `libx11/1.8.13` + 选 `libxext/6.4.0.1`**，
`libxpm` 在 1.8.13 轨上的二进制由 CI 的 `--build=missing` 从源码补建。实测源码构建可行：

```bash
$ conan install --requires=...libxpm/3.5.17... --build=missing
libxpm/3.5.17: Created package revision 942e0ac711a541dffa88a2496f38dba8
libxpm/3.5.17: Package 'eab79208a9437a856077cc57885309d75bdb4a31' created   # 1.8.13 轨，构建成功
Install finished successfully   # EXIT=0
```

> 代价：CI 里 libxpm 每次需要现场编译（本机实测约 1-2 分钟）。这是「目标库适配」策略下
> 唯一可行组合（另一选择是放弃 XPM 图标，会损失上游功能面，未采用）。

## 源码修改（patches）

**零补丁**：`patches: {}`。全部平台处置都在 `conanfile.py`（`generate()`/`build()`/`package()`）
内完成，`refresh-patch --auto` 的 `.orig` vs `.work` 差分为空（见 finish 日志）。

## 依赖版本

| 依赖 | 版本 | 角色 |
|------|------|------|
| libx11 | 1.8.13 (force) | `<X11/Xlib.h>`、`libX11.so.6` |
| libxt | 1.3.1 | `<X11/Intrinsic.h>`（XtAppInitialize） |
| libxext | 6.4.0.1 | `-lXext`（XRectangle / shape） |
| xorgproto | 2025.1 | `<X11/X.h>` 等协议头 |
| motif | 2.3.8 | `libXm.so.4` + `<Xm/*.h>`（GUI 主体） |
| libxmu | 1.3.1.1 | `-lXmu`（上游 LDADD 直链） |
| libxpm | 3.5.17 | `<X11/xpm.h>`、`-lXpm`（窗口图标）；1.8.13 轨二进制由源码补建 |
| libsm | 1.2.6 | `-lSM` |
| libice | 1.1.2 | `-lICE` |

## 验证结果（OBSERVED）

```bash
# 1) 手工 OHOS 构建（探索阶段，日志 logs/manual-build-insource2.log）
$ ./configure --prefix=/ --x-includes=... --x-libraries=... && make -j1 VERSION=1.32 && make install DESTDIR=...
CONFIGURE_EXIT=0
MAKE_EXIT=0
MAKE_INSTALL_EXIT=0
# → bin/xanalyser, share/man/man1/xanalyser.1, usr/share/X11/app-defaults/XAnalyser

# 2) 配方验证（8 道门禁）
$ python3 scripts/ohc-run.py conan-verify xanalyser 1.32
G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS
L2 PASS / L4 PASS / L5 PASS（纯可执行包无 lib/ 与 cache 路径 → 工具报告内标注「跳过」，如实照录）
✅ 配方验证通过

# 3) test_package（消费者 + 鸿蒙特有）
#    日志：reports/conan-create.log:190-224（test_package 输出段；assertions=8 在 :224）
#          reports/w3-local-ci.log（W3 本地 CI 完整日志；上游清点 :1536-1577，test_package :1728）
assertions=8 failures=0
PASS: A1 bin/xanalyser exists and is executable
PASS: A2 share/man/man1/xanalyser.1 installed
PASS: A3 share/X11/app-defaults/XAnalyser installed with XAnalyser.SampleRate resource
PASS: B1 (OHOS) ELF interpreter is the OHOS musl aarch64 loader ld-musl-aarch64.so.1
PASS: B2 (OHOS) ELF machine is AArch64 (native armv8 build)
PASS: B3 DT_NEEDED carries the full Motif/X11 chain (libXm/Xt/Xext/Xmu/Xpm/X11/SM/ICE)
PASS: B4 (OHOS) dynamic loader resolved the packaged Motif/X11/libXpm closure
PASS: B5 headless xanalyser reached upstream Xt and reported the missing display (exit 1)

# 4) 上游测试（原样执行）
make check  -> CHECK_EXIT=0（0 用例，automake 空目标）
make test   -> TEST_EXIT=2（无该 target）
```

## 交付物（包内，实测）

| 文件 | 说明 |
|------|------|
| `bin/xanalyser` | ELF64 AArch64 DYN，interpreter `/lib/ld-musl-aarch64.so.1` |
| `share/man/man1/xanalyser.1` | 上游 man page |
| `share/X11/app-defaults/XAnalyser` | Motif 资源文件（84 行，含 `XAnalyser.SampleRate`） |
| `licenses/COPYING` | GPL-2.0 文本 |

## 复现命令

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build xanalyser 1.32 \
    --url=http://arvin.schnell-web.net/xanalyser/xanalyser-1.32.tar.bz2
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify xanalyser 1.32
python3 $SKILL_ROOT/scripts/ohc-run.py finish xanalyser 1.32 built
```

## 已知限制 / 注意事项

1. **无 X server / Wayland**：GUI 不可交互。`XtAppInitialize` 之前的部分（参数解析、
   `XtAppInitialize` 内部的资源合并）在 headless 下也无法观察；上程序在无 DISPLAY 时
   打印上游的 `Error: Can't open display: ` 并以 exit 1 退出（B5 断言的就是这条真实路径）。
2. **ALSA 未启用**：`configure` 的 `AC_EGREP_CPP` 探测 `sys/asoundlib.h`（ALSA 0.9 头）
   在本平台不存在 → `have_alsa=no`，不链接 `-lasound`；声卡输入退化为 OSS 路径
   （`/dev/dsp`）。这与上游在没有 alsa-devel 的发行版上的行为一致。
3. **`-lXmu`/`-lXpm` 头文件未被源码直接包含**：源码只包含 `<X11/xpm.h>` 与 `<Xm/*.h>`，
   但 LDADD 里显式链接 `-lXmu -lXpm`，故两者必须是直接依赖（否则链接失败）。
4. **libxpm 源码构建**：见上文依赖轨冲突一节（CI 会增加一次 libxpm 源码编译）。
5. **CPPFLAGS 里出现 `~/usr/local/include`**：来自本机用户的 `~/usr/local` 前缀
   （R49 允许的用户级前缀），不是共享系统前缀 `/usr/local` 注入。

---

### 对话 #1 — 编译协作者（implementer）[2026-10-14]

**请求**：适配 xanalyser 1.32（http://arvin.schnell-web.net/xanalyser/）到 HarmonyOS PC（目标库适配任务）。
要求：源码与上游测试入口核验、OHOS 平台适配、真实构建、上游测试、test_package、conan create、
conan-verify、finish、W2/W3 与 PR 文件原子性检查；新增一个鸿蒙特有测试且不得是断言。

**执行摘要**：

1. **W0 依赖检查**：先确认依赖能否消费。`conan download <ref> -r=ohpcd --only-recipe` 逐个实测
   motif/2.3.8、xorgproto/2025.1、libxmu/1.3.1.1、libxpm/3.5.17、libx11/1.8.13、libxt/1.3.1、
   libxext/6.4.0.1、libsm/1.2.6、libice/1.1.2 全部可获取（recipe 均在制品仓）。
2. **W1 同步主仓**：`git fetch origin main` + `git merge --ff-only origin/main`（落后 90 个提交），
   HEAD = `b6fd9ca0ac`，随后切分支 `feat/xanalyser-1.32`。
3. **init-build**：`--url=http://arvin.schnell-web.net/xanalyser/xanalyser-1.32.tar.bz2`，
   sha256 `8ca3f65b…f7946`；autotools；`lang-preflight` 判定 `detected=cpp`（通过）。
4. **手工 OHOS 构建**（探索阶段）：
   - 问题①：configure 的 `umask 077` 在 HMDFS 上导致 config.status 临时目录不可写（E011）→ 改 022。
   - 问题②：`../version:1:1: expected unqualified-id`——源码根纯文本 `VERSION` 被
     `-I$(top_builddir)` 放进 include 搜索路径，HMDFS 大小写不敏感 → C++17 `#include <version>`
     命中它；把 VERSION 移出 include 根（configure 之后改名 VERSION.txt）+ make 传 `VERSION=1.32`。
   - 问题③：`[-Wc++11-narrowing]`（XRectangle 列表初始化 15 处）→ `-Wno-c++11-narrowing`。
   - 问题④：motif 依赖头 `Xm/Xm.h` 的 `register` 关键字（`[-Wregister]`，11 处）→
     `-Wno-error=register`（E293 同族）。
   - 结果：`CONFIGURE_EXIT=0 / MAKE_EXIT=0 / MAKE_INSTALL_EXIT=0`，
     产物 `bin/xanalyser` + `share/man/man1/xanalyser.1` + app-defaults。
5. **依赖轨冲突实测**：`conan list "libxpm/3.5.17:*" -r=ohpcd` 显示只有 libx11/6.4.0 轨二进制，
   `conan graph info` 显示 motif 轨（1.8.13）下 libxpm 二进制 Missing；采用 xmhtml/1.1.10 的
   化解方式（force 1.8.13 + libxext/6.4.0.1），实测 `--build=missing` 可从源码补建 libxpm（成功）。
6. **上游测试清点（R51）**：0 个自动化用例（无 TESTS/check_PROGRAMS、无 test 目标），
   `make check` 在 build() 内原样执行（CHECK_EXIT=0，0 用例），`make test` 无该目标（TEST_EXIT=2）。
7. **配方与门禁**：conan-verify G0-G4 全 PASS（L2/L4/L5 对纯可执行包无 cache 路径，工具报告内如实标注跳过）；test_package 8/8 PASS
   （A1-A3 产物 + B1-B5 鸿蒙特有：musl aarch64 解释器 / AArch64 / Motif-X11 链接链 /
   运行期加载闭包 / headless 上游 Xt 报错路径）；W3 本地 CI 通过（`.ci-result.json` exit_code=0）；
   W2 原子性检查「仅含配方变更（10 文件），无框架文件」。
8. **踩坑**：W3 首次失败于 JC（junk_check）——原因是工作树尚未提交，`git diff origin/main...HEAD`
   为空使 junk_check 回退到 full 模式整仓扫描，命中了**他人历史 PR 遗留**的
   `archives/*/*/.staging-verified` / `.build-closed`（共 8 个，已存在于 main）；提交本包文件后
   转为 incremental 模式即通过（本包 10 个文件均干净，未触碰框架文件与他人归档）。

**产出文件**：`conanfile.py`（371 行，零源码补丁）、`conandata.yml`（官方源 + sha256）、
`test_package/`（conanfile.py + test_xanalyser.sh + MANIFEST.yml）、软件级
`commands.json` / `manifest.yaml` / `README.md`、版本级 `manifest.yaml` / `notes.md`、
`reports/`（test-report.md、conan-verify-report.md、conan-create.log、w3-local-ci.log）。

**编译结束**: 2026-10-14
**最终状态**: built
---

**编译结束**: 2026-10-14 21:19
**最终状态**: built
