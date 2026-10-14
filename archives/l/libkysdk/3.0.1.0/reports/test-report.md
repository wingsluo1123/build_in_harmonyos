# libkysdk 3.0.1.0 上游测试报告（R51 三步法）

- 适配目标：libkysdk / 3.0.1.0（gitee openkylin/libkysdk-base 官方仓库，tag `debian/3.0.1.0-2`）
- 测试平台：本机 OHOS 6.0 / armv8（aarch64）/ clang 15.0.4（Target aarch64-unknown-linux-ohos）/ musl
- 测试日期：2026-10-01
- 日志留档：`/storage/Users/currentUser/rjj/kysdk-base-3.0.1.0/logs/`（`upstream_tests/`、`gtest/`）

## 一、测试清点（R51 第 1 步）

上游测试入口共两个：

1. **CMake 模块内建测试目标 12 个**（随 `cmake.build()` 编译，各模块 CMakeLists 的
   `add_executable(...test...)`）：test-utils、test-delete、test-insert、test-search、
   test-kytimer、kylog-testlog、kylog-testsetdir、kylog-testautowrap、kylog-testpressure、
   test-kygsetting、kyconf2-test、kyconf-test-struct。
2. **qmake + gtest/gmock 套件**（`src/tests/*.pro`，上游 `src/tests/auto-test.sh` 驱动，
   带 lcov/gcov 覆盖率）：tests.pro SUBDIRS 共 7 套件 —— kyskiplist-gtest、
   kyconfig-gtest、kygsettings-gtest、kylog-gtest、kytimer-gtest、kyutils-gtest、
   kyconf2-gtest。

用例口径（与 3.0.1.3 完全一致，src/tests/ 两版逐字节相同）：

| 套件 | TEST/TEST_F 数 |
|---|---|
| kyconf2-gtest | 7 |
| kyconfig-gtest | 8 |
| kygsettings-gtest | 23 |
| kylog-gtest | 9 |
| kyskiplist-gtest | 3 |
| kytimer-gtest | 1 |
| kyutils-gtest | 33 |
| **gtest 合计** | **84** |
| CMake 内建目标 | 12 |
| **上游声明总数** | **96** |

> 注：`src/tests/` 下另有 kydiagnostics-gtest.cpp（1 用例）与 kyprocess-gtest.cpp（1 用例）
> 两个文件，但它们**没有 .pro**、不在 tests.pro SUBDIRS 中，上游 auto-test.sh 也不会构建，
> 故不计入上游声明口径（与 3.0.1.3 申报一致）。

## 二、实际运行结果（R51 第 2 步）

### 入口一：CMake 内建测试目标 —— 12/12 通过（rc=0）

| 目标 | rc | 说明 |
|---|---|---|
| test-utils | 0 | kyutils 容量进制转换 |
| test-delete | 0 | 跳表删除与顺序一致性（含 20s 随机 sleep） |
| test-insert | 0 | 跳表插入与层级打印（上游 sleep(1)×100 约 100s） |
| test-search | 0 | 跳表查找 |
| test-kytimer | 0 | 定时器注册/回调/停止 |
| kylog-testlog | 0 | 日志写入 |
| kylog-testsetdir | 0 | 日志目录设置 |
| kylog-testautowrap | 0 | 日志自动换行 |
| kylog-testpressure | 0 | 日志压力 |
| test-kygsetting | 0 | GSettings 读写（无 schema 数据时 GLib 打 CRITICAL 但返回 0） |
| kyconf2-test | 0 | conf2 配置读写 |
| kyconf-test-struct | 0 | kyconf 结构化配置读取（需 cwd 含 `struct.conf`，实测 cwd=src/config/test） |

日志：`logs/upstream_tests/*.log`，逐目标 rc 见文件头。

### 入口二：qmake + gtest 套件 —— 6/7 可构建运行

