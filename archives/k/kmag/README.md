# kmag

KMagnifier（kmag）是 KDE 无障碍工具集的屏幕放大器：把鼠标附近的屏幕区域实时放大，
帮助低视力用户看清细节。它是 Qt Widgets 图形界面应用（KXmlGui 主窗口），支持跟随鼠标、
跟随键盘焦点、选区窗口与全屏四种模式，带缩放档位、画面旋转、色觉障碍模拟（红色盲/
绿色盲/蓝色盲/全色盲）以及快照导出。

- 上游：https://apps.kde.org/kmag/ （KDE Gear，随 release-service 发布）
- 源码：https://download.kde.org/stable/release-service/26.04.0/src/kmag-26.04.0.tar.xz
- 版本：26.04.0（首次适配，上游版本号）
- 构建系统：CMake（KDE ECM 标准布局）

## OHOS PC 适配要点

- **PrintSupport 模块缺失**：仓库发布的 qtbase/6.11.1 以
  `FEATURE_printsupport=OFF` 构建，不提供 Qt6PrintSupport。补丁 0001 从
  `find_package(Qt6 ...)` 与链接行删除该组件，补丁 0002 用上游已有的
  `QT_NO_PRINTER` 条件把 QPrinter/QPrintDialog 代码与“打印”菜单项编译掉；
  快照导出（QImageWriter + KIO::file_copy）不受影响。
- **CMake 系统名**：CMake 没有 HarmonyOS 平台模块，system=HarmonyOS 时
  `UNIX=FALSE`，所有 `if(UNIX)` 守卫的探测会被静默跳过；toolchain 设
  `CMAKE_SYSTEM_NAME=Linux`（OHOS 即 Linux 内核）。
- **文档构建**：`BUILD_DOC=OFF`，KF6DocTools 未发布到制品仓，手册不是运行期依赖。
- **翻译目录**：`KF_SKIP_PO_PROCESSING=ON`，设备没有 gettext/msgfmt 工具链。
- **Qt 路径查询**：`QUERY_EXECUTABLE=qtpaths6` 绕过 ECMQueryQt 对
  `Qt6::qtpaths` 目标的解析失败。
- **KF6 版本线**：主链用 6.26.0；kconfigwidgets 制品仓只有 6.18.0，其传递 KF6
  依赖统一 override 到 6.26.0 线（kxmlgui 6.26.0 先例）。
- **链接布局**：`-Wl,-z,max-page-size=0x1000`，避免 lld 默认 64K 页大小把
  .dynsym/.dynstr 拆到独立高地址 RW 段导致 OHOS musl 加载器拒绝映射。

## 依赖

qtbase/6.11.1、kio/6.26.0、kxmlgui/6.26.0、kcrash/6.26.0、ki18n/6.26.0，
KF6 传递闭包 kconfig/kcoreaddons/kguiaddons/kwidgetsaddons/kcolorscheme/kcodecs/
kiconthemes/kitemviews/karchive/kservice（6.26.0 线）、kconfigwidgets/6.18.0、
openssl/3.5.6.1、zstd/1.5.7，构建工具 ecm/6.26.0。

## 使用

```bash
# 当前版本未上传制品仓二进制，需从配方源码构建
conan create archives/k/kmag/26.04.0 \
    -pr:h <ohos-profile> -pr:b <ohos-profile> \
    --build=missing --build=kconfigwidgets/6.18.0 \
    --user=ohpcd --channel=stable
kmag   # Qt6 + KF6 图形界面应用，需图形会话
```
