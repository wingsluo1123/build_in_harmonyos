# w-calc 2.5 适配笔记

## 基本信息

- 软件: w-calc 2.5
- 上游仓库: https://sourceforge.net/projects/w-calc/
- 源码: https://downloads.sourceforge.net/project/w-calc/Wcalc/2.5/wcalc-2.5.tar.bz2
- SHA256: `0e2c17c20f935328dcdc6cb4c06250a6732f9ee78adf7a55c01133960d6d28ee`
- 构建系统: autotools (configure + make)
- 依赖: gmp/6.3.0, mpfr/4.2.2.1（均为已发布的 Conan 包；mpfr/4.2.2.1 精确要求 gmp/6.3.0）
- 编译器: clang / clang++
- 状态: built

## 注册知识库的使用

本适配使用了仓库注册条目 `knowledge/graph/E011.kv`（文档 `knowledge/doc/E011.md`，
`edit-umask-in-configure`）：HMDFS 文件系统下 autoconf `configure`/`config.status`
以 `umask 077` 创建临时目录，目录对构建用户不可写，导致
`./confXXXXXX/subs1.awk: Permission denied`。E011 建议把该 umask 改为 `022`。
补丁 `patches/0001-configure-hmdfs-umask.patch` 对上游发布的 `configure` 落地该修复，
仅当 `os=OHOS` 时应用（`configure` 是生成文件，按 R6 以补丁而非运行时改写处理）。
并遵循 `knowledge/graph/E074.kv`（HMDFS 上 make jobserver FIFO 受限 → 串行 make）。
本条目为 E011/E074 的使用记录，未新增知识条目。

## 编译步骤

1. `source()` 下载并解压官方 tar.bz2，`strip_root=True`。
2. `generate()`：`AutotoolsToolchain` 追加 `--without-readline`、
   `--with-gmp=<gmp pkg>`、`--with-mpfr=<mpfr pkg>`；`AutotoolsDeps` 注入依赖的
   include/lib 到 conanbuild 环境。
3. `build()`：`os=OHOS` 时先覆盖 `CONFIG_SHELL/SHELL=/bin/sh`（见问题 5）、导出
   `PWD`；应用补丁 0001；`configure`；随后把生成的 `config.status`
   中残留的 `umask 077` 就地改为 `022`（生成文件、仅 OHOS，防 `make check` 触发
   config.status 重跑时复发 E011）；`make -j1`；`make check -j1`。
4. `package()`：`autotools.install()` 安装 `bin/wcalc` 与 man 页，并把上游测试结果
   标记复制进包内 `res/`，供 test_package 在缓存命中时重新输出。
5. test_package：编译 `test.c` 并真实执行安装产物 `bin/wcalc`。

## 上游测试

`test/Makefile.am` 用 automake 并行测试框架登记 `TESTS`：

- `POSITIVE_TESTS` 12 个：basic_ints、basic_float、basic_vars、basic_math、
  implicit_mult、precision_guard、conversion、website_math、factorial、formatting、
  active_variable、vars。
- `XFAIL_TESTS` 9 个：err.assert、err.question、err.assign、err.conv_category1、
  err.conv_category2、err.recursion1、err.recursion2、err.recursion3、err.recursion4。

合计 21 个测试，口径为 `autotools_tests`（`upstream_test_total: 21`）。
`build()` 内真实执行 `make check`，计数只取自 `test/test-suite.log` 的
`# TOTAL/# PASS/# FAIL/# SKIP/# XFAIL/# XPASS/# ERROR` 汇总块（单一数据源，不做
字符串数数或算术修补）。XFAIL 是上游在 `test/Makefile.am` 中显式声明的预期失败
（属于「按预期结果执行」而非「跳过」），因此计入 passed；SKIP 才计入 skipped。
标记生成前自检恒等式 `passed + failed == executed` 与
`executed + skipped <= discovered`。

## Linux x86_64 源码基线（仅供定位，不作为 PR 通过率）

