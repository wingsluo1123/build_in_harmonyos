# knotifications 6.28.0 适配笔记

## Scope

本包续接 KF6 6.28.0 基线（依赖项活动），把已发布的 knotifications/6.26.0
配方推进到 KDE Frameworks 6.28.0。knotifications 是 KDE 桌面通知库
（KNotification / KNotificationAction / KNotificationPermission /
KNotificationReplyAction / KNotifyConfig），产出 libKF6Notifications.so。
版本目录形态沿用 6.26.0 线（conandata + conanfile + 单个 CMakeLists 补丁 +
test_package），并按 6.28 线统一口径补上 OHOS 共享库 SONAME 规则与消费者级
SONAME/DT_NEEDED 回归测试（kitemviews / kcontacts 6.28.0 定稿打法）。

上游 tarball：`knotifications-6.28.0.tar.xz`，sha256
`e5d3b284ccc907f190d3ab10995a0ae7fa0f505088acc69edc7adfcc6a8140d6`
（官方源与南京大学镜像双源字节一致，已本地交叉核验）。conandata.yml 保留
官方源第一优先，NJU 镜像（KDE 官方镜像列表成员）兜底。

## 上游变化 (6.26.0 → 6.28.0)

- CMakeLists：KF_VERSION / KF_DEP_VERSION 6.26.0 → 6.28.0；ECM 最低版本
  6.26.0 → 6.28.0（tool_requires 相应升到 ecm/6.28.0）；弃用线
  KF 6.23 → 6.27；configure_package_config_file 不再传
  PATH_VARS KDE_INSTALL_DBUSINTERFACEDIR。
- 公共头文件无变化：diff 仅涉及 src 下的 .cpp 与 android 侧文件
  （knotification.cpp、knotificationmanager.cpp、notifybyandroid.* 等），
  6.x 的 API/ABI 面保持稳定；6.26.0 的 5 处补丁对 6.28 树原样适用
  （GNU patch dry-run 干净，补丁产物与手改稿逐字节一致）。
- autotests / tests 维持上游形态：KNotificationTest 仍为注释状态，
  tests/ 两个可执行仍由 HAVE_DBUS 守卫 → 本 feature set 上游 CTest N=0
  （见「测试说明」）。

## 补丁（patches/0001-CMakeLists.txt.patch，5 处，均在顶层 CMakeLists.txt）

1. KF_DEP_VERSION 6.28.0 → 6.26.0（`# ohpcd KF6 dep ceiling`）：制品仓 KF6
   最高线为 6.26.0.x；KF6 在 6.x 内保持 API/ABI 兼容。
2. include(ECMQmlModule) 注释：ECMQmlModule6 内部非 QUIET 的
   find_package(Qt6 COMPONENTS Core Qml) 会把 Qt6 标记为缺失必需包，在
   ecm_feature_summary() 处中止（qtbase 制品包无 Qt6Qml；src/qml 子目录
   上游已有 if(TARGET Qt6::Qml) 守卫，不受影响）。
3. DBus+Canberra 块整体 if (FALSE)：qtbase 制品包无 Qt6DBus 组件、
   libcanberra 未发布；音频通知后端（notifybyaudio.cpp）与 DBus
   popup/portal 后端不编译（沿 6.14/6.26 同语义）。
4. Python 绑定探测由 REQUIRED 改为静默探测 + 目标缺失时 FORCE OFF
   （恢复 6.14 的 cmake_dependent_option 语义；Shiboken6/PySide6 未发布）。
5. ecm_install_po_files_as_qm(poqm) 注释（Qt6LinguistTools 不在 qtbase
   制品包）+ add_subdirectory(examples) 注释（examples 需要 Qt6 Quick）。

## 适配点

1. **SONAME-only 共享库规则**（kitemviews 6.28.0 定稿口径）：OHOS CMake 无
   Platform/HarmonyOS 模块，CMAKE_SHARED_LIBRARY_SONAME_* 为空 → lld 不发
   DT_SONAME、消费者把绝对构建路径写进 DT_NEEDED。配方经
   CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX 注入只含 SONAME 标志的 rules 文件，
   并设 CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE（HMDFS 拒 symlink(2)
   EPERM，版本化符号链无法落地）。刻意不定义
   CMAKE_SHARED_LIBRARY_RUNTIME_*（rpath）：定义后 cmake install() 会重写
   ELF 剥掉 RUNPATH，设备 loader 对重写产物 dlopen EACCES；SONAME-only 时
   install() 退化为逐字节拷贝。
2. **/system/lib64 前置**：ECM 6.28 的 KDEInstallDirs6 在 configure 期执行
   qtbase 的 qtpaths；沙箱 LD_LIBRARY_PATH 内的 libc++_shared.so 不兼容，
   前置 /system/lib64 让兼容版优先（SDK llvm/lib 另行供 lld 链接期使用；
   kconfig 6.26.0 先例）。
