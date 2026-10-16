# openigtlink 3.0.0 — 测试报告

**日期**: 2026-10-14
**目标平台**: OpenHarmony / HarmonyOS PC, aarch64-linux-ohos, musl libc, clang 15, Release
**框架**: Conan 2.29.1 (OHOS 适配版), profile `ci/conan/profiles/ohos-aarch64`

### 证据日志来源说明（必读）

本包有 **3 个日志**，性质不同，引用时必须区分：

| 日志 | 性质 | 本文引用的关键位置 |
|------|------|-------------------|
| `reports/w3-local-ci.log` | **权威证据**：W3 本地 CI 模拟（`ci/conan/build_and_test.sh`，与真实 CI 同一脚本入口），从官方 tarball 从零构建 | 结果行 `100% tests passed` 第 **714** 行；耗时 `Total Test time` 第 **716** 行；`Package … built` 第 **718** 行；逐用例明细第 **590–712** 行；消费者测试第 **880** 行 |
| `.ci_logs/conan_build_openigtlink_3.0.0.log` | 同一次 W3 运行内 `conan create` 的**原始逐字日志**（已被 `.gitignore` 忽略，不入库） | 第 **596**（结果行）/ **598**（耗时）/ **600**（`Package built`）/ **762**（消费者测试）行 |
| `reports/conan-create.log` | 仅 **conan-verify G2** 门禁日志。本次运行为**缓存命中重跑**（`openigtlink/3.0.0@ohpcd/stable#1a8f… - Cache`）：**不含 CTest 段**（故不承载上游测试证据），只含 Export + Cache 校验 + test_package 构建与执行 | Export 第 2–10 行；`- Cache` 第 56/60/71/75 行；test_package 构建/执行第 80–129 行（消费者输出第 128 行） |

> 为什么权威证据取 W3 而非 `reports/conan-create.log`：`conan-verify` 的 G2 在二进制已入 cache 时
> 只做 Export + Cache 校验 + test_package 重跑，不再编译库、不跑 CTest。因此「从零构建 + 62 用例」
> 的唯一完整证据在 **W3 本地 CI 模拟**（126 个 TU 真实编译 + 62 用例），这也是真实 CI 走的同一条路径。

---

## 一、上游官方测试（层 1，docs/TEST_QUALITY_SPEC.md）

### 测试入口

上游是 CMake 项目，**没有 `make check`**，CTest 就是上游唯一的自动化测试入口。
`conanfile.py::build()` 末尾调用 `cmake.test()`，由 CTest 在同一个编译目录内驱动：
```python
def build(self):
    apply_conandata_patches(self)
    cmake = CMake(self); cmake.configure(); cmake.build()
    cmake.test()          # ← 上游官方测试（层 1）
```
实际执行的命令：`ctest --output-on-failure`（工作目录即 conan 构建目录，权威 W3 运行为
`/storage/Users/currentUser/.conan2/p/b/openi80a08fe386aff/b/build/Release`，见 `reports/w3-local-ci.log` 第 **719** 行）。

上游 CMake 开关：`BUILD_TESTING=ON`、`USE_GTEST=OFF`。
`USE_GTEST=OFF` 走上游 `Testing/igtlTestConfig.h.in` 内置的非-gtest 回退 runner，
免除 configure 期通过 `ExternalProject` 联网下载 googletest/googlemock release-1.7.0；
两条路径下 `ADD_TEST` 注册面与用例集合完全相同。

### 结果汇总

| 项 | 值 |
|----|----|
| 测试命令 | `ctest --output-on-failure`（由 `cmake.test()` 调用） |
| 用例总数 | **62** |
| 通过 | **62** |
| 失败 | **0** |
| 跳过 / 未执行 | **0** |
| 结果行 | `100% tests passed, 0 tests failed out of 62` |
| 耗时 | `Total Test time (real) = 17.51 sec`（62 条用例耗时逐条累计 17.40 s） |
| 日志路径 | **权威**：`archives/o/openigtlink/3.0.0/reports/w3-local-ci.log` 第 **714** 行（结果行）、第 **716** 行（耗时），逐用例明细第 **590–712** 行；**原始逐字**：`.ci_logs/conan_build_openigtlink_3.0.0.log` 第 **596** / **598** 行 |

