# pkgfile 25 HarmonyOS 适配前置分析报告（A 类）

> **后续进展（2026-10-14）**：本报告完成后的真机构建又暴露并修复了 6 个问题
> （meson 归档器裸名 exec、`get_define` 头宏探测、pkg-config 缺失、`stdc++fs`
> find_library 硬要求、`src/db.cc` 的 clang15/libc++15 兼容性、mksh/TMPDIR 临时文件），
> 并新增补丁 0003/0004。**最终结果以 `reports/device-verification.md` 为准**：
> 真机 shadow CI 单包 L0/L1/L2/L4/L5 全 pass，Build Summary 1/1（100%），
> 上游单元测试 11/11、消费者测试 16/16 断言通过。本报告保留为**前置分析阶段**的
> 原始记录（其中「只有 curl 是 shared」的判断已被真机实测纠正，见 §5.6）。

| 项 | 值 |
|----|----|
| 目标库 | pkgfile |
| 版本 | 25（上游 tag `v25`） |
| 任务类型 | A 类（前置适配：依赖检查 + 源码/构建系统分析 + 配方与 test_package + 本机验证 + 下一步命令） |
| 分支 | `feat/pkgfile-25` |
| worktree | `D:\harmonyos\worktrees\pkgfile` |
| 改动范围 | `archives/p/pkgfile/`（软件级 `manifest.yaml`/`README.md`/`commands.json` + `25/`） |
| 状态 | **前置分析完成；真机 shadow CI 单包验证通过**（`status: built`，见 `device-verification.md`） |
| 真机占用 | 前置阶段未占用；后续在真机空闲窗口完成单包验证（`--try-lock` 排队） |

## 1. 结论摘要

pkgfile 25 是 Meson + C++20 的 Arch 生态命令行工具。经 W0 依赖检查、源码与构建系统
分析后判定：**可适配**，且不需要新增任何依赖库 PR。共识别 8 个适配问题，其中 3 个是
「不处理必然 configure/编译失败」的硬阻塞：

| 阻塞级别 | 问题 | 处置 |
|---------|------|------|
| 硬阻塞 | `libsystemd` 为**无条件依赖**，OHOS 无 systemd 生态，ohpcd 制品仓 0 命中 | 补丁 0001 把 `pkgfiled` 守护进程改为 `-Ddaemon=false` 可关闭 |
| 硬阻塞 | `find_program('pod2man')` 为硬要求，OHOS 无 perl | 补丁 0002 把 man 页改为 `-Dman_pages=false` 可关闭 |
| 硬阻塞 | CI profile `compiler.cppstd=17` 会静默覆盖上游 `cpp_std=c++20` | `configure()` 内把 `compiler.cppstd` 抬到 20 |
| 高风险 | libc++ 15004 默认不暴露 `std::format`（源码 44 处使用） | 启用 `_LIBCPP_ENABLE_EXPERIMENTAL` + 链接 `libc++experimental.a`（仓库内已有 20+ 先例） |
| 中 | `dependency('libpcre')` 与 conan 包名 `pcre` 不一致 | 消费侧 `PkgConfigDeps.set_property` 改写 .pc 名，不改上游 meson.build |
| 低 | `find_program('pkg-config')` 硬要求 | `tool_requires("pkgconf/3.0.5")` |
| 低 | `update.cc` 在 `TMPDIR` 未设时回落 `/tmp`（OHOS 可能只读） | 不改源码，test_package 显式 `export TMPDIR` |
| 低 | `meson add_install_script` 在 DESTDIR 下建 `/var/cache/pkgfile` | `package()` 内删除包内空 `var/` 树 |
| 中 | 产物缺少运行期 rpath → CI L2 裸执行 `bin/pkgfile --version` 可能失败 | `generate()` 内为全部 host 依赖补 `-L`/`-Wl,-rpath` |

