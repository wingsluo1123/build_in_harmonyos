# kdialog

KDE 对话框 shell 工具（KDE Gear 26.04.0，invent.kde.org/utilities/kdialog）：
从 shell 脚本弹任意 KDE 风格对话框的 **kdialog 本体**（`bin/kdialog`：
msgbox/yesno/yesnocancel/inputbox/imgbox/textbox/textinputbox/combobox/
menu/checklist/radiolist/passivepopup/getopenfilename/getsavefilename/
getexistingdirectory/geticon/progressbar/getcolor/slider/calendar 等）加
**--progressbar 的 D-Bus 助手**（`bin/kdialog_progress_helper`，
org.kde.kdialog-<pid> 服务，`qt_add_dbus_adaptor()` 自
org.kde.kdialog.ProgressDialog.xml 生成适配器）。

- 上游：https://invent.kde.org/utilities/kdialog
- 适配版本：26.04.0（`archives/k/kdialog/26.04.0/`）
- 构建系统：CMake + KDE ECM（release-service tarball）
- 依赖基座：qtbase/6.11.1.1（FEATURE_dbus=ON，override）、qtsvg/6.11.1、
  ktextwidgets/knotifications/kguiaddons/kiconthemes/kwindowsystem/kio
  6.26.0 主干、kdbusaddons/6.18.0、KF6 6.26.0 覆盖闭包（kconfig/
  kcoreaddons/kcrash/kcolorscheme/kcodecs/kwidgetsaddons/karchive）、
  kcompletion/6.26.0.1、sonnet/kservice 6.26.0、openssl/3.5.6.1、
  zstd/1.5.7、expat/2.8.2.1、libxml2/2.15.3、ecm/6.26.0（tool_requires）
- 上游源码补丁：**2 个**（`patch_type: portability`，不含平台宏，R8 合规）：
  - `patches/0001-ohos-link-kiocore.patch`：已发布 kio/6.26.0 为
    KIOCORE_ONLY 基线（无 libKF6KIOWidgets）；kdialog 唯一 KIO 符号
    `KRecentDocument::add()`（--getsavefilename 分支）由 KIOCore 导出，
    `KF6::KIOWidgets` -> `KF6::KIOCore` 一行链接替换即保留最近文档功能
    （KColorMimeData 属 KGuiAddons 不受影响；KF6::IconWidgets 属
    kiconthemes 同一配置，正常供应）。
  - `patches/0002-ohos-explicit-framework-links.patch`：ohpcd KF6 制品
    不传播依赖组件的传递 include 目录（依赖链接被拍平为 -lKF6Xxx 与
    绝对 INTERFACE_LINK_DIRECTORIES）——直用的 KF6::WidgetsAddons
    （KMessageBox/KPasswordDialog/KNewPasswordDialog/KDatePicker）、
    KF6::CoreAddons（KAboutData）、KF6::ConfigCore（KConfig）、
    KF6::I18n（KLocalizedString）显式声明进 find_package 组件表
    （KConfig 的组件名为 Config）与 target_link_libraries。
- 上游测试：**0 用例**（tests/ 仅 3 个交互式演示脚本且不在构建内；见
  `test_package/MANIFEST.yml` 清点证据）；`BUILD_TESTING=OFF`。
- 消费者验证（`test_package/`，R51 第三步）：5 用例 / **10 断言** +
  1 鸿蒙特有用例 / 2 断言（共 12）——两个产物可执行；--version 报告
  26.04.x；--help 选项面完整（--passivepopup/--progressbar 注册在案）；
  --author（David Faure）/--license（GPL）元数据；未知选项非零退出 +
  "Unknown option" 诊断；[鸿蒙特有] --msgbox 模态事件循环 3 秒存活探针
  （兼门禁 kdialog 本体 DT_NEEDED closure）+ kdialog_progress_helper
  直接启动的闭包加载门禁。
- 已知交互路径限制（如实申报，配方 docstring 同步）：`--passivepopup`
  在无会话总线时挂起（26.04.0 无 KPassivePopup 回退，
  `sendVisualNotification()` 返回 false 后 `qApp->exec()` 无窗口可退）；
  `--progressbar` 需 helper 在 PATH 且等待 D-Bus 客户端关闭对话框。
  消费者用例以 --msgbox 存活探针与 helper 直接启动替代验证。

## 与上游的差异

| 项 | 上游默认 | OHOS 适配 | 原因 |
|---|---|---|---|
| KIO 链接目标 | `KF6::KIOWidgets` | `KF6::KIOCore`（补丁 0001） | 已发布 kio 为 KIOCORE_ONLY 基线，唯一 KIO 符号在 KIOCore |
| KF6 直用框架声明 | 依赖全量 KF6 安装的传递 include | 显式组件与显式链接（补丁 0002） | ohpcd KF6 制品不传播依赖组件的 include 目录 |
| X11 集成 | 启用（HAVE_X11） | 关闭（WITHOUT_X11=ON） | 平台无 X11 头/库 |
| `.qm` 翻译目录 | `ki18n_install(po)` | 关闭（KF_SKIP_PO_PROCESSING=ON） | msgfmt/lconvert 在本平台不可用，非功能必需 |
| KDE 平台白名单检测 | 启用 | 关闭（KF_IGNORE_PLATFORM_CHECK=TRUE） | OHOS 不在 KDE 平台列表 |
| KF6DocTools（可选文档） | 找到即构建 | 显式禁用 | 未发布；26.04.0 本无 doc/，防御性 |

功能裁剪：无（两处源码变更均为构建配置级：KIOWidgets -> KIOCore 等价
替换、直用框架显式声明）；交互对话框行为与上游一致。
