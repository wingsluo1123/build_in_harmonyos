# kcron 26.04.1 鸿蒙 PC 适配笔记

上游: <https://invent.kde.org/utilities/kcron>
版本: 26.04.1（KDE Gear 26.04.1 发行版）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

产物（install 树实测）：

- `kcm_cron.so` —— QML KCM 插件（MODULE 目标，无 SOVERSION），安装于
  `lib/plugins/plasma/kcms/systemsettings/`，旁附
  `kcmdesktopfilegenerator` 生成的 `kcm_cron.desktop`；
- `kcron_helper` —— KAuth 提权助手可执行文件（`libexec/kauth/`）+
  `local.kcron.crontab` 激活文件；
- crontab 表模型（TasksModel/VariablesModel）与任务校验
  （TaskValidator）编进插件本体。

平台适配 7 个补丁（`patches/0001`–`0007`，`patch_type: portability`，
均不含平台条件编译宏，R8 合规；每个补丁都是平台中立的源码变更，无条件
应用——kcachegrind 26.04.0 先例）：

1. **PrintSupport 缺失**（0001/0002/0003）：已发布 qtbase 以
   `FEATURE_printsupport=OFF` 构建、无 Qt6PrintSupport 模块
   （algobox/conducteo/ksystemlog 26.04.0 先例）——必需组件列表去掉
   PrintSupport（显式请求 Gui/Widgets），cron 打印动作改走 `QPdfWriter`
   （QtGui）+ `QFileDialog::getSaveFileName`（Widgets）的 PDF 导出流程；
2. **无 passwd 条目的 uid**（0004）：`CTHost` 构造中 `getpwuid()` 返回
   空指针时上游直接解引用终止宿主进程——降级为
   `CTInitializationError`，KCM 可加载；
3. **空当前用户 cron**（0005/0006）：该错误下 `currentCron()` 恒为空，
   `TasksModel`/`VariablesModel` 在
   `create()/applyCreate()/paste()/refresh()` 中解引用空 `CTCron*`——
   改为容忍空 cron，模型保持可用（空、可添加、可校验）；
4. **上游测试可移植化**（0007）：`taskvalidatortest` 的两个绝对路径用例
   假定 `/usr/bin` 可搜索且存在 `true`/`printf`；OHOS 上构建 uid 无法
   stat `/usr/bin`——改用 `QCoreApplication::applicationFilePath()`
   （任何构建环境中都存在且可执行的绝对路径），保持两用例原意。

测试口径：

- 上游套件：1 目标 / 9 具名用例（`taskvalidatortest`），
  `BUILD_TESTING=ON` 在 `build()` 内真实执行；
- 消费者测试（`test_package/`，R51 第三步）：7 组 / **25 断言**（PASS
  口径；另有 9 条 INFO 回显），真机全过；
- 真机八门禁 **Verdict PASS**（2026-10-16，reports/conan-verify-report.md）。

## 二、问题与处置

### 问题 1：Qt6PrintSupport 模块不存在（补丁 0001/0002/0003）

上游 `CMakeLists.txt` 在必需组件里列 `PrintSupport`，
`src/CMakeLists.txt` 把 `Qt6::PrintSupport` 链接进 kcm_cron，
`cronPrinter.cpp` 用 QPrinter/QPrintDialog 实现打印。

**处置**：0001 从组件列表移除 PrintSupport、显式加回 Gui/Widgets；
0002 链接改 `Qt6::Widgets`；0003 把 CrontabPrinter 重写为 QPdfWriter +
QFileDialog 的 PDF 导出（`print()` 槽签名与 QML 接线不变）。打印对话框
→ 保存 PDF 为形态替换，功能保留。

### 问题 2：getpwuid() 空指针终止宿主进程（补丁 0004）

平台允许无 /etc/passwd 条目的 uid（本设备构建/测试 uid 20020084 即无
条目）。`CTHost` 构造函数对 `getpwuid()` 结果直接解引用——KCM 插件被
QPluginLoader 加载时即终止宿主进程（System Settings 场景即闪退）。

**处置**：空结果降级为 `CTInitializationError`（构造仍成功、对象带错误
态），KCM 可加载、模型空但可用。消费者 CASE 3 断言捕获该错误串
（`No password entry found for uid ...`）。

### 问题 3：空当前用户 cron 的解引用（补丁 0005/0006）

问题 2 的降级态下 `currentCron()` 返回空，`TasksModel::create()` 等槽
仍解引用空指针（平台无 crontab 后端，此路径非交互即可到达）。

**处置**：两模型的 create()/applyCreate()/paste()/refresh() 调用组逐一
加空 cron 容忍，模型保持空可用；消费者 CASE 4/6 覆盖。

### 问题 4：taskvalidatortest 绝对路径用例不可移植（补丁 0007）

`testAbsolutePathExecutable`/`testAbsolutePathWithArguments` 直接
断言 `/usr/bin/true`、`/usr/bin/printf` 的行为（QStandardPaths 查找 +
进程执行）。OHOS 上构建 uid 无 `/usr/bin` 搜索权（stat 被拒），且平台
本就没有这两个路径——用例必然失败，且断言的是平台事实而非被测逻辑。

