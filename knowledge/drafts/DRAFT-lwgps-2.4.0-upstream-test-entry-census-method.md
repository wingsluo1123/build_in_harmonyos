# DRAFT: 上游测试清点必须按官方枚举器全量枚举（glob *.cmake），顶层 CMakeLists 默认装配只含 1 个入口 → rule4 少报

- **库**: lwgps 2.4.0（MaJerle，轻量级 GPS NMEA 解析库，CMake）
- **路径**: B（`knowledge_decision: new_draft`，跨库可复用）
- **日期**: 2026-10-15（r02 返工：rule4 少报修正）

## 问题

r01 报告上游测试声明为 `pass 1/1 (ctest --test-dir build/tests)`，平台实测上游 N=4，
判定「少报」（rule4：上游实测 N=4 > 声明 N=1）。根因不是测试没过，而是**清点口径**错误：
r01 按顶层 CMakeLists 的默认装配计数，只覆盖了 4 个上游测试入口中的 1 个。

## 根因

lwgps 2.4.0 顶层 `CMakeLists.txt` 对独立构建走：

```cmake
set(TEST_CMAKE_FILE_NAME "test_parse_sat_det/cmake.cmake")  # 默认只装这一个入口
add_subdirectory(tests)
```

而 `tests/CMakeLists.txt` 用 `include(${TEST_CMAKE_FILE_NAME})` 注入测试源与专用
`lwgps_opts.h`，并对每个装配 `add_test(NAME Test ...)`。**上游官方枚举器**是
`tests/test.py`（上游 CI `build-and-test.yml` 即运行 `python test.py`），它递归
glob `tests/**/*.cmake`（排除 `__build__`），枚举出 4 个入口：

| # | 入口（相对 tests/） | 测试源 | ctest 注册项 |
|---|--------------------|--------|-------------|
| 1 | `test_parse_beidou/cmake.cmake` | `test_parse_beidou.c` + `test_main.cpp` | `Test` |
| 2 | `test_parse_ext_time/cmake.cmake` | `test_parse_ext_time.c` + `test_main.cpp` | `Test` |
| 3 | `test_parse_sat_det/cmake.cmake` | `test_parse_sat_det.c` + `test_main.cpp` | `Test` |
| 4 | `test_parse_standard/cmake.cmake` | `test_parse_standard.c` + `test_main.cpp` | `Test` |

顶层默认 `TEST_CMAKE_FILE_NAME` 只装配 sat_det 一个入口 → r01 按此申报 N=1。
**错误结论**：顶层 CMakeLists 的默认装配 ≠ 全部上游测试入口；清点必须以上游官方
枚举器（test.py 或等价 glob）为准。

## 方案

对每个普查到的入口，在 `tests/<entry>/__build__` 按上游 test.py 等价方式独立
配置、构建、运行：

```bash
cmake -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -S../.. -G Ninja \
      -DTEST_CMAKE_FILE_NAME=<abs path>/cmake.cmake \
  && cmake --build . \
  && ctest . --output-on-failure -C Debug
```

关键点：

1. **清点以官方枚举器为准**：`python3 -c "glob tests/**/*.cmake"`（或 find/grep 等价），
   逐入口列出路径/源/注册项；禁止只按顶层默认装配计数；
2. **逐入口真实运行**：每个入口独立 configure+build+ctest，分类为可运行且已运行/
   可运行但未运行/不可运行，未运行与不可运行项必须给尝试命令/退出码/缺依赖/阻塞
   归属/恢复条件（禁止 `build-tests=false` 后写 0，禁止"环境不支持"泛化表述）；
3. **ctest 目录语义**：ctest 需在含 add_test 的子目录（`tests/<entry>/__build__`）运行
   （上层 CMakeLists 无 enable_testing()，上游缺陷；与 DRAFT-21003 机制相关但问题不同）；
4. **按实测 N 申报**：实测 N=4，声明 N=4，对账一致才不触发 rule4 少报。

## 验证

- 普查命令（官方枚举器口径）：
  `python3 -c 'import glob,os; files=[f for f in glob.glob(os.path.join(os.getcwd(),"tests","**","*.cmake"),recursive=True) if "__build__" not in f]; print(len(files))'` → `COUNT=4`，exit 0
  （日志 `/storage/Users/currentUser/tmp/builds/lwgps-r02-census.log`，SHA-256
  `f61192b6549bf8319c1fe1b24ce3afa6b67bad4811be1ca507ac19984cac4888`）
