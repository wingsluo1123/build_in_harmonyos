# kscreenlocker 6.7.2 鸿蒙 PC 适配笔记

上游: <https://invent.kde.org/plasma/kscreenlocker>
版本: 6.7.2（Plasma 6.7.2 发行版）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

构建产物：`libKScreenLocker.so`（KSldApp 锁状态机 / Wayland 锁服务端 /
全局快捷键 / logind 会话跟踪 / 电源管理抑制）。上游 6.7.2 顶层只
install 这一个 SHARED 目标（round 21 全树 grep 实证：无顶层
add_executable，main() 只在 greeter/tests/autotests——greeter 被 0002
关停，守护进程本体已迁入 KWin）。

裁剪范围（ohpcd 池内无依赖包）：

- **greeter**（`KSCREENLOCKER_BUILD_GREETER=OFF`）：需要 PAM、PlasmaQuick、
  LayerShellQt、KF6Screen，全部未发布到 ohpcd；
- **KCM 设置模块**（`KSCREENLOCKER_BUILD_KCM=OFF`）：需要 KCMUtils；
- **X11 锁路径**：OHOS 无 X11/XCB，x11locker 与 ksldapp/globalaccel 中的
  X11 抓取路径整块编译排除，保留 Wayland 锁路径。

## 二、问题与处置

### 问题 1：X11 硬依赖（补丁 0001）

上游把 `x11locker.cpp` 无条件编入 ksld_SRCS，且 ksldapp.cpp / globalaccel.cpp
里散布 X11/XCB 调用（XSetScreenSaver、xcb_key_symbols、XServerGrabber 等），
autotests 还有三个 X11 测试（keyboardGrabber / pointerGrabber /
x11LockerTest）。

**处置**：`config-unix.h.cmake` 增加 `#cmakedefine01 HAVE_X11`；CMake 层把
X11/XCB finds 改为 OPTIONAL，XCB 组件不全或 X11 未找到时 `HAVE_X11=FALSE`；
源文件层用 `#if HAVE_X11` 门控全部 X11 路径（含 `m_isX11` 初值、s_XTimeout
静态量、doUnlock 的 xcb 分支、showLockWindow 的 X11Locker 实例化），
autotests 三个 X11 测试随 HAVE_X11 裁剪。

### 问题 2：greeter / KCM 顶层硬 REQUIRED（补丁 0002）

上游在主 CMakeLists 顶层 `find_package(KF6 ... Crash KCMUtils KIO Svg)`、
`find_package(PlasmaQuick/LayerShellQt/KF6Screen/PAM REQUIRED)`，且
`add_subdirectory(greeter)` / `add_subdirectory(kcm)` 无条件执行。

**处置**：新增 `KSCREENLOCKER_BUILD_GREETER` / `KSCREENLOCKER_BUILD_KCM`
两个 option（默认 ON 保持上游 Linux 行为），把对应 find_package 与
add_subdirectory 整块搬进守卫；autotests 的 pamTest、tests 的
kcheckpass_test（依赖 greeter 产物）一并随 GREETER 选项门控。

### 问题 3：Qt6GuiPrivate 硬 REQUIRED（补丁 0003）

主 CMakeLists 在 Qt6Gui >= 6.10 时 `find_package(Qt6GuiPrivate REQUIRED
NO_MODULE)`，而全树只有 X11 autotest（x11lockertest.cpp 的
qtx11extras_p.h）用到它。

**处置**：find 去 REQUIRED；`target_link_libraries(x11LockerTest
Qt::GuiPrivate)` 加 `if (Qt6GuiPrivate_FOUND)` 守卫（该测试本就在
HAVE_X11 块内，OHOS 上不会构建）。

### 问题 4：C++23 的 std::expected（补丁 0004）

`interface.h` 的 `PowerInhibitor::m_cookie` 用
`std::optional<std::expected<uint, QDBusError>>`，`<expected>` 是 C++23
专属头，OHOS 工具链 clang15 / libc++15 没有它；上游同时把
`CMAKE_CXX_STANDARD` 设为 23。