**未验证项（不得视为通过）**：真机 `conan create`（W3）与上游 11 个 gtest 单元用例的
实际执行结果尚未取得，`test_package/MANIFEST.yml` 的 `upstream_tests_passed` 记 0。

## 2. 目标与范围

- 目标：完成 pkgfile 25 的前置适配，产出可直接进入真机验证的配方与测试。
- 范围内：源码/构建系统分析、W0 依赖检查、`conanfile.py`、`conandata.yml`、补丁、
  `test_package/`（含真实断言）、软件级 `commands.json`、本机可做的全部验证、下一步命令。
- 范围外：真机构建与发布（需真机窗口）；`libsystemd`/`systemd` 的适配（按「依赖缺失先拆
  依赖库单独适配」原则，本 PR 不混入，且已通过关闭功能规避）。

## 3. W0 依赖发布检查

检查方式：`conan download <ref> -r=ohpcd --only-recipe`（遵循 R35，不用 `conan list` 判二进制）。

| 依赖 | 上游 meson.build 要求 | ohpcd 实测结果 |
|------|----------------------|---------------|
| pcre | `dependency('libpcre', version: '>= 8.30')` | ✅ `pcre/8.45` 实拉成功 |
| libarchive | `dependency('libarchive', version: '>= 3.2.0')` | ✅ `libarchive/3.8.7`、`libarchive/3.7.7` 实拉成功 |
| curl | `dependency('libcurl')` | ✅ `curl/8.15.0.1` 实拉成功 |
| **libsystemd** | `dependency('libsystemd')`（顶层无条件） | ❌ **0 命中**（`conan list "libsystemd/*" -r=ohpcd` → no matching recipe references） |
| gtest / gmock | `dependency('gtest'/'gmock', required: false)` | ✅ `gtest/1.17.0`（另有 .1/.2）、`gmock/1.17.0` |
| meson | 构建工具 | ✅ `meson/1.11.0`（另有 1.11.0.1） |
| ninja | Meson 后端（meson 配方不代管） | ✅ `ninja/1.12.1`（另有 1.13.2） |
| pkgconf | 提供 `pkg-config` | ✅ `pkgconf/3.0.5`（另有 3.0.4/3.0.6） |
| pod2man | `find_program('pod2man')`（硬要求） | ❌ OHOS 无 perl，仓库无独立 pod2man 包 |

对 `libsystemd` 缺失的判定依据（决定不新建依赖 PR 的关键证据）：

1. 上游 `INSTALL` 明确列出运行期依赖为 `libcurl / libarchive / pcre / pthreads`，
   **不含 libsystemd**；
2. `libsystemd` 只被 `src/pkgfiled.cc` 使用（`#include <systemd/sd-event.h>`，
   使用 `sd_event_default` / `sd_event_add_inotify` / `sd_event_add_signal` /
   `sd_event_loop`），即 systemd socket 激活的守护进程；
3. `pkgfile`（CLI）自身不引用任何 sd-* 符号。

因此按工作流「可选依赖缺失 → 优先最小化关闭可选功能，记录到 PR 说明」处置。

## 4. 源码与构建系统分析

```
pkgfile-25/
├── meson.build            # 5710 B，meson_version >= 0.56，default_options cpp_std=c++20
├── meson_options.txt      # 仅 cachedir / systemd_units 两个选项（无关闭守护进程的开关）
├── src/
│   ├── archive_converter.cc/.hh   # alpm .files -> pkgfile 分片缓存
│   ├── archive_io / archive_reader
│   ├── compress / db / filter / repo / result / update / queue
│   ├── pkgfile.cc         # CLI 主程序（561 行）
│   ├── pkgfiled.cc        # systemd 守护进程（sd-event）
│   ├── filter_test.cc     # 上游单测 10 例
│   ├── repo_test.cc       # 上游单测 1 例
│   └── test/gtest_main.cc
├── tests/                 # python 集成测试 27 例（database 3 / list 8 / search 8 / update 8）
├── man/, systemd/, extra/, build-aux/
└── INSTALL
```