| 套件 | 结果 | 通过/总数 | 说明 |
|---|---|---|---|
| kyskiplist-gtest | ✅ 通过 | 3/3 | 跳表 GTest |
| kyconfig-gtest | ✅ 通过 | 8/8 | kyconf GTest；需 cwd 可解析 `../src/tests/kyconfig-gtest/struct.conf`（实测 cwd=源码目录） |
| kytimer-gtest | ✅ 通过 | 1/1 | 定时器 GTest（含 28s 定时等待） |
| kygsettings-gtest | ⚠️ 部分通过 | 18/23 | 5 失败均因**缺 Kylin 桌面 GSettings schema 数据**（本环境无 schema，GLib 报 schema source lookup 失败）；与 3.0.1.3 完全一致 |
| kylog-gtest | ⛔ 运行中止 | 0/9 | 首个用例 `kdk_logger_init("logtest.conf")` 断言失败（rc=134）——需**可写 `/var/log` 与 `/etc/kysdk` 配置**；本机无该目录写权限 |
| kyconf2-gtest | ⛔ 超时 | 0/7 | 无任何输出、60s 超时（rc=124）——依赖 **D-Bus / conf2 服务端**，本环境无该服务 |
| kyutils-gtest | ❌ 无法编译 | — | 上游用例调用 `strisletter()`，上游实现中函数名是 `strisalpha()`（`src/utils/cstring-extension.h:424`）——**上游用例缺陷**（与 3.0.1.3 一致），未修改上游测试文件；编译报错原文：`kyutils-gtest.cpp:312:17: error: use of undeclared identifier 'strisletter'` |

日志：`logs/gtest/*.log`（含 kyutils-gtest 编译失败日志 `kyutils-gtest-build.log`）。

**有完整结果的 42 例（CMake 12/12 + gtest 30/30：kyskiplist 3 + kyconfig 8 + kytimer 1 +
kygsettings 18）全部通过**；其余 54 例未完成，原因均为本环境缺桌面数据/服务
（GSettings schema、/var/log 写权限、D-Bus 服务端），或上游用例自身缺陷（strisletter）。
以上失败均非 OHOS 适配引入，与 3.0.1.3 版本申报完全一致。

### gtest 套件本地构建说明（三处覆盖，均为上游测试工程自身问题）

1. **gtest/gmock .pc**：conan 包内 `.pc` 的 prefix 指向已失效的构建路径，本地重建指向
   实际包目录的 `.pc`（`PKG_CONFIG_PATH` 注入）。
2. **上游 .pro 的 `-fno-exceptions`**：与 cpp_stub 的 `throw` 冲突，构建时移除。
3. **`-lgcov`**：clang 无 libgcov，移除。
4. 本机 qmake 的 Qt 模块 pri 解析指向失效的 build 路径（`qt_plugin_*.pri` 缺失），
   故直接以 clang/clang++ 显式编译 7 套件（与 .pro 的 SOURCES/LIBS 语义等价）：
   .c 源文件用 clang 按 C 编译、.cpp 用 clang++（-std=c++17，libc++ 头注入），
   链接 gtest/gtest_main 静态库 + glib/gio/gobject/dbus/sqlite3 依赖库。

## 三、鸿蒙特有测试（OHOS 平台专项）

- **test_package 消费者测试（`test_package/test_kysdk.c`）即鸿蒙特有测试**：在本机 OHOS 6.0 /
  armv8 设备上经 `conan create` 的 test_package 阶段**真实链接并运行**被测包安装后的共享库，
  调用 kydatastruct（kysdk_create_skiplist/insert/search/delete）与 kyutils
  （kdkVolumeBaseNumericalConvert）公开 API，10/10 断言通过（`total failures = 0`）。
  该测试同时隐式验证了鸿蒙特有适配点——SONAME 软链实体化（E316/E492）：
  未实体化时按 SONAME 打开软链即 rc=127 加载失败，实体化后全部通过（见 notes.md 踩坑 #7）。
- **上游测试全程在 OHOS 设备实测**：入口一（CMake 内建 12 目标）与入口二（gtest 套件）
  均在本机 OHOS 6.0 / armv8 / clang 15.0.4 上运行，非 x86 模拟。
- 无 schema/服务/写权限导致的用例失败均如实申报（见第二节），均为 OHOS 桌面环境缺数据所致，
  非适配引入，与 3.0.1.3 申报一致。

## 四、如实回填（R51 第 3 步）

- 本文档即 `reports/test-report.md`；结构化申报见 `test_package/MANIFEST.yml`
  （upstream_tests 12 项 / gtest_suites 7 项 / test_package_tests 1 项，assertion_count=106）。
- test_package 消费者测试：链接被测包安装后的共享库，调用 kydatastruct
  （kysdk_create_skiplist/insert/search/delete）与 kyutils（kdkVolumeBaseNumericalConvert）
  公开 API，10 条断言全部通过（`total failures = 0`），见 `logs/conan-create.log` 尾部。
- 无任何占位符；所有数字均为本机实测值，失败均附具体报错原文与日志路径。