**处置**：`std::expected<uint, QDBusError>` 与 `QDBusReply<uint>` 语义完全
同构（存值或存错误、`isValid()` 即可判值），替换后 inhibit 失败存错误、
成功存 cookie、uninhibit 判值后 `ReleaseInhibition(value())` 的行为不变；
`CMAKE_CXX_STANDARD` 降为 20（knighttime 6.7.2 先例），C++20 下全树编译
干净。round 20 修订：QDBusReply 无 T 值 ctor（仅 QDBusMessage /
QDBusPendingCall / QDBusPendingReply / QDBusError 四个 ctor），成功路径
须写 `QDBusReply<uint>(reply)`（QDBusPendingReply ctor），失败路径
`QDBusReply<uint>(reply.error())` 与 uninhibit 的
`if (const auto &result = m_cookie.value(); result.isValid())` 本就正确。

### 问题 5：上游 6.7.2 不装任何公共头（补丁 0005）

CMakeLists 调用了 `ecm_generate_headers(...
REQUIRED_HEADERS KScreenLocker_HEADERS)` 并在 install(FILES) 里引用
`${KScreenLocker_HEADERS}`，但全树没有任何地方定义这个变量——生成的头
列表为空、安装列表只剩 export 头，消费者拿不到 ksldapp.h / KsldApp。

**处置**：在 ecm_generate_headers 前补
`set(KScreenLocker_HEADERS ksldapp.h)`，使 ksldapp.h 与
`KScreenLocker/KsldApp` 转发头进入安装（test_package 的消费者用例依赖
此修复）。

### 问题 6：上游测试无法进构建期 ctest

- `logindTest`（QTest 17 检查）：fakelogind 向会话 D-Bus 注册
  `org.freedesktop.login1`，无会话总线时 `QVERIFY(connectedSpy.wait())`
  必失败；
- `kscreenlocker_test`：交互式演示程序，启动即 `lock(Immediate)` 拉起
  greeter（本适配不构建）并 `exec()` 直到解锁，无头环境必挂起；
- pamTest / kcheckpass_test 依赖 greeter，keyboardGrabber / pointerGrabber
  / x11LockerTest 依赖 X11——被门控裁剪。

**处置**：`BUILD_TESTING=OFF`（libkscreen 先例），上游 7 个测试目标的口径
与减少原因见 `test_package/MANIFEST.yml`；消费者侧验证由 test_package 的
KSldApp 无头 E2E（18 断言）+ OHOS 制品检查（12+N 断言，真机 N=20 → 32）承接。

### 问题 7：KF6::CoreAddons / ConfigGui / Package target 缺失（补丁 0006）

上游主 CMakeLists 的 `find_package(KF6 ... COMPONENTS)` 列表只有 7 个组件
（GlobalAccel/I18n/IdleTime/Notifications/Solid/WindowSystem/XmlGui），
而核心 KScreenLocker target 直接链接 KF6::CoreAddons / KF6::ConfigGui /
KF6::Package——上游在 Linux 上靠传递 find_dependency 链（kxmlgui 配置 →
KF6ConfigWidgets → KF6CoreAddons 等）兜底。ohpcd 发布的 KF6 配置把特性
门控烘焙成字面值（kxmlgui 6.26.0 配置里 `if (NOT ON)` 包住整段
find_dependency），这些链在 ohpcd 构建里全部断开 → 三个 target 缺失，
round 14 G2 configure "target was not found" 实录。

**处置**：补丁 0006 把 CoreAddons / **Config** / Package 显式加进主
COMPONENTS 列表（KF6 meta find 逐组件 find_package CONFIG，路径层
conan_cmakedeps_paths.cmake 已把各包 lib/cmake 前置，直接命中）。
组件名写 `Config` 而非 `ConfigGui`：ohpcd 发布的 kconfig/6.26.0 只发
一个 KF6Config 包（KF6ConfigConfig.cmake，其 targets 文件同时导出
KF6::ConfigCore + KF6::ConfigGui），缓存全树 find 无
KF6ConfigGuiConfig.cmake（round 16 G2 实录）。

### 问题 8：KF6::ConfigQml 在 ohpcd kconfig 里不存在（补丁 0006）

settings/ 链接 KF6::ConfigQml，但 ohpcd 发布的 kconfig/6.26.0 只导出
KF6::ConfigCore / KF6::ConfigGui（包内无 libKF6ConfigQml.so，KConfigQml
需 Qt6 Qml 未随 ohpcd kconfig 构建），round 14 G2 settings target 缺失
实录。settings/ 全部源码无任何 ConfigQml API 使用（仅两处 "config.qml"
文件名串），链接是虚的。