C++20 特性使用统计（`src/*.cc|hh`）：

| 特性 | 出现次数 | 说明 |
|------|---------|------|
| `std::format` | 44（archive_converter 9 / update 15 / pkgfile 8 / pkgfiled 6 / repo 4 / filter 2） | 需 libc++ 的 `<format>` |
| `std::span` | 3 | libc++ 15 已实现 |
| `operator<=>` | 1 | clang 15 `-std=c++20` 支持 |
| `<format>` include | 6 | — |
| ranges / views / concepts / jthread | 0 | 未使用 |

其余平台相关点扫描：

- 无 glibc 专有符号依赖；
- 无 `mkstemp` 之外的临时文件用法；`update.cc:98-126 OpenTmpfile()` 读 `TMPDIR`，
  未设时回落 `/tmp`；
- 无 symlink/hardlink/FIFO 依赖（`Finalize()` 用 `fs::rename` 落盘分片）；
- 无 GUI/外设/系统底层调用，仅标准 POSIX + libarchive + libcurl + pcre。

## 5. 根因分析（逐项）

### 5.1 `libsystemd` 硬依赖 → configure 必失败

- **现象（预判）**：`meson setup` 阶段报
  `Dependency "libsystemd" not found, tried pkgconfig and cmake`，因为
  `meson.build:34` 是顶层无条件 `dependency('libsystemd')`。
- **根因**：`pkgfiled` 是 systemd 专属守护进程（inotify + sd-event 事件循环 +
  socket 激活），上游把它当作项目的一部分而非可选组件；`meson_options.txt` 里只有
  `systemd_units`（是否安装 unit 文件），**没有**「不构建守护进程」的开关。
- **处置**：补丁 0001 新增 meson 选项 `daemon`（默认 `true`），用它门控
  `libsystemd` 依赖、`executable('pkgfiled')` 与 systemd unit 安装块；
  OHOS 构建时 `-Ddaemon=false`。
- **为什么不用 stub**：`pkgfiled` 的核心逻辑全部建立在 `sd_event_*` 之上，
  stub 只能产出无法工作的空壳二进制（且触碰 R40/反 stub 约束）。
  关闭一个与目标平台无关的 systemd 守护进程是语义正确的选择。

### 5.2 `pod2man` 硬要求 → configure 必失败

- **现象（预判）**：`meson setup` 报 `Program 'pod2man' not found`。
- **根因**：`meson.build:40` `find_program('pod2man')` 未加 `required: false`，
  且两个 man 页 `custom_target` 无条件引用它。pod2man 来自 perl；
  OHOS 镜像不含 perl，仓库也无独立 pod2man 制品。
- **处置**：补丁 0002 新增 `man_pages` 选项（默认 `true`）门控 pod2man 与两个
  `custom_target`；OHOS 构建时 `-Dman_pages=false`。
- **为什么不引入 perl 依赖**：为一个 OHOS 上无消费场景的 man 页引入完整 perl
  工具链，属于用重依赖换非必要功能；`-Dman=disabled` 在仓库内已有先例
  （account-utils 1.4.0）。

### 5.3 C++ 标准被静默降级

- **现象（预判）**：`std::format`/`std::span`/`<=>` 报
  `no member named 'format' in namespace 'std'` 或
  `'span' file not found`。
- **根因**：`ci/conan/profiles/ohos-aarch64` 固定 `compiler.cppstd=17`；
  Conan `MesonToolchain` 用 `compiler.cppstd` 经 `to_cppstd_flag()` 生成 machine
  file 的 `cpp_std`，**machine file 的 project options 优先级高于上游
  `meson.build` 的 `default_options`**。因此上游写的 `cpp_std=c++20` 会被 17 覆盖，
  且不会报「标准不足」的显式错误，而是在使用 C++20 特性处报「找不到符号」。