3. **CMakeDeps 路径手工补全**：qtbase 与 KF6 系包 cmake_find_mode=none，
   CMakeDeps 不生成 conan_cmakedeps_paths.cmake；配方手写该文件（全部依赖
   的 lib/cmake、lib、include 路径 + 生成器目录自身），并直接导出
   ECM_MODULE_PATH（项目 set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH}) 依赖它；
   CMakeDeps 版 ECMConfig.cmake 不设置该变量）。
4. **依赖面**：qtbase/6.11.1（Qt6Gui）+ kconfig/6.26.0.1。上游
   KF6NotificationsConfig.cmake.in 在共享库构建下只 find_dependency(Qt6Gui)，
   KF6ConfigCore 不进 configure 链、而是以裸 DT_NEEDED 进运行期；kconfig 的
   .1 版本即裸 SONAME 重发版，recipe 与 test_package 两侧都显式 require，
   保证运行期解析与 E537 检查在纯净缓存上也成立。

## 测试说明（N 申报）

上游构建系统注册的 add_test 数（ctest -N 实测）：**0**。
- autotests/：KNotificationTest 上游注释（需 DBus session bus +
  fake_notifications_server，无头 CI 不具备，平台限制豁免口径）；
- tests/：unitylaunchertest / knotificationdbustest 由 HAVE_DBUS 守卫
  （USE_DBUS=OFF 时 0 项注册）；
- examples/：无 add_test，且需 Qt6 Quick，已随补丁禁用。
ctest 以 `--no-tests=ignore` 运行：N=0 是实测事实，`--no-tests=error` 会对
真实的 0 测试集误报失败；命令仍真实执行，任何真实测试失败都会红。
消费者侧补全：test_package 两个可执行、18 项检查——12 项 KNotification
属性/动作模型（eventId/title+text/iconName/flags/urgency/componentName/
hints/urls/autoDelete/addAction/addDefaultAction）与 6 项 SONAME/DT_NEEDED
回归（消费者可执行自身 DT_NEEDED 全裸、引用裸 libKF6Notifications.so；
重开产物校验裸 DT_SONAME 与全裸 DT_NEEDED，E537 回归网），CTest 2/2。

## 验证结果

真机（ohos-aarch64 profile，2026-10-17）conan-verify 全链通过，报告（脱敏）
随档：reports/conan-verify-report.md（Verdict: PASS）：

- G0：PASS（已知风险 E092——CMake 无 HarmonyOS platform 模块——已在配方
  侧以 SONAME-only 规则化解）
- G1：PASS（name/version/source/build/package/package_info/export_sources
  齐备、补丁调用、R26 静态链接配置、conandata、test_package + MANIFEST.yml）
- G2：PASS（conan create 成功）
- G3：PASS（纯库包无 bin/；无系统同名库冲突）
- G4：PASS（产物检查）
- L2 / L4 / L5：PASS（跳过——纯库包无 cache 路径，沿批次口径）

证据（conan create 实录，日志依平台规则不随档）：

- recipe revision：`knotifications/6.28.0@ohpcd/stable#bb3de088c40a98413831bda4192cb866`
- package id：`9ac997b13b31904eacd4cb5763db91fb7c96e609`
  （package revision 93a01d13bac0eb0fa472eeffe8ad2008）
- 上游 CTest：本 feature set 注册数 0，`--no-tests=ignore` 下实跑通过
  （命令真实执行，任何真实测试失败仍会使构建变红）
- test_package CTest：2/2（test_knotifications、test_knotifications_ohos，
  100% tests passed, 0 tests failed out of 2）
- 检查计数：TEST PASS 18 / TEST FAIL 0（12 项 API + 6 项 SONAME/DT_NEEDED）
- 产物：lib/libKF6Notifications.so，203328 字节，
  md5 `b7faa87eba984f03189b1b8785420877`
- ELF 动态段：DT_SONAME = 裸 `libKF6Notifications.so`；DT_NEEDED 5 项全裸
  （libQt6Gui.so.6、libKF6ConfigCore.so.6、libQt6Core.so.6、
  libc++_shared.so、libc.so）；无 RPATH/RUNPATH
- install() 产物与构建目录产物逐字节一致（同 md5）——SONAME-only 规则下
  install 不重写 ELF，消费者 dlopen 不受 RUNPATH 剥离影响

构建日志 reports/conan-create.log 依平台规则不随档（reports/ 仅随脱敏 md）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（SONAME 规则 + 测试运行环境） |
| conandata.yml | 源码 URL（官方 + NJU 双源）+ sha256 + 补丁登记 |
| patches/0001-CMakeLists.txt.patch | 5 处适配（依赖上限 / Qml / DBus+Canberra / Python 绑定 / poqm+examples） |
| test_package/ | 消费者测试（12 + 6 项检查，CTest 2/2） |
| manifest.yaml | 版本级元数据 |
| notes.md | 本笔记 |
| reports/conan-verify-report.md | 真机验证报告（脱敏） |
