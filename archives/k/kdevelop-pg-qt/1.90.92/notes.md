# kdevelop-pg-qt 1.90.92 编译笔记（HarmonyOS PC / aarch64）

## 这是什么

`kdevelop-pg-qt` 是 **KDevelop 的解析器生成器**：消费方通过 CMake 宏
`KDEVPGQT_GENERATE()`（由本包安装的 `KDevelop-PG-QtConfig.cmake` 提供）把 `.g`
语法文件编译成 C++ 解析器。KDevelop 的 **QMake 构建器/管理器插件**需要它。

适配现状核查报告把它标为 **RECOMMENDED**（`TYPE RECOMMENDED`）——缺它不是
KDevelop 本体的硬阻断，但该插件与"生成解析器"这条链路会缺失。报告登记的需求
版本是 `1.90.90`。

## 版本选择：为什么是 1.90.92 而不是 1.90.90

上游 KDE 下载站的 `stable/kdevelop-pg-qt/` 里，1.90.x 线**只有 1.90.91 与
1.90.92 两个发行包**（1.90.90 只存在 git tag，没有发行包；实测直连 404）。
本包取 **1.90.92** —— 同 1.90.x 线的最新发行版，满足消费方
`KDevPGQt >= 1.90.90` 的要求，且是上游仍在维护的那一支。

源码：`https://<mirror>/kde/Attic/kdevelop-pg-qt/1.90.92/src/kdevelop-pg-qt-1.90.92.tar.xz`
sha256 `a522adc9f77727197dcfcf7e68c3602fa0c6447d4d41156a6d954a1e22f8c5b1`（636,696 字节）。
**三个镜像（ftp.kaist.ac.kr / mirrors.mit.edu / mirrors.dotsrc.org）实测 sha256
逐字节一致**；1.90.92 已归档到 `Attic/`（`stable/` → `Attic/` 的多跳重定向在受限
Worker 上会超时，同款现象见 `karchive5/5.116.0` 与 `libkdepim/25.12.3` 的 conandata）。

## 交付物

| 路径 | 说明 |
|---|---|
| `bin/kdev-pg-qt` | 生成器可执行（上游 `ADD_EXECUTABLE(kdev-pg-qt ...)` + `INSTALL(TARGETS kdev-pg-qt DESTINATION bin)`） |
| `include/kdevelop-pg-qt/*.h` | 生成代码依赖的运行时头（allocator / location-table / memory-pool / token-stream / list / char-sets） |
| `lib/cmake/KDevelop-PG-Qt/KDevelop-PG-QtConfig*.cmake` | 消费方 `find_package(KDevelop-PG-Qt)` 入口与 `KDEVPGQT_GENERATE` 宏 |

## 构建要点

1. **ECM**：上游 `find_package(ECM 1.1.0 REQUIRED NO_MODULE)`，以
   `tool_requires("ecm/6.26.0")` 提供；其 CMakeDeps 配置不传播
   `ECM_MODULE_PATH`，配方显式设置 `ECM_DIR` / `ECM_MODULE_PATH`
   （modules / find-modules / kde-modules 三条）。
2. **Qt5 直接命中 qtbase 自带 config**：上游 `find_package(Qt5 5.2.0 CONFIG
   REQUIRED Core Test)`。制品实测 qtbase 内含**聚合** `lib/cmake/Qt5/Qt5Config.cmake`
   与 `Qt5Core/Qt5Test` 分模块 config、`bin/moc`、`bin/rcc`、`lib/libQt5Test.so`
   —— 故本配方**不用 CMakeDeps 转发**，而是把 `qtbase/lib/cmake` 放进
   `CMAKE_PREFIX_PATH`（`conan_cmakedeps_paths.cmake`），保真且少一层转换。
   `CMAKE_AUTOMOC_EXECUTABLE` / `CMAKE_AUTORCC_EXECUTABLE` 显式指向 qtbase 的
   moc/rcc（CMakeDeps 不导出这两个工具）。
3. **flex/bison 故意禁用**：宿主装了 flex/bison 时，上游会**重新生成**
   `kdev-pg-parser.cc`（122KB）/ `kdev-pg-lexer.cc`（113KB），产物随宿主工具版本
   漂移。源码包里已带这两份生成文件，故把 `FLEX_EXECUTABLE` /
   `BISON_EXECUTABLE` 置为 `*-NOTFOUND`，走上游 `ELSE` 分支 —— 确定性优先，
   零补丁。
4. **上游测试真跑（R51）**：`tests/CMakeLists.txt` 用
   `ecm_add_test(... LINK_LIBRARIES Qt5::Core Qt5::Test)` 注册 3 个 CTest 用例：
   `testlocationtable`、`testmemorypool`、`benchmarks`。本配方在 `build()` 内
   **实际执行 `ctest`**（`--no-tests=error` 防静默跳过），执行前对构建目录里的
   测试 ELF 做 **E318 自签**（OHOS 拒绝 exec 用户可写路径下未签名的 ELF），
   并以 `QT_QPA_PLATFORM=offscreen` + 独立 HOME/XDG 目录运行。
   结果见本文末「本地实测」与 `test_package/MANIFEST.yml`。

## 打包

- `cmake.install()`（上游自带 install 规则：可执行 + 头 + 两个 config 文件）；
- 安装后对包内 ELF 统一 **E318 重签**（`bin/kdev-pg-qt`）；
- **构建目录引用审计**：包内任何文本文件不得残留本配方构建目录的引用，否则报错
  （上游 config 由 `ecm_configure_package_config_file` 生成，本应 relocatable，
  这里以审计兜底）。

