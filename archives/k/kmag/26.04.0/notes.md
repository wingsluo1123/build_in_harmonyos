# kmag 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake (ConanToolchain via conan)
- 编译日期: 2026-10-18
- 编译器: clang 15 (OHOS SDK, /data/service/hnp/bin/clang++)
- 状态: built（本地 conan create 全量验证 + conan-verify 通过；未上传制品仓）
- package_id: 242b20bd6d8ed51e479359ec9c03675395da5866

## 编译步骤

1. 依赖预检（W0/R35/R36）：`conan install --requires=kio/6.26.0
   --requires=kxmlgui/6.26.0 --requires=kcrash/6.26.0 --requires=ki18n/6.26.0
   --requires=qtbase/6.11.1 -r=ohpcd --build=never` 在真机返回
   `Install finished successfully`（RC=0）。KF6 6.26.0 线齐备；kconfigwidgets
   仅有 6.18.0（其传递 KF6 依赖按 kxmlgui 6.26.0 先例 override 到 6.26 线）；
   kdoctools/kdbusaddons 未发布（BUILD_DOC=OFF、KIO 以 KIOCORE_ONLY/USE_DBUS=OFF 发布）。
2. 确认 qtbase 制品内容：包内 `lib/cmake` 无 Qt6PrintSupport，`lib/libQt6PrintSupport*`
   不存在，平台插件 `plugins/platforms/libqoffscreen.so` 存在（真机实测）。
3. 生成两个移植补丁（`patch -p1 --dry-run` 在全新源码树逐文件验证通过）。
4. W3 正式验证：`conan create archives/k/kmag/26.04.0 -pr:h=ohos-aarch64
   -pr:b=ohos-aarch64 --build=missing --build=kconfigwidgets/6.18.0
   --user=ohpcd --channel=stable` —— 源码缓存命中 → 打补丁 → 构建 → 打包 →
   test_package 消费者用例 11/11 通过。

## 上游测试三步法（R51）

- 清点：26.04.0 tarball 全树无 `tests/`、无 `autotests/`，无任何
  `add_test` / `ecm_add_test` / `enable_testing` / `QTEST_*` 注册；
  `find . -iname '*test*'` 0 命中；`grep -rnE 'add_test|ecm_add_test|QTEST_|enable_testing' .`
  计数 0。源码中的 5 处 `Q_SLOTS` 是应用信号的槽声明，不是测试槽。
- 运行：上游没有可执行测试，无可运行项。
- 回填：上游测试 0 个；消费者用例见 test_package（11/11）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 找不到 Qt6PrintSupport | 发布的 qtbase/6.11.1 以 FEATURE_printsupport=OFF 构建，无该模块（ksystemlog 26.04.0 先例） | 补丁 0001：根 CMakeLists 的 find_package 组件与 src 链接行移除 PrintSupport；给 kmag 目标加 QT_NO_PRINTER |
| 2 | 打印菜单/代码引用 QPrinter | PrintSupport 未发布 | 补丁 0002：kmag.h/kmag.cpp 的 QPrinter/QPrintDialog include 与动作创建用 QT_NO_PRINTER 包住（上游实现已全部在 QT_NO_PRINTER 守卫内）；kmagui.rc 删除两处 file_print 动作 |
| 3 | kconfigwidgets/6.18.0 需要从源码重建 | 6.26 override 改变了它的 package_id（be43a923...），制品仓虽有 6.18 二进制但配置不匹配 | 用 NJU 镜像 kconfigwidgets-6.18.0.tar.xz（sha256 aa5a7be6278a19733f77e6a435f84c3e71926b28f1ac3766313778890d640813）种子到 srccache-isc/s，`--build=kconfigwidgets/6.18.0` 显式构建 |
| 4 | 首次两次 detached conan create 在 “Checking compatible configurations” 阶段被 SIGKILL | 未确定（设备侧直接 kill，日志止于该阶段） | 改为持久 dev-exec 会话运行 + 强制构建 kconfigwidgets 跳过远程兼容配置扫描，后续稳定完成 |
| 5 | GUI 用例报 “Could not find the Qt platform plugin offscreen” | QT_QPA_PLATFORM_PLUGIN_PATH 被设成两个目录的路径串，Qt 把整串当单个目录（debug 日志显示扫描 'a b'） | test_package 去重后只把含 libqoffscreen.so 的目录写入该变量；插件根目录继续走 QT_PLUGIN_PATH |
| 6 | test_package/MANIFEST.yml 缺失导致 conan-verify G1 失败 | 首次提交配方目录时漏了该文件（CI L0e 门禁要求） | 补入配方目录后重跑 conan-verify |