- **处置**：`configure()` 内 `self.settings.compiler.cppstd = "20"`
  （`archives/a/apache-arrow/24.0.0` 同口径）。

### 5.4 libc++ 15004 的 `std::format`

- **现象（预判）**：即使 `-std=c++20`，仍报 `<format>` 相关
  `no member named 'format'/'vformat'/'make_format_args' in namespace 'std'`，
  或链接期 `undefined symbol: ... format_error`。
- **根因**：OHOS SDK clang 15 + libc++ **15004** 的 `<format>` 头存在，但
  `std::format` 默认不暴露（需 `_LIBCPP_ENABLE_EXPERIMENTAL`），其运行时符号位于
  `libc++experimental.a`。仓库内已有大量同口径先例（asyncpp 0.2.4、libpqxx 8.0.1、
  ladybug 0.18.2、openal-soft 1.25.2、omath 5.6.0、plutobook 0.19.0 等 20+ 条）。
- **处置**：`generate()` 中在 OHOS 上追加
  `tc.extra_defines += ["_LIBCPP_ENABLE_EXPERIMENTAL"]`、
  `tc.extra_ldflags += ["-lc++experimental"]`。
- **残余风险（必须在真机确认）**：libc++ 15004 的 format 实现完整度。
  仓库内 `barkeep/0.1.5` 记录过「设备最小探针 `std::format("{}", 42)` 失败」，
  但该探针**未**定义 `_LIBCPP_ENABLE_EXPERIMENTAL`；asyncpp 定义了该宏后报告可用。
  本适配取 asyncpp 路线。若真机仍失败，退路见 §8。

### 5.5 pkg-config 名不匹配

- **根因**：上游用 `dependency('libpcre')`；`archives/p/pcre/8.45` 的
  `package_info()` 只声明 `cpp_info.libs`，未声明 `pkg_config_name`，
  故 `PkgConfigDeps` 按包名只生成 `pcre.pc`（已核对 Conan
  `pkgconfigdeps.py:_get_name()`：`pkg_config_name or dep.ref.name`）。
- **处置**：消费侧 `deps.set_property("pcre", "pkg_config_name", "libpcre")`
  ——Conan 官方支持的消费侧覆盖（`pkgconfigdeps.py:390` 有文档字符串），
  **不修改上游 meson.build**，也不改他人配方。
- 已核对无冲突项：`curl/8.15.0.1` 自带 `pkg_config_name = "libcurl"`；
  `libarchive/3.8.7` 未设该属性 → 默认 `libarchive.pc`，与上游名字一致。

### 5.6 运行期 rpath 缺失 → CI L2 smoke test 有失败风险

- **现象（预判）**：`bin/pkgfile --version` 报
  `Error loading shared library libcurl.so.4: No such file or directory`。
- **根因**：Conan 的 `MesonToolchain._rpath_link_flag` 只输出
  `-Wl,-rpath-link=<dirs>`（**链接期**解析间接依赖），不写运行期 rpath；
  而 CI 的 L2 smoke test 是**裸执行**产物：
  `ci/conan/build_and_test.sh:1680` 的 `timeout 15 "$bin_file" --version </dev/null`，
  `scripts/ohc/conan_verify.py:816` 的 `self._run([str(bin_file), "--version"])`
  —— 两者都**不加载** `conanrun` 环境（即没有 `LD_LIBRARY_PATH`）。
  只有 `test_package` 里的 `env="conanrun"` 才会提供它。