**处置**：改用 `QCoreApplication::applicationFilePath()`（任何构建环境
中都存在且可执行的绝对路径），保持两用例原意（裸绝对路径 / 带引号路径
加参数），真机与 Linux CI 同口径通过；补丁仅动手两用例，其余 7 用例
保持上游逐字。

### 问题 5：Qt6 跨包组件查找（配方 + test_package 双处，无补丁）

qtdeclarative/qtsvg/qtshadertools/qtmultimedia 是独立 conan 包，而
`find_package(Qt6 COMPONENTS Qml ...)` 会先命中 qtbase 的
Qt6Config.cmake（CMakeDeps 按包生成、qtbase 在前），因其缺组件而失败
（期望 `.../qtbase*/p/lib/cmake/Qt6Qml/Qt6QmlConfig.cmake` 不存在）。

**处置**：主配方的 `generate()` 与 test_package 的 `generate()` 都注入
`QT_ADDITIONAL_PACKAGES_PREFIX_PATH`（官方跨包组件查找钩子，指向
qtdeclarative 等包前缀；kcmutils 6.26.0 先例）。test_package 侧若漏配
同样失败——两处必须一致。

### 问题 6：OHOS 加载器的 4-LOAD 段布局要求（配方既有手段，无补丁）

OHOS lld 默认 `max-page-size=0x10000`，会把 .dynsym/.dynstr 拆进高地址
RW 段，OHOS musl 加载器拒绝 mmap 该布局。

**处置**：`generate()` 统一 `-Wl,-z,max-page-size=0x1000`
（MODULE/SHARED/EXE），可执行文件另加 `--disable-new-dtags`
（工具链若落依赖 RPATH 则取 DT_RPATH 形式；audiocd/kcolorchooser 先例）。
**真机实测**：本 OHOS 工具链/CMake 平台不落 RPATH——构建树 `link.txt`
无 `-rpath`、两个随包 ELF（kcm_cron.so / kcron_helper）`llvm-readelf -d`
均 0 条 RPATH/RUNPATH 标签；`CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH`
变量设置为跨平台意图保留，本平台运行时解析全部经导出 `LD_LIBRARY_PATH`。

### 问题 7：依赖制品 DT_NEEDED 三重怪癖（配方 test_package + package 双层处置）

已发布 KF6 6.26.0 制品在各自构建机上留下了三类不可移植的 DT_NEEDED：

- **绝对路径指向旧 conan home**：设备上存在两个 conan home（现行
  `.conan2` + 早期 `.cache/conan2` 残留），制品内烧死的绝对条目恰好指向
  仍存在的旧 home——加载器会跟随它加载**图外**的陈旧副本，而旧副本内又
  有构建树相对条目（`../../bin/libKF6*.so`）无法在外层修复；
- 制品内的相对条目：OHOS 按符号链路径解析，跨包布局下断链；
- 本包产物：因池内 KF6 库无 DT_SONAME，链接器把依赖库的**建造机绝对
  路径**烧进 kcm_cron.so/kcron_helper 的 DT_NEEDED（E537 现象）。

**处置**（真机 HMDFS 全盘禁 symlink，EACCES/EPERM，故以原位改写为主）：

- 配方 `build()` 的构建期 ctest：`_bake_needed_path_stubs()` 对缺失的
  绝对路径条目按同基名建**目录 + 符号链**补齐（仅限 $HOME 下可写区），
  `_prepare_ctest_runtime_links()` 把依赖库摊进 `bin/`、`../bin` 等
  相对条目的解析点（kcmutils 6.26.0 先例）——构建期 ctest 与上游套件
  由此可跑；
- 配方 `package()`：`_sanitize_needed_entries()` 对**本包产物** ELF 的
  路径形态 DT_NEEDED 做 `.dynstr` 原位改写（仅当路径独享时，防撞共享
  串；独享串判定只锚定字符串型 tag——DT_NEEDED/SONAME/RPATH/RUNPATH
  ——数值型 tag 的取值不参与，避免其恰好落入串区间时误判共享而漏改）
  → 裸基名，随后剥 `.codesign` 重签（kcolorchooser 26.04.0 先例）
  ——制品可移植；两个产物 ELF 同口径净化（kcm_cron.so 10 条 +
  kcron_helper 1 条）；净化后任何残留路径形态条目即中止打包
  （fail-closed 守卫，防"静默漏改照常出包"）；
- test_package `test()`：`_prepare_runtime_links()`（符号链农场；HMDFS
  禁 symlink 时打警告跳过，安全）、`_fix_relative_needed()`（依赖库
  相对条目 → 基名）、`_fix_absolute_needed()`（依赖库**绝对条目** →
  基名，patchelf --replace-needed + 去 .codesign + 重签，幂等；本包
  产物已在 package() 净化，扫描不再命中）
  ——阻断加载器跟随 `.cache/conan2` 陈旧副本，全部查找走导出的
  `LD_LIBRARY_PATH`（实测产物无 RPATH 标签，见问题 6；kgoldrunner
  26.04.0 先例，适配为设备现实）。