**处置**：补丁 0006 从 settings 链接列表删除 KF6::ConfigQml（无符号引用，
行为不变）。

### 问题 9：KConfigPropertyMap 在 ohpcd 包体系里不存在（补丁 0007）

settings/ 的 shell_integration / wallpaper_integration 用
KConfigPropertyMap 包装配置（Q_PROPERTY(KConfigPropertyMap*)，QML 面
由 KCM/greeter 消费），round 17 G2 编译 settings/ 时
`'KConfigPropertyMap' file not found`。破案：该类自 KF 5.89 起住在
KConfigQml 组件（kconfig src/qml/）——ohpcd 发布的 kconfig/6.26.0 只
构建 ConfigCore/ConfigGui（问题 8 同根），缓存全域 find 无头文件、
libKF6ConfigWidgets.so 无符号（kconfigwidgets/6.18.0 不随行该类）。
settings 的 configScheme() 返回 KConfigLoader*，KConfigLoader 是
KCoreConfigSkeleton 子类，与 QML 版 ctor 签名精确匹配。

**处置**：补丁 0007 把 kconfig 6.26.0 src/qml/kconfigpropertymap.{h,cpp}
逐字 vendor 进 settings/（仅剥离 kconfigqml_export.h 与
KCONFIGQML_EXPORT，其余上游原码；QQmlPropertyMap/QJSValue 来自已依赖
的 qtdeclarative，AUTOMOC 已开启），并登记进 settings STATIC 库源列表；
符号经 KScreenLocker.so 最终链接的 KF6::ConfigGui 传递解析。配套两处
（round 18 实录）：上游 `#include <KConfigPropertyMap>` 是 angle include，
上游靠 KF6::ConfigQml 传递的 INTERFACE 目录解析（0006 已删该链接）→
①vendor 一个 `settings/KConfigPropertyMap` 转发头（上游经
ecm_generate_headers 生成，含 `#include "kconfigpropertymap.h"`）②
settings target 加 `target_include_directories(settings PUBLIC
${CMAKE_CURRENT_SOURCE_DIR})`。Linux 默认构建同样使用 vendor 版
（settings 未链接 KF6::ConfigQml，无符号冲突），实现逐字一致、行为不变。

### 问题 11：KKeyServer / netwm.h 住 kwindowsystem 的 X11 面（round 20）

globalaccel.cpp:8 `'KKeyServer' file not found`。破案：KDE 6 的
KKeyServer 与 netwm.h 住在 kwindowsystem 的 X11 源码目录
（src/kkeyserver.{h,cpp}、src/platforms/xcb/netwm.h），只在 X11 构建
下安装；ohpcd 发布的 kwindowsystem/6.26.0 是无 X11 构建，包内无这两个
头。kglobalaccel 6.26.0 也没有 KKeyServer（旧 KF5 时代 KKeyServer 在
kglobalaccel，6 代已迁走）。缓存全域 find 均无。

**处置**：扩展 0001 的 HAVE_X11 门控覆盖 globalaccel.cpp 其余 4 处
X11 路径：KKeyServer/netwm.h 两个 include 挪进 `#if HAVE_X11` 块；
g_keyModMaskXAccel/g_keyModMaskXOnOrOff + calculateGrabMasks() 静态量
整体门控；keyEvent 的 shift 剥离门控；checkKeyPress 整体门控（签名含
xcb_key_press_event_t，include 门控后函数体无从编译，必须整函数门控，
调用点 x11locker.cpp 本就在 HAVE_X11 内）。头文件 globalaccel.h 无需改
（只用前置声明）。

### 问题 10：池缓存 wayland-scanner 的 ELF 签名被真机内核拒 exec（round 19）

G2 构建打到 40%（settings/ 已全过、libsettings.a 已链接、0007 完整
生效），wayland 协议生成步骤 make 执行池缓存 wayland/1.22.0 的
`.conan2/p/wayla…/p/bin/wayland-scanner` 时
`Operation not permitted`（Error 127）。设备实测：二进制本身带
.codesign 节但 exec 被内核拒（EPERM）；剥掉签名节后 exec 变 EACCES；
`binary-sign-tool sign -selfSign 1` 重签后内核放行（手跑时只剩
libxml2.so.16 缺失——构建环境 conanbuildenv 的 LD_LIBRARY_PATH 已含
wayland/libxml2/expat 的 lib 目录，in-build 无此问题）。破案：池缓存
ELF 带 CI 证书，不被真机内核信任；本机自建包（package() 重签）才可
执行。知识图谱 E540 命中为误报（runner-path-prepend 与签名问题无关）。

