# kscreen 6.7.2 适配笔记

## 软件说明

kscreen 是 KDE Plasma 的屏幕管理服务，建立在已发布的 libkscreen 6.7.2 运行时之上：

- `lib/plugins/kf6/kded/kscreen.so`：kded 模块（KDEDModule + KScreen::Config 生成/序列化 + OSD 动作切换），由 kcoreaddons 的 kcoreaddons_add_plugin 装为 KDED 插件；
- `kscreen-console`：命令行诊断工具；
- Plasma KCM/OSD/plasmoid 与 HDR 校准器：依赖（Plasma/PlasmaQuick、LayerShellQt、plasma5support、KF6::KCMUtils/Svg/Crash、Qt6GuiPrivate/Qt6WaylandClient 私有头）在 OHOS 上均未发布，本适配裁剪，仅关闭这两组桌面组件，上游默认（ON）不变。

上游 tarball：`kscreen-6.7.2.tar.xz`，
sha256 `a67fbbb8c2fa2a875f29d056d72453d340143219b08062a932c7b1f1501add48`
（https://download.kde.org/stable/plasma/6.7.2/）。

## 编译环境

- 构建系统：CMake（KDE ECM 系），生成器 Ninja（OHOS 的 GNU make 4.4.1 jobserver 依赖 mkfifo，沙箱全面拒绝 → 见下）
- 编译器：clang/clang++ 15（OHOS SDK，aarch64-linux-ohos），C++20（上游自设，配方移除 profile 的 cppstd 块避免打架）
- 构建日期：2026-10-15；`conan create` 真机干净构建（ohc conan-verify 八门禁）

## 依赖核验（制品仓 ohpcd 实测）

| 依赖 | 用途 | 制品仓核验 |
|---|---|---|
| qtbase/6.11.1.2 | Qt6 Core/Gui/Widgets/DBus/Quick（含 offscreen QPA 插件）| ✅（override=True 钉版）|
| qtdeclarative/6.11.1 | Qt6Quick/QuickControls2（kded 插件）| ✅ |
| libkscreen/6.7.2 | KF6::Screen 公有链接依赖 + 运行期后端插件 | ✅（真机自 ohpcd 拉取二进制）|
| kcoreaddons/6.26.0.1 | KPluginFactory/KDirWatch（kcoreaddons_add_plugin）| ✅（依赖项修订版；6.26.0 未针对此 Qt 构建发布二进制，且其源码构建在 OHOS 上死于上游插件自测 QFile::copy，6.26.0.1 的补丁 0006 已修，自测 30/30）|
| kdbusaddons/6.18.0 | KDEDModule | ✅（制品仓二进制与 qtbase-sql-dbus/6.11.1 对齐；6.29 修订只与 qtbase/6.11.1 线对齐，且其源码构建死于 Qt6GuiPrivate/XKB，详见移植要点 9）|
| qtbase-sql-dbus/6.11.1 | kdbusaddons 6.18 的 Qt 闭包（传递）| ✅ |
| ki18n/6.26.0 | KLocalizedString | ✅ |
| kwindowsystem/6.26.0 | KWindowSystem（console）| ✅ |
| ecm/6.26.0 | 构建工具（ECM 模块 + FindKF6 伞形）| ✅ |
| qt6linguisttools/6.11.1 | lrelease（ki18n_install(po) → ECMPoQmTools）| ✅ |

## 移植要点（问题 / 根因 / 解法）