- **影响面核实**（决定必须修还是可以放着）：本项目 host 依赖中
  **只有 curl 是 shared**——
  `curl/8.15.0.1` `default_options = {"shared": True}`；
  `libarchive/3.8.7` 配方无 `options`（只产静态库）；
  `pcre/8.45` `shared=False`；
  curl 自身又静态链接 `openssl/3.5.6.1`（无 shared 选项）与 `zlib/1.3.1.1`（PIC 静态版）。
  因此 `pkgfile` 的非系统运行期 NEEDED 实际只有 `libcurl.so` 一项，
  给可执行文件补 rpath 即可完全解决（不存在"libcurl 的 NEEDED 无法被可执行文件
  RUNPATH 传递解析"的二阶问题）。

  > **真机实测纠正**：上面的「libarchive 只产静态库」判断有误。
  > `archives/l/libarchive/3.8.7` 虽然配方里没有 `options`，但用的是 autotools
  > 且未加 `--disable-shared`，实际产出共享库；真机 `llvm-readobj` 显示产物
  > NEEDED 为 `libarchive.so.13`、`libcurl.so`、`libc++_shared.so`、`libc.so`。
  > 所幸处置代码是对**全部** host 依赖统一补 `-L/-Wl,-rpath`，因此结论不变、
  > 无需改动；但依赖形态表（notes.md §3）已按实测更正。
- **处置**：`generate()` 内遍历全部 host 依赖，补
  `-L<libdir>` + `-Wl,-rpath,<libdir>`（`archives/a/akku/1.1.0`、
  `archives/b/bsdtar/3.7.7` 的既有做法，仓库内 720 处同款）。
- **附带收益**：`test_package` 的主断言不再依赖 `LD_LIBRARY_PATH` 是否被正确注入，
  失败面更窄。

## 6. 已验证方案与结果（本机证据）
本轮**未执行真机构建**，以下为本机可复现的验证及其证据：

| # | 验证项 | 方法 | 结果 |
|---|-------|------|------|
| 1 | 源码真实性与哈希 | codeload.github.com 与 gh-proxy.com 两条独立链路下载 → 比对 sha256 | 两者一致：`dc18d7fcb03844bfd9857cb7b05b666d8a3469a38c73d3182da05fd4f8dd6403`（452028 B） |
| 2 | 下载内容未被篡改 | 解包后 `meson.build` 与 raw.githubusercontent.com 单独抓取的 v25 原文逐一比对 | 逐字节一致（均 sha256 `3a1bc94a6b5f38982098fec3aaf4a90939befec5036bb6fca690c730836ea858`） |
| 3 | 补丁可应用 | 在纯净 v25 源码上顺序 `git apply --verbose` 0001 → 0002 | 两个补丁均 `Applied ... cleanly`，无 fuzz/冲突 |
| 4 | 补丁结果正确 | 检查应用后的 `meson.build` / `meson_options.txt` | `daemon`/`man_pages` 选项就位；`libsystemd` 加 `required: get_option('daemon')`；`pkgfiled` 与两个 man target 被正确缩进门控块 |
| 5 | W0 依赖 | `conan download <ref> -r=ohpcd --only-recipe` | pcre/8.45、libarchive/3.8.7+3.7.7、curl/8.15.0.1 全部实拉成功；libsystemd 0 命中 |
| 6 | 配方语法 | `python -m py_compile` on `conanfile.py`、`test_package/conanfile.py` | 通过 |
| 7 | YAML/JSON 可解析 | PyYAML / json 解析 `conandata.yml`、`MANIFEST.yml`、两个 `manifest.yaml`、`commands.json` | 全部通过 |
| 8 | test_package 脚本语法 | `sh -n`（Git for Windows sh）与 `bash --posix -n` | 均无告警 |
| 9 | test_package 逻辑自检 | 用**桩二进制**（复现真实 CLI 的输入输出契约）在 Windows 上跑 `test_pkgfile.sh` | 正向：16 个断言点全过，退出 0 并打印 `PASS`；**反向对照**：把桩的搜索结果改成错误值后退出 1 且打印 `FAILED: 2 项断言未通过` → 证明断言非空转 |
| 10 | 测试数据格式 | 与上游 `tests/golden/alpm/x86_64/testing/testing.files` 对比结构 | 实测上游为**未压缩 tar**，成员 `<pkg>-<ver>-<rel>/files`，内容 `%FILES%\n` + 路径行；自建测试归档与之一致（现为**纯文本成员 + 测试运行时 `tar` 现场组装**，原因见 device-verification.md §3.2：二进制文件会让 CI 的 `git apply pr.diff` 失败） |
| 11 | 文本编码 | 逐文件检查 BOM 与 CRLF | 全部新增文本文件 BOM=False、CRLF=False（LF） |
| 12 | 上游测试清单对齐 | `meson.build:180-229` 注册项 ↔ `MANIFEST.yml` 声明 | 11 个 gtest 用例 + 27 个 python 集成用例，共 38，与声明一致 |

