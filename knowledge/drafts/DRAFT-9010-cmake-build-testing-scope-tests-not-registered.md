# DRAFT-9010-cmake-build-testing-scope-tests-not-registered

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-9010-cmake-build-testing-scope-tests-not-registered.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-9010: 上游明明定义了测试却一个都没注册 —— CMake `BUILD_TESTING` 目录作用域陷阱

- 条目主题：`ENABLE_TESTING()`/`ADD_TEST` 分散在不同子目录时，先被处理的子目录看不到"后设置"的
  `BUILD_TESTING`，整套测试静默不注册（`ctest -N` 数量偏少），易误判为"上游没有测试"。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxxx）
- 关联 PR：feat/pftools-3.2.12

## 现象

```console
$ ctest -N
Total Tests: 6                       # 只注册了 tests/examples/ 里的 6 个

src/C/CMakeLists.txt:195: IF(BUILD_TESTING)
src/C/CMakeLists.txt:196:   INCLUDE(.../cmake/tests/TestSuite_pfsearchV3.cmake)
src/C/CMakeLists.txt:197: ENDIF(BUILD_TESTING)
cmake/tests/macros.cmake:6: ADD_TEST(NAME pfsearchV3_${subdir}_${name} ...)   # 宏里 ADD_TEST 未生效
```

关键特征：配置日志能看到 `Building test suite for ...`（`INCLUDE()` 执行了），但用例没进 `ctest -N`；
显式 `-DBUILD_TESTING=ON` 重新配置后数量依旧不变。

## 根因

- `ENABLE_TESTING()` 设置的是**普通变量** `BUILD_TESTING`（非 cache），CMake 变量作用域是**目录树自顶向下**：
  在某子目录里设置，只对该目录及其后续子目录可见。
- `ENABLE_TESTING()` 写在 `tests/examples/`，而 `IF(BUILD_TESTING)` 在**更早处理**的 `src/C/`
  （顶层 `ADD_SUBDIRECTORY(src)` 排在 `ADD_SUBDIRECTORY(tests/...)` 之前）→ 处理 `src/C` 时变量未定义 →
  整套用例不注册。
- `-DBUILD_TESTING=ON` 也可能无效：该值被后续作用域的普通变量遮蔽。

## 判定与处置

1. `ctest -N | tail -1`（注册数）对比 `grep -rn "ADD_TEST" --include=CMakeLists.txt --include=*.cmake`（应有数）—
   不等即命中本模式，**不要**下"上游无测试"结论。
2. `grep -rn "ENABLE_TESTING|include(CTest)|BUILD_TESTING"`，检查保护块所在目录是否先于设置点被处理。
3. 处置：顶层 `PROJECT()` 后调用 `ENABLE_TESTING()`/`include(CTest)`；或把设置点提前；或让保护块不依赖该变量。
4. 上报口径：若上游/发行版同样不注册（本例 x86 上也是 6），属上游自身行为 → notes/MANIFEST 如实说明，
   标注"未注册原因已定位、与适配无关"，不得伪造数量。

## 证据（真实执行）

pftools 3.2.12（HarmonyOS/aarch64）：

- `tests/examples/CMakeLists.txt` 注册 6 个用例 → **实跑 6/6 通过**；
- `src/C/CMakeLists.txt:195` 保护的 `cmake/tests/TestSuite_pfsearchV3.cmake`（宏生成 9+ 用例 + Truth 真值比对）
  **一个都没注册**；配置日志确有 `-- Building test suite for pfsearch in .../testing`；
  显式 `-DBUILD_TESTING=ON` 后 `ctest -N` 仍为 6；
- `grep -l "BUILD_TESTING|TestSuite_pfsearchV3" patches/*.patch` → **无命中**（与本次适配无关）。

## 推广价值

- 所有 CMake 工程统计上游测试规模时的必查项；与 R51 配套：清点必须同时给出**注册数**与**应有数**。

## 查重关键词

ENABLE_TESTING、BUILD_TESTING、include(CTest)、CMake 变量作用域、ADD_TEST 未注册、
ctest -N 数量偏少、宏未展开、测试套件静默缺失、上游测试清点