补充说明（`ADD_TEST` 语句 63 条、唯一用例 62 个）：上游 `Testing/CMakeLists.txt` 在
"Message Tests Added in Version 3" 分支里把 `igtlPositionMessageTest` 注册了第二次
（无 gtest filter 参数），CMake 同名测试后者覆盖前者，因此 CTest 只暴露 62 个唯一用例。
这是上游缺陷，未做修改。

用例构成：`Testing/CMakeLists.txt` 贡献 44 个唯一 gtest 用例（协议 3 个消息格式代际 +
消息工厂 + 多线程 + 条件变量 + 时间戳）；`Testing/igtlutil/CMakeLists.txt` 贡献 18 个纯 C 用例
（igtlutil 序列化层）。

### 上游未覆盖的部分（重要）

上游把 3 个网络测试的 `ADD_EXECUTABLE` / `TARGET_LINK_LIBRARIES` **全部注释掉了**
（`Testing/CMakeLists.txt` 第 66-68、133-135 行）：

```
#ADD_EXECUTABLE(igtlSocketTest         igtlSocketTest.cxx)
#ADD_EXECUTABLE(igtlServerSocketTest   igtlServerSocketTest.cxx)
#ADD_EXECUTABLE(igtlClientSocketTest   igtlClientSocketTest.cxx)
```

因此上游套件对一个**网络协议库**实际不覆盖任何 socket 路径。实测这 3 个源文件在
`USE_GTEST=OFF` 的回退路径下**编译不过**（依赖仅 gmock 提供的 `testing::_` / `testing::AtLeast` /
`testing::Invoke`），属上游死代码。适配未强行启用它们，而是从公开 API 侧在消费者测试里
补了一条真实回环 TCP 往返（见第二节）。

### 上游用例逐项清单