**处置**：配方 generate() 把 WaylandScanner_EXECUTABLE 指到
`build_folder/wayland-scanner-tool/wayland-scanner`；build() 在
configure 前把池缓存扫描器复制到该路径并走 `_sign_ohos_elf_tree`
（剥 .codesign + selfSign 重签，与 package() 对自有 ELF 同款）。
Linux/CI 无签名校验，保持池二进制原路径不变。

### 问题 12：SOVERSION 符号链 + 池 KF6 库无 DT_SONAME（round 21，补丁 0008 + 配方）

round 21 全树编译+链接成功（0001/0004 修复生效），死在链接收尾：
`cmake_symlink_library: failed to create symbolic link
'bin/libKScreenLocker.so.6': Permission denied`。破案（与池内先例对证）：
①配方设了 CMAKE_SHARED_LIBRARY_SONAME_*_FLAG（kdecoration 先例）→
CMake 生成版本化符号链（.so.6.7.2/.so.6/.so）→ OHOS /storage 禁
symlink（pangomm 真机清单同款坑），EPERM；②池内 KF6 库全部无
DT_SONAME（llvm-readelf 实证 libKF6ConfigCore.so 只有 NEEDED 无
SONAME），其导出 targets 带 IMPORTED_NO_SONAME=TRUE（kconfig 包
Targets-release.cmake 实证）→ 按绝对路径链接会把机器私有缓存路径烧进
DT_NEEDED（E537）。kpackage/6.26.0.1 是唯一真机构建过共享库的 KF6
先例：其 0005 补丁 IMPORTED_SONAME 打戳 + 直传
`-Wl,-soname,libKF6Package.so`，device-built 产物实测 DT_NEEDED 全是
基名（libKF6CoreAddons.so 等）+ SONAME 直传生效——机制全链实证。

**处置**：配方删除 CMAKE_SHARED_LIBRARY_SONAME_*_FLAG（平台无 soname
flag 时 CMake 产出单一无版本 libKScreenLocker.so，无符号链——kpackage
真机产物同款）；新增补丁 0008：①KF6:: 导入目标不再参与链接（仅借
IMPORTED_LOCATION_RELEASE，-NOTFOUND 哨兵门取库路径），KF6 依赖改按
`-l:libKF6Xxx.so` 精确文件名链接——lld 记录命令行所给名字=裸基名
（E537 规避）；settings 静态库自身的 -l: 旗标挂 INTERFACE 传递到
KScreenLocker 链接行；
②`if(NOT CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG)` 门内直传
`-Wl,-soname,libKScreenLocker.so`（Linux 上有平台 flag 时跳过，保住
上游版本化行为不变）。

### 问题 13：KSldApp::isInhibited 私有、消费者测不到（round 22，补丁 0009）

round 22 G2 主体 + install + package 全过（0008 生效实证：单一无版本
libKScreenLocker.so，DT_NEEDED 全基名），挂在 test_package 编译：
`'isInhibited' is a private member of 'ScreenLocker::KSldApp'`
（test_kscreenlocker.cpp 五处调用）。上游把 isInhibited() 声明在私有段，
消费者侧黑盒验证 inhibit/uninhibit 计数器回环需要读有效抑制态。

**处置**：补丁 0009 把声明从私有段挪进公开 "For testing" 块——上游同块
已有同款公开测试钩子（idleId/setIdleId/setGraceTime）先例；定义
（ksldapp.cpp）与内部调用点不动，Linux 行为不变。否决
`#define private public`（审查风险）。

## 三、依赖解析

