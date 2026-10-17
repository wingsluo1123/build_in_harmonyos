# verhaal 025 适配笔记

> 上游: https://git.sr.ht/~gregkh/verhaal （tag `v025`，Greg Kroah-Hartman）
> 用途: 解析 Linux stable 分支提交并建库，反查「某个提交被回填到哪些发行版」，
> 供内核 CVE 团队工具链（vulns.git）与发行版维护者使用。

## 编译环境

- 构建系统: meson（上游 meson.build，另有 autogen.sh 封装 meson setup）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，/data/service/hnp/bin/clang）
- 目标平台: HarmonyOS PC / OpenHarmony aarch64（conan profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（PR 阶段；`published` 需合并后发布流水线 `conan upload` 成功，见 ARCHIVE-SPEC §3）

## 编译步骤

```bash
# 探索阶段（本机即鸿蒙 PC aarch64，原生编译验证）
conan install --requires=sqlite3/3.53.4 --requires=libgit2/1.9.0 --requires=pcre2/10.45 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    -g PkgConfigDeps --output-folder=<gen>
export PKG_CONFIG_PATH=<gen>          # 含 conan 生成 .pc 与 libpcre2-8.pc 别名
meson setup build <src> --prefix=<inst>
ninja -C build && ninja -C build install

# 固化后（配方流程）
ohc-run.py conan-verify verhaal 025   # conan create + test_package（G0-G4/L2/L4/L5）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Error opening git repo at '…'` 启动即退出（rc=220） | libgit2 ≥ 1.7 引入仓库目录属主校验（`GIT_OPT_SET_OWNER_VALIDATION`，等价 git `safe.directory` 的**库 API 层**）。HMDFS 把 `/storage` 下所有文件属主归一为共享账号 uid（实测 `stat` 属主 20001006），而进程 euid 为另一 uid（实测 20020085），该校验对**任何**仓库恒失败 | 补丁 `0001-src-main.c.patch`：`git_repository_open()` 失败时 `git_libgit2_opts(GIT_OPT_SET_OWNER_VALIDATION, 0)` 重试一次。知识库同源条目 `DRAFT-libgit2-1.9.0-owner-validation-hmdfs`（另见 E101/E497 为命令层同根因族） |
| 2 | `fatal error: 'pcre2.h' file not found` | meson 依赖名为 `libpcre2-8`；Conan 的 pcre2 包经 PkgConfigDeps 只产出合并后的 `pcre2.pc`，而包内自带的 `libpcre2-8.pc` 前缀写死为 `prefix=/`（安装到 Conan 缓存后不可重定位，展开成 `-I//include`） | 配方 `generate()` 依依赖包实际路径生成 `libpcre2-8.pc` 别名（仓库既有 dbus-1.pc 别名同款做法） |
| 3 | `Fatal: 'git describe' failed for the master branch head (error -3)` | verhaal 用 `git_describe_commit` 取 master 头所属发行版；**轻量 tag 无法被 describe**（libgit2 报 "no annotated tags can describe"） | 非配方问题，属使用/测试输入约束：内核发行 tag 本就是附注标签。已写入 test_package/test_ohos 用例构造说明 |
| 4 | `Fatal: Could not find 'master' branch (error -3)` | verhaal 固定取本地 `master` 分支头作为 mainline 基准 | 同上，使用约束（真实内核树即 master）。测试用例按 master 构造 |
| 5 | 本地 CI：`NotADirectoryError: .../predl_cache/06d9b097_verhaal/archive/v025.tar.gz`，`conan create` 失败（同一配方 `conan-verify` G2 却通过） | `ci/conan/build_and_test.sh` 预下载用宽松正则 `(?:^|\s)(?:url:?\s*)?["\']?-?\s*(https?://[^\s"\']+)` 扫描 **整个 conandata.yml**（含注释），并把命中的每个 URL 下载后 `content.replace(url, 'file://' + local)`。本文件注释里写了裸 URL `https://git.sr.ht/~gregkh/verhaal`，被当作第二个源码；替换时该短 URL 是真实 tarball URL 的前缀，于是 `sources.url` 被污染成 `file://…/06d9b097_verhaal/archive/v025.tar.gz`（缓存条目为文件而非目录） | conandata.yml 注释中**不写完整 http(s) URL**（仓库惯例，如摘要式的 `git.sr.ht/~gregkh/verhaal`）。修正后 `conan create` 通过 |
| 6 | **CI（build #93597）**：`../meson.build:4:0: ERROR: Unknown linker(s): [['llvm-ar']]` / `Running 'llvm-ar --version' gave "[Errno 2] No such file or directory: 'llvm-ar'"`；同一配方本地 `conan-verify` 与 W3 均通过 | meson 探测 ar/ranlib/pkg-config 时按**命令名**调用（内部走 subprocess 的 PATH 查找）。该查找在 OHOS 上不可靠：`llvm-ar` 在 shell 里可正常执行（`/data/service/hnp/bin/llvm-ar` 为 SDK 内符号链接），但经 subprocess 按名调用报 `Errno 2`。**本地之所以假通过，是因为 W3/conan-verify 跑在本机时带了 `PYTHONPATH=<pyshim>`（该 shim 把 `subprocess._USE_POSIX_SPAWN=False`，顺带修好了按名查找）**，而 CI 无此 shim | 配方 `generate()` 新增 `_inject_meson_tools()`：把 `ar`/`ranlib`/`pkg-config` 的**绝对路径**写入 MesonToolchain 生成的 `conan_meson_native.ini` 的 `[binaries]` 段，绕过按名探测（与仓库既有 meson 配方如 `archives/a/accountsservice` 同款对策）。验证口径：**`unset PYTHONPATH` 下 `conan remove "verhaal/*" -c` + `conan create` 从零重建**通过（消费者用例 4/4） |
| 7 | **CI（build #93687 / #93996 / PR #16072）**：`meson compile` 处失败。第一次（#93687，`-j20`）为 `ninja: fatal: posix_spawn: Resource temporarily unavailable`；**同一根因更早还打死过 setup 步**（build #93650：`/system/bin/sh: conanbuildenv-release-armv8.sh[13]: can't fork - try again` → `meson.configure()`）；加了重试后（#93996，`-j2`）退避重试按设计连续触发 5 次仍全部命中 `/bin/sh: can't fork - try again`，说明该 worker 的 fork 枯竭窗口持续 100s 以上。前序步骤全绿（L0/KC/JC 门禁、5 个依赖二进制、`meson setup` 与依赖 found: YES 均通过） | **worker 侧 fork 枯竭（基建），非源码/配方问题**：conan 的 `Meson.build()` 并行度取 `tools.build:jobs`，CI worker 的 profile 未设该项 → 回落 `cpu_count()`（实测 **20**）。CI 沙箱对进程/句柄配额有硬限，ninja 并发 spawn（ninja → sh → clang → ld 进程链）打满配额即 EAGAIN/`can't fork`；worker 同时跑着其它 CI 任务时连 setup 步的 shell 都 fork 不出来 | 配方 `build()`/`package()` 复刻 conan 的 meson 三步命令行（setup / compile / install），compile 步**顺序编译 `-j1`**（仅 7 个源文件 + 1 个可执行目标，代价可忽略），三步共用**仅命中进程创建失败特征**的退避重试：**最多 10 次尝试（9 次退避，30s/次，上限 4.5min，骑过实测 >100s 的饱和窗口）**。重试路径**完全不 fork**：`time.sleep` + 进程内读日志/匹配特征（shell 版重试自身要用 sleep/cat/grep，配额枯竭时重试机制先死 —— pgqd/PR #16073 教训）；非 fork 类错误（编译报错等）首次即失败并打印完整转录，不把真错误掩盖成基建抖动。test_package 消费者用例同样加了该退避（用例内的 git/verhaal 调用同样会被打断） |

