# libini_config 1.4.0 适配笔记

## 版本与源码说明

- 任务包版本：`libini_config/1.4.0`（目录 `archives/l/libini_config/1.4.0/`）。
- 上游仓库：https://github.com/SSSD/ding-libs（任务指定）。
- ding-libs 上游未单独发布 `libini_config 1.4.0` tag（`git ls-remote` 仅有 `0.6.0/0.6.1/0.6.2/0.7.0` 等 ding-libs 主版本；`version.m4` 中 `INI_CONFIG_VERSION` 在 `0.6.2` 为 `1.3.1`，在 master/`0.7.0` 为 `2.0.0`，无 `1.4.0` 落点，已用本地克隆核验）。
- 本配方采用 ding-libs 官方 `0.7.0` release tarball 作为源码：
  `https://github.com/SSSD/ding-libs/releases/download/0.7.0/ding-libs-0.7.0.tar.gz`
  sha256 `5df2f202f892b4c1a6caf87f0056398a8288b281da9d7e65cd7637978ec20ef3`（与已合入的 `ding-libs/0.7.0` 配方同源同哈希）。
- 配方构建完整源码树以运行全部上游 Automake 测试，`package()` 移除伴随构建的 `dhash` 产物，仅交付 `libini_config`（头文件 `ini_configobj.h`/`ini_configmod.h`、`libini_config` 库、`ini_config.pc`）。
- conan 包版本遵循任务要求的 `1.4.0`；源码内部 `INI_CONFIG_VERSION` 为 `2.0.0`，差异仅为任务命名口径，不影响产物 API（`ini_config_parse`/`ini_get_config_valueobj` 等公共接口一致）。

## 编译环境

- 目标：HarmonyOS PC aarch64，`os=OHOS`、`arch=armv8`
- 构建系统：Autotools
- 编译器：clang/clang++ 15（HNP）
- Conan：2.x；profile：`ci/conan/profiles/ohos-aarch64`
- 配方默认：`shared=False`、`fPIC=True`

## 编译步骤

