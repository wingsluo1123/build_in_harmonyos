# xdriinfo 1.0.8 适配笔记

## 编译环境
- 构建系统: autotools（上游 tarball 自带 autoconf 2.73 预生成 `configure`，无需 autoreconf；本机无 automake 不影响）
- 编译日期: 2026-10-16
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，profile `ci/conan/profiles/ohos-aarch64`）
- 目标: HarmonyOS PC aarch64，**原生 build=host**，全程未使用 `--build/--host/--target`（铁律 #0）
- 产物: `bin/xdriinfo`（application，纯可执行包，无 lib/）

## 依赖

xdriinfo 只有一个 C 源文件，`configure.ac` 声明：

```
PKG_CHECK_MODULES(XDRIINFO, x11 glproto)
AC_SEARCH_LIBS([glXGetProcAddressARB], [GL], [], AC_MSG_FAILURE(...), [$XDRIINFO_LIBS])
```

即需要 Xlib、GL 协议头，以及一个提供 `glXGetProcAddressARB` 的 GL 库。

| 依赖 | 版本 | 作用 |
|---|---|---|
| libx11 | 6.4.0 | Xlib（`x11.pc`） |
| glproto | 1.4.17 | `GL/glxint.h`、`GL/glxproto.h` 等协议头（`glproto.pc`） |
| mesa | 24.3.4.1.1.1 | `libGL.so.1`（SONAME libGL.so.1）+ `GL/glx.h`/`glxext.h` + `gl.pc` |
| llvm | 20.1.0 | **仅运行期**：mesa `libGL.so.1 → libgallium-24.3.4.so → DT_NEEDED libLLVM.so.20.1` |

全部为 `ohpcd` 已发布 OHOS/armv8 二进制（`conan install --build=never` 实测可解析并下载）。

### 为什么不是 libglvnd（认领侦察给出的依赖集）

侦察结论（`claim-recon-5-20261016-1/xdriinfo/dependencies.txt`）写的是 “链接 libGL（glvnd）”。实测不成立：

- `libglvnd/1.7.0` 配方把 `x11`/`glx` 关闭，产物只有 `libGLdispatch/libOpenGL/libGLESv1_CM/libGLESv2`（动态）+ `libEGL.a`（静态），
  **没有 `libGL.so`、没有 `libGLX.so`、没有 `gl.pc`、没有 `GL/glx.h`**；`configure` 的
  `AC_SEARCH_LIBS([glXGetProcAddressARB],[GL])` 永远无法被满足。
- 实测（`llvm-nm -D`）：mesa 的 `libGL.so.1` 导出 `glXGetProcAddressARB`、`glXGetScreenDriver`、
  `glXGetDriverConfig`、`glXGetClientString` —— 这是唯一同时也是语义正确的提供者（DRI/GLX 查询工具）。
- 对照实测 `gl4es/1.1.6`：也提供 `libGL.so.1` + `GL/glx.h`，但其 `glXGetProcAddressARB("glXGetScreenDriver")`
  与 `("glXGetDriverConfig")` 均返回 NULL（探针程序实测），xdriinfo 会在解析 argv 之前就打印 “libGL is too old.” 退出，
  无显示器可验证的命令行路径全部不可达。故选择 mesa。

### 运行期闭包

`libGL.so.1` 的 DT_NEEDED 含 `libglapi.so.0`、`libgallium-24.3.4.so`、`libX11.so.6`、`libxcb.so.1`、
`libxcb-glx/shm/dri3/present/xfixes.so`、`libX11-xcb.so.1`、`libXext.so.6`、`libXxf86vm.so.1`、`libexpat.so`；
`libgallium` 再需要 `libLLVM.so.20.1`、`libz.so`、`libc++_shared.so`。

mesa 二进制包里 `mesa_llvm_lib_dir` 记录的是**构建者**的 conan home（`.cache/conan2/...`），在消费者机器上
不可达（本机 conan home 为 `.conan2`），OHOS SDK 只带 `libLLVM-15`，因此配方显式声明 `llvm/20.1.0`（`run=True`）
让运行期能找到 `libLLVM.so.20.1`。

