# toontag 0.0-git20220105193632.41237ef 适配笔记（HarmonyOS PC / OpenHarmony aarch64）

## 上游信息

- 上游仓库：https://github.com/edrosten/tag（TooN Algorithm Library，TaG）
- 版本提交：41237efe686d286bc9009eae70d1758b7c6282c5（2022-01-05T19:36:32Z，PR #2 合并提交，清理 TR1 引用）
- 源码归档：GitHub API tarball（与姊妹库 toon 同口径），sha256 见 `conandata.yml`
- 许可证：BSD-2-Clause（`COPYING` 随包安装到 `licenses/`）
- 构建系统：GNU Autotools（`configure.in` + `Makefile.am` + libtool，产物 `libtoontag.la`，头文件 `tag/*.h` 共 20 个）
- 依赖：TooN 头文件（Conan 包 `toon/0.0-git20240623085717.2982ecc`，制品仓已发布，见下方核验）

## 依赖发布核验（W0）

- `toon/0.0-git20240623085717.2982ecc` 已在本仓库归档（`archives/t/toon/0.0-git20240623085717.2982ecc/`），为 header-only 包，无传递依赖。
- toontag 决算时依赖：TooN 头（`--with-TooN`）+ LAPACK 链接；`configure.in` 只探测 TooN 头，无 pkg-config / GVars / libCVD 接线，但 `tag/absorient.h` 内联的 `TooN::SVD` 在消费者链接期必需 `dgesvd_`（Debian 用 `liblapack-dev` 兼容，OHOS 用仓内 `lapack/3.12.1`）。

## 上游测试审计（R51：先清点，再谈验证）

盘点范围：`Makefile.am`、`configure.in`、`src/`、`tag/`、`test/` 全树（commit 41237ef）。

- `Makefile.am`：只定义 `lib_LTLIBRARIES = libtoontag.la` 与 `pkginclude_HEADERS`，无 `TESTS` / `check_PROGRAMS` / `check-local`。
- `configure.in`：`AC_INIT/AM_INIT_AUTOMAKE` + 编译器与 TooN 头检查，无任何测试宏。
- 全树无 `enable_testing/add_test`（ctest）、`TEST/TEST_F`（gtest）、`def test_`（pytest）。
- `test/` 下 4 个 `.cpp`（absorient / fivepoint / handeye / sim）均为手工演示程序：随机输入、打印输出、无断言、无 PASS/FAIL 判定，不被任何构建目标或 harness 引用（`fivepoint.cpp` 的 `main` 直接跑 2x1000000 次随机扰动打印误差）。
- `make -n check` 展开为空目标（automake 默认 `check-am: all-am`），执行 0 用例退出 0，不构成测试套件。

结论：上游确无自动化测试套件。`test_package/MANIFEST.yml` 以 `upstream_tests_exist: false` + 非空 `upstream_test_audit` + `upstream_test_total: 0`（口径 `autotools_tests`）声明；配方输出 `status:"no_tests"` 的诚实标记。`make check` 刻意不接入——跑空目标冒充"测试通过"属于伪造证据。

## OHOS 适配改动