### 6.1 关键设计选择的依据（源码级）

- **test_package 用 `file://` 而不是 HTTP**：`src/update.cc:344` 的失败判据是
  `if (msg->data.result != CURLE_OK || resp >= 400)`。`file://` 传输的
  `CURLINFO_RESPONSE_CODE` 为 0，不满足 `resp >= 400`，因此走正常成功分支。
  这让端到端测试**完全离线**，无需 fakehttp 服务，也避开了 OHOS 上
  `multiprocessing`/端口监听的不确定性。
- **端到端测试能覆盖什么**：libcurl 读取 → `ArchiveConverter::RewriteArchive()`
  解析 alpm tar、丢弃 `%FILES%` 首行、给路径加 `/` 前缀 → 写出
  `<repo>.files.000` 分片与 `.db_version` → `Pkgfile::ProcessRepo()` 重新读回分片
  → PCRE 过滤器（`Basename` / `Exact`）→ `Result::Print()` 输出格式。
  即除 `pkgfiled` 之外的全部主路径。
- **断言的具体预期值来源**：`repo.cc`+`update.cc PrepareUrl()` 决定 URL 为
  `<server>/<repo>.files`；`pkgfile.cc:429 Version()` 输出 `pkgfile v25`；
  `pkgfile.cc:349` 的错误串 `Database version file not found`；
  `pkgfile.cc:165 ParsePkgname()` 决定 `demo-1.2.3-1` → 名字 `demo`、版本 `1.2.3-1`；
  `pkgfile.cc:296-305` 决定带 `/` 的搜索走 `Exact`、不带的走 `Basename`。

## 7. 依赖链状态

```
pkgfile/25
├── pcre/8.45              ✅ 已发布（静态库）
├── libarchive/3.8.7       ✅ 已发布
│   └── (zlib/bzip2/xz/zstd/openssl… 传递依赖，由 libarchive 配方自带)
├── curl/8.15.0.1          ✅ 已发布（shared）
└── [构建期] meson/1.11.0  ✅ 已发布
    ├── ninja/1.12.1       ✅ 已发布
    ├── pkgconf/3.0.5      ✅ 已发布
    └── gmock/1.17.0       ✅ 已发布
        └── gtest/1.17.0   ✅ 已发布
```

**依赖链完整，无缺口，不需要新增依赖库 PR。** `libsystemd` 已通过关闭
`pkgfiled` 规避。

## 8. 阻塞点与残余风险

| # | 阻塞/风险 | 当前状态 | 解除条件 |
|---|----------|---------|---------|
| B1 | 真机 `conan create`（W3）未执行 | 阻塞「标记 built/published」 | 取得真机空闲窗口后按 §9 单包排队执行 |
| B2 | libc++ 15004 的 `std::format` 完整度未在设备实证 | 高风险（有仓库内先例支持，但 barkeep 有反例记录） | 真机编译若失败：核对 `cpp_args` 含 `-D_LIBCPP_ENABLE_EXPERIMENTAL`、链接含 `-lc++experimental` |
| B3 | `pkgfiled` 守护进程未适配 | 已知功能缺口（有意关闭） | 若业务需要，先独立适配 `libsystemd`（sd-event）并单独提交依赖库 PR |
| B4 | pcre 配方 `libs` 声明为 `["pcre","pcrecpp","pcreposix"]`，生成的 `libpcre.pc` 会同时带这三个 `-l` | 低风险 | 若真机链接报缺 `libpcrecpp`/`libpcreposix`，改为在消费侧用 `pkg_config_custom_content` 只保留 `-lpcre` |
| B5 | 上游 27 个 python 集成用例不可运行 | 已在 MANIFEST.yml 声明豁免原因 | 无需解除；如需覆盖，可在真机额外跑一个自定义夹具 |