| # | 问题 | 根因 | 解法 |
|---|------|------|------|
| 1 | KCM/OSD/plasmoid 找不到 Plasma/PlasmaQuick/LayerShellQt/KCMUtils/Svg；HDR 校准器找不到 Qt6 私有头 | 这些依赖在 OHOS 未发布 | 补丁 0001：KSCREEN_PLASMA_INTEGRATION / KSCREEN_BUILD_HDRCALIBRATOR 选项化（上游默认 ON，OHOS 构建 OFF），只保留 kded 插件 + console |
| 2 | find_package(KF6 ...) 失败 | ohpcd 的 KF6 包不带 lib/cmake/KF6/KF6Config.cmake；CMakeDeps 不传播 ECM_MODULE_PATH | 配方显式注入 ECM 的 modules/find-modules/kde-modules 三目录，经 ECM 的 FindKF6.cmake 伞形模块逐组件解析（补丁同时把组件清单显式化为 CoreAddons/DBusAddons/I18n/WindowSystem）|
| 3 | 链接出的 KF6 依赖是 Conan 缓存绝对路径（DT_NEEDED 不可重定位，E537）| 已发布 KF6 的无版本 .so 不带 SONAME，CMake 按导入目标绝对路径链接；osdactions（ECMAddTests）与 kscreen-console 上游已用 plain 签名 target_link_libraries，plain 与 keyword 签名不能混用于同一目标 | 补丁 0002：kscreen_link_kf6_relocatable() 用 -l:<basename> + target_link_directories 重链（PLAIN 开关对已有 plain 签名的目标改用 plain 形式；调用必须带 DEPS 关键字——cmake_parse_arguments 只收集 DEPS 之后的多值，遗漏时目标名落入 UNPARSED_ARGUMENTS，helper 静默失效致 source 缺 libkscreen 头目录），kscreen_common 对象库经 INTERFACE 传播给 kded 插件 |
| 4 | 运行期 Qt6DBus 拿到无效会话总线 | OHOS qtbase 的 Qt6DBus dlopen() libdbus-1.so.3，ohpcd 只有静态 libdbus-1.a | 配方内置 dbus-1.14.10 源码构建共享 libdbus-1.so.3 随包分发（kglobalacceld 先例）|
| 5 | make -jN 构建死（jobserver mkfifo 被拒）| OHOS GNU make 4.4.1 用 mkfifo 实现 jobserver，HMDFS EPERM、/tmp EROFS | 全链 Ninja；dbus 内置构建同用 conan_toolchain 直驱 cmake -G Ninja |
| 6 | XInput 触屏映射路径编译失败 | qtbase 系 FEATURE_xcb/xlib=OFF | WITH_X11=OFF（上游非 X11 平台也走此分支，kwin/kglobalacceld 先例）|
| 7 | 上游测试 add_test 需要 dbus-launch/会话总线 | OHOS 无 dbus-launch | osdactions 不需总线：Fake 后端由测试自身 KSCREEN_BACKEND=Fake 进程内加载，只需 QT_PLUGIN_PATH（KSC_Fake.so）+ offscreen QPA；ctest 由配方真机执行 |
| 8 | 安装后二进制被内核拒执行 | cmake.install 重写 RUNPATH，工具链盖的 .codesign 段失效 | package() 对制品树重签（llvm-objcopy 去 .codesign + binary-sign-tool -selfSign 1，kscreenlocker 先例）|
| 9 | kdbusaddons 6.29.0 源码构建死于 configure：Qt6GuiPrivate 需要 XKB_LIBRARY/XKB_INCLUDE_DIR | qtbase/6.11.1.2 按 libkscreen 6.7.2 要求 override 钉版；kdbusaddons 6.29 上游在 Qt6Gui ≥ 6.10 时强制 `find_package(Qt6GuiPrivate REQUIRED)`（需要 X11 私有头），本工具链闭包内没有；其制品仓修订又只与 qtbase/6.11.1 线对齐 | 改用 kdbusaddons/6.18.0（与 qtbase-sql-dbus/6.11.1 对齐的制品仓二进制，kglobalacceld 6.7.2 先例，KDEDModule 公有 API 跨系列不变）；补丁 0003 把 KF6_MIN_VERSION 6.26.0→6.18.0（其余组件仍解析到 6.26.0）|
| 10 | 内置 dbus 构建在链接成功后下一步失败：创建 libdbus-1.so.3 / libdbus-1.so 报 Permission denied | OHOS 沙箱全盘拒绝 symlink()（构建树与 $HOME 实测均 EACCES）；dbus 构建强制 CMAKE_SYSTEM_NAME=OHOS（CMake 有 OHOS 平台文件、沿用 Linux 式规则）→ 产物带版本名并追加符号链接步骤 | 版本化 .so（libdbus-1.so.3.32.4）作为显式 Ninja 目标构建，两个别名以普通文件复制物化（动态装载器解析等价）；package() 三个名字随包 |
| 11 | 上游 osdactions 全部用例同挂：报统一串 "Plugin does not provide valid KScreen backend"，末了 SIGSEGV | libkscreen 包内 KSC_Fake.so 的 DT_NEEDED 带构建树相对项 `../../bin/libKF6Screen.so`（含 `/` 的名字不搜 LD_LIBRARY_PATH，装载器按测试进程 CWD 直接 open）；文件缺失→dlopen 失败；路径上是无关副本→插件绑定第二个 libKF6Screen 实例，qobject_cast\<AbstractBackend\*> 因 QMetaObject 链地址不匹配失败（装载/转型各分支在 configoperation.cpp 归并为同一错误串，表象易误判为环境缺插件）| 配方 _stage_relative_backend_layout()：把 `<build_folder>/../bin/libKF6Screen.so` 以普通文件复制物化（沙箱拒绝 symlink()/link()，实测 EPERM），并把相对目录 `../../bin` 置 LD_LIBRARY_PATH 首位——测试主程序按裸名搜索与插件相对 NEEDED 解析到同一文件、同一实例；真机 12/12 全过。定位链=readelf -d 双端 NEEDED 对照 + QT_LOGGING_RULES="org.kde.kscreen\*=true" 的 qCDebug 分支 + ctypes dlopen 矩阵（中性 CWD 复现、相对布局命中）|