- 逐入口真实运行 4/4 通过（各 1/1）：

| 入口 | 退出码 | 日志 | 日志 SHA-256 |
|------|--------|------|-------------|
| test_parse_beidou | 0 | `/storage/Users/currentUser/tmp/builds/lwgps-r02-test-test_parse_beidou.log` | `e2c76150534abfbdbd94ecbcf8277df788c71bfc086da1f2c1189caf4f25aa00` |
| test_parse_ext_time | 0 | `/storage/Users/currentUser/tmp/builds/lwgps-r02-test-test_parse_ext_time.log` | `5bbb2b826e7fda6e962322388b294eb2ee2f980cdd8f186a2f072700ae257474` |
| test_parse_sat_det | 0 | `/storage/Users/currentUser/tmp/builds/lwgps-r02-test-test_parse_sat_det.log` | `7c0b742d8c4de9b5585eebddac99c4392ea123f00b3526ad3d1cf5a43207e697` |
| test_parse_standard | 0 | `/storage/Users/currentUser/tmp/builds/lwgps-r02-test-test_parse_standard.log` | `3a04b8f1eddb6ea10d535f6dff01c086cc5fb4ec3859302f056911a676122bd0` |

- 不可运行/未运行项：0 个。

## 适用边界

- 顶层 CMakeLists 用「默认变量 + add_subdirectory」只装配部分测试入口的 CMake 工程；
- 每入口一个 `cmake.cmake`/include 文件、`tests/CMakeLists.txt` 逐入口 `add_test` 的布局；
- 任何依赖"顶层默认装配计数"申报上游测试 N 的适配任务（R51 三步法执行口径）。

## 反例与限制

- **不能**只改统计数字不普查（`changed_numbers_only_without_census` 是 result_contract
  的 prohibited_marker）；
- **不能**禁用测试目标/跳过入口后把数量写成 0；
- **不能**用「环境不支持」等泛化表述给不可运行入口定性——必须逐项给证据；
- 若平台实测 N 与本地方案仍有差异，须逐入口台账定位差异来源，不得直接采信任一数字。

## 查重差异

- **vs DRAFT-21003**（lwjson，ctest-subdir-testfile）：该条覆盖「enable_testing/add_test
  在子目录 → CTestTestfile.cmake 只生成在 <build>/tests/ → 顶层 ctest 'No tests were
  found' 假阳性，需 --test-dir <build>/tests」。本条覆盖「顶层默认 TEST_CMAKE_FILE_NAME
  只装配 1 个入口 → 清点须用官方枚举器 glob *.cmake 并逐入口独立运行」。触发机制、方案、
  症状（rule4 少报 vs 本地假阳性）均不同。非等价命中。
- **vs E410**（adapt，Python pytest）：同属"只跑默认/单个入口造成测试覆盖不足"家族，
  但语言框架（C/CMake vs Python/pytest）、枚举机制、申报后果均不同。非等价命中。
- **vs E231**（测试发现须绑定已校验压缩包）：来源绑定问题，与本条清点口径正交。
- **vs E294**（共享包第二个静态构建树恢复上游测试）：BUILD_SHARED_LIBS 变体问题，不同。
- **vs E321/E327/E328/E344/E353/E366/E370/E417/E489/E698/E738** 及快照 547 条正式 +
  4662 条草稿：均不在"顶层默认装配截断上游测试入口"范畴，无等价命中。

## 审计

- 快照：`https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git` @ main，
  HEAD `b544378a4ea82b4959135eebb21f5e509eeebf91`，稀疏路径 `knowledge`，外置只读
  `/storage/Users/currentUser/tianyi/kb-snapshot-lwgps-2.4.0-r02-upstream-test-entry-census-full-run-pc2-47-20261015T120000Z`
  （SNAPSHOT-AUDIT.json 记录远端 URL/ref/HEAD/稀疏范围/创建命令/只读审计）；
- 扫描范围：`graph/E*.kv`（547 条）+ `graph/index.tsv` + `doc/E*.md` + `drafts/*` +
  根级 `DRAFT-*` 对 + 全部快照命中 greenfield 候选（E231/E294/E321/E327/E328/E353/
  E366/E370/E410/E417/E489/E698/E738、DRAFT-21003、DRAFT-box2d-ctest-empty-suite）；
- 判定：无等价命中、候选可跨库复用 → `new_draft`（路径 B）。