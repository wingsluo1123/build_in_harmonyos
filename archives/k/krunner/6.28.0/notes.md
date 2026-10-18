# krunner 6.28.0 鸿蒙 PC 适配笔记

上游: <https://invent.kde.org/frameworks/krunner>
版本: 6.28.0（KDE Frameworks 6.28 发行版）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

构建产物：`lib/libKF6Runner.so`（KF6Runner 库：AbstractRunner 基类 /
QueryMatch / RunnerSyntax / RunnerContext 值语义、RunnerManager 插件编排
与 D-Bus remote-runner 协议）。上游 6.28.0 只安装这一个 SHARED 目标；
runner 插件模板树（`templates/`）是源材料，无构建目标。

适配要点：6 个补丁（`0001` 降 KF_DEP_VERSION、`0002` 可重定位基名
SONAME 链接、`0003` KWaylandExtras 能力探测、`0004` libc++15 ranges
兼容、`0005` autotest fixture 安装加固与诊断、`0006` autotest fixture
改为直写安装——CI 上 `QFile::copy` 静默失败），全部经 conandata.yml
声明并由 `apply_conandata_patches` 应用；`BUILD_TESTING=ON`，上游 7 个
autotest 目标全部构建、全部进入真机 ctest。

## 二、问题与处置

### 问题 1：ohpcd 的 KF6 依赖栈止步 6.26.0（补丁 0001）

上游要求 KF6 >= 6.28.0（`KF_DEP_VERSION 6.28.0`）。ohpcd 制品仓的 KF6
stack 止步 6.26.0：kconfig / kcoreaddons / kwindowsystem 有 .1 修复版，
ki18n / kitemmodels 停在 6.26.0（无 .1）。**处置**：只降
`KF_DEP_VERSION` 一行到 6.26.0；`find_package(ECM 6.28.0)` 线不动——
extra-cmake-modules/6.29.0（tool 包）满足它。

### 问题 2：KF6 库无 DT_SONAME，绝对路径链接把机器私有路径烧进 DT_NEEDED（补丁 0002）

发布的 KF6 库不带 DT_SONAME（其导出 targets 带
`IMPORTED_NO_SONAME=TRUE`），按绝对 Conan 缓存路径链接会把机器私有
路径烧进 `libKF6Runner.so` 的 DT_NEEDED（非可重定位，E537）。
**处置**（kscreenlocker 6.7.2 `0008` / kpackage 6.26.0.1 `0005` 先例）：

- lld 按命令行原样记录库名，因此五个直接依赖（CoreAddons / ConfigCore /
  I18n / ItemModels / WindowSystem —— 源码实际消费的组件）改按
  `-l:libKF6Xxx.so` 精确文件名链接（裸基名），依赖目录以
  `target_link_directories(... PRIVATE)` 挂给 KF6Runner；
- `Qt6::DBus` / `Qt6::Gui` 保持 PRIVATE 走导入目标——Qt6 库有真
  versioned SONAME；配方首版（真机 round 1 实录）把 Qt6::DBus 从链接
  列表删除后 dbusrunner.cpp 缺 `<QDBusArgument>`（该组件无其他提供者），
  遂成此最终形态；
- `KF6::CoreAddons` 留 INTERFACE（公共头 `abstractrunner.h` /
  `runnermanager.h` include `<KPluginFactory>` / `<KPluginMetaData>`；
  包内 `KF6RunnerConfig.cmake` 已有 `find_dependency(KF6CoreAddons)`，
  按名字导出、绝不绝对路径）；
- 离开链接行的依赖其使用需求（include 目录 / 定义）按
  `INTERFACE_LINK_LIBRARIES` 传递闭包拷贝（`_kr_walk`），每个
  `get_target_property` 带 `-NOTFOUND` 哨兵门（KDE targets 文件只设
  per-config 的 `IMPORTED_LOCATION_RELEASE`，非空哨兵串会被朴素
  `if(NOT var)` 误判为"已设置"）；
- 平台模块无 soname flag 时直传 `-Wl,-soname,libKF6Runner.so`（Linux
  有平台 flag 时跳过，保住上游版本化行为）。

### 问题 3：`<KWaylandExtras>` 无条件 include（补丁 0003）