在本机对同一 tar.bz2 解包后执行 `./configure --without-readline && make -j1 &&
make check -j1`：`# TOTAL: 21 / # PASS: 12 / # XFAIL: 9 / # FAIL: 0 / # ERROR: 0`。
9 个 err.* 用例均为上游 XFAIL。该基线只用于确认测试真实执行、harness 能抓到失败，
PR 正文的通过率以 HarmonyOS 真机预检日志为准。

## 证伪检查（避免「假绿」）

- 消费者测试 `test.c` 用 8 项确定性断言，故意把被测二进制换成 `exit 1` 的桩后
  harness 报告 1/8 失败并以非零码退出；换成只打印版本号的桩报告 2/8 失败。
  证明测试确实在断言真实行为，而非空跑通过。
- 上游 `make check` 的用例输出非空：`test-suite.log` 有 21 条 `PASS:/XFAIL:` 结果行
  与汇总块，二进制被真实调用（每个 .test 通过 `checktest.sh` 执行 `wcalc`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 报 `subs1.awk: Permission denied` | configure 以 umask 077 创建临时目录，HMDFS 上对构建用户不可写（E011） | 补丁 0001 将 configure 中两处 umask 077 改为 022，仅 os=OHOS 应用 |
| 2 | `make -j` 并行可能卡住 | HMDFS/SELinux 限制 jobserver FIFO（E074） | 统一 `make -j1` |
| 3 | readline 依赖非必需 | 上游 configure 中 readline 为可选 | `--without-readline`；标准输入交互保留 |
| 4 | GMP/MPFR 头文件/库定位 | autotools 需要显式路径 | `--with-gmp`/`--with-mpfr` 指向 Conan 包目录，`AutotoolsDeps` 注入环境 |
| 5 | `configure: error: working directory cannot be determined`，伴随大量 `shell-init: error retrieving current directory: getcwd` | 共享 ohos-aarch64 profile 的 `[buildenv]` 导出 `CONFIG_SHELL=/data/service/hnp/bin/bash`；autoconf `configure` 在 `CONFIG_SHELL` 非空时无条件 `exec $CONFIG_SHELL`，该 hnp bash 在 HMDFS 构建树上 getcwd 失败 | `build()` 向生成的 `conanbuild.sh` 末尾追加 `export CONFIG_SHELL=/bin/sh; export SHELL=/bin/sh`（/bin/sh 为 toybox sh，getcwd 正常），并导出 `PWD` 使 `pwd` 走逻辑路径；parted/3.8、tetradraw/2.0.3 同款先例 |
| 6 | CI #91942 在 `autotools.configure()` 处 `can't fork - try again`；CI #92079 中 configure 已通过，但 `make` 在 `Making all in common` 时又报 `/bin/sh: can't fork - try again`；CI #93107 对 make 做 3 次有界重试仍全部失败（每次都在同一处 `can't fork`） | 每次 `self.run` 都被 Conan 包成 `. conanbuild.sh && <cmd>`，而生成的 env 脚本（`conanautotoolstoolchain.sh`、`conanbuildenv-*.sh`）以**反激活前导块**开头，逐变量 fork 一次 `$(printenv $v)`。在负载较高的共享真机上，这一串短命进程瞬间耗尽进程表，紧接其后的 fork 即 EAGAIN。CI #91942 恰好死在 `conanautotoolstoolchain.sh[13]`（即前导块的 `$(printenv $v)`），#92079/#93107 死在其后的 `make` fork。由于重试会重新 source 同一前导块、再次制造同样的 fork 风暴，纯重试无法自愈 | 在 `generate()` 内 `self.conf.define("tools.env:deactivation_mode", "function")`：Conan 把前导块改写为「仅定义反激活函数」（纯 shell 内建，source 期零 fork），仍导出同样的变量，从源头消除 fork 风暴。`test_package` 显式声明 `generators="VirtualRunEnv"`，显式 generator 在 `generate()` 之前运行，故在其 `configure()` 内注入同一 conf。本地以同源 Conan 2.29.1 实测：注入前 `conanautotoolstoolchain.sh` 含 `$(printenv $v)`，注入后该脚本及全部 `conan*.sh` 的 `printenv` 计数均为 0；profile `[buildenv]` 派生的 `conanbuildenv-*.sh` 前导块同样归零。`_run_with_fork_retry` 骨架保留为兜底（仅命中 fork 指纹时有界重试），但主修复不再依赖重试 |
| 7 | CI #93618（-018）、#93656（-003）在 `make -j1` 的 `Making all in common` 处 `can't fork - try again`，三次有界重试全失败；而同一配方版本 `w-calc/2.5#843249272aaef70f2482da8cf104ab4e`（提交 b5061f84，**尚未包含问题 6 的 deactivation 修复**）在 CI #93377（-021）完整通过 | 证据表明这是**机器相关、瞬时的 worker 进程表争用**：同一 recipe revision 在不同 worker 上结果不同（#93377 pass / #93618 fail / #93656 fail）。此外通过日志显示 `package()` 走 `Autotools(self).install()`，未传 `-j`，GNU make 采用 `build_jobs`（宿主核数），实测为 `make install ... -j20`——这是构建/检查已用 `-j1` 之外**唯一未被 fork 门控覆盖**的并行步骤，同样会 fork 出大量 sh/install 子进程 | (a) 把 `_run_with_fork_retry` 的重试次数 3→5、退避改为指数 15/30/60/120s，以覆盖更长的压力窗口；(b) 新增 `_install_with_fork_retry()`：`package()` 改为走 `make install ... -j1` + 同一有界重试，消除 `-j20` 安装 fork 风暴。根因仍是 worker 资源抖动，非配方/源码缺陷；deactivation 修复（问题 6）尚未被官方 CI 验证，本轮修复叠加其上 |
| 8 | CI #93820（-013，当前 head `0fcb0b22ad`，recipe revision `73424de7`）在 `configure` 的 `checking whether the C compiler works... no` 处失败，`configure: error: C compiler cannot create executables`，且 `ConanException: w-calc configure failed (attempt 1/5, rc=77)`——即**配方已有的 fork 门控重试一次都没触发**；同一 head 在真机预检 21/21 通过 | 现有 `_run_with_fork_retry` 只扫描 `configure` 自己的 stdout/stderr。autoconf 在编译器探测失败时，stdout 只输出通用句 `C compiler cannot create executables`，**真正的编译器/链接器错误（例如探测子进程里的 `can't fork - try again`，或 lld 加载 libxml2.so.16 失败）写在构建目录的 `config.log`**。因此 fork 指纹落在 `config.log` 里、重试门控看不到，任何由 fork/环境抖动引起的 configure 失败都会在 attempt 1 直接抛出（rc=77 是 autoconf 编译器不可用的固定退出码） | 给 `_run_with_fork_retry` 增加 `diag_paths` 参数：每轮尝试前删除旧诊断文件，尝试后读取并把内容打印进 CI 日志，同时把 `config.log` 内容并入 fork 指纹扫描；`_configure_with_fork_retry()` 传入 `build_folder/config.log`（并兼容 `source_folder`）。这样 configure 内部的瞬时 fork/链接失败能命中门控并重试，真实错误也不再被通用句掩盖 |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 构建配方（含上游 make check 接入与标记输出） |
| conandata.yml | 上游源码 URL 与 SHA256、补丁声明 |
| patches/0001-configure-hmdfs-umask.patch | OHOS HMDFS umask 适配补丁 |
| test_package/conanfile.py | 消费者测试驱动 |
| test_package/test.c | 真实执行 bin/wcalc 的 8 项断言测试 |
| test_package/MANIFEST.yml | 上游 21 个测试与消费者测试声明 |
| commands.json | 命令行工具声明（软件级） |
