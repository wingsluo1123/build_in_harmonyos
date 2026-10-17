# kcoreaddons 6.28.0 适配笔记

## 编译环境
- **类型**: C++/CMake 共享库（KDE Frameworks 6 - KCoreAddons，libKF6CoreAddons.so）
- **编译日期**: 2026-10-16
- **编译器**: clang 15.0.4（OHOS SDK 26.0.0.18 随附工具链）
- **平台**: arm64-ohos（OHOS 6.0，ohos-aarch64-full profile）
- **状态**: built（官方 conan-verify 八门禁 Verdict PASS，见 reports/conan-verify-report.md）

## 源码（source()）
`get()` 下载 KDE Frameworks 官方 tarball 并 `strip_root=True` 解压：

- URL: `https://download.kde.org/stable/frameworks/6.28/kcoreaddons-6.28.0.tar.xz`
- sha256: `a713febee2f43bc31986d6c27d846ccab556fc7bc7c1919c3a662495720b431a`

## 适配决策
1. **KF_IGNORE_PLATFORM_CHECK=TRUE** — OHOS 不在 KDE 平台列表中（kconfig / kholidays 先例）。
2. **DT_SONAME 注入** — CMake 无 Platform/HarmonyOS 模块时 `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG`
   为空、lld 不写 DT_SONAME，消费者会把构建机绝对路径记入 DT_NEEDED；配方注入
   `-Wl,-soname,`（6.26.0.1 先例延续）。另：设备构建环境统一无版本化命名（设备卷不支持
   符号链接，平台构建链路在 generate 前剥离 VERSION/SOVERSION），已装库核查
   `SONAME libKF6CoreAddons.so`（裸名单文件），configure 期版本值不受影响（版本头文件 6.28.0）。
3. **C++20** — 上游对 `CMAKE_CXX_STANDARD` 使用 variable_watch 覆盖配置值，必须经
   `CMAKE_CXX_FLAGS=-std=c++20` 强制（编译标志最可靠；kholidays cppstd 块移除同类处置）。
4. **ECM 基线** — 6.28.0 树要求 `find_package(ECM 6.28.0 NO_MODULE)`；注册表无 ecm/6.28.0，
   采用 extra-cmake-modules/6.29.0（kholidays/6.28.0 先例），并手动设置 ECM_MODULE_PATH
   （CMakeDeps 生成的 ECMConfig.cmake 不传播该变量）。
5. **最小 KF 基线** — KCOREADDONS_USE_QML=OFF（QML 插件不属 KF 基线）、
   BUILD_PYTHON_BINDINGS=OFF（Shiboken6/PySide6 未发布）、USE_DBUS=OFF（同 6.26.0.1）。
6. **BUILD_TESTING=ON** — 上游 autotest 全量构建并以 ctest 运行：QT_QPA_PLATFORM=offscreen、
   隔离 HOME/XDG_RUNTIME_DIR、TZ=Asia/Kolkata（时间格式用例按上游 KDE 默认时区预期）、
   `--no-tests=error` 守护注册数。
7. **消费者配置透传** — `cmake_find_mode=none` + `builddirs=lib/cmake`，消费者经项目自带的
   KF6CoreAddonsConfig.cmake 解析（find_dependency(Qt6Core) 由上游维护）。

## 补丁说明（patches/0001–0006，均在 `settings.os == "OHOS"` 时应用）

| 补丁 | 目标文件 | 内容与理由 |
|---|---|---|
| 0001 | CMakeLists.txt | 注释 `ecm_install_po_files_as_qm` 调用：无 Qt6LinguistTools，不产出 .qm 翻译（6.26 同款） |
| 0002 | src/lib/CMakeLists.txt | `if (UNIX AND NOT IOS)` → `if (NOT WIN32 AND NOT IOS)`：OHOS 平台 CMake 不置 UNIX，unix 源集（kmacroexpander_unix、klistopenfilesjob_unix 等）需接通 |
| 0003 | src/lib/CMakeLists.txt | 时钟偏差引擎：`CMAKE_SYSTEM_NAME MATCHES "Linux"` 分支并入 `"HarmonyOS"`，使用 ksystemclockskewnotifierengine_linux.cpp |
| 0004 | 7 文件 / 12 hunk | OHOS autotest 差异处置：① `src/lib/CMakeLists.txt` dladdr 探测与链接：`if(UNIX)` → `if(NOT WIN32 AND NOT IOS)`，`MATCHES "Linux"` → `"Linux\|HarmonyOS"`（OHOS dladdr 不在 libc，需链接 dl）；② kdirwatch 硬链接用例按能力 QSKIP；③ kformattest 时间格式改用 QLocale::c()；④ kusertest 依赖 /etc/passwd 的用例 QSKIP；⑤ kfileutils 复合后缀（MIME）用例修正；⑥ kjsonutils LANGUAGE 回退；⑦ knetworkmountstestcanonical 符号链接能力探测：initTestCase 内创建符号链接失败（OHOS 用户卷不支持 symlink(2)）即整例 QSKIP |
| 0005 | src/lib/kaboutdata.cpp | `std::ranges::find_if` → `std::find_if`：OHOS SDK libc++（clang 15）缺 C++20 ranges 算法（kholidays std::none_of 同类） |
| 0006 | autotests/plugin/kpluginmetadatatest.cpp | copyPluginFixture 夹具读写循环（EOVERFLOW）：按上游拷贝语义重写读写循环，插件元数据用例可在 OHOS 文件系统下运行 |

## 上游测试清点（实测非推断）

