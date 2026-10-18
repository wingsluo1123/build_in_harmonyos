# DRAFT: 顶层 CMake 把测试专用配置头注入库目标编译 → 库与消费者结构体布局错位 → test_package Signal 11

- **库**: lwgps 2.4.0（MaJerle，轻量级 GPS NMEA 解析库，CMake）
- **路径**: B（`knowledge_decision: new_draft`，跨库可复用）
- **日期**: 2026-09-28

## 问题

lwgps 2.4.0 的 conan 配方首次 `conan create`（G2）时，test_package 的两个测试可执行文件
（`test_lwgps`、`lwgps_ohos_test`）在 OHOS aarch64 目标上均以 `Signal 11 (core dumped)`
（exit 139）崩溃；同一测试源码级现象为字段读到垃圾值（`course=0.000000`）后段错误。
库本身编译成功、上游测试 1/1 通过，故障只在"打包库 + 消费者头文件"组合下复现。

## 根因

lwgps 顶层 `CMakeLists.txt` 对独立构建走 `add_subdirectory(tests)`，而
`tests/CMakeLists.txt` 在 `add_subdirectory(lwgps)` **之前**先 `include` 测试的
`cmake.cmake`，其内容为：

```cmake
set(LWGPS_OPTS_FILE ${CMAKE_CURRENT_LIST_DIR}/lwgps_opts.h)
```

该测试专用 `lwgps_opts.h` 定义 `LWGPS_CFG_STATEMENT_GPGSV_SAT_DET 1`，使库在编译期
看到含 `sats_in_view_desc[48]`（48 × `lwgps_sat_t`）的 `lwgps_t` 结构体。而 conan 配方
打包给消费者的头文件是官方空模板（`lwgps_opts_template.h` → `lwgps_opts.h`，默认 opts，
无 SAT_DET 字段），`lwgps_t` 明显更小。于是：

```
库（编译期）：  +--- 含 sats_in_view_desc[48] 的大 lwgps_t ---+
消费者（头文件）：+--- 小 lwgps_t ---+
库按大结构体写入，消费者按小结构体访问 → 静默内存越界 → Signal 11
```

类似地，结构体大小不一致还会让同一字段读到错位/垃圾值（本案例中 `course=0`）。

## 方案

配方 `build()` 只构建 `lwgps` 库子目录，保持与打包头文件同配置：

```python
def build(self):
    apply_conandata_patches(self)
    cmake = CMake(self)
    cmake.configure(build_script_folder="lwgps")  # 独立构建：LWGPS_OPTS_FILE 未设 → 默认模板
    cmake.build()

def package(self):
    # 手工打包：无上游 install 规则
    # 头文件 include/lwgps/*.h（含由官方模板复制产出的 lwgps_opts.h）
    # 静态库 liblwgps.a（位于构建目录根：self.build_folder/liblwgps.a）
```

关键点：

1. **禁止**用顶层 CMakeLists 构建后打包——测试配置会注入库编译；
2. 打包的默认 `lwgps_opts.h` 必须与库编译所用配置**逐字节一致**（都由官方模板产出）；
3. 若库子目录不可独立构建，退化方案为显式 `-DLWGPS_OPTS_FILE=<官方模板路径>` 固定配置。

## 验证

- 修复前：`conan create`（G2）中 ctest 2/2 失败（`***Exception: SegFault`），exit 139；
- 修复后：`conan create`（G2）中 ctest 2/2 通过（`test_lwgps` 0.02s + `harmonyos_specific_test` 0.02s）；
- HarmonyOS 专项测试直接运行：`./lwgps_ohos_test` → `arch: aarch64 (HarmonyOS PC)`、
  `lwgps_ohos_test OK: parsed lat=39.122600 lon=-121.041367 fix=1`，exit 0
  （日志 SHA-256: `1e745199efbde32d5766d12499314c3b3cfa5ad226fea9158dc39667e17a7bcb`）；
- `conan-verify` G1–G4 全部通过；finish W3 本地 CI 模拟通过（`.ci-result.json` exit_code=0）。

## 适用边界

- 顶层 CMake 把测试专用 opts/配置头经 `add_subdirectory` 注入库目标编译的 C/C++ 库；
- 库公共结构体含仅测试配置启用的字段时必然触发（`lwgps_t.SATS_IN_VIEW_SIZE` 类）；
- 症状判断特征：test_package 段错误 + 部分字段读到垃圾值，库与上游测试单独跑均正常。

## 反例与限制

- **不能**以 E543 方案（`cpp_info.defines` 下发特性宏）替代：本案例库编译期配置已固化差异，
  消费者用什么宏都救不回（且测试专用宏本就不应进入消费者）；
- **不能**修改上游测试配置或删除测试 opts 以"让测试通过"（伪造构建事实）；
- **不能**用 `print`/空壳 test_package 绕过段错误（R34/PF3）。

## 查重差异

- **vs E543-draft-5CC4**（fossa `NS_ENABLE_IPV6` 布局宏）：同属"库与消费者结构体布局
  ABI 不一致 → 静默越界/段错误"家族，但触发机制（上游 CMake 测试配置注入 vs 配方漏下发
  defines）、方案（库独立子目录构建 vs `cpp_info.defines` 钉契约）、症状签名（运行期
  SegFault vs 编译期 no member/sizeof）均不同；E543 为草稿（draft:true）。非等价命中。
- **vs E040/E213/E249/E338/E194/E470** 及 36 个根级 DRAFT-*：均不在"测试配置注入库编译"
  范畴，无等价命中。

## 审计

- 快照：`https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git` @ main，
  HEAD `78a2955eb7d646a9f94bf42251e20d611851bf74`，稀疏路径 `knowledge`，外置只读
  `/storage/Users/currentUser/tianyi/kb-snapshot-lwgps-20260928T080743Z`；
- 扫描范围：`graph/E*.kv`（541 条）+ `graph/index.tsv` + `doc/E*.md` + `drafts/*` +
  根级 `DRAFT-*` 对（36 对）；
- 判定：无等价命中、候选可跨库复用 → `new_draft`（路径 B）。