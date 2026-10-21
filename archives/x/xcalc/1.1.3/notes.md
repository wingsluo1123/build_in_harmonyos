# xcalc 1.1.3 适配笔记

## 编译环境
- 构建系统: autotools (configure + make，tarball 自带预生成 configure/Makefile.in，无需 autoreconf)
- 编译日期: 2026-10-20
- 编译器: clang 15 (OHOS SDK，profile `ci/conan/profiles/ohos-aarch64`)
- 目标: OHOS aarch64 **原生 build=host**（不传 `--build/--host/--target`，铁律 #0）
- 状态: built（PR 阶段，未 upload）

## 编译步骤

```bash
# 由 CI/hmbs 在 HarmonyOS aarch64 真机执行（profile: ohos-aarch64）
conan create archives/x/xcalc/1.1.3 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

1. `source()`：下载 X.Org 官方 tarball `xcalc-1.1.3.tar.xz`（sha256
   `86e157b6…4980`，146996 字节，与官方发布及 FreeBSD ports distinfo 一致）
2. `generate()`：`PkgConfigDeps`（重命名 `libxmu::xmu`→`xmu`、`xorgproto`→`xproto`）
   + `AutotoolsToolchain`（追加 `--with-appdefaultdir=/share/X11/app-defaults`）
3. `build()`：`apply_conandata_patches` → `./configure`（原生三元组，见下）→ `make -j1`
   → `make check`（上游 0 用例）
4. `package()`：`make install` → `bin/xcalc` + `share/X11/app-defaults/XCalc[-color]`
   + `share/man/man1/xcalc.1`；对 `bin/xcalc` 做 OHOS ELF 自签（E077）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` / 原生 build 无法判定 | tarball 自带 `config.guess`（2024-07-27）用 `uname -s` 识别系统，设备返回 `HarmonyOS` 不在其已知 OS 列表；且它对 `Linux|GNU` 分支编译探针写 `$TMPDIR`，HMFS 上失败（本机实测 `can't create .../dummy.c: Permission denied`）。铁律 #0 禁止 `--build/--host/--target` | 补丁 `0001-config.guess.patch`：加 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`；`__OHOS__` 时 `LIBC=ohos`；编译探针临时目录 `umask 077→022`（E007/E205/E011）。tarball 自带 `config.sub`（2024-05-27）**已接受** `ohos*`/`linux-ohos*`（本机 `config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`），无需 config.sub 补丁 |
| 2 | `configure: error: working directory cannot be determined`（HMDFS 下） | conan 缓存父目录对 `getcwd()` 不可达；autoconf 2.72 生成的 configure 顶部严格 `pwd` 判定直接 abort | 补丁 `0002-configure.patch`：`ac_pwd=\`pwd\`` 加 `2>/dev/null \|\| ac_pwd="$PWD"` 回退（2 处） |
| 3 | `config.status: cannot create a temporary directory in .` | `config.status` 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，HMFS 上 0700 目录不可写（E011/E114） | 同一补丁 `0002`：`umask 077→022`（2 处） |
| 4 | `configure` 的 `PKG_CHECK_MODULES(XCALC, [xaw7 xt x11 xproto >= 7.0.22])` 找不到 `xproto` | PkgConfigDeps 生成的 `.pc` 名取自 Conan `pkg_config_name`：xorgproto 未设（默认 `xorgproto`）；libxmu 的 Xmu 组件发布名是 `libxmu` | `generate()` 里 `set_property("libxmu::xmu","pkg_config_name","xmu")`、`set_property("xorgproto","pkg_config_name","xproto")`（libxaw/1.0.14、xfontsel/1.1.2 同款）；`build()` 里以 generators 目录优先拼 `PKG_CONFIG_PATH` |
| 5 | `make install` 时 app-defaults 安装到 `/`（appdefaultdir 为空） | conan `xt.pc` 无 `appdefaultdir` 变量，`xt_appdefaultdir=` 取到空串 | 显式 `--with-appdefaultdir=/share/X11/app-defaults`（`$(DESTDIR)` 前缀化后落到包内路径） |
| 6 | W3 CI 预下载步骤把源码 URL 原地改写为本地路径型 URL，且**不校验 HTTP 状态码、不校验 sha256**（成功判据只有 `size>100`B）⇒ 命中死镜像时 `source()` 只收到 162 字节的 404 错误页，conan 报 `sha256 hash failed`（Computed 340c8464…，Expected 86e157b6…） | 框架 `ci/conan/build_and_test.sh` 预下载段（Python 块）对 `xorg.freedesktop.org/(archive|releases)/` 走「镜像优先」重试，三条镜像 `mirror.csclub.uwaterloo.ca` / `www.mirrorservice.org` / `mirrors.ircam.fr` 对该 `archive/individual/app/` 路径实测全部 404（csclub 的 `/x.org/individual/` 停在 2023-09，无 2026-02 发布的 1.1.3），404 页 162B > 100B 被误判为成功 ⇒ `archive/` 条目被改写成坏文件。属框架预下载缺陷（单独 PR 范畴，本包不修框架） | `sources.url` 改为**同一官方主机 xorg.freedesktop.org 的两条官方路径**：`pub/` 在前（不命中那条路径正则 ⇒ 预下载直连官方取到 146996 字节真包）、`archive/` 兜底；两条都是官方原始 URL，无第三方代理前缀 ⇒ 符合 R39。conan `tools.files.download()` 对 URL 列表按序逐条尝试且逐条校验 sha256 ⇒ 首条即命中真包，**sha256 未改**。与 xdriinfo 1.0.8 / xev 1.2.7 已过门禁同款 |