## 消费侧验证（test_package）

用随 test_package 交付的**上游真实语法样例** `examples/fact/fact.g`（236 行）
真跑生成器，调用形态与消费方宏一致：

```
kdev-pg-qt --output=fact fact.g
```

断言：退出码 0；至少 3 个非空产物；其中必须含 `*parser.cpp`。

## 本地实测（2026-10-16，本机 OHOS aarch64）

- `conan create archives/k/kdevelop-pg-qt/1.90.92`（profile `ci/conan/profiles/ohos-aarch64`）**rc=0**
- **上游 CTest 实跑**：构建后对 3 个测试 ELF 自签（E318）→ 运行 ctest →
  `100% tests passed, 0 tests failed out of 3` ✓（**3/3 执行并通过**）
- 打包：`bin/kdev-pg-qt`（生成器，已 E318 重签）+ `include/kdevelop-pg-qt/*.h`
  + `lib/cmake/KDevelop-PG-Qt/*.cmake`
- **消费侧验证**（test_package）：真跑生成器处理上游 `examples/fact/fact.g` →
  产出 **9 个文件**：`factparser.cpp/h`、`factast.h`、`factast-fwd.h`、
  `factvisitor.cpp/h`、`factdefaultvisitor.cpp/h`、`facttokentype.h` ✓

## 构建期踩坑（都已固化进配方注释，值得复用）

1. **CMake ≥3.5 策略下限**：上游是 `cmake_minimum_required(VERSION 2.8.12)`
   （第 7 行），现代 CMake 直接报错。注意 `CMAKE_POLICY_VERSION_MINIMUM` **必须
   以 cache 变量/`-D` 传**——toolchain 里的普通 `set()` 晚于第 7 行执行，无效。
2. **qtbase 5.15.2.2 包内 CMake config 烙死构建树路径**：
   `Qt5CoreConfigExtras.cmake` 引用 `${prefix}/../b//mkspecs/linux-clang`
   （configure 期构建目录，发布后不存在）→ 任何 `find_package(Qt5Core)` 致命报错。
   且该 config 用 `get_filename_component(... ${CMAKE_CURRENT_LIST_DIR}/../../../)`
   **按自身位置反推前缀** → 换位置拷贝会指错，修复副本必须放在与原包相同的相对深度。
3. **CMakeDeps 生成的 Qt5 配置不够**：能给出 `Qt5::Core/Qt5::Test` 目标，但**不带
   上游 Qt5 宏**（`Qt5CoreMacros.cmake` 的 `QT5_ADD_RESOURCES` 等），上游
   `kdev-pg/CMakeLists.txt:7` 直接用 → `Unknown CMake command "QT5_ADD_RESOURCES"`。
   （另外：一旦写了 `conan_cmakedeps_paths.cmake`，`conan_toolchain` 就不再自动
   把生成器目录放进搜索路径，`Qt5Config.cmake` 会找不到。）
   → 最终方案：**qt-prefix 镜像**（除 `lib/` 外符号链接到真实包，`lib/cmake` 做真实
   拷贝并把 `/../b//` 归一成 `/`），上游真实 config 与宏全部可用。
4. **禁用宿主 flex/bison 的写法**：`FLEX_EXECUTABLE=<tool>-NOTFOUND` **无效**
   —— `find_program` 见到 NOTFOUND 值会**重新搜索**，宿主 flex 仍被找到并重新生成
   lexer，与上游 `.ll` 用户代码不兼容（10 处
   `use of undeclared identifier 'yymore_used_but_not_detected'`）。
   必须用**空值**（`-DFLEX_EXECUTABLE=`）：已定义 → 跳过搜索，且 `IF()` 判假 →
   走上游 ELSE 分支用随包生成文件。
5. **老 flex 产物的 `register`**：随包 `kdev-pg-lexer.cc` 是 flex 2.5 时代产物，
   C++17 下 clang 把 `register` 当硬错误（19 处）→ 加 `-Wno-register` 降级。
6. **`std::hash<QBitArray>` 重定义**：Qt 5.15 已在 `qhashfunctions.h:209` 自带该
   特化且无可关闭守卫 → 上游本地特化重定义 → 唯一补丁按 `QT_VERSION < 5.15` 守卫。
7. **没有 RUNPATH 的 ELF 只能靠 `LD_LIBRARY_PATH`**：测试二进制与生成器都没有
   RPATH/RUNPATH 条目。而且 `VAR=... cmd1 && cmd2` 的**内联变量只作用于 cmd1**
   （`cd X && kdev-pg-qt ...` 会报 127）→ 必须 `sh -c '...'` 包住整条命令。
   另外 conan 的 `Environment().apply()` 在本平台实测没有传到 `self.run` 的子进程，
   故两处都改为命令行内联。

## 上游测试申报（R51）

- **清点**：`tests/CMakeLists.txt` 用 `ecm_add_test` 注册 3 个用例
  （`testlocationtable`、`testmemorypool`、`benchmarks`），只依赖 `Qt5::Core/Test`。
- **实跑**：**3/3 执行并通过**（`100% tests passed, 0 tests failed out of 3`）。
- **回填**：N = 3、N′ = 3、通过 3（无豁免、无跳过）。