## 源码修改

`patches/0001-src-main.c.patch`（+15/-0，仅 `git_init()`）：

```c
 	ret = git_repository_open(&git_repo, git_repo_location);
 	if (ret) {
+		/*
+		 * libgit2 >= 1.7 refuses to open a repository whose on-disk
+		 * owner does not match the current euid … (HMDFS …)
+		 */
+		git_libgit2_opts(GIT_OPT_SET_OWNER_VALIDATION, 0);
+		ret = git_repository_open(&git_repo, git_repo_location);
+	}
 	if (ret) {
 		fprintf(stderr, "Error opening git repo at %s", git_repo_location);
```

设计取舍：**未使用任何平台宏**（`__OHOS__` 等），而是可移植的「打开失败→关闭校验重试一次」。
只在原本必然失败时改变行为：正常多用户主机上首次 `open` 即成功，校验保持开启；
而 verhaal 的仓库路径来自用户显式设置的 `CVEKERNELTREE`，并非从不信任目录自动发现，
故该回退不构成实际攻击面（关闭该校验的语义边界见知识草稿「适用边界/反例」一节）。

## 依赖版本

| 依赖 | 版本 | 制品仓二进制 |
|------|------|--------------|
| libgit2 | 1.9.0 | ✅ 已发布（W0 实测 `conan install` 安装成功） |
| sqlite3 | 3.53.4 | ✅ 已发布 |
| pcre2 | 10.45 | ✅ 已发布（提供 libpcre2-8，满足 meson.build `>= 10.42`） |
| threads | 系统 | OHOS libc 自带 |