| # | 用例名 | 结果 | 耗时(s) |
|---|--------|------|---------|
| 1 | `igtlMultiThreaderTest1` | Passed | 0.46 |
| 2 | `igtlMultiThreaderTest2` | Passed | 0.64 |
| 3 | `igtlMultiThreaderTest3` | Passed | 0.44 |
| 4 | `igtlMessageFactoryTest` | Passed | 0.04 |
| 5 | `igtlTimeStampTest1` | Passed | 0.03 |
| 6 | `igtlMessageBaseTest` | Passed | 0.03 |
| 7 | `igtlConditionVariableTest` | Passed | 7.06 |
| 8 | `igtlImageMessageTest` | Passed | 0.04 |
| 9 | `igtlImageMessage2Test` | Passed | 0.03 |
| 10 | `igtlCapabilityMessageTest` | Passed | 0.04 |
| 11 | `igtlStatusMessageTest` | Passed | 0.03 |
| 12 | `igtlTransformMessageTest` | Passed | 0.03 |
| 13 | `igtlPositionMessageTest` | Passed | 0.03 |
| 14 | `igtlBindMessageTest` | Passed | 0.02 |
| 15 | `igtlColorTableMessageTest` | Passed | 0.04 |
| 16 | `igtlLabelMetaMessageTest` | Passed | 0.04 |
| 17 | `igtlNDArrayMessageTest` | Passed | 0.04 |
| 18 | `igtlImageMetaMessageTest` | Passed | 0.02 |
| 19 | `igtlPointMessageTest` | Passed | 0.04 |
| 20 | `igtlPolyDataMessageTest` | Passed | 0.03 |
| 21 | `igtlSensorMessageTest` | Passed | 0.04 |
| 22 | `igtlStringMessageTest` | Passed | 0.03 |
| 23 | `igtlTrackingDataMessageTest` | Passed | 0.03 |
| 24 | `igtlTrajectoryMessageTest` | Passed | 0.02 |
| 25 | `igtlMessageBaseTestFormatVersion2` | Passed | 0.02 |
| 26 | `igtlImageMessageTestFormatVersion2` | Passed | 0.03 |
| 27 | `igtlImageMessage2TestFormatVersion2` | Passed | 0.02 |
| 28 | `igtlBindMessageTestFormatVersion2` | Passed | 0.02 |
| 29 | `igtlCapabilityMessageTestFormatVersion2` | Passed | 0.03 |
| 30 | `igtlColorTableMessageTestFormatVersion2` | Passed | 0.03 |
| 31 | `igtlConditionVariableTestFormatVersion2` | Passed | 7.05 |
| 32 | `igtlLabelMetaMessageTestFormatVersion2` | Passed | 0.03 |
| 33 | `igtlNDArrayMessageTestFormatVersion2` | Passed | 0.02 |
| 34 | `igtlImageMetaMessageTestFormatVersion2` | Passed | 0.03 |
| 35 | `igtlPointMessageTestFormatVersion2` | Passed | 0.03 |
| 36 | `igtlPolyDataMessageTestFormatVersion2` | Passed | 0.02 |
| 37 | `igtlSensorMessageTestFormatVersion2` | Passed | 0.02 |
| 38 | `igtlStatusMessageTestFormatVersion2` | Passed | 0.02 |
| 39 | `igtlStringMessageTestFormatVersion2` | Passed | 0.03 |
| 40 | `igtlTrackingDataMessageTestFormatVersion2` | Passed | 0.04 |
| 41 | `igtlTrajectoryMessageTestFormatVersion2` | Passed | 0.02 |
| 42 | `igtlTransformMessageTestFormatVersion2` | Passed | 0.04 |
| 43 | `igtlCommandMessageTestFormatVersion1` | Passed | 0.03 |
| 44 | `igtlCommandMessageTestFormatVersion2` | Passed | 0.03 |
| 45 | `igtl_image_test_01` | Passed | 0.03 |
| 46 | `igtl_header_test_01` | Passed | 0.03 |
| 47 | `igtl_transform_test_01` | Passed | 0.03 |
| 48 | `igtl_status_test_01` | Passed | 0.03 |
| 49 | `igtl_util_test_01` | Passed | 0.04 |
| 50 | `igtl_position_test_01` | Passed | 0.03 |
| 51 | `igtl_capability_test_01` | Passed | 0.03 |
| 52 | `igtl_colortable_test_01` | Passed | 0.04 |
| 53 | `igtl_imgmeta_test_01` | Passed | 0.03 |
| 54 | `igtl_lbmeta_test_01` | Passed | 0.03 |
| 55 | `igtl_point_test_01` | Passed | 0.03 |
| 56 | `igtl_tdata_test_01` | Passed | 0.03 |
| 57 | `igtl_trajectory_test_01` | Passed | 0.04 |
| 58 | `igtl_sensor_test_01` | Passed | 0.04 |
| 59 | `igtl_string_test_01` | Passed | 0.04 |
| 60 | `igtl_bind_test_01` | Passed | 0.03 |
| 61 | `igtl_ndarray_test_01` | Passed | 0.03 |
| 62 | `igtl_polydata_test_01` | Passed | 0.03 |
---

## 二、消费者测试（层 2）+ 适配新增的鸿蒙测试用例

### 测试入口

`test_package/conanfile.py::test()`，独立于库源码树，只使用**已安装**的包
（导出的 CMake target `OpenIGTLink::OpenIGTLink`）：

```python
def test(self):
    if not can_run(self): return
    temporary = os.path.join(self.build_folder, "consumer-tmp")
    os.makedirs(temporary, exist_ok=True)
    environment = Environment()
    environment.define("TMPDIR", temporary)
    with environment.vars(self).apply():
        executable = os.path.join(self.cpp.build.bindirs[0], "test_openigtlink")
        self.run(executable, env="conanrun")
```

### 实测结果

```
openigtlink/3.0.0 (test package): RUN: ./test_openigtlink
CONSUMER_1_OF_1_PASS assertions=51 pack_size=106 loopback_port=59801 protocol=3 header=2
```
（`loopback_port` 是内核分配的临时端口，逐次运行不同：W3 运行为 `59801`，conan-verify G2 重跑为 `56601`。
`assertions` / `pack_size` / `protocol` / `header` 四次运行完全一致。）