| 上游需求 | ohpcd 选择 | 说明 |
| --- | --- | --- |
| Qt6 DBus/Widgets/Quick/Test >= 6.10 | qtbase/6.11.1 + qtbase-sql-dbus/6.11.1 + qtdeclarative/6.11.1 | 裸 qtbase 为 FEATURE_dbus=OFF 构建，Qt6::DBus 只在 qtbase-sql-dbus 变体；两包共存（knighttime 先例），Qt6_DIR 末尾重钉到 sql-dbus |
| Wayland 1.3+ Client/Server | wayland/1.22.0 | 与 qtbase 6.11.1 钉版一致；wayland-scanner 用包内 arm64 原生二进制（libkscreen 先例），免 qtwayland（会钉 qtbase/6.11.1.2 与 KF6 线冲突） |
| KF6 >= 6.26.0（10 组件） | kconfig / kcoreaddons / kglobalaccel / ki18n / kidletime / knotifications / **kpackage/6.26.0.1** / solid / kwindowsystem / kxmlgui @6.26.0 | KF6_MIN_VERSION=6.26.0 要求每个组件 >= 6.26.0；kpackage 用 6.26.0.1 修复版（karchive 6.19.0→6.26.0 + zstd 直连，独立 MR 先合入——kpackage/6.26.0 钉 karchive/6.19.0 与 kiconthemes/6.26.0 钉 karchive/6.26.0 同图必冲突，round 8 实录）；kcoreaddons override=True（kconfigwidgets/6.18.0 经 kxmlgui 钉 kcoreaddons/6.18.0，方向由 kpackage 的 6.19.0 KF_DEP 地板锁定） |
| ECM >= 6.26.0 | ecm/6.26.0（tool_require） | CMakeDeps 生成的 ECMConfig 不带 ECM_MODULE_PATH，手工注入 |
| 翻译 po->qm | qt6linguisttools/6.11.1（tool_require） | ECMPoQmTools 的 lrelease |
| PAM / PlasmaQuick / LayerShellQt / KF6Screen / KCMUtils | —（裁剪） | 无池内包，greeter/KCM 关停 |

## 四、真机验证

- rounds 8-13：G2 全挂在依赖解析——`kpackage/6.26.0.1` 未解析（"Unable to
  find in remotes"）。破案：conan 2.29.1 sqlite 缓存索引按引用串精确匹配，
  verify 的 G2 带 `--user=ohpcd --channel=stable` 导出 kpackage 为
  `kpackage/6.26.0.1@ohpcd/stable`，而 kscreenlocker 的 require 是裸
  `kpackage/6.26.0.1` → 精确匹配 miss → 走 remotes → 失败。处置：
  `conan export`（不带 u/c）裸导出 kpackage/6.26.0.1 进缓存，DB 增加裸
  引用行（同 rrev 31e6f134），round 14 解析通过 + build=missing 自动
  重建 kpackage（裸引用无二进制）。
- round 14：G2 进入 kscreenlocker 自身 configure（首次），暴露问题 7/8
  （KF6::CoreAddons/ConfigQml target 缺失）→ 补丁 0006。
- round 15：source() 下载失败——设备网络不可达 KDE 镜像站
  （mirrors.bfsu.edu.cn Errno 101，与配方无关；31 依赖全解析含
  kpackage/6.26.0.1 裸引用 23/32，resolution 修复实证）。处置：PC 下载
  官方 tarball（sha256 77f02418… 与 conandata 一致）经 18765 局域网镜像
  服务，设备 conandata.yml 的 sources.url sed 为
  `http://192.168.43.12:18765/kscreenlocker-6.7.2.tar.xz`（pwp 同款暂存
  手法；仅设备侧暂存，PC 版 conandata.yml 保持官方 URL）。
- round 16：下载换源后 configure 首达 KF6 meta find——CoreAddons /
  Package 命中（补丁 0006 生效），ConfigGui 组件仍缺失：缓存全树 find
  无 KF6ConfigGuiConfig.cmake。破案：ohpcd kconfig/6.26.0 只发一个
  KF6Config 包（KF6ConfigConfig.cmake，targets 双 target
  ConfigCore/ConfigGui），meta find 组件名应为 `Config` → 补丁 0006 修正
  （问题 7 实录）。
- round 17：`Config` 组件修正生效，configure 通过，构建打到 settings/
  编译——`'KConfigPropertyMap' file not found`（问题 9，补丁 0007）。
- round 18：0007 已应用（日志 Apply patch 实录+源目录文件在）但同样报头
  文件找不到——`<KConfigPropertyMap>` 是 angle include，上游靠
  KF6::ConfigQml 的 INTERFACE 目录解析（0006 已删）→ 0007 补转发头
  `settings/KConfigPropertyMap` + settings 的
  target_include_directories；PC 侧 git apply 全链 0001-0007 校验通过
  （GNU patch 2.7.6 对同一 hunk 误拒=MSYS 怪癖，git apply/patch-ng
  语义通过）。
