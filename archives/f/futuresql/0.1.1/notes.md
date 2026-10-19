# futuresql 0.1.1 适配笔记

## 编译环境

- 构建系统: cmake (CMake 4.1.2, Makefile generator)
- 编译日期: 2026-10-18
- 编译器: clang/clang++ 15 (OHOS SDK, `--target=aarch64-linux-ohos`, libc++, C++20)
- Conan: 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（os=OHOS, os.version=6.0, arch=armv8, Release）
- 状态: built（conan-verify G0-G4 PASS，未 upload）

## 编译步骤

```bash
conan create archives/f/futuresql/0.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方要点（`conanfile.py`）：

- `source()` 从 conandata.yml 的四个 https 源下载 `futuresql-0.1.1.tar.xz`
  （sha256 `e44ed8d5a9618b3ca7ba2983ed9c5f7572e6e0a5b199f94868834b71ccbebd43`）。
- `requires("qtbase-sql-dbus/6.11.1")`：唯一带 Qt6Sql（`FEATURE_sql=ON`）和
  QSQLITE 驱动插件的 Qt6 构建。
- `tool_requires("ecm/6.26.0")`；`test_requires("qcoro/0.13.0")`：上游测试的
  协程体需要 `QCoro6::Core`，test_requires 不会传播给消费者。
- `generate()` 写入 `conan_cmakedeps_paths.cmake`（qtbase-sql-dbus 的
  `lib/cmake`、`lib`、`include` 置顶；真实 qcoro 包 `lib/cmake` 排在
  CMakeDeps 生成目录之前），并设置 `ECM_MODULE_PATH`、`Qt6_DIR`、
  `QT_MAJOR_VERSION=6`。
- `BUILD_TESTING=ON`：上游 `sqlitetest` 在 `build()` 内通过 ctest 执行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(Qt6 COMPONENTS Core Sql)` 找不到 Qt6Sql | 基础 qtbase/6.11.1.1 以 `FEATURE_sql=OFF` 构建；只有 qtbase-sql-dbus/6.11.1 提供 Qt6Sql 与 QSQLITE 插件 | 配方依赖 qtbase-sql-dbus；路径文件中排除基线 qtbase，并把 qtbase-sql-dbus 的 `lib/cmake`/`lib`/`include` 置顶 |
| 2 | configure 报 `Unknown CMake command "qcoro_enable_coroutines"` | CMakeDeps 生成的 `QCoro6Config.cmake` 只声明 Conan 组件目标，不含上游 `QCoroMacros.cmake` 里的宏；上游顶层 CMakeLists 在 `find_package(QCoro6)` 之后调用该宏 | 把真实 qcoro 包的 `<pkg>/lib/cmake` 插到生成目录之前，使 `find_package(QCoro6)` 走真实配置链 `QCoro6Config -> QCoro6CoreConfig -> find_dependency(QCoro6Coro) -> QCoroMacros.cmake` |
| 3 | 链接 `libfuturesql6.so` 时 CMake 报 `failed to create symbolic link ... Permission denied`（探测实测 errno=EACCES，即 Permission denied） | 设备存储（HMDFS）不支持 symlink(2)；上游 `SOVERSION 0` 让 `cmake_symlink_library` 必须创建 `libfuturesql6.so -> libfuturesql6.so.0` 软链 | `generate()` 运行期探测 symlink 能力；不可用时设 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`（保留注入的 `-Wl,-soname,`），产出单一未版本化的 `libfuturesql6.so`，ELF 仍带 `DT_SONAME`（DRAFT-7341 libtiff 先例）。软链可用的主机上保持上游版本化布局 |
| 4 | CMake 无 Platform/HarmonyOS 模块，共享库无 `DT_SONAME` | 原生构建落在 Generic 平台模块，`CMAKE_SHARED_LIBRARY_SONAME_*` 为空 | generate() 注入 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` / `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG = -Wl,-soname,` |
| 5 | ECM 的 `KDEInstallDirs6` 在 configure 期执行 `Qt6::qtpaths` 失败 | qtpaths 需要运行时库路径 | 构建环境把 qtbase-sql-dbus 的 `bin`、`lib`、`plugins` 加入 PATH/LD_LIBRARY_PATH/QT_PLUGIN_PATH，并前置 `/system/lib64` 与 SDK llvm lib |

## 源码修改

无。本版本不使用任何补丁（`patches_applied: []`），适配全部通过 Conan
generate 阶段变量与运行期能力探测完成。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| qtbase-sql-dbus | 6.11.1 | Qt6Core/Qt6Sql + QSQLITE 驱动插件（运行依赖） |
| ecm | 6.26.0 | KDE CMake 模块（build tool_require） |
| qcoro | 0.13.0 | 上游测试协程支持（test_require） |
| dbus / expat | 1.14.10 / 2.8.Z | qtbase-sql-dbus 传递依赖 |