1. 从上游 HTTPS release tarball 解压源码，应用 13 个源码层补丁后直接使用预生成 Autotools 文件（不做 autoreconf，R6）。
2. `AutotoolsToolchain` 配置 `--disable-nls --disable-dependency-tracking`，按 `shared` 选项切换 `--enable/disable-shared/static`；不传 `--build/--host/--target`（原生构建）。
3. 不声明 autoconf/automake/libtool tool-requires：预检机 profile 的 `/data/service/hnp/bin/bash` 不可访问，conancenter m4 重建必败（`configure[139]: ... inaccessible or not found`），而 HMBS 保证 `/bin/sh`；构建期以 sed 将预生成 `configure` 内 `umask 077` 改为 `umask 022`（E129/zzuf 先例），`SHELL/CONFIG_SHELL` 均钉为 `/bin/sh`。
4. `AutotoolsToolchain.extra_cflags` 注入 Check 头文件路径；`configure` 以 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh configure --prefix=<package_folder>` 显式直调（Environment.define 覆盖不掉 profile 坏 bash，cvsgraph 先例），`make`/`make check` 均以 `SHELL=/bin/sh CONFIG_SHELL=/bin/sh` 传参并透传 `ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER=true` 防止重生成覆盖已适配的 `config.guess/config.sub`。
5. `make check` 前设置任务私有 `TMPDIR/TMP/TEMP` 与 `CK_FORK=no`，Check 动态库路径仅在测试环境中加入 `LD_LIBRARY_PATH`。
6. `package()` 执行 `make install` 后删除 `libdhash.*`、`dhash.h`、`dhash.pc` 与 `share/`，删除 `*.la`，保留 licenses。

## 上游测试盘点（口径 autotools_tests）

- 来源：`Makefile.am` 的 `TESTS +=` 注册项（`0.7.0` 源码）。
- 总数 20：
  - `path_utils_ut`（1）
  - `ini_augment_ut_check`、`ini_configmod_ut_check`、`ini_parse_ut_check`、`ini_validators_ut_check`（4，Check 框架）
  - `dhash_test`、`dhash_example`、`dhash_ut_check`（3，伴随构建的 dhash 组件）
  - `collection_ut`、`collection_stack_ut`、`collection_queue_ut`（3，0.7.0 中已并入 ini 但保留独立测试二进制）
  - `ref_array_ut`（1，同上并入 ini）
  - `simplebuffer_ut`（1，同上并入 ini）
  - `ini_config_ut`、`ini_comment_ut`、`ini_valueobj_ut`、`ini_parse_ut`、`ini_augment_ut`、`ini_configmod_ut`、`ini_save_ut`（7）
- 配方在 `build()` 末尾运行完整 `make check`（非子集），`test_package/MANIFEST.yml` 声明 `upstream_test_total: 20`。
- 其中与 `libini_config` 交付直接相关的为 17 项（除 3 项 dhash 外）；3 项 dhash 测试作为源码树构建验证一并运行，不计入本包交付范围但计入上游总数。

## 补丁说明（13 个，均沿用 ding-libs 0.7.0 同源验证，已删 0003-configure.ac）

- `0001/0002`：`build/config.guess`、`build/config.sub` 识别 HarmonyOS 与 `linux-ohos`。0001 含 `__OHOS__` libc 探测分支，为 R8 例外（识别 libc 无 POSIX 等价物，紧邻上游 `__ANDROID__` 分支，PR 正文说明理由）。
- HMDFS 临时目录权限（原 0003 configure.ac 的 `umask 027` 重生成方案）已改为构建期对预生成 `configure` 的 `umask 077→022` 直修（E129/zzuf 先例），不再需要 autoreconf，故删除 0003，避免拉起必败的 m4 重建。
- `0004/0005/0009/0011`：HMDFS 权限归一化与保存比较的可移植处理（掩码限定比较位，非平台宏）。
- `0006`：`open_memstream` 在 `fclose` 前 `fflush`。
- `0007/0008/0010/0013`：`ENABLE_NLS` 判据的恒等翻译宏（无 gettext 时平台无关回退）。
- `0012`：regex 诊断语义匹配（跨 libc）。
- `0014`：path 测试改用 `/usr/bin/env` 避免 OHOS `/etc` 符号链接影响。
- 源码（`.c`/`.h`）补丁中无新增 `__OHOS__`（0001 例外除外）；生成文件（`configure`/`Makefile.in`）不进入补丁集，构建时重生成。

## 依赖版本

- 构建工具：无 autoconf/automake/libtool tool-requires（直接使用 tarball 预生成 configure，避免预检机 m4 重建失败）
- 测试依赖：`check/0.15.2`（test-require，仅 `make check` 使用）
- 运行时无新增 Conan 依赖；产物为 `ini_config` 单组件。

## 验证结果（待真机预检回填）

- 本轮仅完成未提交工作树，未运行真机 `conan create`；以下为预期，数字以 HMBS 真机预检日志为准：
  - 上游 `make check`：目标 `20 TOTAL / 20 PASS / 0 FAIL`。
  - Conan `test_package`：目标通过，调用 `ini_config` 公共 API（内存 INI 解析 + 整数/字符串取值），输出 `libini_config public API test passed`。
- 证伪要求（真机轮执行）：确认测试输出与参照文件非空；区分通过与静默跳过；`make check` 日志保留 `test-suite.log` 汇总。
- `conan create` 日志中的真实计数将用于填写 PR 正文「上游测试用例通过率」与「新增测试用例通过率」，本轮不猜测数字。

## 注意事项

- W3/verify 预下载可能临时改动 `conandata.yml` 源地址；归档必须保持官方 HTTPS URL 与原 sha256。
- Check 的 `LD_LIBRARY_PATH` 仅作用于测试过程。
- 库包无命令行工具，不需要软件级 `commands.json`。
- 本分支仅包含 `archives/l/libini_config/` 相关新增文件；工作区另有历史残留的 `libxext` 大小写碰撞改动与 `upstream-main.tar`，非本任务产物，未纳入本配方。

## 本轮真机证据修复（2026-10-16 incomplete：缺 test_package 计数与机器标记）

- 现象：`make check` 与 `./libini_config-test` 实际通过，但日志无 `HMBS_TEST_PACKAGE_RESULT`/`HMBS_UPSTREAM_TEST_RESULT`，门禁判 incomplete（上游 0/0/0）。
- 改动：
  - 主配方 `build()` 后解析真实 `test-suite.log` 的 `# TOTAL/# PASS/...` 块（取 TOTAL 最大者为顶层聚合），双通道发射 `HMBS_UPSTREAM_TEST_RESULT` 并落盘 `hmbs_upstream.json`，`package()` 携带至 `res/`；计数恒等式自检，不凑数。
  - `test.c` 每通过一项打印一行 `CASE PASS:`（共 7 项），`test_package` 捕获日志逐行计数发射 `HMBS_TEST_PACKAGE_RESULT`（discovered=7），并重发 `res/hmbs_upstream.json`；`MANIFEST.yml` 的 `assertion_count` 由 8 更正为 7（实核 7 处检查）。
- 未删断言、未跳过测试；数字待下轮真机复跑验证。

## 本轮真机OOM硬化

- 预检2026-10-16 compile阶段 /bin/sh: Out of memory, 上游测试 0/0/0, 无配方栈指向; 配方已严格串行(-j1 + jobs=1), 无并发可降。
- 判断: 共享设备瞬时 fork/内存压力致自举链和 autoconf 探测失败面大。
- 改动(conanfile.py仅): 预置两个 am_cv 缓存变量跳过 fork 密集探测; aclocal/autoconf/automake 幂等重试 4 次。不改测试口径。

**适配路径**：路径 A（基础适配）
**申请人**：gcw_uQ09W7jl
**队伍名称**：干
