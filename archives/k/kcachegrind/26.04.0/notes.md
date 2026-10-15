# kcachegrind 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（CMake 4.1.2）+ KDE ECM 6.29.0
- 编译日期: 2026-10-15
- 编译器: clang 22.1.8 / clang++（HarmonyOS PC aarch64，profile `ohos-aarch64`：
  os=OHOS、os.version=6.0、arch=armv8、compiler.libcxx=libc++、compiler.cppstd=17、
  build_type=Release）
- Conan: 2.29.1（OHOS 适配版），remote `ohpcd`
- 状态: built

## 源码
- 官方源: `https://download.kde.org/stable/release-service/26.04.0/src/kcachegrind-26.04.0.tar.xz`
  （R39 官方 HTTPS；KDE Release Service 26.04.0）
- sha256: `476919c3a9bec436b1a55a6c1a28ebfb07b43d6e22c05c6a476d0bfa537c8fa4`
- 上游仓库: https://invent.kde.org/sdk/kcachegrind （GPL-2.0-or-later）

## 依赖版本（W0 探测：全部已发布后才开工）
| 依赖 | 版本 | 角色 |
|---|---|---|
| qtbase | 6.11.1.1 | Qt6 Core/Gui/Widgets/**DBus**（`FEATURE_dbus=ON` 变体；上游 main.cpp 的 `KDBusService` 需要 Qt6DBus） |
| kdbusaddons | 6.29.0 | `KDBusService` |
| kio | **6.14.0** | `KF6::KIOCore/KF6::KIOGui/KF6::KIOWidgets`。**ohpcd 上的 kio/6.26.0 是 KIOCORE_ONLY 变体（无 KIOWidgets），上游 `kcachegrind/CMakeLists.txt` 显式链接 `KF6::KIOWidgets` ⇒ 必须取 6.14.0 完整变体** |
| kxmlgui | 6.18.0 | `KF6::XmlGui`（KXmlGuiWindow / KRecentFilesAction / KStandardAction） |
| kconfigwidgets | 6.18.0 | `KF6::ConfigGui`（KColorButton） |
| karchive | 6.19.0 | `KF6::Archive`；对齐 kiconthemes/6.18.0 **已发布二进制**的钉版 |
| kconfig / kcoreaddons / ki18n / kwidgetsaddons / kjobwidgets / kservice / kcolorscheme / kguiaddons / kiconthemes / kitemviews / kwindowsystem / kauth / solid / kbookmarks / kcompletion / kcodecs / kcrash / knotifications | 6.18.0 | `kio/6.14.0` 内部 6.14 钉版由 `override=True` 整图抬到 6.18 闭包 |
| openssl | 3.5.6.1 | `KF6ArchiveConfig.cmake` 硬性 `find_dependency(OpenSSL)`；必须作为**直接** requires 才会下载二进制（ktimer 先例） |
| libxml2 | 2.15.3 | OHOS SDK lld 链接期需要 `libxml2.so.16`（其 SONAME） |
| extra-cmake-modules | 6.29.0（tool_requires） | `find_package(ECM REQUIRED NO_MODULE)` |

`conan graph info` 实测：**`Missing packages` = 仅 `kio`**，其余 31 个包全部命中已发布
二进制；kio 配方自带 `BUILD_TESTING=OFF`，本地重建不跑上游测试。

## 编译步骤
1. `init-build kcachegrind 26.04.0 --url=<官方 tarball>`（构建系统自动识别为
   autotools 属误判——包内含 `po/` 目录的 autotools 痕迹；实际为纯 CMake，
   按 CMake 走 `conan-init` → 手写 CMake 配方）。
2. W0 依赖预检：逐包 `conan download <pkg>/<ver> -r=ohpcd --only-recipe`（R35）。
3. `conan create archives/k/kcachegrind/26.04.0 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64
   --build=missing`（= W3 本地验证口径）。
4. `conan-verify kcachegrind 26.04.0`（G0–G4 + L2/L4/L5）。
5. `graph validate`（W5）。

关键 CMake 变量：`BUILD_TESTING=OFF`、`KF_IGNORE_PLATFORM_CHECK=TRUE`、
`KF_SKIP_PO_PROCESSING=ON`、`CMAKE_INSTALL_LIBDIR=lib`、
`CMAKE_EXE_LINKER_FLAGS_INIT="-Wl,-z,max-page-size=0x1000 -Wl,--disable-new-dtags -Wl,-rpath,<dep libs>"`。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游链接 `KF6::KIOWidgets`，ohpcd 的 kio/6.26.0 无此库（KIOCORE_ONLY 变体） | kio 6.26 配方为绕开未发布的 solid/kbookmarks/kcolorscheme/kjobwidgets/kiconthemes 6.26 而裁成 KIOCore-only | 改用带 KIOWidgets 的 **kio/6.14.0** + `override=True` 把闭包抬到 6.18 线（ktimer 26.04.0 同款）；源码实证 kcachegrind 只用 `KIO::file_copy`（KIOCore）与 `KJobWidgets::setWindow`，功能零裁剪 |
| 2 | `Could NOT find OpenSSL`（`KF6ArchiveConfig.cmake:51 find_dependency`）| karchive 配方不声明 openssl；只经 kiconthemes 传递时 conan 判 `files=False` 而 BINARY_SKIP，包不落地 | 新增**直接** requires `openssl/3.5.6.1`（ktimer CI #65871 的修法） |
| 3 | **`kcachegrind --version` 退出码 1**，输出 `kf.dbusaddons: DBus session bus not found` | 上游 `main.cpp` 在解析命令行**之前**构造 `KDBusService`；kdbusaddons 6.29 在找不到会话总线时直接终止进程。OHOS 无 D-Bus 会话总线 ⇒ 程序在任何参数下都启动即退出 | 补丁 `0001-kcachegrind-main.cpp.patch`：仅当 `QDBusConnection::sessionBus().isConnected()` 为真时才构造 `KDBusService`（`std::unique_ptr` 持有）。该对象在本程序内无其他消费者，跳过它只关闭 D-Bus 激活；有会话总线的系统行为完全不变 |
| 4 | `doc/` 与 `kdoctools_install(po)` 需要 KF6DocTools | 上游 `find_package(KF6DocTools)` 为 `TYPE OPTIONAL`，非 REQUIRED | 不声明 kdoctools 即由 `KF6DocTools_FOUND` 守卫自动跳过，**无需补丁**（代价：在线手册不可用） |
| 5 | 主二进制裸名 `DT_NEEDED`（`libKF6KIOCore.so` 等）在 OHOS musl 下无法解析 | OHOS musl 加载器不认 `LD_LIBRARY_PATH`（E088 族），而 Qt6/KF6 预编译包普遍无 DT_RPATH/DT_RUNPATH | `generate()` 用 `-Wl,--disable-new-dtags -Wl,-rpath,<全部依赖 lib>` 写入 **DT_RPATH**（对整棵依赖树生效）——运行时 31 项冒烟含真实 GUI 加载 trace 全绿 |
| 6 | 12/27 个 `DT_NEEDED` 是 conan 缓存绝对路径（如 `/storage/.../kxmlg.../p/lib/libKF6XmlGui.so`） | ohpcd 上发布的 KF6 库不带 `DT_SONAME`（CMake 的 OHOS 平台不认 VERSION/SOVERSION），ld 只能按链接行的绝对路径记录（E537 族） | **已知生态限制，非本配方缺陷**：仓内同族包实测同形（kbreakout、kcolorchooser、kio 自带 `ktelnetservice6`、kcoreaddons 的 `kiconfinder6` 为 `../../../bin/...` 相对路径）。test_package 如实记录为 INFO 不判失败；DT_RPATH 覆盖全部依赖 lib 目录保证运行期可解析 |
| 7 | **远端 CI 到 test_package 阶段失败（构建 #92573，26/31）**：`Error loading shared library ../../bin/libKF6ConfigCore.so (needed by …/libKF6ConfigGui.so)`、`../../bin/libKF6IconThemes.so (needed by …/libKF6IconWidgets.so)`；**本地 conan create 却 31/31 全过** | 含 `/` 的 `DT_NEEDED` 被加载器当成**相对 CWD 的路径**直接打开，绕过 DT_RPATH/LD_LIBRARY_PATH。CI worker 缓存里的 kconfigwidgets/kiconthemes 是**上游配方在 worker 上本地重建**出来的同一 package_id 副本（Conan 不校验同名 package_id 的字节一致性），其 intra-package 链接记录了生产者的 `../../bin/<lib>.so`；本机 `~/.cache/conan2` 恰好存在且副本为发布方构建（绝对路径），故本地不暴露 | test_package 增加 `_reconstruct_kf6_rpaths()`（kteatime/ktimer 26.04.0 先例）：把全部依赖 `.so` 实体复制到 `<conan_cache>/bin`（并兜底 `<home>/.conan2 → cache_home` 软链），测试以 `<conan_cache>/recon/kcg` 为 CWD 运行 ⇒ `../../bin/<lib>.so` 命中。**已用自造 ELF 实验证明机制**：无 SONAME 的 `libB.so` 记 `NEEDED ../../bin/libA.so` 后，在无关 CWD 报同款 `OSError: Error loading shared library ../../bin/libA.so`，在 `recon/kcg` 下 `LOADED OK` |
| 8 | 前 6 次 CI 尝试全部基础设施故障（非本包） | worker 进程 spawn 资源耗尽（`posix_spawn failed: Resource temporarily unavailable` / `/bin/sh: Resource temporarily unavailable`、`make … Error 127`）或 worker 挂死（`mkdir` 超时 1200s） | 按踩坑清单 #10 重触发 `/rebuild` 换 worker（同批 #15874 亦 PASS→FAIL→PASS）；第 7 次才跑到真实失败（即第 7 行） |

| 9 | **pc-pr-review rule12 FAIL**：「鸿蒙特有测试行只有断言（N=26），不算完整消费者用例」 | test_package 旧版把「产物布局 9 + ELF 17」当作鸿蒙特有测试的全部（纯断言），把唯一的功能冒烟放在「集成测试」行 | 按要求重构 test_package 为**3 个消费者「用例」**，其中 **CASE 2 = 完整消费者用例（Callgrind 剖面分析端到端流程）**：构造确定性语料（含仅入口改名的对照语料）→ offscreen 真实运行安装后的 `bin/kcachegrind` → 产出 `Selected "<fn>"` 与 `kcachegrindrc` → 与**独立 Python 参考解析器**比对 + 对照语料反向验证 + KConfig 写回校验；鸿蒙特有测试行改为按用例申报（CASE 2 + CASE 3），合计 3 用例 / 35 断言 |

## 源码修改
`patches/0001-kcachegrind-main.cpp.patch`（`patch_type: portability`，由
`refresh-patch --auto` 生成，1 文件 +13/-1）：
- `kcachegrind/main.cpp`：`#include <memory>`、`#include <QDBusConnection>`；
  把 `KDBusService service(KDBusService::Multiple);` 改为「仅在会话总线可用时构造」。
- 补丁不含任何平台宏（符合 R8 / PF5 口径）：用运行期能力探测
  （`QDBusConnection::sessionBus().isConnected()`）而非 `__OHOS__` 条件编译。

无其他源码改动；`conandata.yml` 单值官方 URL，无镜像残留。

## 验证结果

```
$ conan create archives/k/kcachegrind/26.04.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
...
======== Installing packages ========
kcachegrind/26.04.0: Already installed! (32 of 32)
======== Testing the package: Executing test ========
== kcachegrind consumer smoke (bin=.../p/bin/kcachegrind) ==
  [PASS] bin/kcachegrind installed / executable
  [PASS] converter bin/{dprof2calltree,hotshot2calltree,memprof2calltree,op2calltree,pprof2calltree}
  [PASS] desktop metadata share/applications/org.kde.kcachegrind.desktop / metainfo appdata
  [PASS] PIE (ET_DYN) / GNU_STACK / DT_RPATH present
  [PASS] DT_NEEDED 链接到 libKF6KIOCore/KIOWidgets/KIOGui/XmlGui/ConfigGui/ConfigCore/
         DBusAddons/CoreAddons/I18n/WidgetsAddons/JobWidgets + libQt6Widgets/libQt6DBus
  [PASS] kcachegrind --version → rc=0，输出 `kcachegrind 26.04.0`
  [PASS] 功能冒烟：offscreen 加载 mini.callgrind → 输出 `Selected  "main"`
         （trace loader 真实解析成功），GUI 存活 30s 未崩，无 loader/symbol 错误
== 35/35 checks passed ==
== 3 个消费者用例：CASE1 运行期冒烟 / CASE2 完整端到端剖面分析 / CASE3 产物与 ELF ==
KCACHEGRIND CONSUMER CASES: ALL PASS
```

上游测试清点（R51 第一步）：源码树 `find . -iname '*test*'` = 0 个文件；全部
`CMakeLists.txt` 中 `add_test`/`enable_testing`/`BUILD_TESTING` 出现 0 次
⇒ 上游确无测试套件（N_static = 0），消费者验证由 test_package 补全
（实测 **3 个消费者用例 / 35 条断言全过**，其中 CASE 2 为 rule12 要求的完整端到端消费者用例；口径见 `reports/test-report.md`）。

## 注意事项
- 功能零裁剪：调用图/调用矩阵/源码与反汇编注解/Treemap 等全部视图、KIO
  打开与另存路径、KXmlGui 菜单工具栏均保留；唯一行为差异是无会话总线时不再
  因 `KDBusService` 而启动失败。
- `KF_SKIP_PO_PROCESSING=ON` 使包内不含 `.qm` 翻译目录（msgfmt/lconvert 在本
  平台不可用），界面回落到英文，非功能缺陷。
- 转换脚本（`bin/*2calltree`）依赖 perl/php/python 运行时，OHOS 无需随包提供；
  它们与 `bin/kcachegrind` 一同安装，属上游默认交付物。
---

**编译结束**: 2026-10-15 00:58
**最终状态**: built