## 上游测试双口径台账（R51）

清点对象：上游源码包 `futuresql-0.1.1/tests/`（1 个测试源文件
`sqlitetest.cpp` + `migrations/` 数据目录），CMake 通过 `add_subdirectory(tests)`
注册 1 个 CTest 用例 `sqlitetest`。

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total（源码声明测试总数） | 2 个 QTest 槽 | `tests/sqlitetest.cpp` 的 `private Q_SLOTS`：`testDeserialization`、`testMigration`；槽内通过 `QCoro::Task` 协程体执行数据库操作 |
| configured_executable_total（当前配置实例化可执行用例） | 1 个 CTest 用例 | `ctest -N` 仅注册 `sqlitetest`（两个槽在同一可执行内） |
| executed_passed_total | 2/2 槽（1/1 CTest 用例） | 真机 `conan create` 内 `ctest --output-on-failure --no-tests=error`，输出 `1/1 Test #1: sqlitetest ... Passed`，`100% tests passed, 0 tests failed out of 1` |
| 失败 / 未运行 / 未实例化 | 0/0/0 | 无排除项 |

- 通过率口径：源码声明槽 2/2（100%）；CTest 注册用例 1/1（100%）。
- `testDeserialization` 覆盖自定义/默认反序列化器（`getResult`/`getResults`）；
  `testMigration` 覆盖 `runMigrations`（`tests/migrations/` 目录）。
- 消费者用例（`test_package/test_package.cpp`，8 项检查）单独计数，不计入上游 N。

## 验证结果

```text
$ conan create archives/f/futuresql/0.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
...
1/1 Test #1: sqlitetest .......................   Passed    0.06 sec
100% tests passed, 0 tests failed out of 1
...
======== Testing the package: Executing test ========
futuresql/0.1.1@ohpcd/stable (test package): RUN: ./test_package
TEST PASS: DatabaseType::SQLite maps to the QSQLITE driver
TEST PASS: packaged QSQLITE driver opens the database
TEST PASS: CREATE TABLE created the test table (verified via sqlite_master)
TEST PASS: INSERT with a bound QVariant stored one row (verified via count(*))
TEST PASS: getResults returns exactly one row
TEST PASS: getResults deserializes the integer column
TEST PASS: getResults deserializes the text column
TEST PASS: getResult returns the first row as a std::optional
TEST SUMMARY: PASS (0 failure(s))
```

```text
$ python3 scripts/ohc-run.py conan-verify futuresql 0.1.1
G0: PASS  G1: PASS  G2: PASS  G3: PASS  G4: PASS
L2: PASS  L4: PASS  L5: PASS
✅ 配方验证通过: futuresql 0.1.1
```

注：conan-verify 对无 cache 路径的 L2/L4/L5 打印“跳过”但仍计入 PASS 行，
G4 的“无法找到程序包 ID”也是同一原因；实际证据为 conan create 日志中的
`Package 'fe643a6a365d349533fe6eecb9772405e9423933' created` 与下方设备包
目录的产物核验。

产物核验（设备包目录）：

```text
lib/libfuturesql6.so
  SONAME  libfuturesql6.so
  NEEDED  libQt6Sql.so.6, libQt6Core.so.6, libc++_shared.so, libc.so
include/FutureSQL6/{ThreadedDatabase, futuresql_export.h, threadeddatabase.h, threadeddatabase_p.h}
lib/cmake/FutureSQL6/{FutureSQL6Config.cmake, FutureSQL6ConfigVersion.cmake, FutureSQLTargets.cmake, FutureSQLTargets-release.cmake}
  IMPORTED_SONAME_RELEASE "libfuturesql6.so"；无 IMPORTED_NO_SONAME
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Conan 2 配方（cmake 构建，含路径文件生成/运行环境/上游测试） |
| `conandata.yml` | 源码 URL 列表 + sha256 |
| `test_package/` | 消费者 E2E（CMakeLists.txt、test_package.cpp、conanfile.py、MANIFEST.yml） |
| `manifest.yaml` | 版本编译元数据 |
| `notes.md` | 本笔记 |
| `reports/conan-verify-report.md` | conan-verify 报告（脱敏） |

## 注意事项

- futuresql 0.1.1 已归档到 KDE Attic；`download.kde.org/stable/futuresql` 会重定向，
  conandata 列出 gwdg/NJU/USTC 三个 Attic 镜像与官方 URL，sha256 一致。
- 消费者必须使用 qtbase-sql-dbus（而非基础 qtbase）作为 Qt6 来源；使用基础
  qtbase 时 `find_dependency(Qt6Sql)` 会失败。
- 设备 HMDFS 不支持 symlink：任何带 `VERSION`/`SOVERSION` 的共享库项目都需要
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`（能力探测）才能链接成功。