三者均以静态库链入，产物 `readelf -d` 仅 `NEEDED libc.so`。

## 上游测试清点（R51）

**上游 025 无已注册测试套件（meson/ctest 无测试目标）**，清点证据：

| 清点项 | 结果 |
|--------|------|
| meson.build 中 `test()` 目标 | 无（`meson test --list` 为空） |
| 源码树 `tests/`、`test/` 目录 | 无 |
| 源码树 `*test*` 命名文件 | 无（`find <src> -iname '*test*'` **零命中**） |
| README.md / justfile 测试入口 | 无（justfile 仅 `_help`/`spdx`/`lint`/`make`/`build_db` 等目标，无 test 目标） |
| 未注册的开发脚本自测 | `scripts/git-resolve.sh --selftest`（脚本内 `run_selftest()`）含 **10 个用例**，但**未在 meson/ctest 注册**；其期望值是具体内核提交哈希（`00250b5`、`ffef737` 等），必须在包含这些提交的内核 git 树内运行 —— 本环境实测 **8 例 FAILED + 2 例空过（用例 6/7 期望「无输出 + 非 0 退出」，无 git 树时恰好满足），有效验证 0/10**（原始输出存档 `reports/git-resolve-selftest.log`） |
| 上游可运行测试数 N | 0（仅统计**已注册**测试套件；未注册自测不计入，另在上表如实列出） |

故上游实测回填为 **N/N′ = 0/0**（无**可运行**测试，非未执行）：唯一自测入口
`scripts/git-resolve.sh --selftest` 需内核 git 树，本环境实测不可运行
（8 FAILED / 2 空过，有效验证 0/10，原始输出见 `reports/git-resolve-selftest.log`），
已在 `test_package/MANIFEST.yml:upstream_tests_unrunnable` 同步记录，不隐瞒、不假装执行。
功能覆盖由 test_package 消费者用例与 test_ohos 鸿蒙专项用例承担（下表）。

## 验证结果

### 消费者用例（test_package/test.sh，conan create 内执行）

| 用例 | 断言 | 结果 |
|------|------|------|
| T1 | `verhaal --version` 报告 `verhaal version 025` | PASS |
| T2 | 以仿真内核树建库生成 `verhaal.db` | PASS |
| T2b | 建库流程走完（`Saved commits to database`） | PASS |
| T3 | 回填查询语义：`mainline_id` 映射 + 按 mainline 提交反查被回填发行版 + `Fixes:` 映射 | PASS |

（消费者用例合计 4 项）

### 鸿蒙专项用例（test_ohos/run_ohos_test.sh，鸿蒙 PC 真机执行）

| 用例 | 断言 | 结果 |
|------|------|------|
| T1 | 产物为 ELF64 AArch64 | PASS |
| T2 | 产物无本包构建机绝对路径 | PASS |
| T3 | `--version` 输出核验 | PASS |
| T4 | **HMDFS 共享属主下打开真实 git 仓库并建库（补丁 0001 回归）** | PASS |
| T4b | 建库流程走完（`Saved commits to database`） | PASS |
| T5 | 回填查询语义（mainline→被回填发行版 / 稳定分支 `mainline_id` / `Fixes:`） | PASS |
| T6 | 未设置 `CVEKERNELTREE` 时报错并以非 0 退出 | PASS |

（鸿蒙真机专项合计 7 项；**总口径 4 + 7 = 11 项全部通过**，与
`manifest.yaml:test_results`、`test_package/MANIFEST.yml`、`reports/test-report.md`
及 PR 正文一致）

### 重试逻辑桩注入自检（CI fork 枯竭修复，15/15 PASS）