## 编译步骤（实际）

1. `conan create archives/x/xdriinfo/1.0.8 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=missing`
2. `generate()`：`AutotoolsToolchain` + `AutotoolsDeps`；`PKG_CONFIG_PATH` 覆盖全部 host 依赖的
   `lib/pkgconfig` 与 `share/pkgconfig`；并把依赖 `libdirs` 前置注入 `LD_LIBRARY_PATH`（见问题 2）
3. `build()`：`apply_conandata_patches()` → `configure` → `make -j1`（HMDFS 上 make 并行作业 server fifo 有 EPERM 先例，故 `-j1`）
4. `package()`：`make install` + OHOS ELF 签名（`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one`（配置更早一步其实是 `config.guess` 退出 1：`unable to guess system type`） | 上游自带 config.guess（timestamp 2024-07-27）不认识 HarmonyOS（`uname -s` = `HarmonyOS`），退出码 1；`configure` 第 4987 行 `ac_build_alias=config.guess` 拿到空值后报错。`config.sub` 本身**已支持** `ohos*`/`linux-ohos*`（实测 `config.sub aarch64-unknown-linux-ohos` → rc=0），只需补 config.guess | `patches/0001-config.guess.patch`：加 `*:HarmonyOS:*:*` 分支输出 `${MACHINE}-unknown-linux-ohos`。**不使用** `--build/--host/--target`（铁律 #0 / P-AUTOTOOLS-001）；补丁为纯 shell 分支，不含 `__OHOS__` 记号（不触 PF5） |
| 2 | `configure: error: cannot run C compiled programs`，config.log 显示 `Error loading shared library libGL.so.1: (needed by ./conftest)`（以及 libEGL/libX11/libxcb-*/libLLVM… 一长串） | `AutotoolsDeps` 只提供 `-I/-L/-l`，不负责运行期搜索路径；`AC_PROG_CC` 的 `AC_RUN_IFELSE` conftest 链接了这些共享依赖后要**立即执行**，而 conan 缓存目录不在加载器默认搜索路径内 → 运行失败 → autoconf 误判为交叉编译（`cross_compiling=yes`）→ 报 “cannot run C compiled programs” | `generate()` 里用 `Environment` 把每个 host 依赖的 `libdirs` 前置进 `LD_LIBRARY_PATH` 并 `save_script("conanbuild_runpath")`（同 `aaphoto/0.45`、`dirb/2.22`，知识库 DRAFT-conan-dep-shared-libs-break-configure-conftest 的 rec 方案）。修后 `checking whether we are cross compiling... no` |
| 3 | `./config.status: line 612: ./confbnKgFD/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery` | HMDFS 有 uid 映射（文件属主 uid ≠ 进程 kernel uid），权限检查落到 group 分支；autoconf 生成的 `configure` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录 → mode 0700，group 无权限 → 写 `subs1.awk` EACCES | `patches/0002-configure.patch`：把构建路径上的 `umask 077` 改为 `umask 007`（保留 group rwx），对应 E114 / DRAFT-10863。`Makefile.in:782` 的 `umask 077` 位于 distdir 规则、不在构建路径，按该条目口径**不**改 |

## 源码修改（补丁）

| 补丁 | 对象 | 内容 | 类型 |
|---|---|---|---|
| `patches/0001-config.guess.patch` | `config.guess` | 新增 `*:HarmonyOS:*:*` 分支，输出 `${MACHINE}-unknown-linux-ohos` | portability |
| `patches/0002-configure.patch` | `configure` | `umask 077` → `umask 007`（2 处，autoconf 安全临时目录） | portability |

两个补丁均由 `ohc-run.py refresh-patch --auto` 从真实改动源码生成（R3），未手写 diff。
SHA256：0001 = `530d182e9355935074ceff4ea504c34ae36f3cd6b369884a29e0524c782d8f74`，
0002 = `7c3dc1ea0ea9fdb96447aaf540c5dcdf821b5dd05dc8fcb35ec23462831e648a`。
无 `#ifdef __OHOS__` 空壳、无 stub、无删除用例、无改断言。上游源码（`xdriinfo.c`）**零修改**。