## 源码修改

- `patches/0001-config.guess.patch`：教 config.guess 识别 HarmonyOS →
  `aarch64-unknown-linux-ohos`，并把编译探针临时目录 umask 放宽为 022。
- `patches/0002-configure.patch`：configure 顶部加 `$PWD` 回退（HMDFS
  getcwd 不可达，2 处），config.status 临时目录 umask 077→022（2 处）。
- 两个补丁均由 `refresh-patch --auto` 从真实源文件改动生成（orig/work 双轨），
  实测 `patch -p1` 对原始 tarball 干净应用（rc=0，应用后与 work 目录逐字节一致）。
- `xcalc.c` / `actions.c` / `math.c` / `xcalc.h` 未改动。

## 依赖版本

- `libxaw/1.0.14`（组件 xaw7）、`libxmu/1.3.1.1`、`libxt/1.3.1`、
  `libxext/6.4.0.1`、`libx11/1.8.13`（force，与 libxmu/libxaw 同轨）、
  `xorgproto/2025.1`（提供 xproto.pc）
- 运行期闭合（run=True，仅供 test_package conanrun 环境）：
  `libxcb/1.17.0`、`libxau/1.0.11`、`libxdmcp/1.1.5`
- 全部为 ohpcd 已发布 OHOS/armv8 二进制（本轮 conan 求解后全部命中 Cache，
  无源码重建）

### 真实依赖图求解结果（conan create 的 "Computing dependency graph"）

```
Requirements
  libice/1.1.2   libsm/1.2.6    libx11/1.8.13  libxau/1.0.11
  libxaw/1.0.14  libxcb/1.17.0  libxdmcp/1.1.5 libxext/6.4.0.1
  libxmu/1.3.1.1 libxpm/3.5.17  libxt/1.3.1    xorgproto/2025.1
  xcb-proto/1.17.0  xtrans/1.4.0  xtrans/1.6.0
Overrides
  libx11/6.4.0 → libx11/1.8.13      # 根配方 force 覆盖 libxmu 链的 6.4.0，无冲突
WARN risk: xorgproto/2025.1 被 libsm/libice 以 visible=True 与 False 同时要求（非致命）
```

即 libxaw 传递引入的 libxmu/libxpm/libice/libsm/libxext 与根 force 的
`libx11/1.8.13` 图求解一致，**无版本冲突**（可证伪项通过）。

## 验证结果

### 真机门禁（`porting run`，每次作业用新 JOB_ID）

门禁经 `porting run` 在 HarmonyOS aarch64 真机执行；每次作业的完整日志与 `job.json`
（记录 `head_before` / `head_after` / 真实退出码）落在
`$HOME/.local/share/ohpc-porting/runs/<job-id>/`。下列为本 HEAD 上实测的逐项结果。
**刻意不内嵌具体 job_id 与短 SHA**：二者随提交变化，写死在文档里会随下一次文档改动而失准；
需要核对「该次门禁绑定的是当时 HEAD」时，以该目录 `job.json` 的
`head_before == head_after == 提交时 HEAD` 为准。

**① conan-verify**（`ohc-run.py conan-verify xcalc 1.1.3`）— 真实退出码 **0**，
`job.json` 记 `head_before == head_after == 提交时的 HEAD`

```
G0: PASS   G1: PASS   G2: PASS（conan create 干净构建成功）
G3: PASS（无系统同名库冲突）
G4: PASS，但工具附告警「⚠️ 无法找到程序包 ID」——未真正定位包 ID，
    见下「工具限制」第 1 条，不按完整通过采信
L2/L4/L5: 该工具内被跳过（见下「工具限制」），未作通过采信
```

