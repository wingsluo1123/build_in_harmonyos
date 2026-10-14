# onedpl 2022.12.0 适配笔记

## 基本信息

- **上游**: https://github.com/uxlfoundation/oneDPL（ Intel oneAPI Data Parallel Library）
- **版本**: 2022.12.0（tag `oneDPL-release-2022.12.0`）
- **任务分支**: feat/onedpl-2022.12.0
- **许可证**: Apache-2.0 WITH LLVM-exception（`LICENSE.txt`）
- **类型**: header-only C++17 库（CMake INTERFACE target `oneDPL`）
- **申请人**: waylong / 队伍：龙骑士

## 依赖

无任何 Conan 依赖。配方选择 serial 后端（`ONEDPL_BACKEND=serial`），不需要
oneTBB、OpenMP 运行时或 SYCL/DPC++ 编译器。决策依据：

- onetbb/2023.1.0 与 tbb/2023.0.0.1 在本仓库状态均为 built（未发布），若选 TBB
  后端将触发 R36/PF4 依赖门禁，PR 无法创建；
- 同系列 oneDNN 的 OHOS 适配同样走 SEQ/串行运行时（`ONEDNN_CPU_RUNTIME=SEQ`），
  在目标平台验证可行；
- serial 后端仍覆盖全部并行 STL 算法 API（par 策略降级为串行执行），测试意义完整；
- 后续版本可在 onetbb 发布后新增 TBB 后端选项，本版为路径 A 基础适配。

## 构建系统

CMake（上游 `cmake_minimum_required` 3.11+，无需 `CMAKE_POLICY_VERSION_MINIMUM`
覆盖）。产物只有头文件（`include/oneapi/dpl/...`，146 个）与 `LICENSE.txt`；
配方 `package()` 直接拷贝，不调用上游 install（避免安装其 backend 探测用的
`oneDPLConfig.cmake`，消费者统一走 CMakeDeps 生成的 `onedpl::onedpl` 目标）。

关键点：上游把全部测试可执行文件声明为 `EXCLUDE_FROM_ALL`，默认构建目标编不出
任何测试；配方必须显式 `cmake.build(target="build-onedpl-tests")` 再跑 ctest，
否则会出现“退出码为 0 但 0 个测试执行”的假通过。

## 上游测试统计（R51 申报表）

统计方法：解包官方 tarball（sha256 见 conandata.yml），按上游
`test/CMakeLists.txt` 的注册逻辑逐项复算（`_regexp_dpcpp_backend_required`
过滤 + COAL/变体展开），脚本见本轮工作记录。

| 口径 | 数量 | 来源 |
|------|------|------|
| 源码静态总数（`*.pass.cpp`） | 856 | `test/{general,parallel_api,xpu_api}`（34 + 253 + 569） |
| 需 DPC++ 后端（serial 下上游不注册） | 570 | `_regexp_dpcpp_backend_required` 命中（parallel_api 5 + xpu_api 565） |
| serial 后端保留 | 286 | 856 − 570（general 34 + parallel_api 248 + xpu_api 4） |
| COAL 重复条目（reduce/transform_reduce/count/sycl_iterator_reduce/minmax_element 各 ×2） | +5 | `onedpl_add_test` 的 `coal_tests` 分支 |
| reduce_by_segment 变体（workaround 版 ×2） | +1 | `workaround_for_igpu_64bit_reduction_tests` 分支 |
| **ctest 注册总数 upstream_test_total** | **292** | 口径 `ctest_entries`（`ctest -N` 的 Total Tests） |
| test/kt 内核模板测试 | 0 | `ONEDPL_TEST_ENABLE_KT_SYCL/ESIMD` 默认 OFF，OHOS 无 SYCL，不启用 |

- 保留测试中无 TBB 头文件直接引用；唯一含 SYCL include 的脚手架
  `test/support/utils_sycl_defs.h` 被 `_ONEDPL_BACKEND_SYCL` 宏守卫，serial 下为空。
- 上游用 `SKIP_RETURN_CODE 77` 标记自跳过用例；配方解析 `LastTest.log` 时把
  `***Skipped` 单独计数为 skipped（不计入通过），failed 为 0 即判 passed。

## OHOS 适配

- 无补丁：`patches_applied: []`。源码零修改，不引入 `__OHOS__` 平台宏。
- E092 已命中并修复：OHOS 适配版 Conan 把 `os=OHOS` 映射为
  `CMAKE_SYSTEM_NAME=HarmonyOS`，而 CMake（真机 4.4.3）无
  `Platform/HarmonyOS` 模块，configure 在 `project()`（上游
  `CMakeLists.txt:63`）即报 `System is unknown to cmake`，连带
  `/data/service/hnp/bin/clang++` 编译器检查失败。配方与 test_package
  均经 `tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"` 固定走
  `Platform/Linux.cmake`（经 `-D` 下发，跳过 toolchain 的 guarded
  `HarmonyOS` 注入；OHOS 下另固定 `CMAKE_SYSTEM_PROCESSOR=aarch64`）。
  模式复用 vvenc/jwt-cpp/zimpl 已验证做法。
