# lwgps 2.4.0 功能测试报告

**测试日期:** 2026-09-28
**测试环境:** OpenHarmony PC aarch64
**编译器:** clang 15.0.4 / clang++ 15.0.4
**构建系统:** CMake（库子目录独立构建）

## 1. 编译测试

### 1.1 编译状态
✅ 编译成功（`cmake -S lwgps -B build` library-only 构建，产物 `liblwgps.a`）

### 1.2 编译警告
- `make: jobserver mkfifo: Operation not permitted`（OHOS 沙箱平台限制，不阻塞构建，E046 类已知现象）

### 1.3 源码修改
- 无补丁（上游源码零修改）

## 2. 上游测试

### 2.1 上游测试入口普查（R51 / r02 返工：rule4 少报修正）
- 普查方法：上游官方枚举器 `tests/test.py`（上游 CI `build-and-test.yml` 即运行 `python test.py`）递归 glob `tests/**/*.cmake`（排除 `__build__`），精确命令与输出见普查日志 `/storage/Users/currentUser/tmp/builds/lwgps-r02-census.log`（SHA-256 `f61192b6549bf8319c1fe1b24ce3afa6b67bad4811be1ca507ac19984cac4888`）
- 普查结果：恰好 **4 个测试入口**（对应平台实测 N=4）：

| # | 入口（相对 tests/） | 测试源 | ctest 注册项 | 平台 N=4 对应 |
|---|--------------------|--------|-------------|--------------|
| 1 | `test_parse_beidou/cmake.cmake` | `test_parse_beidou.c` + `test_main.cpp` | `Test`（`tests/CMakeLists.txt` add_test） | ✅ |
| 2 | `test_parse_ext_time/cmake.cmake` | `test_parse_ext_time.c` + `test_main.cpp` | `Test` | ✅ |
| 3 | `test_parse_sat_det/cmake.cmake` | `test_parse_sat_det.c` + `test_main.cpp` | `Test` | ✅ |
| 4 | `test_parse_standard/cmake.cmake` | `test_parse_standard.c` + `test_main.cpp` | `Test` | ✅ |

- 顶层 CMakeLists 默认仅装配 `test_parse_sat_det`（`TEST_CMAKE_FILE_NAME="test_parse_sat_det/cmake.cmake"`）——这是 r01 只跑 1/1 少报的根因；上游结构上 4 个入口各自可独立配置运行（`-DTEST_CMAKE_FILE_NAME=<绝对路径>`），每个入口经 `include()` 注入测试源与专用 `lwgps_opts.h`

### 2.2 上游测试逐入口真实运行（r02，每个入口独立构建+ctest）

对每个普查到的入口，在 `tests/<entry>/__build__` 按上游 `test.py` 等价方式真实构建并运行：
`cmake -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -S../.. -G Ninja -DTEST_CMAKE_FILE_NAME=<abs path>/cmake.cmake && cmake --build . && ctest . --output-on-failure -C Debug`

| # | 入口 | 分类 | 运行命令（日志内完整命令） | 退出码 | 结果 | 日志路径 | 日志 SHA-256 |
|---|------|------|--------------------------|--------|------|---------|-------------|
| 1 | test_parse_beidou | 可运行且已运行 | configure+build+ctest（见日志） | 0 | 1/1 通过 | `/storage/Users/currentUser/tmp/builds/lwgps-r02-test-test_parse_beidou.log` | `e2c76150534abfbdbd94ecbcf8277df788c71bfc086da1f2c1189caf4f25aa00` |
| 2 | test_parse_ext_time | 可运行且已运行 | configure+build+ctest（见日志） | 0 | 1/1 通过 | `/storage/Users/currentUser/tmp/builds/lwgps-r02-test-test_parse_ext_time.log` | `5bbb2b826e7fda6e962322388b294eb2ee2f980cdd8f186a2f072700ae257474` |
| 3 | test_parse_sat_det | 可运行且已运行 | configure+build+ctest（见日志） | 0 | 1/1 通过 | `/storage/Users/currentUser/tmp/builds/lwgps-r02-test-test_parse_sat_det.log` | `7c0b742d8c4de9b5585eebddac99c4392ea123f00b3526ad3d1cf5a43207e697` |
| 4 | test_parse_standard | 可运行且已运行 | configure+build+ctest（见日志） | 0 | 1/1 通过 | `/storage/Users/currentUser/tmp/builds/lwgps-r02-test-test_parse_standard.log` | `3a04b8f1eddb6ea10d535f6dff01c086cc5fb4ec3859302f056911a676122bd0` |

✅ **上游测试 4/4 通过（实测 N=4，与声明 N=4 对账一致，无少报）**
- 不可运行/未运行项：0 个（无 `build-tests=false`、无跳过、无禁用目标）
- 注：上游顶层 CMakeLists 未调用 `enable_testing()`（上游缺陷），ctest 需在 `tests/<entry>/__build__` 子目录运行——r02 已按上游 test.py 的目录语义覆盖全部 4 个入口

## 3. 消费者测试（test_package，conan create G2 内实际运行）

```bash
$ ctest --test-dir <test_package>/build/clang-15-armv8-17-release --output-on-failure
1/2 Test #1: test_lwgps .......................   Passed    0.02 sec
2/2 Test #2: harmonyos_specific_test ..........   Passed    0.02 sec
100% tests passed, 0 tests failed out of 2
```
✅ test_package 2/2 通过（真实调用 lwgps API 解析上游样例 NMEA 并断言字段）

### 3.1 HarmonyOS 专项测试（任务契约 harmonyos_specific_test）
```bash
$ ./lwgps_ohos_test
arch: aarch64 (HarmonyOS PC)
lwgps_float_t sizeof=8, LWGPS_CFG_DOUBLE=1
lwgps_ohos_test OK: parsed lat=39.122600 lon=-121.041367 fix=1
```
✅ 新增 1 个、实际运行、调用当前库并验证 OHOS 行为的测试，exit 0（日志 SHA-256: 1e745199efbde32d5766d12499314c3b3cfa5ad226fea9158dc39667e17a7bcb）

## 4. 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 配方完整性 | ✅ 通过 | conanfile.py + conandata.yml + test_package + MANIFEST.yml |
| G0 预构建风险评估 | ✅ 通过 | 知识图谱预查询 |
| G2 conan create | ✅ 通过 | 干净构建 + test_package 2/2 |
| G3 系统同名库隔离 | ✅ 通过 | 无系统同名冲突 |
| G4 产物完整性 | ✅ 通过 | include/lwgps/*.h + lib/liblwgps.a |
| W3 本地 CI 模拟 | ✅ 通过 | build_and_test.sh 全绿（.ci-result.json exit_code=0） |

## 5. 测试结论

✅ **lwgps 2.4.0 编译、上游测试（4/4）、消费者测试、HarmonyOS 专项测试全部通过**

### 已知问题
- 上游顶层 CMakeLists 未调用 `enable_testing()`（上游缺陷）；上游官方枚举器 `tests/test.py` 递归枚举 4 个 `cmake.cmake` 测试入口，每个入口需在 `tests/<entry>/__build__` 子目录独立配置运行（r02 已全量覆盖）
- 上游 CMake 无 install 规则，配方 `package()` 手工复制头文件与静态库
- 顶层 CMake 会把测试专用 opts（`LWGPS_CFG_STATEMENT_GPGSV_SAT_DET=1`）注入库编译，造成库与消费者结构体布局错位（test_package 段错误）；配方改为只构建 `lwgps` 子目录（默认 opts）解决