## 上游测试

`tests/osdactions.cpp`（ecm_add_tests → 1 个 ctest 目标）：QTest 类 TestOsdActions，10 个测试函数（testSwitchToExternal / testSwitchToInternal / testClone / testExtendLeft / testExtendRight 及对应 *Rotated 组）对 libkscreen Fake 后端执行 OSD 切换动作校验；`kcm_smoketest` 因 KF6KCMUtils 未参与构建而不会注册（上游以 KF6KCMUtils_VERSION ≥ 6.27.0 设门）。

真机执行结果（2026-10-15，ohc conan-verify 干净构建；归档 reports/conan-verify-report.md，Verdict PASS；构建日志按仓库审查规则不入库、留存设备侧）：

- ctest `osdactions`：1/1 Passed（Total Test time 0.17 s），`100% tests passed, 0 tests failed out of 1`；函数级 12/12（initTestCase + 10 个动作函数 + cleanupTestCase，Totals: 12 passed, 0 failed）。
- 依赖包后端插件的构建树相对 DT_NEEDED 需按移植要点 11 物化相对布局：修复前 0/10 全挂（结束于 SIGSEGV），修复后全绿（修复随配方 `_stage_relative_backend_layout()`）。

## test_package（消费者用例）

真实执行器：安装后经 CMake 消费者工程（Qt6::Core + 运行期环境）——找 kded 插件 kscreen.so 并 QPluginLoader 加载（IID org.kde.KPluginFactory、KPlugin.Version 6.7.2、X-KDE-Kded-autoload=true、instance() 非空）、跑 kscreen-console --help、并做 10 项 ELF 制品断言（KF6 门控库不得出现、SONAME、无绝对缓存路径、无 kcm_/hdrcalibrator 残留）。逐项 TEST PASS/FAIL，任一失败 exit(1)。

## 构建复现

```bash
conan create archives/k/kscreen/6.7.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```