- round 19：0007 完整生效——settings/ 全量编译过（kconfigpropertymap
  .cpp 编译成功）+ libsettings.a 链接，KScreenLocker target 进入
  wayland 协议生成；卡在池缓存 wayland-scanner exec
  `Operation not permitted`（问题 10）。处置：配方复制+设备重签
  扫描器（问题 10）。
- round 20：配方级扫描器重签（问题 10）生效——wayland 协议生成通过；
  编译打到 KScreenLocker 源文件层，暴露两处新错：interface.cpp:62
  `QDBusReply<uint>(reply.value())` 无匹配 ctor（QDBusReply 无 T 值
  ctor，见问题 4 修订）+ globalaccel.cpp:8 `'KKeyServer' file not
  found`（问题 11）。处置：0004 改 `QDBusReply<uint>(reply)`（
  QDBusPendingReply ctor），0001 扩展 4 处门控。
- round 21（启动 2026-10-01 02:52Z）：0001/0004 更新版已推设备
  （md5 52787933/568d2e76 双侧一致）。PC 侧 0001 再生成说明：设备版
  0001（441cf9b0，round 14-19 实证）拉回后叠加 4 处 globalaccel 门控
  重生成，与 wt-kwin 旧 0001 的差异仅 globalaccel.cpp 节；此前链校验
  "0003 FAIL" 是假警报——校验循环只跑 `git apply --check` 不真 apply，
  0003 拿缺 0002 的树去对（CMakeLists:48 上下文错位）；改为逐补丁真
  apply 后 0001→0007 全链通过（ksl-regenerate worktree，CHAIN_APPLY_OK
  + 补丁内容 grep 实证）。round 21 战果：settings 全过+libsettings.a
  链接，KScreenLocker 全源编译通过（globalaccel/interface/ksldapp 全
  过=0001/0004 生效），wayland 协议生成过（问题 10 配方修复生效），
  97% 链接收尾挂 cmake_symlink_library EPERM（问题 12）。
- round 22（启动 2026-10-01 03:11Z）：0008 + 配方（删 SONAME flags）
  + conandata（8 补丁）已推设备（md5 8b68e941/3e35caec/f8137133 双侧
  一致，URL 已 sed LAN 镜像）。PC 侧 0001→0008 全链真 apply 通过且与
  工作副本逐字节一致（MATCH_EDITED）。战果：G2 主体编译+链接全过、
  install + package 全过（0008 生效实证：无符号链 EPERM、单一无版本
  libKScreenLocker.so）；挂 test_package 编译：isInhibited 私有
  （问题 13）→ 补丁 0009。
- round 23（启动 2026-10-01 ~04:00Z）：0009 + conandata（9 补丁）已推
  设备（md5 55e43b8c/95b31660 双侧一致，URL 重新 sed LAN 镜像）。
  PC 侧：0009 从（pristine + 0001-0008 --include）diff 纯出（11+/2-），
  `git apply -R --check` 对当前树通过（REVERSE-CHECK-OK）。待八门禁
  G0/G1/G2/L0/L1/L2/L4/L5 + test_package 18+11 断言回填（最终口径 18+32，见 round 36）。
- rounds 24-30：test_package 与八门禁逐项推进（断言执行器化、compat
  bin 暂存泛化、平台 conan fork 布局 p/cache.sqlite3 定位、fix_db.py
  自愈 34 行 broken DB、kpackage+kconfigwidgets 本地重建成功）。
- round 31：G2 FAIL——链接 KScreenLocker 时 `ld.lld: unable to find
  library -l:libKF6XmlGui.so`。破案：settings 是 STATIC 库，其
  -l: 循环（0008）产生的裸标志经 $<LINK_ONLY:> 传播进 KScreenLocker
  链接行，但搜索目录在 settings 上是 PRIVATE（其实是根本未注册
  target_link_directories）→ 目录不传播，标志裸奔。link.txt 实证：
  -l:libKF6XmlGui.so 在列而 kxmlgui 的 -L 缺席。
- round 32：先尝试改缓存源目录（p/b/kscre2b5418f65c6fa/b/settings/
  CMakeLists.txt）当场重启——无效：平台 conan create 每次导出后新
  建源文件夹（round 32 用 kscreaafdbe2039d06），只认 bih/archives
  里的配方文件。已改走正规路径：0008 补 settings 节（_ksld_dirs
  收集 + target_link_directories(settings INTERFACE ...)，INTERFACE
  而非 PRIVATE——STATIC 库的 PRIVATE 目录不传播），conandata 描述
  同步补 round 31/32 叙事，新 0008 全链真 apply 校验通过
  （SETTINGS_MATCH_REGENERATE）。
