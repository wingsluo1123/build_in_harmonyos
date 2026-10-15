# kcachegrind

KCachegrind 是 KDE 的性能剖析数据可视化工具（KDE Gear 26.04.0，
invent.kde.org/sdk/kcachegrind）：读取 Callgrind / Cachegrind / Valgrind
（`cachegrind.out.*`、`callgrind.out.*`）产生的剖析数据，以调用图、调用矩阵、
源码/反汇编注解、Treemap 等视图展示热点函数与调用关系。纯 Qt Widgets GUI
应用，无后台守护进程；随包附带 5 个 callgrind 格式转换脚本。

- 上游：https://invent.kde.org/sdk/kcachegrind
- 适配版本：26.04.0（`archives/k/kcachegrind/26.04.0/`）
- 构建系统：CMake + KDE ECM（`find_package(ECM REQUIRED NO_MODULE)`）
- 依赖基座：qtbase/6.11.1.1（FEATURE_dbus=ON，唯一 Qt6 提供者）、
  kdbusaddons/6.29.0、**kio/6.14.0**（带 `KF6::KIOWidgets` 的完整变体）、
  kxmlgui/6.18.0、kconfigwidgets/6.18.0、kconfig/kcoreaddons/ki18n/
  kwidgetsaddons/kjobwidgets 等 6.18.0 闭包、karchive/6.19.0（对齐
  kiconthemes 已发布二进制）、openssl/3.5.6.1（`KF6ArchiveConfig.cmake` 硬性
  `find_dependency(OpenSSL)`）、libxml2/2.15.3（OHOS SDK lld 链接期依赖）、
  extra-cmake-modules/6.29.0（tool_requires）
- 依赖闭包：`conan graph info` 实测 rc=0、**仅 kio 一个包需本地重建**
  （其配方自带 `BUILD_TESTING=OFF`，不跑上游测试），其余全部命中已发布二进制
- 上游源码补丁：**1 个** —— `patches/0001-kcachegrind-main.cpp.patch`
  （`patch_type: portability`，+13/-1）：`main()` 改为仅当
  `QDBusConnection::sessionBus().isConnected()` 为真时才构造 `KDBusService`；
  kdbusaddons 在无会话总线时于构造函数内终止进程，导致 OHOS 上启动即退出。
  补丁不含平台宏（R8 合规），有会话总线的系统行为与上游一致。
  另有 `KF6DocTools` 为非 REQUIRED 可选依赖，`doc/` 由 `KF6DocTools_FOUND`
  守卫，不声明 kdoctools 即自动跳过（**无需补丁**）
- 上游测试：0（源码树无 tests/、无 `add_test`/`enable_testing`；QA 由 KDE CI
  源码构建承担），由 `test_package/` 消费者验证补全（R51 第三步）：**3 个用例 /
  35 条断言**，其中 **CASE 2 是 rule12 要求的完整消费者用例**（Callgrind 剖面分析
  端到端流程：确定性语料 → offscreen 真实运行产品 → `Selected "<fn>"` 与独立
  Python 参考实现比对 + 入口改名的对照语料反向验证 + `kcachegrindrc` KConfig 写回）
- **消费者测试环境重建**：KF6 依赖库存在坏 `DT_NEEDED`（相对 `../../bin/<lib>.so`
  被加载器按 CWD 解析；绝对路径指向构建方 conan home）——`test_package/conanfile.py`
  的 `_reconstruct_kf6_rpaths()` 按 kteatime/ktimer 26.04.0 先例把依赖 `.so` 复制到
  `<conan_cache>/bin` 并以 `<conan_cache>/recon/kcg` 为 CWD 运行测试。
  CI 实测该缺陷只在 worker 缓存（上游配方在 worker 上本地重建的同 package_id 副本）
  上暴露，本开发机不可复现
- 命令入口：`bin/kcachegrind` 及 `bin/{dprof2calltree,hotshot2calltree,
  memprof2calltree,op2calltree,pprof2calltree}`（见本目录 `commands.json`）

## 与上游的差异

| 项 | 上游默认 | OHOS 适配 | 原因 |
|---|---|---|---|
| `KF6::KIOWidgets` 来源 | kio 全量变体 | kio/6.14.0（6.26.0 在 ohpcd 上是 KIOCORE_ONLY 变体，无 KIOWidgets） | 上游 `kcachegrind/CMakeLists.txt` 显式链接 `KF6::KIOWidgets` |
| 在线手册（`doc/`、`kdoctools_install(po)`） | 依赖 `KF6DocTools` | 不构建 | 可选依赖，非 REQUIRED，守卫自动跳过 |
| `.qm` 翻译目录 | `ki18n_install(po)` | 关闭（`KF_SKIP_PO_PROCESSING=ON`） | msgfmt/lconvert 在本平台不可用，非功能必需 |
| KDE 平台白名单检测 | 启用 | 关闭（`KF_IGNORE_PLATFORM_CHECK=TRUE`） | OHOS 不在 KDE 平台列表 |
| 运行期库搜索 | 依赖系统安装布局 | 二进制写 DT_RPATH（依赖 lib 目录） | OHOS musl 加载器不认 `LD_LIBRARY_PATH`，Qt6/KF6 预编译包无 RUNPATH |
| D-Bus 应用激活（`KDBusService`） | 启动时无条件构造 | 仅当会话总线可达时构造 | 无会话总线时上游构造即终止进程（OHOS 无 D-Bus 会话总线）；`KDBusService::Multiple` 无单实例语义，跳过仅关闭 D-Bus 激活 |

功能裁剪为零：所有视图、文件打开/另存（KIO `file_copy`）、D-Bus 单实例
（`KDBusService`，有会话总线时）路径均保留；无会话总线时唯一的差异是跳过
D-Bus 激活而非启动失败。