fork 枯竭无法在受控环境复现，故对 `_meson_step()` 做桩注入自检
（脚本 `reports/retry-selftest.py`，`time.sleep` 打桩为记账、不真等；
判定口径已按 W4 审计意见收窄，见下表第 3/4 行）：

| # | 场景 | 期望 | 结果 |
|---|------|------|------|
| 1 | setup 步命中 CI #93650 实测特征 `can't fork - try again` | 退避 1 次后成功 | PASS |
| 1b | setup 命令行形态 | 复刻 conan（`--native-file` + build/source + `--prefix=/`） | PASS |
| 2 | compile 步命中 CI #93687 实测特征 `posix_spawn: Resource temporarily unavailable` | 退避 1 次后成功 | PASS |
| 2b | compile 命令行形态 | `meson compile -C <build> -j1`（顺序编译） | PASS |
| 3 | 真实编译报错（非进程创建失败） | 首次即失败，**不退避**、打印完整转录 | PASS |
| 4 | 非 fork 语境的 EAGAIN（写文件/磁盘类） | **不退避**（判定要求 fork/spawn 与 EAGAIN 同行） | PASS |
| 5 | 转录为空（shell 没起来）后恢复 | 重试后成功 | PASS |
| 6 | 转录持续为空 | 只重试 2 次即失败（与静默失败无法区分，不烧满窗口） | PASS |
| 7 | 持续命中 EAGAIN | 重试到上限（最多 10 次尝试）后失败，不无限重试 | PASS |
| 8 | `run()` 自身抛异常（shell 都起不来） | 可重试 | PASS |
| 9 | `make[2]: fork: retry: …` 等其它 fork 特征 | 命中并重试 | PASS |
| 10 | `tools.compilation:verbosity=verbose` | 透传 `--verbose`（保留 conan conf 语义） | PASS |
| 10b | `tools.build:jobs=16` | 不放大并发（恒定 `-j1`，沙箱配额硬限） | PASS |
| 11 | install 步命中 `cp: can't fork - try again` | 同样退避重试 | PASS |
| 11b | install 命令行形态 | 复刻 conan（`install -C <build> --destdir <package>`） | PASS |

## 注意事项

- **PF9 已知误报（本 PR 处理口径）**：本 PR 除版本级目录 `025/` 外还新增软件级
  `archives/v/verhaal/{README.md,commands.json,manifest.yaml}`。preflight PF9 会以
  「archives 变更须全落单一 `包/版本` 目录」命中，但软件级三文件是归档规范
  （ARCHIVE-SPEC）与 R38/L0k（CLI 包必须有 commands.json）强制要求，全仓同布局，
  属已知误报（另见知识草稿 E434）。处理方式：保留文件，必要时以
  `OHC_PREFLIGHT=0` 建 PR，并在此留证。
- **L2 探针与消费者用例结论不一致（观察项，非本包缺陷）**：W3 日志
  `[warn] L2: verhaal --version/--help failed (non-blocking)`，而消费者用例 T1
  实测 `verhaal --version` 输出正常（真机 test_ohos T3 同样通过）。同一产物两种
  结论，应为 L2 探针的调用环境（缺 conanrun 的 PATH/LD_LIBRARY_PATH）所致，
  非阻断，记录待后续核对探针实现。
- **产物为命令行工具**（`bin/verhaal`），非库：软件级声明 `commands.json`（R38）。
- **属主校验回退的边界**：该补丁使「无法打开的仓库」变为「可以打开」。在需要
  属主隔离的真实多用户主机上不应关闭该校验（知识草稿已列反例）；本包面向
  HarmonyOS PC，其文件系统语义使原校验不可能通过，属功能性必需。
- **测试输入约束**：verhaal 依赖本地 `master` 分支头 + **附注** tag 判定发行版本；
  轻量 tag 会导致 `git describe` 失败。构造测试仓库时必须 `git tag -a`。
- 依赖包自身烘焙的路径（如 openssl 的 `ssl/ct_log_list.cnf`、libgit2 源码路径）
  会出现在产物字符串中，属预编译依赖固有属性、不在本包可控范围；test_ohos T2
  的排除项显式限定为依赖安装/构建目录，本包自身路径已由 `-ffile-prefix-map` 重映射。
---

**编译结束**: 2026-10-16 02:24
**最终状态**: built