**B2 的退路（若 `std::format` 在设备上确实不可用）**：不伪造通过。按 A 类产出转为
B 类分析报告，记录设备最小探针的实际报错；可行方案按优先级为
(a) 引入 `fmt` 依赖并把 `std::format` 调用重定向到 `fmt::format`（需改上游源码，
补丁量约 44 处，不推荐作为首选）；(b) 等待/升级 OHOS SDK 的 libc++。**不得**为了
凑适配而改基础设施、绕过门禁或把 NOT_RUN 写成 pass。

## 9. 下一步命令（真机 / shadow CI，单包排队）

### 9.1 真机前置检查（共性问题指南 §11 清单）

```sh
ssh ohos 'echo "home=$HOME"; uname -a; id'
command -v sh git conan clang clang++ meson ninja pkg-config
python3 --version 2>/dev/null || true
mkdir -p "$HOME/tmp-probe"
TMPDIR="$HOME/tmp-probe" sh -c 't=$(mktemp); echo ok > "$t"; cat "$t"; rm -f "$t"'
conan profile show -pr:h ci/conan/profiles/ohos-aarch64
conan profile show -pr:b ci/conan/profiles/ohos-aarch64
```

重点确认：`settings.yml` 认识 `OHOS`；`/data/service/hnp/bin/clang` 存在；
`compiler_executables` 是合法 dict；`git` 在 runner PATH 内。

### 9.2 单包构建 + 上游单测 + test_package（W3）

```sh
cd <repo>/archives/p/pkgfile/25
TMPDIR="$HOME/tmp" conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

日志中应出现（用于 L1a/L1b/L1c 取证）：

```text
meson test -C <builddir> unit_tests --print-errorlogs
  → Ok: 1            # 11 个 gtest 用例（filter_test 10 + repo_test 1）
Testing package
  → PASS: pkgfile 25 消费者测试全部通过