- round 33（启动 2026-10-01 ~06:0xZ）：新 0008（md5 6368da90）+
  conandata（f4c7ed03）已推设备双侧一致，运行中。

## Round 34 (2026-10-01) — KConfigSkeleton undefined symbols → KF6::ConfigGui
- G2 FAIL: undefined KConfigSkeleton::qt_metacast/qt_metacall/ctors with only -l:libKF6ConfigCore.so on the link line.
- Root cause: kconfig 6.26.0 splits the skeleton classes — KCoreConfigSkeleton lives in libKF6ConfigCore.so, but the KConfigSkeleton class proper (settings' generated base inherits it; kconfigskeleton.h is at include/KF6/KConfigGui/) lives in libKF6ConfigGui.so.
- llvm-nm -D proof on seed p/kconf7db3dce604ff1: libKF6ConfigGui.so exports _ZN15KConfigSkeleton* ctors/qt_metacast/qt_metacall/staticMetaObject; libKF6ConfigCore.so has only the KConfigSkeletonItem family.
- libKF6ConfigGui.so carries DT_NEEDED ../../bin/libKF6ConfigCore.so (build-tree-relative) — the test_package compat-bin staging (recipe_folder/bin, CWD=build_folder → ../../bin) already globs EVERY transitive libKF6*.so, so the relative entry resolves; same _prepare_ctest_runtime_links mechanism as the kconfig recipe.
- Fix (0008): KF6::ConfigGui added to settings' -l: loop (INTERFACE dirs propagate to the KScreenLocker link line); main KScreenLocker link untouched (its sources include no KConfigGui headers).
- Patch assembly: git apply 2.53 "Skipped patch" bug ONLY inside the ksl-patch-work enclosing repo — scratch must live outside any repo (TEMP); base = git archive HEAD + git apply 0001-0007; VERIFY = apply to fresh base + LF-normalized byte-compare.

## Round 35 (2026-10-01，定位与处置延续至 10-02) — G2 test_package 运行期：依赖制品绝对 DT_NEEDED 命中（E537 现象面）
- G2 FAIL：test() 第 204 行 cmake.test() 挂（ctest test_kscreenlocker 0.24s 失败，
  LastTest.log 空）；同一轮制品探针 32 项全过、主二进制缓存命中（Already installed 31/31）。
- 定位：把 31 个依赖前缀的 lib/*.so* 全摊到测试可执行文件旁，llvm-readelf -d 全量扫
  DT_NEEDED——exe 自身 5 条全基名；首个硬停点是依赖制品内部的绝对条目：
  libKF6XmlGui.so → /storage/Users/currentUser/.cache/conan2/p/b/kconfb33c5c9339725/
  p/lib/libKF6ConfigWidgets.so（该路径在本设备文件系统视图不存在）。同轮三组实验证实：
  OHOS 加载器不搜主程序所在目录、LD_LIBRARY_PATH 有效（按基名解析 DT_NEEDED）、
  依赖库内相对条目按进程 CWD 解析（compat bin ../../bin 手法的依据）。
- 性质：E537 类的生产侧残留——依赖制品在各自构建机上把私有缓存路径烧进了 DT_NEEDED，
  非本配方产物；本配方产物 20 条 DT_NEEDED 全基名由制品探针逐条核验（0008 即本配方对
  自身产物的根治手法：-l: 精确文件名链接，lld 按命令行原样记基名）。
- 处置：设备侧按 E537 口径补建缺失的绝对路径目标（同基名库副本），配方文件不涉及。
- 处置后复跑：ctest Test Passed，SUMMARY: 18 passed, 0 failed。

## Round 36 (2026-10-02 17:53) — 八门禁全绿 Verdict PASS
- G0/G1/G2/G3/G4 全 PASS（L2/L4/L5 无 cache 路径跳过）；conan create 全过；
  test_package：ctest Test Passed（18/18 行为 E2E）+ 制品检查 32/32
  （12 项结构化 + N=20 条逐 DT_NEEDED 基名）。
- 报告：reports/conan-verify-report.md（Verdict PASS）+ reports/conan-create.log；
  R46 终态 result.json 已上报（draft:false），manifest status 可标记 published。