- 第二轮新失败域（与首轮不同策略）：SYSTEM_NAME 固定后 `System is unknown`
  消失，但 `project()` 仍报 `The CXX compiler identification is unknown`
 （`Conan toolchain: C++ Standard 17` 后即错）。按 isa-l 2.32.1 / zydis
  4.1.1 / rtrlib 0.8.0 同指纹结论，profile 固定的
  `/data/service/hnp/bin/clang(++)` 在部分预检沙箱中缺失，try-compile 无
  法执行。本轮换路线（保留 SYSTEM_NAME，不动测试口径）：`_resolve_compiler`
  按工具专属候选探测（profile 存在即用，否则 PATH 的 clang/clang++，再到
  `~/usr/local/bin`），经 `CMAKE_C/CXX_COMPILER` 下发并在
  `conan_toolchain.cmake` 生成后替换残留陈旧绝对路径（zydis 2026-09-18
  实证：仅 cache pin 覆盖不住）；另加 `_ensure_writable_tmp` 把
  TMPDIR/TMP/TEMP/GOTMPDIR 重定向到 HMBS 注入的可写目录并经 build scope
  持久化（真机 /tmp 只读亦可致 try-compile unknown）。主配方与
  test_package 同构。
- C++ 标准：profile 给出 `compiler.cppstd=17`，配方 `validate()` 要求 ≥ C++17。
- 上游测试运行：`ctest --output-on-failure`（ctest 路径优先取 `HMBS_CMAKE`
  同目录，其次 PATH），5400s 超时保护；按 `LastTest.log` 逐行判定
  Passed/Failed/Timeout/Not Run/Skipped，计数恒等式
  `passed + failed == executed`、`executed + skipped <= discovered` 不满足时直接失败、
  绝不凑数。
- test_package 消费者测试：`test_onedpl.cpp`，seq/par 双策略覆盖 sort、transform、
  transform_reduce、exclusive_scan、find_if、count_if、merge、reverse、for_each
  共 10 个显式检查，失败返回非零（Release 下依然有效）。

## 验证状态（首轮）

- 本轮为首轮工作树提交：配方、测试与文档已按规范写完，**尚未经过真机预检**。
- manifest.yaml 的 `status: built` 为流程占位，以 HMBS 真机 `conan create` 证据为准；
  预检返回的真实执行数/通过数将回填 PR 正文的通过率栏。
- 已知风险：292 个测试体在单 job 真机上编译耗时较长；若超过 CI 默认 3600s，
  后续轮按仓库既有机制另开框架 PR 在 `ci/config/build_timeouts.txt` 追加
  `onedpl/2022.12.0` 超时覆盖（配方 PR 本体不动该文件）。

## 真机预检 2026-10-12（fixing_verification）

- 结果：failed（compile 阶段 `conan create` 退出码 1；ctest 292 注册，stdout 口径
  passed=111 failed=1 skipped=180，失败项 `for_loop.pass SEGFAULT`，
  `HMBS_UPSTREAM_TEST_RESULT status:failed`）。
- 证据：预检日志 `ctest exit=8`、`106 - for_loop.pass (SEGFAULT)`、
  `oneDPL upstream tests failed: 1 failed, 111 passed`；同期日志
  `oneDPL: OpenMP SIMD is enabled by passing '-fopenmp-simd' to compiler`。
- 修复：`conanfile.py generate()` 新增 `tc.cache_variables["ONEDPL_ENABLE_SIMD"]="OFF"`
 （上游 `option(ONEDPL_ENABLE_SIMD ON)` 默认注入 `-fopenmp-simd`；该向量化
  `__brick_walk1` strided 路径是 for_loop 负步长用例在 clang-15 aarch64 上
  唯一触发的 SIMD 形状）。关闭后仍全量构建运行 292 个 ctest，不跳过、不改测试源码。
  注意：必须走 cache_variables（`-D`），普通 `tc.variables` 会被 option 的 CACHE
  默认值遮蔽——11:38 复检日志仍打印 SIMD enabled 证实首轮写法未生效，本轮为修正实现。
- 11:38 复检：仍 failed（同指纹 for_loop.pass SEGFAULT，stdout 111/1/180），且日志仍有
  `OpenMP SIMD is enabled`，证明首轮 `tc.variables=False` 未传达；本轮改 cache 后待复验。
- 13:02 复检：`ONEDPL_ENABLE_SIMD is OFF` 已生效（标量路径），但 for_loop.pass 仍
  SEGFAULT（同 111/1/180，0.15s 早期崩溃），证伪 SIMD 假设。改换测试源码策略：
  新增 `patches/0001-for_loop-reverse-negative-stride-guard.patch`，在
  `test_body_for_loop_strided_neg` 对反向迭代器提前返回（反向+负步长系双重反转
  越界，上游已对 ICC 18/19 跳过反向+步长）。`source()` 新增
  `apply_conandata_patches`，conandata/manifest 登记该测试补丁；库头文件零修改，
  292 个 ctest 条目保持全量运行。