```

### 9.3 shadow CI 单包定向验证

```sh
CI_PACKAGES="archives/p/pkgfile/25" zsh ci/conan/build_and_test.sh
# 或
/path/to/run-ohos-shadow-ci.sh archives/p/pkgfile/25
```

提交前确认：build 日志只发现目标包、`Build Summary` 为 `Total: 1`、L0/L1 为
`pass`、L2 对命令行工具应为 `pass`（`pkgfile --version` 返回 `pkgfile v25`）、
L4 的 warn 已阅读、L5 确认 `bin/pkgfile` 真实存在、`ci-metadata.json` 与日志一致。

### 9.4 真机队列登记

```text
库名：pkgfile
版本：25
分支：feat/pkgfile-25
issue：（本轮未绑定 issue；当前阶段 issue 与 PR 不绑定）
包路径：archives/p/pkgfile/25
预计耗时：轻量偏中（pkgfile 本身是小工具；若 libarchive/curl 需从源码构建则偏中）
资源类型：CPU / IO（源码首次拉取用网络；测试全程 file:// 离线）
测试命令：conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
是否重任务：否
可接受运行时间段：白天短时窗口
```

### 9.5 真机首个失败点的排查顺序

1. **`std::format` 编译/链接失败** → 查 `meson configure` 输出的 `cpp_args` 是否含
   `-D_LIBCPP_ENABLE_EXPERIMENTAL`、`cpp_link_args` 是否含 `-lc++experimental`；
   按 §8 的 B2 退路处理，不得伪标通过。
2. **`dependency('libpcre')` 未找到** → 确认 `generators/libpcre.pc` 已生成，
   且 machine file 的 `pkg_config_path` 指向 generators 目录。
3. **`pkgfile -u` 失败** → 先确认 `TMPDIR` 指向可写目录（`update.cc` 的
   `OpenTmpfile`），再确认 curl 为 shared 且 `LD_LIBRARY_PATH`（`env="conanrun"`）正确。
4. **`unit_tests` 链接失败** → 检查 gmock 的 `.pc` 是否把 gtest 作为 Requires 传递；
   必要时在 `build_requirements()` 中补 `test_requires("gtest/1.17.0")`。
5. **L2 smoke test 报 `Error loading shared library libcurl.so...`** → 确认
   `meson configure` 的 `cpp_link_args` 含 `-Wl,-rpath,<curl 包 lib 目录>`
   （见 §5.6）；`ci/conan/build_and_test.sh` 的 L2 只是非阻塞 warn，
   但 `scripts/ohc/conan_verify.py` 的 L2 在唯一二进制失败时判 FAIL。
6. **集成用例被误跑导致失败** → 保持按名点跑 `unit_tests`（`meson.test()` 全跑会带上
   4 个 python 集成用例），并在 MANIFEST.yml 维持豁免说明。

## 10. 附录：本报告引用的上游代码位置

| 位置 | 用途 |
|------|------|
| `meson.build:7` | `default_options: ['cpp_std=c++20']` |
| `meson.build:31-38` | 依赖声明（libpcre/libarchive/libcurl/**libsystemd**/threads/gtest/gmock） |
| `meson.build:40-41` | `find_program('pod2man')` / `find_program('pkg-config')` |
| `meson.build:82-88` | `executable('pkgfiled', …)` |
| `meson.build:90-122` | 两个 man 页 `custom_target` |
| `meson.build:124-146` | systemd units 安装块 |
| `meson.build:156` | `meson.add_install_script(... mkdir -p $DESTDIR/var/cache/pkgfile)` |
| `meson.build:180-200` | unit_tests（gtest 协议） |
| `meson.build:202-229` | 4 个 python 集成测试 |
| `src/update.cc:98-126` | `OpenTmpfile()`：`TMPDIR` → `/tmp` 回落 |
| `src/update.cc:62-70` | `PrepareUrl()`：`<server>/<repo>.files` |
| `src/update.cc:344` | 下载失败判据 `result != CURLE_OK \|\| resp >= 400` |
| `src/archive_converter.cc:152-179` | `RewriteArchive()`：只取 `files` 成员 |
| `src/archive_converter.cc:67-106` | `WriteCpioEntry()`：丢首行 + 加 `/` 前缀 |
| `src/db.cc:51-97` | `Database::Open()`：`.db_version` 校验与分片枚举 |
| `src/db.cc:16-27` | 错误串 `Database version file not found` |
| `src/pkgfile.cc:165-180` | `ParsePkgname()`：`name-ver-rel` 切分 |
| `src/pkgfile.cc:289-332` | `BuildFilterFromOptions()`：带 `/` → Exact，不带 → Basename |
| `src/pkgfile.cc:349-357` | 缓存目录打开失败的错误路径与退出码 |
| `src/pkgfile.cc:392-427` | `Usage()` 输出（`--search`/`--update`/`--cachedir`） |
| `src/pkgfile.cc:429` | `Version()` → `pkgfile v25` |
| `src/pkgfiled.cc` 全文 | `sd-event` 使用证据（关闭守护进程的依据） |
| `ci/conan/profiles/ohos-aarch64` | `compiler.version=15` / `compiler.libcxx=libc++` / `compiler.cppstd=17` |