`src/dbusrunner.cpp` 无条件 include `<KWaylandExtras>`，但 kwindowsystem
只在带 Wayland 支持构建时才发布该头（激活令牌 API）——ohpcd 的
6.26.0.1 包内没有它（真机 `'KWaylandExtras' file not found` 实录）。
消费该头的块本身已由 `KWindowSystem::isPlatformWayland()` 运行时门控。
**处置**：`__has_include(<KWaylandExtras>)` 能力探测（C++17 原生特性、
无平台宏，符合任务审查的平台宏禁令）——头缺失处整块编译出、
`run()` 走与既有非 Wayland 分支相同的路径；其余环境保持上游行为。

### 问题 4：libc++ 15 的 ranges 算法默认禁用（补丁 0004）

`autotests/threadingtest.cpp` 调 `std::ranges::all_of`。OHOS SDK 的
libc++ 15 默认 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`（ranges 算法默认
关闭），`-std=c++20` 下也不解析（真机 `no member named 'all_of' in
std::__n1::ranges` 实录；SDK clang++ 独立探针证实
`-D_LIBCPP_ENABLE_EXPERIMENTAL` 可解锁，但那会全树翻转实验库行为，
不取）。全树唯一一处 ranges 用法。**处置**：改写为语义等价的短路
迭代器对重载 `std::all_of(matches.cbegin(), matches.cend(), pred)` +
补 `<algorithm>` include（此前靠传递包含）。

### 问题 5：4 个上游 autotest 需要活的会话 D-Bus

`dbusrunnertest` / `runnermanagersinglerunnermodetest` /
`runnermanagertest` / `threadingtest` 经 `krunner_configure_test` 挂
`testremoterunner`（D-Bus adaptor helper），需要会话总线。配方
`_start_session_bus` 用 dbus/1.14.10.3（tool 包）的 dbus-daemon 自起
会话总线（unix EXTERNAL + getpwuid shim，TCP/ANONYMOUS 兜底）。

检视与复核阶段定位了两层失败原因并在本 head 修复：**（a）** shim 经
`copy()` 导出多嵌套一层（落成 `es/test_shim/test_shim/ohos_nopw.c`），
且 `_build_bus_shim()` 只从缓存构建中不含它的 `recipe_folder` 取源——
shim 从未被编入，unix 路的 EXTERNAL 握手必败；**（b）** daemon 启动
环境未把自身包的 `lib` 目录置于 `LD_LIBRARY_PATH` 之首，环境里的另一
份 libdbus-1.so.3 被先行解析且缺 daemon 所需符号，daemon 在打印地址
前即死于重定位错误（真机 `Error relocating .../dbus-daemon: dbus_free:
symbol not found` 实录）。**处置**：`export_sources` 改
`shutil.copytree` 落单层（kcoreaddons5 5.116.0.1 先例）；shim 查找跨
`source_folder` / `export_sources_folder` / `recipe_folder` 三基并在
缺失时显式 warn（不再静默返回）；daemon 环境把 dbus 包 `lib` 目录钉在
`LD_LIBRARY_PATH` 首位（其先于 DT_RUNPATH 被搜索）。修复后本 head
真机会话总线自起、ctest 7/7 全过（用例级 11 / 7 / 8 / 5，另 1 skip by
default，Total 14.30 sec）。无法提供总线的环境配方仍自动 warn+waiver
保底（kdbusaddons 先例），不阻塞构建。

### 问题 6（CI 专有）：testLoadingDisabledRunner 的 fixture 安装被静默吞掉（补丁 0005）

CI 两个工位在 `runnermanagersinglerunnermodetest` 的首个断言处失败：
`manager->runners().count()` Actual 0 / Expected 1（第 103 行）；同一
二进制内的 loadTwoRunners / testAllRunnerResults / testSingleRunnerResults /
testNonExistentRunnerId 全部通过，真机同用例 7/7 通过。该用例里唯一会
「静默失败」的环节是两次丢弃返回值的 `QFile::copy()`：目标已存在时
不覆盖、直接返回 false，后续元数据扫描只看到空目录，断言便退化成
不明所以的 0-vs-1。**处置**（补丁 0005）：先删旧目标文件再复制、对
两次复制做 `QVERIFY`，并把 fixture 目录清单、复制源与结果、
`QStandardPaths` 数据位置、`RunnerManager::runnerMetaDataList()` 的
offer 列表 dump 到 `qWarning`——若根因仍在环境侧，下一轮 CI 日志可
直接读出（offer 为空 / 复制失败 / GenericDataLocation 差异）。该补丁
只动 autotest，不触碰库代码。

**第一轮 CI 日志回读（补丁 0005 生效后）**：`copied false false`，
fixture 目录条目只有 `.`/`..`，两个复制源路径均存在（
`<缓存源根>/autotests/plugins/*.desktop`），元数据 offer 列表为空。
即目标目录刚 `mkpath` 创建且可写、源文件在，`QFile::copy` 仍两次返回
false——问题在 Qt 6 的 `QFile::copy` 走 QSaveFile 临时文件 + rename
路径在此镜像上静默失败，与 0005 假设的「目标已存在」不同。**处置**
（补丁 0006）：fixture 安装改为普通 `QFile` 读写直拷（源 ReadOnly、
目标 WriteOnly|Truncate、短写检查），每条失败路径打印 `errorString`，
断言与查询逻辑保持上游原意；该补丁同样只动 autotest。

## 三、依赖解析

| 上游需求 | ohpcd 选择 | 说明 |
| --- | --- | --- |
| Qt6 >= 6.10（Core/Gui/DBus/Test） | qtbase/6.11.1 + qtbase-sql-dbus/6.11.1 | 裸 qtbase 为 FEATURE_dbus=OFF 构建，Qt6::DBus 只在 sql-dbus 变体；两包共存（kscreenlocker 先例），配方末尾把 Qt6_DIR 重钉回 sql-dbus |
| KF6 >= 6.28.0（Config/CoreAddons/I18n/ItemModels/WindowSystem） | kconfig、kcoreaddons、kwindowsystem @6.26.0.1；ki18n、kitemmodels @6.26.0 | 补丁 0001 降版；.1 修复版注入裸 DT_SONAME（消费者记录裸 soname 而非绝对路径，kscreen CI 实证） |
| ECM >= 6.28.0 | extra-cmake-modules/6.29.0（tool_require） | find 线保留；CMakeDeps 生成的 ECMConfig 不带 ECM_MODULE_PATH，配方手工注入三个子目录 |
| 4 个 autotest 的会话总线 | dbus/1.14.10.3（tool_require） | 仅 build 上下文，不传播到发布的包 |

## 四、真机验证

- 配方成形期（前几轮真机 create）：依赖解析与 0001/0002 迭代——ohpcd
  制品核验、qtbase-sql-dbus 双包 Qt6_DIR 重钉、ECM_MODULE_PATH 注入；
  0002 首版把 Qt6::DBus 也移出链接行后 dbusrunner.cpp 缺
  `<QDBusArgument>`（问题 2 实录）→ 修订成最终形态。
- build 7：0002（修订版）生效，编译越过头文件关；死在
  `src/dbusrunner.cpp` `'KWaylandExtras' file not found`（问题 3）→ 补丁 0003。
- build 8：0003 生效（主体编译通过）；死在
  `autotests/threadingtest.cpp:42` `no member named 'all_of' in
  std::__n1::ranges`（问题 4）→ 补丁 0004。
- build 9：4 补丁全生效——全量编译 100%、ctest（3 过 + 4 bus
  waiver）、test_package 编译、fixdeps 扫描（165 库、0 条带路径条目）、
  ELF 制品检查 22/22（10 条基名 DT_NEEDED、DT_SONAME=libKF6Runner.so、
  `.codesign` 在场）；消费者测试 17/5，定位两处用例缺陷：
  1. **QueryMatch::setId 组合语义**：上游 `QueryMatchPrivate::setId`
     产出 `<runnerId>_<id>`（除非 runner 元数据顶层声明
     `X-Plasma-Runner-Unique-Results: true`，由
     `AbstractRunnerPrivate::hasUniqueResults` 读取）。CASE 12/18/20
     期望裸 id 属误设 → 按上游语义修正期望，并新增 CASE 23 覆盖
     unique-results 分支；
  2. **KPluginMetaData ctor 语义**：`KPluginMetaData(const QString&)`
     是 QPluginLoader 插件语义——对普通 JSON 文件 valid=0、pluginId
     回退为文件名 stem（`dummyrunner-XXXXXX`）、name 空（真机 DIAG
     实录）；非插件来源元数据须走
     `KPluginMetaData(QJsonObject, fileName)` ctor（6.0 起）。
     修正后 DIAG `valid=1 id=dummyrunner name=Dummy Runner`。
  → 手动重编迭代 **23/23（SUMMARY: 23 passed, 0 failed）**。
- build 10（2026-10-16，交付版本，配方 docstring 同步 0003/0004 后
  rrev 全量重建）：全链重跑 `conan create`——编译 100% → ctest 同口径
  （`43% tests passed, 4 tests failed out of 7`：3 个非总线套件过，4 个
  会话总线套件各 300s Timeout 后 waiver）→ 打包成功（Package
  `868fee8c…` built）。test_package 阶段因共享 shell 的 cwd 残留在
  被 test() 清理的 ohos-xdg 目录内，CMakeDeps generator 触发
  `os.getcwd()` FileNotFoundError（环境性，非配方缺陷）。
- build 11（2026-10-16）：以干净 cwd（配方目录）+ HOME/XDG 重置重跑
  `conan create`——同 rrev/package_id 复用二进制（Already installed!）→
  test_package 全链：fixdeps 扫描 `217` 个运行时库、0 条带路径条目 →
  ELF 制品检查 22/22（10 条基名 DT_NEEDED、DT_SONAME=libKF6Runner.so、
  `.codesign` 在场）→ 消费者 23/23（`SUMMARY: 23 passed, 0 failed`）→
  **RC=0**。
- 交付版收官（2026-10-16 04:05，conan-verify G2 干净重建）：`conan remove`
  清旧 rrev 后由 conan-verify 全链重跑——编译 100% → ctest 同口径
  （`43% tests passed, 4 tests failed out of 7`，Total 1200.69 sec，4 项
  waiver）→ Package `868fee8c…` built → test_package：fixdeps 扫描
  `215` 个运行时库（随 LD_LIBRARY_PATH 环境浮动）、0 条带路径条目 →
  ELF 22/22 → 消费者 23/23 → **Verdict PASS / RC=0**（报告 + 裁剪版
  日志见 `reports/`；原样全文 124077 行留存设备）。
- P2 整改重建（2026-10-16 05:27，离线检视 R1 → P2 修复触发 rrev 变更后
  的 conan-verify 干净重建；R2 中间版）：`test_shim/ohos_nopw.c` 的
  `getpwuid_r` 按检视意见修边界差 1 字节（`need … + 1`，注释见该文件）→
  全链重建——编译 100% → ctest 同口径（`43% tests passed, 4 tests failed
  out of 7`，Total 1200.96 sec，4 项 waiver）→ Package `868fee8c…` built
  （package_id 不变；rrev 随导出源变更）→ test_package：fixdeps 扫描
  `165` 个运行时库（随 LD_LIBRARY_PATH 环境浮动）、0 条带路径条目 →
  ELF 22/22 → 消费者 23/23 → **Verdict PASS / RC=0**（报告 + 裁剪版
  日志见 `reports/`；原样全文 160069 行留存设备）。
- 会话总线修复重建（2026-10-16 06:52，**本轮即交付版**；离线检视（P2：
  shim 导出/查找）与自证复核（daemon 的 libdbus 解析）两层修复触发
  rrev 变更后的 conan-verify 干净重建）：编译 100% → 会话总线由配方
  自起（`Session bus for upstream autotests: unix:path=…/kr-session-bus.sock`
  EXTERNAL，`test-bus/daemon-unix.log` 实录）→ ctest **7/7 全过**
  （dbusrunnertest 1.65 / runnermatchmethodstest 0.11 /
  runnermanagerhistorytest 0.11 / runnermanagersinglerunnermodetest 1.08 /
  runnermanagertest 10.27 / testmetadataconversion 0.18 / threadingtest
  0.86 sec；`100% tests passed, 0 tests failed out of 7`，Total Test time
  (real) = 14.30 sec；无 waiver）→ Package `868fee8c…` built（package_id
  不变；rrev 随配方变更）→ test_package：fixdeps 扫描 `165` 个运行时库、
  0 条带路径条目 → ELF 22/22 → 消费者 23/23 → **Verdict PASS / RC=0**
  （报告 + 原样全文日志——本 head 无省略、1010 行——见 `reports/`）。

## 五、交付物

- `lib/libKF6Runner.so`——单一无版本实体共享对象（OHOS /storage 禁
  symlink，无版本链），DT_SONAME=libKF6Runner.so、DT_NEEDED 全基名、
  安装文件已重签（`.codesign` 在场）
- `patches/0001`–`0006` + conandata.yml 声明（每补丁带说明与
  portability 分类）
- test_package：消费者 E2E 23 用例（行为）+ 制品检查 22 项（ELF 结构）
  + fixdeps 注册表卫生扫描

- 构建日志 `reports/conan-create.log` 依平台规则不随档（reports/ 仅随档脱敏 md）；脱敏的 `reports/conan-verify-report.md` 保留随档。