- conanfile.py `build()` 内 `BUILD_TESTING=ON` + ctest 全量运行：
  **100% tests passed, 0 tests failed out of 30**
- 注册项含平台条件分支（klistopenfilesjob unix、kdirwatch INotify/QFileSystemWatcher 后端、
  plugin 元数据/工厂用例），以上游 CMake 实际注册数为准，`--no-tests=error` 守护。
- 关键输出摘录见下文「验证输出摘录」（全量日志留存本机构建会话，未随档）；官方 verify
  的复验记录（包已缓存、未触发重建）见 `reports/conan-verify-report.md`。

## 遇到的问题与解决方案

1. **KDE 官方下载链路被地区镜像劫持**：真机访问 `download.kde.org` 被跳转至 BFSU 镜像节点，
   该节点证书为 `CN=localhost / Demo SSL / WRDTech Co., Ltd.` 的演示自签证书，Python/conan
   证书校验必然失败（重试无解）；USTC 镜像亦经同节点。处置：经 **aliyun 镜像**取得同一
   tarball（字节级 sha256 与 conandata 一致），置入 conan 源码缓存
   （`core.sources:download_cache`，按 sha256 内容寻址），`source()` 离线命中；
   配方层 sha256 校验对下载来源不敏感，产物一致性不受影响。
2. **源码缓存脏标记**：先前失败下载在缓存路径留下 `.dirty` 标记，按设计触发缓存条目删除；
   清理标记后重新播种即命中（该机制属 conan 正常行为，非配方问题）。
3. **`core.sources:download_cache` 配置位置**：`core.*` 配置不允许写在 profile 或命令行
   `-c`（报 "not allowed in profiles"），只能写 `global.conf`（本机已有既有配置，直接复用）。
4. **上游 autotest 的 OHOS 差异**：见补丁 0004/0006（硬链接、符号链接、/etc/passwd、时区格式、
   MIME 复合后缀、LANGUAGE 回退、插件夹具读写循环）。
5. **符号链接能力缺失（knetworkmountstestcanonical）**：该用例以 `QFile::link` 创建符号链接为
   核心夹具；OHOS 真机可写卷（HMDFS 用户卷）不支持 `symlink(2)`（实测 `ls -l` 同款 EACCES /
   errno 13），`/tmp` 为只读挂载（EROFS-同款 errno 30），无其他候选可写卷，无法以更换测试
   目录的方式规避。处置：按能力探测——创建失败即整例 QSKIP（Qt 官方语义：initTestCase() 中
   QSKIP 跳过全部用例函数），用例构建与注册全保留，结果如实记为跳过。

## 依赖版本
- qtbase/6.11.1（Qt6Core，requires）
- extra-cmake-modules/6.29.0（tool_requires；6.28 树 ECM >= 6.28.0 下限）

全部命中制品仓（conan.cnb.cool ohpcd），无新增上游依赖。

## 验证结果（真机）

| 项 | 结果 |
|----|------|
| conan create（干净构建） | ✅ 成功（161 个 CXX 目标完整重编译，包 ID `57ffd8c720a5bfee7e8827990cd6550a49181c1b`） |
| 上游 autotest 套件（ctest） | ✅ 30/30 (100%)（见「验证输出摘录」） |
| test_package 消费者用例 | ✅ 4/4 (100%)（checks executed: 13, check failures: 0，见「验证输出摘录」） |
| 官方 conan-verify 八门禁 | ✅ Verdict PASS（G0-G4 + L2/L4/L5；`reports/conan-verify-report.md` 随档） |
| 证据文件 | `reports/conan-verify-report.md`（官方复验报告）；「验证输出摘录」为干净构建日志关键输出（全量日志未随档） |

## 验证输出摘录（干净构建）

全量构建日志留存于本机构建会话、未随档提交（平台规则禁止 PR 携带运行产物日志）；以下为
干净构建（2026-10-16）关键输出的逐字摘录：

```text
[  2%] Building CXX object autotests/CMakeFiles/autotests_static.dir/autotests_static_autogen/mocs_compilation.cpp.obj
（本包共 161 行 Building CXX object，此处省略中间行）
[ 27%] Linking CXX shared library ../../bin/libKF6CoreAddons.so
30/30 Test #30: kpluginfactorytest ...............   Passed    0.07 sec

100% tests passed, 0 tests failed out of 30

Total Test time (real) =  56.86 sec

kcoreaddons/6.28.0@ohpcd/stable: Package '57ffd8c720a5bfee7e8827990cd6550a49181c1b' built
kcoreaddons/6.28.0@ohpcd/stable: Package '57ffd8c720a5bfee7e8827990cd6550a49181c1b' created

# test_package（消费者端到端）
1/1 Test #1: test_kcoreaddons .................   Passed    0.10 sec

100% tests passed, 0 tests failed out of 1

kcoreaddons consumer E2E executor (4 cases)
== case: kaboutdata_identity
TEST PASS: kaboutdata_identity
== case: kaboutdata_authors
TEST PASS: kaboutdata_authors
== case: kformat_byte_size
TEST PASS: kformat_byte_size
== case: kstringhandler_obscure
TEST PASS: kstringhandler_obscure
checks executed: 13, check failures: 0
TEST SUMMARY: 4 passed, 0 failed
```

## 注意事项
- 消费者使用方式：`find_package(KF6CoreAddons)`（项目自带 Config，`cmake_find_mode=none`
  透传）；链接目标 `KF6::CoreAddons`。
- `.qm` 翻译不随包安装（补丁 0001）；如需翻译文件，再引入 Qt6LinguistTools 基线另行处置。