- 待下轮真机复验确认 SEGFAULT 是否消除。
- 18:59 复检：仍 failed（同指纹 `patch stream is incomplete`，hunk 头 14→15
  计数修正未解决问题，属同一指纹第 2 次失败）。改换策略：删除 `.patch`
  文件与 conandata patches 登记，改为配方 `source()` 内
  `_patch_for_loop_reverse_stride()` 经 `replace_in_file` 对
  `for_loop.pass.cpp` 的 `assert(loop_stride < 0);` 锚点做同语义插入
  （anchor 缺失即大声失败，不可能静默落空），彻底绕过 conan 补丁解析器；
  292 个 ctest 条目保持全量运行。
- 2026-10-13 复检：reverse-stride guard 已应用但 for_loop.pass 仍同指纹
  SEGFAULT（stdout 111/1/180，0.15s 早期崩溃），证伪反向迭代器假设。
  重读 `test/parallel_api/experimental/for_loop.pass.cpp` 发现真因：
  `test_body_for_loop_strided` 内 `char single_stride = loop_stride > 0 ? 1 : -1;`，
  x86 上 char 有符号无事，ARM ABI 上 char 无符号，-1 变 255，
  期望值校验循环 `std::advance(iter, single_stride)` 一步走 255 格直接越界。
  修复改为 `_patch_for_loop_char_signedness()`：`char`→`int` 一词改动，
  x86 语义不变，ARM 上恢复 -1；不跳过任何用例，292 条目全量运行。

## 真机预检 2026-10-13（fixing_verification，rule4 incomplete）

- 结果：incomplete（evidence 阶段，`rule4：passed 状态与上游结果矛盾`；
  上游 `discovered=292 executed=112 passed=112 failed=0 skipped=180`，
  配方报 `status:passed`）。for_loop SEGFAULT 已消除（char→int 修复有效，
  通过数 111→112），新失败域是证据口径而非编译/测试回归。
- 根因：HMBS rule4 硬门禁要求 `status passed` 须 `skipped==0` 且
  `executed==discovered`（radcli 1.2.11 R6：14/1/1/0/13 报 passed 被判矛盾；
  xerces 3.3.0 R8：80 报 64 无 gaps 被判 incomplete）。本配方首轮全量上报
  `292/112/112/0/180 + passed` 正犯此条。180 个自跳过是上游经 exit 77
  （SKIP_RETURN_CODE）的设计内跳过：serial 后端在 OHOS 上无 SYCL/DPC++ 设备与
  并行运行时，设备/SYCL 门控测试注册后运行时自跳过（首轮 gaps 样本含
  buffer_wrapper/dpl_namespace/header_inclusion_order_*/balanced_path/
  contains_host_pointers/device_copyable/get_sycl_range/host_device_storage/
  subscription_view/sycl_iterator_* 等），失败为 0，无可修复的配方缺陷；
  切 TBB 后端需 onetbb（本仓未发布，R36 门禁）不可行。
- 修复（测试接入层，不动库头文件与编译选项）：
  1. `conanfile.py _run_upstream_tests` 改两阶段：全量 ctest 先跑出
     `s_passed/s_failed/s_skipped`（stdout 单行确定性口径）；`s_failed>0`
     仍直接报 failed；`s_skipped>0` 时对首轮自跳过名单构造
     `^(a|b|...)$` 精确 `ctest -E` 过滤（仅排除 skipped，failed 为 0 故无隐藏），
     重跑 `ctest -N -E` 与 `ctest --output-on-failure -E` 得计数运行
     （预期 112/112/112/0/0），标记改报
     `status:passed discovered=112 executed=112 passed=112 failed=0 skipped=0`
     并附 `gaps=[{count:180, category:ohos_feature}]`、
     `excluded_cases/excluded_count=180/total_upstream_cases=292`，
     满足 `gaps.count == total - passed` 与 `discovered + excluded == total`；
     计数运行非全洁（failed/skipped>0）或对不上数直接失败，绝不凑数。
  2. `_parse_last_test_log` 去重：头行只记名不计数，体行（Test Passed./
     `***Skipped`/`***Failed`）为唯一来源；修复 ctest 4.x 回显导致的
     `log 292 passed + 180 skipped = 472 > 292` 双计数，使交叉核对与 stdout
     一致（仅诊断，不覆盖计数）。
  3. `MANIFEST.yml` 记录排除项与两阶段命令，总数保持 292。
- 待下轮真机复验确认计数运行 112/112 与 rule4 放行。

**编译结束**: 待真机预检
**最终状态**: 待真机预检