## 上游测试清点（R51）

上游 1.0.8 发布包**没有自动化测试套件**（清点证据见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`）：

- `Makefile.am`：只有 `SUBDIRS = man`、`bin_PROGRAMS = xdriinfo`、`xdriinfo_SOURCES = xdriinfo.c`，
  无 `TESTS`/`check_PROGRAMS`/`check-local`（`grep -c` = 0）。automake 生成的 `check` 目标存在
  （`Makefile.in:824-825` `check-am: all-am` / `check: check-recursive`），但注册 0 个用例，跑它是空操作。
- `configure.ac`：无任何测试框架宏。
- `meson.build`：无 `test()`（`grep -c` = 0）。
- 源码树 23 个文件，无 `tests/`、无 `*_test`/`test_*` 源文件。
- `xdriinfo.c`：`grep -c 'assert('` = 0。

因此申报表为：上游测试 TOTAL = 0（无测试可跑）；真实执行由 `test_package/test_xdriinfo.sh` 承担。

## 消费者测试（test_package，实测 5/5）

`test_package/conanfile.py` 真实执行被测二进制（R34），断言真实输出与退出码。5 项全部通过：

| # | 命令 | 断言 | 实测结果 |
|---|---|---|---|
| 1 | `xdriinfo --version` | stdout 含 `xdriinfo 1.0.8`，rc=0 | ✅ `xdriinfo 1.0.8`，rc=0 |
| 2 | `xdriinfo -version` | 同上 | ✅ `xdriinfo 1.0.8`，rc=0 |
| 3 | `xdriinfo -help` | 打印 usage banner，rc=0 | ✅ `Usage: xdriinfo [-display <dpy>] [-version] [command]`，rc=0 |
| 4 | `xdriinfo -Zz` | 非 0 退出 + 打印未识别参数诊断 | ✅ `unrecognized argument '-Zz'` + usage，rc=1 |
| 5 | `xdriinfo nscreens`（无 DISPLAY） | 非 0 退出 + `Couldn't open display` | ✅ `Error: Couldn't open display`，rc=1 |

为什么这 5 条是“真跑”而不是空壳：`xdriinfo.c` 在解析 argv **之前**就调用
`glXGetProcAddressARB("glXGetScreenDriver")` / `("glXGetDriverConfig")`，任一为 NULL 即
打印 “libGL is too old.” 并 rc=1。测试 1–3 能通过，说明被测二进制真的加载了 mesa 的
`libGL.so.1`、真的解析到了这两个 DRI 入口点、真的走到了 `puts(PACKAGE_STRING)`（PACKAGE_STRING
来自 configure 生成的 config.h）。测试 5 走的是真实的 `XOpenDisplay` 失败分支（无 X server 的
鸿蒙真机上确定性成立；脚本先 `unset DISPLAY` 保证确定性）。

CI 的 L1e 破坏性反向验证也通过：移走 `bin/` 后 `conan test` 失败 → 证明测试确实依赖被测包。

## 门禁结果

### 本地 conan-verify（`ohc-run.py conan-verify xdriinfo 1.0.8`，rc=0）

| 门禁 | 结果 |
|---|---|
| G0 预构建风险评估 | ✅ PASS（知识命中 E490，提示 autotools 辅助脚本可执行位） |
| G1 配方完整性 | ✅ PASS |
| G2 conan create（含 build + test_package） | ✅ PASS |
| G3 产物 | ✅ PASS（纯可执行包，无 lib/，无系统同名库冲突） |
| G4 | ⚠️ 未找到程序包 ID（框架侧；L2/L4/L5 因此显示“无 cache 路径”跳过，与同目录 xev 报告一致） |

### CI 同构（`ci/conan/build_and_test.sh`，`CI_REPO_ROOT=<worktree>`、`CONAN_PROFILE=<根仓库 profile>`、`JUNK_PR_DIFF=<本 PR 文件清单>`，rc=0）

| 门禁 | 结果 |
|---|---|
| JC（junk check） | ✅ pass |
| L0 前置门禁 | ✅ pass（含 L0j 版本号占用检查：`version not in registry yet (first publish)`） |
| L1 conan create + test_package | ✅ pass（`[ok] xdriinfo/1.0.8 — conan create passed`） |
| L1e 破坏性反向验证 | ✅ pass（移走 bin/ 后测试失败 → 真测试） |
| L5 产物基线 | ✅ pass（`bin/ has content`） |
| L2 smoke（`--version`/`--help`） | ⏭️ skip：框架 L2 直接在**不带依赖 libdir** 的环境里跑 `timeout 15 <bin> --version`，二进制因找不到 `libGL.so.1`（及 libgallium/libLLVM）而无法启动 → 非阻塞跳过。同一二进制在 test_package（注入依赖 libdir 后）5/5 通过，且 `--version` 本身返回 0（见上表测试 1）。属框架 smoke 的环境限制，非本包缺陷 |
| L4 补丁危险函数扫描 | ⚠️ warn（非阻塞）：命中 `patches/0001-config.guess.patch`。**误报**：扫描正则为 `(strcpy|sprintf|gets|strcat)\b`，命中的是补丁**上下文行**里 NetBSD 注释中的单词 “tar**gets**”（第 25/27 行；`\b` 在该 grep 实现下未起词边界作用）。补丁新增行是纯 POSIX shell 分支，不含任何危险 C 函数；真正含 `mktemp` 的 `0002-configure.patch` 未被命中 |
| 汇总 | Total 1 / Success 1 / Failed 0 / Pass rate 100.0% |

### 复现命令

```sh
# 本地 conan-verify
porting run --workspace <wt> --expect-branch feat/xdriinfo-1.0.8 \
  --job-id <unique> --task-id t_xdriinfo12088 -- \
  python3 $F/scripts/ohc-run.py conan-verify xdriinfo 1.0.8 \
  --profile $HOME/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 --project-dir <wt>

