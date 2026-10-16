# kcron

KDE 任务计划程序（KDE Gear 26.04.1，invent.kde.org/utilities/kcron）：
Plasma 系统设置中的 **QML KCM**（`kcm_cron.so` + `kcmdesktopfilegenerator`
生成的 `kcm_cron.desktop`）加一个 **KAuth 提权助手**（`kcron_helper` 及
`local.kcron.crontab` 激活文件），用于查看/编辑当前用户与系统 crontab
（任务、变量、启用状态、注释），并可将 crontab 导出为 PDF。

- 上游：https://invent.kde.org/utilities/kcron
- 适配版本：26.04.1（`archives/k/kcron/26.04.1/`）
- 构建系统：CMake + KDE ECM（release-service tarball）
- 依赖基座：qtbase-sql-dbus/6.11.1、qtdeclarative/qtsvg/qtshadertools/
  qtmultimedia 6.11.1、kcmutils/6.26.0（KF6::KCMUtils + 宏）、
  kauth/6.26.0（KF6::AuthCore）、kio/kxmlgui/kitemviews 6.26.0、
  kconfigwidgets/6.18.0、kirigami/6.18.0、kirigami-addons/1.13.0、
  KF6 6.26.0 覆盖闭包（kconfig/kcoreaddons/kguiaddons/ki18n/
  kwidgetsaddons/kcolorscheme/kcodecs/kiconthemes/kcrash）、
  openssl/3.5.6.1、zstd/1.5.7、libxml2/2.15.3、ecm/6.26.0（tool_requires）
- 上游源码补丁：**7 个**（`patches/0001`–`0007`，`patch_type: portability`，
  均不含平台宏，R8 合规）：
  - 0001/0002/0003：已发布 qtbase 以 `FEATURE_printsupport=OFF` 构建、
    无 Qt6PrintSupport 模块（algobox/conducteo/ksystemlog 26.04.0 先例）。
    PrintSupport 从必需组件移除（显式请求 Gui/Widgets），cron 打印动作
    改走 `QPdfWriter`（QtGui）+ `QFileDialog::getSaveFileName` 的 PDF
    导出流程；
  - 0004：`CTHost` 构造中对 `getpwuid()` 空结果不再解引用（无
    /etc/passwd 条目的 uid 下上游会直接终止宿主进程），降级为
    `CTInitializationError`；
  - 0005/0006：`TasksModel`/`VariablesModel` 在
    `create()/applyCreate()/paste()/refresh()` 容忍空当前用户 cron
    （本平台无 crontab 后端），模型保持可用（空、可添加、可校验）；
  - 0007：`taskvalidatortest` 的两个绝对路径用例（
    `testAbsolutePathExecutable`/`testAbsolutePathWithArguments`）
    可移植化：构建 uid 无法搜索 `/usr/bin` 且平台无
    `/usr/bin/true`|`printf`，改用 `QCoreApplication::applicationFilePath()`
    （任何构建环境中都存在且可执行的绝对路径），保持两用例原意
    （裸绝对路径 / 带引号路径加参数），真机与 Linux CI 同口径通过。
- 上游测试：**1 目标 / 9 用例**（`taskvalidatortest`，见
  `test_package/MANIFEST.yml` 清点证据）；配方 `BUILD_TESTING=ON` 在
  `build()` 内真实执行 ctest（Qt offscreen + KF6 运行环境归一化，
  kcmutils 6.26.0 先例）。
- 消费者验证（`test_package/`，R51 第三步）：7 组 / 25 断言 —— 产物定位、
  QPluginLoader、`KPluginFactory::instantiatePlugin<QObject>` 实例化
  真实 KCM（QObject 接口沿继承链匹配）、空 cron 下的模型/粘贴守卫、
  真实 `QQmlEngine` 驱动 `org.kde.private.kcms.cron` 的任务校验流程
  （空命令拒绝/真实可执行通过/缺失路径报 File not found）。
- 已知交互路径限制（如实申报，配方 docstring 同步）：`save()` 与
  KCM 的 add/modify/remove 槽对 `currentCron()` 无空值检查，仅可从完整
  Plasma 会话的交互动作到达；本平台无法显示 System Settings 会话，
  非交互面（构造、模型、任务创建、校验、打印器接线）已由消费者用例覆盖。

## 与上游的差异

| 项 | 上游默认 | OHOS 适配 | 原因 |
|---|---|---|---|
| cron 打印 | Qt PrintSupport 打印对话框（QPrinter） | `QPdfWriter` PDF 导出（QFileDialog 保存路径） | 已发布 qtbase 无 PrintSupport 模块 |
| `CTHost` 初始化（无 passwd 条目 uid） | `getpwuid()` 空指针解引用 → 宿主进程终止 | 降级为 `CTInitializationError`，KCM 继续加载 | 平台允许无 /etc/passwd 条目的 uid |
| `TasksModel`/`VariablesModel`（空当前用户 cron） | 解引用空 `CTCron*` | 容忍空 cron，模型保持空可用 | 平台无 crontab 后端 |
| `.qm` 翻译目录 | `ki18n_install(po)` | 关闭（`KF_SKIP_PO_PROCESSING=ON`） | msgfmt/lconvert 在本平台不可用，非功能必需 |
| KDE 平台白名单检测 | 启用 | 关闭（`KF_IGNORE_PLATFORM_CHECK=TRUE`） | OHOS 不在 KDE 平台列表 |
| KF6DocTools（可选文档） | 找到即构建 | 显式禁用 | 未发布，非必需 |

功能裁剪：打印对话框 → PDF 导出为形态替换（功能保留）。其余功能区
（任务/变量表、校验、启用状态、KAuth 助手安装）与上游一致。