| 项 | 值 |
|----|----|
| 消费者用例数 | **1**（`test_openigtlink.cpp`，52 处 `CHECK`，OHOS 上实跑 51 个断言） |
| 退出码 | 0 |
| 日志路径 | **权威**：`reports/w3-local-ci.log` 第 **879–880** 行；**原始逐字**：`.ci_logs/conan_build_openigtlink_3.0.0.log` 第 **761–762** 行；**conan-verify G2 重跑**：`reports/conan-create.log` 第 **127–128** 行 |

### 覆盖内容

1. 安装头文件里的协议常量：`OpenIGTLink_PROTOCOL_VERSION==3`、`OpenIGTLink_HEADER_VERSION==2`、
   `IGTL_HEADER_SIZE==58`、`IGTL_TRANSFORM_SIZE==48`。
2. C 工具层（`Source/igtlutil/`）：`igtl_transform_get_crc()` 可复现且非零、
   `igtl_transform_convert_byte_order()` 单次换序确实改变字节、两次换序恢复原字节且 CRC 不变。
3. C++ 消息层：构造 TRANSFORM → `Pack()`（106 字节）→ 用库自身的 `MessageHeader` 解码头部
   （`name` / `device_name` / `header_version` / `timestamp` / `body_size` 逐项比对）→
   拷 body → `Unpack()` → `GetMatrix()` 与发送侧矩阵**逐字节相同**。
4. 端到端回环：`igtl::ServerSocket::CreateServer(0)` 取临时端口 + `igtl::ClientSocket::ConnectToServer("127.0.0.1", port)`
   + `WaitForConnection(5000)`，把整条 TRANSFORM 消息（头部+体）经 socket 发送并在接收侧解码，
   矩阵逐字节一致。
5. **适配新增的鸿蒙专属用例**（`#ifdef __OHOS__` 块，13 个断言）：
   - `uname()` 的 `sysname` 必须是 `HarmonyOS`；
   - `TMPDIR` 已设置且为绝对路径；
   - 序列化后的消息写入任务私有临时目录再读回，**字节完全一致**，且读回的字节仍能解码出同一个矩阵
     （模拟鸿蒙应用把网络线程收到的样本交给消费方线程的场景）。

### 该用例暴露过的一个真实缺陷（适配过程证据）

消费者测试第一版根本无法编译：包 `include/` 下**零个库头文件**。根因是上游
`Source/CMakeLists.txt:75` 的 `IF( MSVC OR ${CMAKE_GENERATOR} MATCHES "Xcode" )` 没有 `ELSE` 分支，
Unix Makefiles 下 `OpenIGTLink_INCLUDE_FILES` 恒为空 → `INSTALL(FILES ...)` 装 0 个文件。
补丁 `0002-Source-CMakeLists.txt.patch` 修复后，从零构建日志中
`-- Installing: .../p/include/*.h` 共 **76** 条（73 个库头文件 + 3 个 configure 生成的配置头，
见 `reports/w3-local-ci.log` 第 **729–806** 行），消费者测试方能编译并通过。

同一次从零构建的真实编译规模（`reports/w3-local-ci.log`）：`Building CXX object` **64** 行
+ `Building C object` **62** 行 = **126** 个 TU，其中库本体 `Source/CMakeFiles` 61、
`Source/igtlutil` 21、上游测试 `Testing/CMakeFiles` 25 + `Testing/igtlutil` 18、
消费者 1；`Linking … library` / `Linking CXX executable` **28** 行。4 条 `Apply patch` 见第 **201–204** 行。

---

## 三、补充：严格标准编译对照（定位 `typeof` 问题的定向实验）

`conan-verify` 的 G2 `conan create` 首次失败于
`Testing/igtlImageMessageTest.cxx:91: error: use of undeclared identifier 'typeof'`。
定向实验（同一 TU、同一 flags，仅替换 `Testing/igtlTestConfig.h.in` 生成的配置头）：

| 输入 | 编译命令 | error 数 |
|------|----------|---------|
| pristine `igtlTestConfig.h.in` | `clang++ -std=c++17 -c igtlImageMessageTest.cxx` | 12 |
| 补丁 0003 后 | 同上 | **0** |

全部「已注册」测试 TU（排除上游未注册的 3 个 socket 测试）在 `-std=c++17` 下编译失败数：**0**。