**② CI 同构**（`zsh <worktree>/ci/conan/build_and_test.sh`，`JUNK_PR_DIFF` 单包口径）
— 真实退出码 **0**，`job.json` 记 `head_before == head_after == 提交时的 HEAD`

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: xcalc version/help failed
L4_RESULT=warn: dangerous functions in patches
L5_RESULT=pass: bin/ has content
L1e 破坏性负测试: pass（移走 bin/ 后 test_package 确实失败）
Build Summary: Total 1 / Success 1 / Failed 0
```

- L2 skip 原因：CI 的 L2 在不注入 conanrun/`LD_PRELOAD` 的环境下直接执行 conan
  缓存 `bin/xcalc`，OHOS 加载器找不到缓存中的 `libXaw7.so.7`/`libXt.so.6` 等 →
  进程起不来。非阻塞项；`xfontsel 1.1.2` / `xdriinfo 1.0.8` / `xwax 1.10` 的
  `ci-metadata.json` 实测同款 `L2=skip`，属该环境对 X11 GUI 小程序的既定行为。
- L4 warn 原因：正则 `(strcpy|sprintf|gets|strcat)\b` 命中补丁上下文行里的单词
  `targets` 结尾 `gets`；假阳性，非阻塞（xfontsel 同款）。

### 消费者测试（test_package，conan create 的 test 阶段）

`test_xcalc.py`：`discovered=5, passedCount=5`（真实断言 stdout/stderr + 退出码）

```
-version  → stdout "xcalc 1.1.3"           rc=0
--version → stdout "xcalc 1.1.3"           rc=0
-help     → stderr "Usage: ..."            rc=0   （main() 调 Syntax(1, argv)）
--help    → stderr "Usage: ..."            rc=0
无 DISPLAY → rc=1 "Error: Can't open display:"
```

运行期以依赖图全部实体 `.so` 经 `LD_PRELOAD` 注入（OHOS loader 可能忽略
`LD_LIBRARY_PATH`、HMFS 不保证 symlink 链，E050），并经 conanrun 环境补齐 libdir。

### 上游测试清点

| 项 | 数量 | 证据 |
|----|------|------|
| PASS | 0 | — |
| FAIL | 0 | — |
| SKIP | 0 | — |
| NOT_RUN | 0 | — |
| **TOTAL** | **0** | `0 = 0 + 0 + 0 + 0` |

xcalc 1.1.3 **上游无自动化测试套件**（清点证据：发布包文件清单无 `tests/`/`test/`
目录与测试源文件；`Makefile.am` 无 `TESTS`/`check_PROGRAMS`/`check-local`；
`man/Makefile.am` 无测试目标；`meson.build` 无 `test()`/`test_suite()`；
`configure.ac` 无 `AC_CONFIG_TESTDIR`）。构建仍显式执行 `make check`（0 注册用例），
`HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","discovered":0,...}`。

### 工具限制（非本包问题，已如实记录，不采信为通过）

1. `conan-verify` 的 G4 用 `conan list <ref>:* --format=json` 后按
   `["Local Cache"][<software>][<ref>]` 取包 ID，而 conan 2.29.1 的实际结构是
   `["Local Cache"][<ref>]` ⇒ KeyError ⇒ `_cache_path` 未设置 ⇒ 该工具内
   L2/L4/L5 全部跳过（报告里显示为 "PASS ⏭️ 跳过"，属工具展示缺陷）。
   同一 KeyError 也令 G4 段在报告里显示为 `✅ PASS ⚠️ 无法找到程序包 ID`——
   即「通过」并未真正定位到包 ID，故本笔记不把 G4 记为完整通过。
   本包的 L2/L4/L5 以 CI 同构门禁（②）的真实 RESULT 行为准。
2. CI 预下载缺陷（见问题 #6）：框架侧问题，本包以官方 `pub/` + `archive/` 双路径
   规避，未改框架。

## 新增 / 未变 / 未验证 三分

- **新增**：`archives/x/xcalc/`（软件级 README.md / commands.json / manifest.yaml；
  版本级 conandata.yml / conanfile.py / manifest.yaml / notes.md / patches×2 /
  test_package×3）
- **未变**：无（首次移植；未触碰其它软件、未改框架/CI/共享控制文件）
- **未验证**：GPG 签名（设备无 X.Org 发布密钥环）；xcalc 完整 GUI 交互（需 X
  server，真机无 X）；制品仓 `upload`/远端下载（未 push、未发布）

## 注意事项

- 上游无自动化测试套件：`test_package/MANIFEST.yml` 写入
  `upstream_tests_exist: false` + 非空 `upstream_test_audit`（发布包清单 /
  Makefile.am / man/Makefile.am / meson.build / configure.ac 五处审计）
- xcalc 实际 GUI 运行需要 X server；真机 CI 无 X 环境，test_package 以
  -version/-help 无头路径验证（与 xfontsel 1.1.2、xterm 410 同款处理）
- 版本号 1.1.3 为首版适配（R37）