### 问题 8：E330 评估——不需要（有意省略）

E330 知识条目建议 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` 规避
cmake_symlink_library 在 HMDFS 上的 EPERM。本包逐项核对后**不使用**：
kcron 只有 MODULE 目标（`Linking CXX shared module kcm_cron.so`，无
SOVERSION、无版本化符号链创建路径），全量重建日志中零 symlink 错误。
最终验证在无任何 `-c` 注入的常规命令下直接通过——平台 CI 常规命令即可
复现，配方不依赖该旗标。

### 问题 9：已知限制（如实申报，不补丁）

`CTHost::save(CTCron*)` 与 KCMCron 的 add/modify/remove 槽对
`currentCron()` 无空值检查，仅可从完整 Plasma 会话的交互动作到达；本
平台无法显示 System Settings 会话（无 passwd 条目 + 无 crontab 后端），
非交互面（构造、模型、任务创建、校验、打印器接线）已由消费者用例覆盖。
配方 docstring 同步申报。

## 三、依赖解析

| 上游需求 | ohpcd 选择 | 说明 |
| --- | --- | --- |
| Qt6 Core/Gui/Widgets/Qml/Quick/Test | qtbase-sql-dbus/6.11.1 + qtdeclarative/6.11.1 + qtbase/6.11.1.1（override） | 裸 qtbase 为 FEATURE 裁剪构建；Qml/Quick 在 qtdeclarative 包，经 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 查找（问题 5） |
| Qt6 Svg/ShaderTools/Multimedia | qtsvg / qtshadertools / qtmultimedia @6.11.1 | Kirigami 运行时与 CMake 链完整（KI18n、KF6::KirigamiAddons 需求） |
| KF6 ConfigWidgets/CoreAddons/Auth/I18n/KCMUtils | kconfigwidgets/6.18.0 + kauth/kcmutils/kio/kxmlgui/kitemviews @6.26.0 + kconfig/kcoreaddons/kguiaddons/ki18n/kwidgetsaddons/kcolorscheme/kcodecs/kiconthemes/kcrash 6.26.0（override） | kcmutils 6.26.0 钉 kconfigwidgets/6.18.0 线；KCMUtils 宏 + KF6::AuthCore 齐备 |
| KirigamiAddons >= 0.11.76 | kirigami-addons/1.13.0 + kirigami/6.18.0 | KF6::KirigamiAddons 导出目标经 CMakeDeps 可达 |
| ECM | ecm/6.26.0（tool_require） | CMakeDeps 的 ECMConfig 不带 ECM_MODULE_PATH，配方手工注入 modules/find-modules/kde-modules |
| expat/openssl/zstd/libxml2 | 2.8.2.1 / 3.5.6.1 / 1.5.7 / 2.15.3 | KIO 闭包与 Qt Network 底座，版本随 KF6 6.26.0 线 |

## 四、真机验证

- 2026-10-16 全量干净重建（收尾口径）：`conan remove
  kcron/26.04.1@ohpcd/stable -c` + 清 `.conan2/p/b/kcron*` 构建目录 +
  删 `test_package/build`，随后由 conan-verify 工具**原样**执行（无任何
  额外 `-c` 注入）。
- 关键日志行（reports/conan-create.log，1065 行）：
  - 209：源码命中设备下载缓存（5 个 URL 全列）；
  - 397–507：本包 100% 编译（kcron_helper、taskvalidatortest、
    kcm_cron 全过）；
  - 509–514：上游 `taskvalidatortest` 100% 通过（1/1，0 失败）；
  - 522–543：`package()` 重建完成（:522 Calling package()），包 ID
    `57c4ffdfe3c8bbe7f0cbbad310640bfd89dfaee4`（配方修订
    `3d344ea3f0d0b8ac7bf8f49c5e1a5737`，包修订
    `b305946f69863d05a5a0f5773aafb7f9`，实录 :540/:541）；
    其中 532–534 为净化实录：`kcm_cron.so: 10` + `kcron_helper: 1`
    合计 11 条（kcron_helper 首度在打包期净化）；
  - 1054–1055：符号链农场对 libxml2.so 的 HMDFS symlink EPERM 警告
    （设计内安全跳过）；测试期**零 ELF 补丁**——全文无
    `patching … DT_NEEDED` 行（kcron_helper 的绝对条目已在打包期
    净化，test_package 扫描不再命中）；
  - 1056–1065：消费者 ctest 100% 通过（末行
    `kcron consumer cases passed`）。
- 消费者逐用例证据：reports/test-package-ctest.log（1/1 Passed；
  25 PASS + 9 INFO：产物定位、QPluginLoader、KPluginFactory 实例化
  真实 KCM、空模型、真实 QQmlEngine 驱动的 TaskValidator 三分支、
  粘贴守卫、load/defaults/isPersonalUse 往返）。
- 八门禁：G0/G1/G2/G3/G4 ✅ PASS，L2/L4/L5 ⏭️ 跳过（无 cache 路径，
  设备侧口径，见报告备注），Verdict PASS。