| # | 问题 | 根因 | 方案 |
|---|------|------|------|
| 1 | `tag/*.h` 默认 `#include <tr1/tuple>` / `<tr1/array>`，libc++ + C++17 下不存在 | 上游以 `NEWCPPSTD` 宏切换标准头（`#if !defined(WIN32) && !defined(NEWCPPSTD)`），OHOS 属于前者分支 | `generate()` 经 `AutotoolsToolchain.extra_cxxflags` 加 `-DNEWCPPSTD`；`package_info()` 经 `cpp_info.defines` 传递给消费者；`test_package/CMakeLists.txt` 亦显式定义（与 Debian 修复 #1133653 同方案） |
| 2 | `configure` 找不到 TooN | 上游只认 `--with-TooN=目录` 参数 | `generate()` 追加 `--with-TooN=<toon>/include`（Conan 包真实路径）+ `AutotoolsDeps` 注入 `-I` 到 CPPFLAGS，configure 检查与编译期包含双覆盖 |
| 3 | 真机 `/tmp` 只读，autoconf/libtool 写临时文件失败 | HMBS 真机环境约束 | `_ensure_writable_tmp()`：按 `TMPDIR/TMP/TEMP/HMBS_TMPDIR/HMBS_AUTOCONF_MKTEMP_FALLBACK`、`~/tmp`、构建目录内备选顺序探测可写目录并导出；只重定向临时根，不跳过任何构建步骤（与 zydis 同模式） |
| 4 | 真机 `configure: error: working directory cannot be determined` + 刷屏 `shell-init/job-working-directory: getcwd`（errno 五花八门） | OHOS 真机 `/data/service/hnp/bin/bash` 在 conan 构建缓存目录（HMDFS 深路径）自身 getcwd 损坏，旧 autoconf 的 pwd 校验直接致命；同目录 `/system/bin/sh` 干净（DRAFT-cvsgraph-bash-getcwd / E386 实证，本轮日志逐字命中） | OHOS 分支能力探针选 shell：`_select_clean_shell()` 在真实 build dir 跑 `pwd`，仅当 rc=0 且 stdout/stderr 均无 getcwd 诊断才接受（`/system/bin/sh`→`/bin/sh` 优先）；`build()` 用 `CONFIG_SHELL=<clean> SHELL=<clean> <clean> configure …` 显式调用（兼避 shebang exec 问题），`CONFIG_SHELL/SHELL` 同步固定防烤进 Makefile 的 SHELL 在 make/config.status 复发；`make/make install` 均显式 `SHELL=<clean>`；Linux 保持默认 Autotools 路径 |
| 5 | 真机 `config.guess: unable to guess system type`（2005-02-10 版）+ `configure: error: cannot guess build type; you must specify one`（UNAME_SYSTEM=HarmonyOS） | 上游 config.guess/config.sub 太旧，无法识别鸿蒙内核；与识别脚本版本无关的系统性问题 | 由 settings 派生 GNU 三元组并原生构建 build==host：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（armv8→aarch64；linux-gnu vendor 被 2005 版 config.sub 直接接受，无需补丁；刻意不用 -ohos vendor，旧 config.sub 会拒绝）。`generate()` 与 OHOS 手工 configure 命令双处追加，已有参数则跳过；保留 shell 探针与临时目录加固 |

无 `patches/`：41237ef 已含 TR1 清理（PR #2），OHOS 侧差异全部经工具链参数解决，无需改上游源码；`patches/` 补丁禁平台宏（R8/PF5），能用 `-D` 解决的不打补丁。

## 编译与验证（待真机预检）

