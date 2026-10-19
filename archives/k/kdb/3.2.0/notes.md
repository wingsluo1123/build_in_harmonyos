# kdb 3.2.0 鸿蒙 PC 适配笔记

上游: <https://invent.kde.org/office/kdb>（KDE Attic 托管的独立 KDb 项目，与 Kexi 共用同一数据库层）
版本: 3.2.0（Qt5/KF5 时代的稳定版 tarball）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15，CMake 4.1.2）

## 一、适配结论

产物（install 树实测）：

- `libKDb3.so` —— 主库。上游 `set_coinstallable_lib_version` 对 3.x 稳定主版本
  特判 SOVERSION 4（tarball 常规输出 libKDb3.so.4.2.0）；本包按家族规则以
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` 输出**裸名** `libKDb3.so`、
  `DT_SONAME=libKDb3.so`（W3 CI L5 SONAME 门禁口径）；
- 驱动插件（MODULE，装于 `lib/plugins/kdb3/`）：
  `kdb_sqlitedriver.so`（sqlite3 driver）+ `sqlite3/kdb_sqlite_icu.so`
  （其 ICU 扩展）；
- `bin/kdb3_sqlite3_dump` —— 上游默认安装的 dump CLI；
- `include/KDb3/*.h`（63 个头，含 sdc 生成头）、`lib/cmake/KDb3/`
  （KDbConfig/KDbTargets 等 5 个 .cmake，导出名=无命名空间的 `KDb`）、
  `KDb3.pc`、`qt_KDb3.pri`。

平台适配 4 个补丁（`patches/0001`–`0004`，`patch_type: portability`，
均无平台条件编译宏、无条件应用，R8 合规；两个 CMake 版本守卫、
一个链接序、一个 ctest 包装）：

1. **CMake 4 的 CMP0059（0001）**：`SetKDbCMakePolicies.cmake` 无条件
   `cmake_policy(SET CMP0059 OLD)`，CMake 4.x 已移除 OLD 行为=硬错
   （真机 4.1.2 实锤）——包 `CMAKE_VERSION VERSION_LESS "4.0"` 守卫；
   本树 `add_definitions()` 调用点都在创建其目标的同一目录，NEW 行为等价；
2. **静态 ICU 链接序（0002）**：仓内自带 `cmake/modules/FindICU.cmake`
   只建裸 imported 库、无组件间依赖边（共享库场景靠 DT_NEEDED 自然解析），
   而 ohpcd 的 icu 是**纯静态**、SQLite ICU 扩展又 `-Wl,--no-undefined`
   链接——补丁请求 `data` 组件并追加 `i18n → uc → data` 链；
3. **flex 预生成扫描器的 `register`（0003）**：`src/parser/generated/sqlscanner.cpp`
   用 `register` 存储类，cppstd=17 下即 `-Wregister` error（树内既有
   `-Wno-deprecated-register` 只覆盖旧措辞）→ 扫描器编译 flags 加 `-Wno-register`；
4. **HeadersTest 脚本的 sh 包装（0004）**：ctest 直接 execve
   `headers_test.sh`，而目标镜像对 `/storage` 上的 shebang 脚本拒发
   execve（文件带可执行位仍 `Permission denied`；同树 ELF 可直跑）
   ——`add_test` 包成 `sh <script>`，语义等价且可移植。

测试口径：

- 上游套件：**14 项 / 100% 通过**（`BUILD_TESTING=ON` 在 `conan create`
  内真实执行；12 个 KDb API 测试目标 + SqlParserTest + HeadersTest
  安装头自包含编译检查——ctest 名实录：ConnectionOptionsTest、
  ConnectionTest、DateTimeTest、DriverTest、ExpressionsTest、
  MissingTableTest、OrderByColumnTest、QuerySchemaTest、KDbTest、
  HeadersTest（198.52s，120 TU）、IdentifierTest、
  StaticSetOfStringsTest、UtilsTest、SqlParserTest）；
- 消费者测试（`test_package/`，R51 第三步）：**45 个检查点全过**——真实驱动
  插件发现、连接生命周期、DDL/insertRecord/查询/事务 API、卸载清理，
  外加 ELF 三查（裸 DT_SONAME、DT_RUNPATH、.codesign）；
- 真机八门禁 **Verdict PASS**（2026-10-17，`reports/conan-verify-report.md`）。

## 二、问题与处置

### 问题 1：CMake 4 硬错（CMP0059 OLD）——补丁 0001

真机 CMake 4.1.2 在 configure 早期即硬错退出。补丁只加版本守卫
（`if(CMAKE_VERSION VERSION_LESS "4.0")`），不触平台宏；CMake ≥ 4 下
CMP0059 只剩 NEW 行为，本树调用点均在目标所在目录内，切换等价。

### 问题 2：静态 ICU 的未定义符号——补丁 0002

表现：`libKDb3.so` 链接期挂 `icudt76_dat` / `_u_*`（`-Wl,--no-undefined`）。
根因：仓内 `FindICU.cmake`（根 CMakeLists line 3 就把自家 `cmake/modules`
放 CMAKE_MODULE_PATH 首位）只建裸 imported lib；共享 ICU 场景依赖
DT_NEEDED 自然解析，静态 ICU 不行。处置：请求 `data` 组件 +
INTERFACE_LINK_LIBRARIES 追加 `i18n → uc → data`。

### 问题 3：预生成扫描器的 register——补丁 0003

`sqlscanner.cpp` 为 flex 预生成、仍用 `register`；cppstd=17 下 clang
报 `-Wregister` error（真机实测 `-Wno-register` 可消除）。只改编译
flags，不动生成源。

### 问题 4：shebang 脚本拒 execve——补丁 0004

真机探针实锤：`/storage/Users/currentUser` 上文件一律显示 770
（owner=file_manager），`chmod` 被文件系统静默吞掉；构建进程 uid
非 owner 非组。脚本直发 `./x.sh` = RC126 Permission denied，
`sh x.sh` = RC0；ELF（含测试二进制）可直跑。→ HeadersTest 的
`add_test` 包 `sh`。（配方里曾试的 chmod 兜底已删——无效码不留。）

### 问题 5：CMAKE_SYSTEM_NAME=Linux（toolchain conf，无补丁）

OHOS Conan toolchain 把 `os=OHOS` 映成 `CMAKE_SYSTEM_NAME=HarmonyOS`，
CMake 无对应 platform module：`UNIX` 不定义、构建被标 cross-compiling。
后果 ①`KDECMakeSettings` 的 POSIX RPATH 段不生效；
②ECM 只在**非** cross-compiling 时注册上游 ctest（14 项全丢）。
强制 Linux 平台（OHOS PC 同 libc / 同 clang 驱动）恢复 `UNIX=1` 与
原生 ctest 注册。

### 问题 6：`metainfo.yaml` 缺失——KF_IGNORE_PLATFORM_CHECK（无补丁）

根 CMakeLists include `KDEFrameworkCompilerSettings` →
ECM 的 `KDEMetaInfoPlatformCheck` 在 include 期就
`file(STRINGS metainfo.yaml ...)`，而 3.2.0 发布 tarball **不带**
metainfo.yaml → configure 读文件失败。置 `KF_IGNORE_PLATFORM_CHECK=TRUE`
同时跳过文件读取与平台比对（ECM 6.26 源码核实）。

### 问题 7：★ HeadersTest 嵌套项目的 CMAKE_PREFIX_PATH 分隔符（配方修复，一行）

**现象**：HeadersTest 的嵌套 `cmake ../app` 在 `find_package(ECM)` 处
失败（"Could not find a package configuration file … ECMConfig.cmake"），
而 ECM 包本体、嵌套依赖链均无问题（逐一排除）。

**根因（真机 CMake 4.1.2 逐层实证）**：**环境变量** `CMAKE_PREFIX_PATH`
按**平台路径分隔符**（unix `:`）拆分，**不是** CMake 的 `;` 列表——
配方原用 `";".join(search_paths)` 把 stage+ecm+qtbase+kcoreaddons5+icu+
sqlite3 六个前缀拼成一串，被当作**单个无效前缀**（`--debug-find` 实录：
整串列为一条搜索路径）。A/B 证据矩阵（同一嵌套 configure）：

| 形态 | 结果 |
|---|---|
| env 单条目 | ✅ 找到 |
| env `;` 多条目 | ❌ 全灭（本单原实现） |
| env `:` 多条目 | ✅ 找到 |
| `-DCMAKE_PREFIX_PATH=a;b`（缓存变量=真 cmake 列表） | ✅ 找到 |

**处置**：一行 `os.pathsep.join(search_paths)`。修复后 120 个头 TU 全量
编译通过（手动整跑 `100% Built target HeadersTest`），随后 attempt 8
的 `conan create` 内 ctest **14/14 全过**。附带实证：env 初始化的
CMAKE_PREFIX_PATH **不写入 CMakeCache**（缓存缺席≠env 缺席）。

### 问题 8：ctest 二进制找不到 libkdbtestutils.so（配方修复）

9 个 DB 套件 + SqlParserTest 首跑全挂 `Error loading shared library
libkdbtestutils.so`：helper 库在构建树 `<build>/autotests/`，而
`CMAKE_BUILD_WITH_INSTALL_RPATH=ON`（E537）使二进制无 build 树 RPATH。
→ `_run_upstream_tests()` 把 `<build>/{autotests,src,lib}` prepend 进
LD_LIBRARY_PATH（`_runtime_env` 同挂 `{src,lib,bin}`）。

### 问题 9：HeadersTest 的构建期 install + 嵌套最低版本（配方）

`headers_test.sh` 按 `$builddir/install_manifest.txt` 逐头编译，manifest
由**构建期 install** 生成 → `build()` 在 `cmake.build()` 与 ctest 之间
向 `<build>/stage` 装一次（120 个头 TU 的编译对象，真机日志逐行计数）。嵌套项目声明
`cmake_minimum_required(2.8.12)`，CMake 4.1.2 对 <3.5 硬错 →
`CMAKE_POLICY_VERSION_MINIMUM=3.5` **env 与 cache 双设**（env 供嵌套
configure 用，cache 供本树 `cmake_minimum_required(3.0)` 用）。

### 问题 10：PYTHON_EXECUTABLE 钉死（配方）

配置期 `KDbCreateSharedDataClasses` 用
`find_package(PythonInterp 2.6)` + `execute_process` 跑 `tools/sdc.py`
生成 `*.shared.h → *.h`（`KDbVersionInfo.h` 等即生成头）。
预置 `PYTHON_EXECUTABLE=sys.executable` 跳过宿主搜索（也规避 CMake 4
对 PythonInterp 的移除）。

### 问题 11：sqlite3 钉路径（配方）

`SQLITE_INCLUDE_PATH / SQLITE_EXT_INCLUDE_PATH / SQLITE_LIBRARIES` 钉到
conan sqlite3 包；其 `find_program(sqlite3)` shell 探针无对象可跑——
唯一被检查的选项是 OMIT_LOAD_EXTENSION，而 conan sqlite3 开
load-extension，探针结果两种途径均无害。

### 问题 12：ECM 查找时序（配方）

根 CMakeLists **line 2** 就 `find_package(ECM)`（`project()` 之前），
而 CMake 只在首个 `project()/enable_language()` 读 toolchain 文件 →
`ECM_DIR` / `ECM_MODULE_PATH` 必须走 `tc.cache_variables`（conan 转 `-D`
上命令行才在 line 2 可见）。ecm 是 tool_requires（build context），
CMakeDeps 不会把其 share/ECM 树接进 host 前缀路径，需显式给。

### 问题 13：E537 家族手段 + 构建并行（配方，无补丁）

`CMAKE_BUILD_WITH_INSTALL_RPATH=ON`（OHOS 拒绝 mmap PROT_EXEC 被改写过的
ELF；按最终 install RPATH 链接则安装期无可改写），其后每个打包 ELF 用
`llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1`
重签；`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + SONAME flags 出裸名；
`CMAKE_BUILD_PARALLEL_LEVEL=1`（HMDFS 拒 make jobserver fifo，EPERM）；
host 工具与测试期把 `/system/lib64` prepend 进 LD_LIBRARY_PATH 让
匹配的 libc++ 胜出（krunner5/kcoreaddons5 先例）。

## 三、依赖解析

- `qt5-qtbase/5.15.2.2`（`force=True`：5.15.2 是 `-no-widgets` 残桩，
  KDb 需要 Widgets）+ `kcoreaddons5/5.116.0.1`（`find_package(KF5 …
  CoreAddons)` 经 ECM 6.26 的 `find-modules/FindKF5.cmake` 转发到
  `KF5CoreAddons` CONFIG；不走 KF5Config 伞包）+
  `icu/76.1`（静态，i18n/uc/data）+ `sqlite3/3.49.1`；
- build: `ecm/6.26.0`（tool_requires）；
- 传递闭包（qt5 系）：dbus/1.14.10、expat/2.8.2、zlib/1.3.1、icu、sqlite3。

## 四、真机验证

- 全量干净构建（`conan create`，`ci/conan/profiles/ohos-aarch64` 双端，
  `--user=ohpcd --channel=stable`）：rc=0；
  - 上游 CTest：**14/14 通过**（含 HeadersTest：嵌套 configure +
    120 个头 TU 串行编译 + 链接，全绿）；
  - 消费者 test_package：**SUMMARY: 45 passed, 0 failed**（含
    `libKDb3.so` 裸 DT_SONAME / DT_RUNPATH / .codesign 三查）；
- 八门禁：G0/G1/G2/G3/G4 ✅ PASS（L2/L4/L5 按设备侧口径跳过），
  **Verdict PASS**，报告 `reports/conan-verify-report.md`。