# CI 同构
porting run --workspace <wt> --expect-branch feat/xdriinfo-1.0.8 \
  --job-id <unique> --task-id t_xdriinfo12088 -- env \
  JUNK_PR_DIFF=<pr file list diff> CI_PACKAGES="archives/x/xdriinfo/1.0.8" \
  CI_REPO_ROOT=<wt> CONAN_PROFILE=$HOME/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  zsh $F/ci/conan/build_and_test.sh
```

## 未验证项 / 已知限制

1. **无 X server → 功能路径未能真机验证**：`nscreens`/`driver`/`options` 三条需要 `XOpenDisplay` 成功的
   查询路径在鸿蒙上无法执行（系统无 X server，也无 DRI 驱动可查）。已验证的是构建、产物、R34 真实执行
   与非显示器路径；**未**宣称 xdriinfo 的 DRI 查询功能在 OHOS 上可用（R40 口径：本包不引入任何平台
   适配桩，功能缺失源于平台本身无 X/DRI，非适配遗漏）。
2. L2 smoke 未通过（框架不注入依赖 libdir），已在上面归因。
3. 无 `packaging/` tar 产物（ARCHIVE-SPEC v3.0 已废弃）。
4. 未做任何平台写入（push / PR / 提审 / 合入 / 上传），`commands.json` 的 `binary` 保持 `false`
   （尚未经 release 流水线上传制品仓）。

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` | 配方（autotools，build=host） |
| `conandata.yml` | 官方源 URL + sha256 + 2 个补丁 |
| `patches/0001-config.guess.patch` | HarmonyOS 三元组识别 |
| `patches/0002-configure.patch` | HMDFS 临时目录权限（umask 077→007） |
| `test_package/{conanfile.py,test_xdriinfo.sh,MANIFEST.yml}` | 消费者测试（5 项真实断言）+ 上游测试清点申报 |
| `manifest.yaml` | 版本级 manifest |
| `../commands.json` | 命令行工具声明（R38） |