```bash
conan create archives/t/toontag/0.0-git20220105193632.41237ef \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- 本轮为首轮工作树（未提交），真机预检由 HMBS 后台执行；上述命令与测试数字待预检日志回填，不在本轮猜测。
- 预期证据：`HMBS_UPSTREAM_TEST_RESULT`（`status:no_tests/discovered:0/executed:0`）+ `HMBS_TEST_PACKAGE_RESULT`（`discovered:8/passedCount:8`，`./test_toontag` 8 个 CHECK 全过）。
- 消费者测试设计（`test_package/test_toontag.cpp`，固定输入、零随机）：
  1. `quartic-count/roots`：`find_quartic_real_roots(0,-5,0,4)` 得 4 实根且为 -2/-1/1/2（链接 `libtoontag` 的真实求解器）；
  2. `absorient-translation/rotation/residual`：已知 SE3（绕 z 30° + 平移 1,2,3）正变换 6 点后反解，误差 < 1e-9；
  3. `essential-det-zero`：同一位姿的本质矩阵行列式为零；
  4. `se3-from-E-count`：`se3_from_E` 返回 4 解；
  5. `rotation-orthonormal`：`computeRotation` 结果正交归一。
- 默认静态库（`shared=False`）：纯数值算法库，无系统同名冲突（R26 不适用）；`package()` 删 `.la`，ELF 签名沿 CI 既有流程，不在配方内自造。

## 已知限制

- 上游 6 个 `.cpp` 实现全部编译进 `libtoontag`，但 `five_point` 的百万次随机优化路径未被消费者测试覆盖（耗时原因）；覆盖的是其确定性部分（`getEssentialMatrix` + `se3_from_E` 往返）。
- LAPACK 为必需链接依赖（矫正前版“内置路径”误写）：`tag/absorient.h` 的 `computeOrientationScale` 内联调用 `TooN::SVD`，而 `TooN/SVD.h` 无条件直调 Fortran `dgesvd_/sgesvd_` specification (`TooN/lapack.h`)，无备选回避；配方 OHOS 分支依赖仓内 `lapack/3.12.1`（reference BLAS，设备原生 flang 构建）且经 `package_info requires` 传递给消费者，与 Debian 启用 LAPACK 的构建数值一致。
## 2026-10-14 真机失败修复（config.status 临时目录 Permission denied）
- 现象：`configure: creating ./config.status` 后 `./config.status: can't create ./conf3GLQSE/subs1.awk: Permission denied`，`config.status: error: could not setup config files machinery`；HMBS 平台诊断 `[unsafe_local_mktemp]`，`HMBS_AUTOCONF_MKTEMP_FALLBACK=1`。
- 根因：HarmonyOS 真机 Toybox `mktemp -d` 建目录为 2700（HMDFS 继承 setgid，大写 S），内核拒绝其内 `open(O_WRONLY)`；autoconf 的 `(umask 077 && mktemp -d "./confXXXXXX")` 分支建目录成功但后续写失败。带 `umask 077` 的 `mkdir` 同样不可写，只有无 umask 的 plain `mkdir` 可写（同 abnfgen/0.21、4ti2/1.6.10 实证）。
- 方案：OHOS 且回退需要时（`HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 直接要求，否则在真实 build dir 实测 `mktemp -d` 建目录后写文件，仅目录建成但不可写时才修），把 `configure`（即其向 `config.status` 逐字写入的模板）在 configure 运行前原地替换为 `tmp="./conf$$-$RANDOM" + mkdir`（无 umask，configure 阶段限定）；健康文件系统保持无补丁 PATH。同时修正 `_ensure_writable_tmp` 不再把值为 "1" 的 `HMBS_AUTOCONF_MKTEMP_FALLBACK` 当作路径候选。
## 2026-10-14 真机失败修复 round-3（test_package 缺 TooN 头）
- 现象：主库 `libtoontag.la` 编译链接成功并输出 `no_tests` 标记，但 test_package 编译 `test_toontag.cpp` 报 `fatal error: 'TooN/TooN.h' file not found`（`tag/absorient.h:13` 公开包含 TooN 头）。
- 根因：`requirements()` 中 `self.requires(REQUIRED_TOON)` 默认不向消费者传递头文件（Conan 2 需显式 `transitive_headers=True`），主库自身编译可见 TooN 但消费者经 `toontag::toontag` 拿不到 `-I<toon>/include`。
- 方案：`self.requires(REQUIRED_TOON, transitive_headers=True)` 单行修复；`package_info()` 的 `cpp_info.requires = ["toon::toon"]` 与 `test_package` 链接关系保持不变，不新增直接依赖、不跳过任何测试。
## 2026-10-14 真机失败修复 round-2（沿用同一指纹的不同策略）
- round-1（probe 门控 + mktemp 分支改 plain mkdir）后真机仍报同一 `can't create ./conf*/subs1.awk: Permission denied`，且失败目录名仍为 mktemp 风格（`conf7J9bEW`），说明旧补丁未生效：门控探针可能静默跳过，且只改了 mktemp 分支而 autoconf 自带的 `(umask 077 && mkdir)` 回退分支同样不可写。
- 本轮改用库内已过门禁的 E114 机制（abiword-plugin-*/3.0.8、afflib、ancient、argyll-cms）：OHOS 无条件（无探针门控）删除运行的 `configure` 中两个临时目录分支的 `umask 077 && `（保留 mktemp，生成可写的组可读目录；该字面块经 `cat >>$CONFIG_STATUS <<\_ACEOF` 逐字写入生成的 config.status），并在 configure 步骤内将 `mktemp *conf*` shadow 到 PATH shim 使其返回失败走已可写的 mkdir 回退（`[unsafe_local_mktemp]` 平台处方），configure 结束后恢复 PATH，make/install 不受影响。已用真实上游 configure 快照离线验证两处替换各命中 1 次、无残留。
## 2026-10-14 真机失败修复 round-4（test_package undefined symbol: dgesvd_）
- 现象：主库 `libtoontag.la` 编译链接成功并输出 `no_tests` 标记，但 test_package 链接 `test_toontag` 失败：`ld.lld: error: undefined symbol: dgesvd_`，调用链为 `tag::Internal::computeOrientationScale<3>` → `TooN::SVD<3>`。
- 根因：`tag/absorient.h` 的 `computeOrientationScale` 是头文件内联模板，实例化在消费者目标中，而 `TooN/SVD.h::do_compute()` 无条件调用 `gesvd_ → dgesvd_` (`TooN/lapack.h` 声明，无 `#ifdef` 回避)；`libtoontag.a` 本身不实例化该模板故建库不报错，链接缺口在消费者链接期爆露。前版 notes “LAPACK 可选/内置路径”为误写，与源码不符。
- 方案：配方 OHOS 分支新增 `requires lapack/3.12.1 (transitive_libs=True)`（仓内已归档、设备原生 flang 构建的 reference BLAS 包，同 devicexlib/0.9.1 先例），`package_info` OHOS 追加 `lapack::lapack` 到 `cpp_info.requires`，CMakeDeps 自动把 `liblapack/libblas/libFortranRuntime` 加入消费者链接行；Linux 保留 `system_libs=[lapack,blas]`（lapack 包 `validate()` 仅 OHOS）。不删除任何断言、不跳过 SVD 路径，8 断言保持不变。
