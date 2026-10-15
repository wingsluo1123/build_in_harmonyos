# picobench 2.10.0 — 适配笔记（OHOS aarch64）

## 软件概要

- **上游**：https://github.com/iboB/picobench （iboB / Borislav Stanimirov）
- **版本**：2.10.0（tag v2.10.0）
- **形态**：header-only C++11 单头库（`include/picobench/picobench.hpp`），
  使用方在一个翻译单元 `#define PICOBENCH_IMPLEMENTATION`（或
  `PICOBENCH_IMPLEMENT_WITH_MAIN`）后 include 即激活实现
- **License**：MIT
- **依赖**：零依赖（W0 通过：无任何 conan requires/tool_requires）

## 适配方式（路径 A 基础适配）

header-only 库，无编译阶段：

- `package_type = "header-library"`、`no_copy_source = True`
- `package()` 精确复制 `source_folder/include → package_folder/include`（argy
  教训：路径不精确会产生 include/include/ 空目录）
- `package_id()` 调 `self.info.clear()`（无二进制构建差异，单一 package_id）
- 无补丁：OHOS clang 15 + libc++ 下单头开箱即用（上游仅要求 C++11）

## 源码获取

- conandata.yml `sources.url` 为列表：ghfast.top 镜像在前、GitHub 官方
  archive 直链兜底；sha256 本机双源实测一致
  （65bdee215110c95a48a3d2aead7e38a89a8260fb7ba1c5f982e2df1690822c81）
- conan 2.29.1 `tools.files.get()` 原生支持 URL 列表回退（files.py
  `isinstance(url, (list, tuple))` 分支已核实）

## 上游测试验证（OHOS aarch64 clang 15 实测）

上游 `test/` 为 doctest 套件（CTest 注册 2 个测试目标、7 个 TEST_CASE），
构建方式 `-DPICOBENCH_BUILD_TESTS=ON`（CPM 拉取 doctest-util 0.1.2 →
doctest-lib 2.4.11 + icm 1.4.6）。

**7 组用例镜像进 test_package 真跑（rule4 整改）**：上游测试源码
（basic.cpp + multi_cpp/ 4 TU）原样复制进 test_package，doctest 框架以
ohpcd 仓 doctest/2.4.11（与上游 CPM 拉取版本一致）等价还原，
doctest_main.cpp 以 DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN 提供官方 main 入口
（等价 doctest-util 的 doctest_with_main 形态）。conan create test 阶段
3 个 CTest 目标 + 显式 self.run 逐一真跑。

⚠ 上游测试的 CPM 直连 GitHub 在 CI 环境不可用（网络边界），故镜像方案
不依赖 CPM，doctest 走 Conan 依赖（cpp-lazy / intrusive-shared-ptr 先例）。

⚠ 本机直跑 OHOS 目标二进制需
`export LD_LIBRARY_PATH=<ohos-sdk>/native/llvm/lib`（libc++.so 位置），
否则报 `Error relocating ... symbol not found`——运行环境问题，非代码问题。
（conan create 经 conanbuild 环境自动携带，无需手工设置。）

实测结果（conan create test 阶段全部通过）：

| CTest 目标 | 测试程序 | test cases | assertions | 结果 |
|---|---|---|---|---|
| test_picobench | 消费者测试 | - | - | PASS |
| test_picobench_basic | 上游 basic.cpp 镜像 | 6/6 | 235/235 | PASS |
| test_picobench_multi_cpp | 上游 multi_cpp 镜像（4 TU） | 1/1 | 86/86 | PASS |
| **上游合计** | | **7/7 (100%)** | **321/321 (100%)** | **全绿** |

（multi_cpp 为多翻译单元场景测试：验证同套件跨 TU 的 PICOBENCH 宏注册，
main.cpp+suite_a.cpp+suite_b.cpp+suite_b_cont.cpp 四个 TU。）

上游 7 组 TEST_CASE 清单（grep TEST_CASE 上游 tag v2.10.0 实测）：

1. `[picobench] test utils`（basic.cpp:103）
2. `[picobench] picostring`（basic.cpp:122）
3. `[picobench] state`（basic.cpp:132）
4. `[picobench] cmd line`（basic.cpp:168）
5. `[picobench] test`（basic.cpp:366）
6. `[picobench] compare`（basic.cpp:581）
7. `[picobench] multi cpp test`（multi_cpp/main.cpp:20）

PICOBENCH_TEST 宏激活假时钟（picobench.hpp:1519 计数器实现，
this_thread_sleep_for_ns 仅累加数值不睡眠），全部断言确定性比对，
无计时精度/环境依赖。

## 消费者测试（test_package，R34 实质调用）

`test_package/test.cpp` 以消费者视角（官方极简 runner 形态，README 先例）：

1. `PICOBENCH(sum_vector)` / `PICOBENCH(string_ops)` 宏注册两个基准
   （`.iterations({64,256,1024}).samples(2)`，PICOBENCH_IMPLEMENT 激活单头实现）
2. `picobench::runner r;` → `r.run_benchmarks()` 真实计时运行
   （两个基准经宏注册、state 迭代、set_result 回写，库对基准异常会输出错误）
3. 输出 consumer test OK（异常路径非零退出）

L1 消费者测试通过 conan create 自动执行（CI 同款）。

## 已知边界

- 上游 `tools/`（CSV 转 gnuplot 图表的辅助工具）非库本体，不打包
  （header-library 无二进制产物）
- 上游测试的 CPM 直连 GitHub 网络依赖在 CI 不可用，已以 doctest/2.4.11
  Conan 依赖等价还原并镜像进 test_package 真跑（rule4 整改，
  7/7 全绿，见上表）
- `test_package/build/` 为本机验证残留，不入库（.gitignore 已覆盖）

## 依赖版本

- 库本体：零依赖
- doctest/2.4.11（test_package 测试框架，等价还原上游 CPM 拉取链）