## 源码修改

- `patches/0001-ohos-printsupport-cmake.patch`：
  - 根 `CMakeLists.txt`：`find_package(Qt6 ... COMPONENTS)` 移除 PrintSupport（附 OHOS 说明注释）
  - `src/CMakeLists.txt`：链接行移除 Qt6::PrintSupport；`target_compile_definitions(kmag PRIVATE QT_NO_PRINTER)`
- `patches/0002-ohos-printsupport-source.patch`：
  - `src/kmag.h`：`#include <QPrinter>` 包进 `#ifndef QT_NO_PRINTER`
  - `src/kmag.cpp`：`#include <QPrintDialog>` 与 `m_pPrint = actionCollection()->addAction(...)` 块包进 `#ifndef QT_NO_PRINTER`
  - `src/kmagui.rc`：删除菜单内两处 `<Action name="file_print"/>`
- 无平台宏注入（PF5）；所有改动均为能力缺失下的按上游既有宏收缩，快照导出（QImageWriter + KIO::file_copy）不受影响。

## 依赖版本

- qtbase/6.11.1（Qt6 Core/Gui/Widgets/Network；无 PrintSupport）
- KF6 6.26.0：kio、kxmlgui、kcrash、ki18n、kconfig、kcoreaddons、kguiaddons、
  kwidgetsaddons、kcolorscheme、kcodecs、kiconthemes、kitemviews、karchive、kservice
- kconfigwidgets/6.18.0（制品仓唯一版本，传递依赖 override 到 6.26 线）
- 间接：qtsvg/6.11.1、libxml2/2.15.3、openssl/3.5.6.1、zstd/1.5.7
- tool_requires: ecm/6.26.0

## 验证结果

### 对话 #1（2026-10-18）

- 用户：将 kmag 26.04.0 适配鸿蒙 PC（aarch64-linux-ohos），按积分赛流程执行。
- 助手：W0 依赖预检通过；生成 PrintSupport 裁剪补丁；真机 conan create 构建 +
  test_package 11/11（安装产物可执行、--version 26.04.0、--help 横幅、
  offscreen KXmlGui 主窗口启动、qimage_smoke 快照导出链路 7 项）；
  conan-verify 见 reports/conan-verify-report.md。
- 结论：状态 built，package_id 242b20bd6d8ed51e479359ec9c03675395da5866。

```bash
# W3 正式验证
$ conan create archives/k/kmag/26.04.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
    --build=missing --build=kconfigwidgets/6.18.0 --user=ohpcd --channel=stable
...
[test] application binary: .../p/bin/kmag
TEST PASS: installed bin/kmag is executable
TEST PASS: kmag --version reports 26.04.0
TEST PASS: kmag --help shows the KAboutData banner
TEST PASS: kmag main window starts offscreen (KXmlGui resources loaded)
TEST PASS: temporary export directory is created
TEST PASS: PNG image writer is available
TEST PASS: magnified view is written to a PNG file
TEST PASS: exported snapshot file exists and is non-empty
TEST PASS: exported snapshot can be read back
TEST PASS: restored size matches the source
TEST PASS: restored pixel matches the rendered view
TEST SUMMARY: 11 passed, 0 failed
kmag/26.04.0@ohpcd/stable (test package): kmag consumer tests passed
```
---
**编译结束**: 2026-10-18
**最终状态**: built
