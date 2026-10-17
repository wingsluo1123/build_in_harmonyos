# kdialog 26.04.0 鸿蒙 PC 适配笔记

上游: <https://invent.kde.org/utilities/kdialog>
版本: 26.04.0（KDE Gear 26.04.0 发行版）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

产物（install 树）：

- `bin/kdialog` —— 对话框 shell 工具本体（Qt6/KF6 Widgets）：从脚本弹
  msgbox/yesno/inputbox/imgbox/textbox/textinputbox/combobox/menu/
  checklist/radiolist/passivepopup/getopenfilename/getsavefilename/
  getexistingdirectory/geticon/progressbar/getcolor/slider/calendar 等
  全部 KDE 风格对话框；
- `bin/kdialog_progress_helper` —— `--progressbar` 对话框的 D-Bus 服务
  （org.kde.kdialog-<pid>），由 `qt_add_dbus_adaptor()` 自
  org.kde.kdialog.ProgressDialog.xml 生成适配器。

平台适配 **2 个补丁**（`patch_type: portability`，均为平台中立源码变更、
不含平台条件编译宏，R8 合规）：

1. **KIOWidgets 缺失**（0001）：已发布 kio/6.26.0 为 KIOCORE_ONLY 基线
   （无 libKF6KIOWidgets）——kdialog 唯一 KIO 符号 KRecentDocument::add()
   由 KIOCore 导出，`KF6::KIOWidgets` -> `KF6::KIOCore` 替换即保留最近
   文档功能（详见问题 1）。
2. **KF6 传递头目录缺失**（0002）：ohpcd KF6 制品不向消费者传播依赖
   组件的 include 目录——直用的 KF6::WidgetsAddons/CoreAddons/
   ConfigCore/I18n 显式声明进 find_package 组件表（KConfig 的组件
   名为 Config）与 target_link_libraries（详见问题 2）。

测试口径：

- 上游套件：**0 用例**（tests/ 仅 3 个交互式演示脚本且不在构建内；
  清点证据见 `test_package/MANIFEST.yml`），`BUILD_TESTING=OFF`；
- 消费者测试（`test_package/`，R51 第三步）：5 用例 / **10 断言** +
  1 鸿蒙特有用例 / 2 断言（共 12）；
- 真机八门禁：**G0–G4 全 PASS，Verdict=PASS**（L2/L4/L5 无 cache 路径跳过；reports/conan-verify-report.md）。

## 二、问题与处置

### 问题 1：kio/6.26.0 无 KIOWidgets 库（补丁 0001）

上游 `src/CMakeLists.txt` 的 `target_link_libraries(kdialog ...)` 含
`KF6::KIOWidgets`。ohpcd 的 kio/6.26.0 是 KIOCORE_ONLY 基线：只发布
libKF6KIOCore 与 kioworker/ktrash6/file/remote/trash workers；
KIOWidgets 库需要 kbookmarks/solid/kjobwidgets/kiconthemes 6.26 整链，
其中数个未发布。

**处置**：链接目标一行替换为 `KF6::KIOCore`。kdialog 对 KIO 的全部
使用即 `KRecentDocument::add()`（`--getsavefilename` 分支），而
KRecentDocument 由 KIOCore 导出（kio `src/core/krecentdocument.cpp`，
`class KIOCORE_EXPORT KRecentDocument`）——最近文档功能完整保留。
另一处 "KIO 观感" 的调用 `KColorMimeData::fromMimeData()`
（`--getcolor` 分支）实际属于 KGuiAddons，不受影响；`KF6::IconWidgets`
是 kiconthemes 在同一 KF6IconThemes CMake 配置中导出的第二个库，随
kiconthemes/6.26.0 正常供应。补丁为纯链接替换（平台中立、无条件应用）。

### 问题 2：已发布 KF6 制品不传播传递头目录（补丁 0002）

ohpcd 的 KF6 6.26.0 制品导出语义：每个框架的 CMake 配置只导出自身的
`${_IMPORT_PREFIX}` 相对头目录，其依赖组件的链接被拍平为 `-lKF6Xxx`
标志与绝对 `INTERFACE_LINK_DIRECTORIES`——依赖组件的头目录不进
`INTERFACE_INCLUDE_DIRECTORIES`，消费者拿不到传递 include 闭包（全量
自建 KF6 安装下由组件配置的依赖声明隐式提供）。

上游 kdialog 直用 KMessageBox/KPasswordDialog/KNewPasswordDialog/
KDatePicker（KWidgetsAddons）、KAboutData（KCoreAddons）、KConfig
（KConfigCore）、KLocalizedString（KI18n）等头，但只对 KF6::TextWidgets
等链接目标显式声明。**处置**（补丁 0002）：在顶层
`find_package(KF6 ... COMPONENTS ...)` 与 `target_link_libraries(kdialog
...)` 中显式声明上述四个直用框架。KConfig 框架的 find_package 组件名
为 `Config`——首轮补丁误按目标名写成 `ConfigCore`，G2 configure 即报
`Could NOT find KF6 (missing: ConfigCore)`；`KF6::ConfigCore`/
`KF6::ConfigGui` 是目标名。改回组件名 `Config` 后 configure 通过。
实测（G2 真机编译，补丁前）：
`kdialog.cpp:16:10: fatal error: 'KMessageBox' file not found`（另
`widgets.cpp:22` 同型 `'KPasswordDialog'`）。平台中立、无条件应用（R8）。

### 问题 3：kdbusaddons 无 6.26.0（配方钉 6.18.0，无补丁）

ohpcd 仅发布 kdbusaddons 6.14.0 / 6.18.0 / 6.29.0。上游
`find_package(KF6 ... DBusAddons)` 与 helper 的
`target_link_libraries(kdialog_progress_helper KF6::DBusAddons ...)` 需要
该组件。

**处置**：按 kaccounts-integration 26.04.0 先例钉 `kdbusaddons/6.18.0`
（该 6.26 线消费者的既有跨线钉法；KF6 6.x 系列内 ABI 兼容）。其配方
自身传递 qtbase-sql-dbus/6.11.1（完整 Qt 构建，含 Sql/Test）→ dbus/
1.14.10 → expat 链；expat 以 `expat/2.8.2.1`（override）收敛
（kcron 26.04.1 先例）。Qt6::DBus 于 kdialog 本体的来源仍为
qtbase/6.11.1.1（问题 4）。

### 问题 4：Qt6::DBus 组件来源（qtbase/6.11.1.1，无补丁）

上游必有 `find_package(Qt6 CONFIG REQUIRED COMPONENTS DBus)`，helper 以
`qt_add_dbus_adaptor()` 生成适配器。

**处置**：qtbase/6.11.1.1 是 FEATURE_dbus=ON 变体，导出 Qt6::DBus
组件；qt_add_dbus_adaptor 在 OHOS 上实测可用（kauth 6.26.0 先例）。

### 问题 5：无 X11（WITHOUT_X11=ON，无补丁）

上游 `utils.cpp` 的 X11 集成在 `HAVE_X11 && !K_WS_QTONLY` 条件下编译；
顶层 CMakeLists 在非 `WITHOUT_X11` 时 `find_package(X11)`。

**处置**：`-DWITHOUT_X11=ON` 跳过 X11 查找，HAVE_X11 不定义，X11 集成
整体编译排除；KWindowSystem 的 Qt-only 后端承担剩余窗口系统交互
（平台无 X11 头/库）。

### 问题 6：OHOS 加载器的 4-LOAD 段布局要求（配方既有手段，无补丁）

OHOS lld 默认 `max-page-size=0x10000`，会把 .dynsym/.dynstr 拆进高地址
RW 段，OHOS musl 加载器拒绝 mmap 该布局。

**处置**：`generate()` 统一 `-Wl,-z,max-page-size=0x1000`
（MODULE/SHARED/EXE），可执行文件另加 `--disable-new-dtags`；
`CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH` 指向全部依赖 lib 目录（DT_RPATH
形式）——OHOS 加载器先于制品自身的坏 RPATH 条目命中已发布 KF6 库
（kcolorchooser 26.04.0 先例）。运行时解析主经 `package_info()` 导出
`LD_LIBRARY_PATH`。

### 问题 7：DT_NEEDED 不可移植条目（package() + test_package 双侧处置）

已发布 KF6 6.26.0 制品带两类不可移植 DT_NEEDED：构建机绝对路径
（旧 conan home 烧死）与构建树相对条目（`../../bin/libKF6*.so`，OHOS
按符号链路径而非 realpath 解析，跨包布局断链）。本包两个可执行文件因
池内 KF6 库无 DT_SONAME，链接器把依赖库建造机绝对路径烧进 DT_NEEDED
（E537 现象）。

**处置**（HMDFS 全盘禁 symlink，以原位改写为主）：

- `package()` 的 `_sanitize_needed_entries()`：对本包两个 ELF
  （bin/kdialog、bin/kdialog_progress_helper）的路径形态 DT_NEEDED 做
  `.dynstr` 原位改写（仅当路径独享时，防撞共享串）→ 裸基名，随后剥
  `.codesign` 重签（llvm-objcopy + binary-sign-tool）——制品可移植；
  任何残留路径形态条目即中止打包（fail-closed 守卫）；
- test_package `test()`：`_prepare_runtime_links()`（符号链农场，
  HMDFS EPERM 时警告跳过）、`_fix_relative_needed()`（依赖库相对条目
  归一为基名）、`_fix_absolute_needed()`（依赖库绝对条目建链指向包内
  同基名库，幂等；两个可执行文件一并扫描）——阻断加载器跟随陈旧副本，
  全部查找走导出的 LD_LIBRARY_PATH（kcolorchooser 26.04.0 /
  kgoldrunner 26.04.0 先例）。

### 问题 8：E330 评估——不需要

E330 建议 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` 规避
cmake_symlink_library 在 HMDFS 的 EPERM。本包**不使用**：kdialog 只产
可执行文件（无 SHARED 带 SOVERSION 目标，无版本化符号链创建路径），
无此需求。

### 问题 9：上游 tests/ 三脚本为交互式演示（清点，不驱动）

`tests/` 仅 `test`（2879B）、`progressdemo`（426B）、
`progresscanceldemo`（448B）三个 shell 演示脚本：人工点击按钮或以
qdbus 驱动 kdialog_progress_helper，无自动判定；tests/ 下无
CMakeLists.txt、顶层未 add_subdirectory(tests)。上游注册测试数为 0
（完整证据见 test_package/MANIFEST.yml）。

### 问题 10：已知交互路径限制（如实申报，配方 docstring 同步）

- `--passivepopup`：26.04.0 已无 KPassivePopup 回退（kdialog.cpp 仅留
  注释）——无会话总线时 `sendVisualNotification()` 返回 false，
  `qApp->exec()` 进入无窗口事件循环且无事可退出（挂起）。消费者用例
  有意不驱动该分支；
- `--progressbar`：需 kdialog_progress_helper 在 PATH 且等待 D-Bus
  客户端关闭对话框，无 DBus 会话的设备上非交互不可达，同样不作端到端
  驱动。

替代验证（用例 6）：`--msgbox` 是真实模态事件循环
（KMessageBox::createKMessageBox + QDialog::exec）——3 秒宽限存活探针
（同时门禁 kdialog 本体完整 DT_NEEDED closure）；helper 二进制直接
启动做闭包加载门禁（有界等待，判据为无链接器解析失败字样）。

## 三、依赖解析

| 上游需求 | ohpcd 选择 | 说明 |
| --- | --- | --- |
| Qt6 Core/Gui/Widgets/DBus | qtbase/6.11.1.1（override） | FEATURE_dbus=ON 变体导出 Qt6::DBus；qt_add_dbus_adaptor 可用（问题 4） |
| Qt6 Svg | qtsvg/6.11.1 | kiconthemes -> Qt6Svg 链；经 QT_ADDITIONAL_PACKAGES_PREFIX_PATH 查找 |
| KF6 TextWidgets/Notifications/GuiAddons/IconThemes/WindowSystem | ktextwidgets/knotifications/kguiaddons/kiconthemes/kwindowsystem @6.26.0 | 上游 find_package(KF6) 必需组件集，与 .kde-ci.yml 依赖表一致 |
| KF6 KIO | kio/6.26.0（KIOCORE_ONLY 基线） | 补丁 0001 链接替换 KF6::KIOCore（问题 1） |
| KF6 DBusAddons | kdbusaddons/6.18.0 | 无 6.26.0；kaccounts-integration 先例跨线钉（问题 3） |
| KF6 I18n/Config/CoreAddons/Crash/ColorScheme/Codecs/WidgetsAddons/Archive | 6.26.0（override 闭包） | 主干 CMake/运行时链；kcompletion 6.26.0.1、sonnet/kservice 传递 |
| expat/openssl/zstd/libxml2 | 2.8.2.1 / 3.5.6.1 / 1.5.7 / 2.15.3 | KIO/kiconthemes 闭包与 Qt Network 底座 |
| ECM | ecm/6.26.0（tool_require） | CMakeDeps 的 ECMConfig 不带 ECM_MODULE_PATH，配方手工注入 |

## 四、真机验证

2026-10-17 首轮真机实录（首版 head `3530c2d92b`；HarmonyOS PC aarch64，
conan 2.29.1，profile ohos-aarch64；
`python3 scripts/ohc-run.py conan-verify kdialog 26.04.0`，VERIFY_RC=0）：

- 八门禁 **Verdict=PASS**：G0–G4 全 ✅ PASS（L2/L4/L5「无 cache 路径」
  跳过），报告原件 `reports/conan-verify-report.md`；
- 依赖解析：依赖图逐项 `- Cache` 命中（无任何 Downloading）；仅被测包
  自身从源码构建（`--build=missing` 未触发任何依赖构建）；
- 编译：clang（aarch64-unknown-linux-ohos），kdialog 与
  kdialog_progress_helper 两目标全量编译 + 安装（G2 ✅）；
- 产物：package_id `7c6935fb7476292039d51209286af9a7437838e1`（recipe
  rev `c0bcb98246152f27245bacb98b110147`，package rev
  `3bd4311d0e7cf93a077b3bd2fc21081c`）；`Packaged 2 files: kdialog,
  kdialog_progress_helper` + ProgressDialog.xml / metainfo.xml /
  org.kde.kdialog.desktop；
- DT_NEEDED 净化：`DT_NEEDED entries sanitized: 8`（kdialog 6 +
  kdialog_progress_helper 2），全部裸基名 + 重签（G3 ✅ 无 lib/ 纯可
  执行包）；
- 消费者套件 12/12 断言全过，末行 `ALL CONSUMER CASES PASSED
  (5 用例 / 10 断言 + 1 鸿蒙特有用例 / 2 断言)`（conan create 输出末段
  `kdialog/26.04.0@ohpcd/stable (test package): kdialog consumer suite
  passed`；含鸿蒙特有 `--msgbox` 3 秒存活探针与 helper 闭包加载门禁）。

## 五、离线 AI 检视 R1 整改与复验（2026-10-17）

R1（真机 AtomCode 离线检视，报告发布至 MR 评论区）共 4 项发现（无 P0/P1：
1×P2 + 3×P3）。按 2026-10-11「检视问题提前改」政策，P2/P3 整改提前修入
新 head 并重跑真机验证，逐条处置如下：

**已整改（3 项）**

1. （P2）`test_package/test.sh` 删除 bash-only 的 `pipefail`（`set -euo
   pipefail` → `set -eu`）：调用方 `test_package/conanfile.py` 以
   `os.environ.get("CONFIG_SHELL", "/bin/sh")` 取解释器，而
   `[buildenv] CONFIG_SHELL` 只写入生成的 conanbuildenv 脚本、不进入
   `os.environ`（kcharselect 26.04.0 实测记录），调用行恒为
   `/bin/sh <归档>/test_package/test.sh`；dash 系会在任何用例执行前报
   `Illegal option -o pipefail` 非零退出。本脚本全部管道均为信息性消费
   （`head` / `if grep`），删除后 `set -eu` 语义完整保留（真 POSIX）。
2. （P3）OHOS 判定统一为 `str(self.settings.os) in ("OHOS",
   "HarmonyOS")`（kcharselect 26.04.0 先例口径）：`conanfile.py`
   generate 分支（原 `== "OHOS"`）与 `test_package/conanfile.py` 两处
   （原 `not in ("Linux", "OHOS")` 与 `== "OHOS"`）共三处统一。原
   test_package 守卫在 `os=HarmonyOS` 下会静默 `return`，把消费者测试
   变成隐性空跑（R34 隐患）。
3. （P3）`test.sh` 临时日志路径多级兜底（kcharselect 26.04.0 先例）：
   `LOG_DIR` 走 `$TMPDIR → mktemp -d → $PWD` 兜底，两个日志文件本身
   再走 `mktemp` 兜底，失败时不再把 `*.log` 落进归档目录。措辞更正
   （R2 复检 #1）：原稿「`$$` 可预测路径 + `>` 覆写的经典不安全临时
   文件形态一并消除」系过度声称——文件级 `mktemp` 是兜底而非主路径，
   `$TMPDIR` 指向共享目录时主路径分支仍保留 `$$` 命名 + 截断打开；该
   形态与已合入的 kcharselect 26.04.0 先例逐字一致，按先例保留代码，
   本节按实况更正表述。

**记录不改（1 项）**

4. （P3）`test_package/conanfile.py` 测试期重复遍历/ELF 重复整读
   （`_iter_elf_libs`/`_elf_needed` 无缓存、`_fix_absolute_needed` 连
   调两次）：纯测试耗时项，无正确性影响；该调用结构属本批 KF6 包先例
   形态，保留待后续家族统一优化。

**复验实录**（整改后新 head，2026-10-17）：

- 设备侧字节一致性：全部 14 个设备文件 `md5sum -c` 逐项 OK（含 10 个
  构建输入；清单为文本格式——设备 toybox md5sum 不识别 GNU `*` 二进制
  标记）；
- `python3 scripts/ohc-run.py conan-verify kdialog 26.04.0` 全链通过，
  八门禁 **Verdict=PASS**（03:41 新报告随档
  `reports/conan-verify-report.md`）；
- 依赖图逐项 `- Cache`（Downloading=0）；仅被测包自身源码构建；
- 产物：package_id `7c6935fb7476292039d51209286af9a7437838e1`（recipe
  rev `251382ed993a3c025add95296b08c517`，package rev
  `3bd4311d0e7cf93a077b3bd2fc21081c`——整改只触及 test_package 与注释/
  谓词，未改变产物二进制，package rev 与首轮一致）；DT_NEEDED 净化
  `DT_NEEDED entries sanitized: 8`（kdialog 6 + helper 2）+ 重签；
- 消费者套件 12/12 断言全过（末行 `ALL CONSUMER CASES PASSED (5 用例 /
  10 断言 + 1 鸿蒙特有用例 / 2 断言)`；`(test package): kdialog consumer
  suite passed`）。

**R2 复检处置**（2026-10-17，覆盖 head `19685657cd`；5 条去重后 3 个独立
发现，全 P3，无 P0/P1/P2）：

1. （P3）临时日志路径形态与措辞矛盾——见上「已整改」第 3 条措辞更正；
   代码按 kcharselect 26.04.0 先例逐字保留。
2. （P3）`test.sh` shebang `#!/bin/bash` 与脚本体（真 POSIX）不一致——
   记录不改：调用链恒为 `sh <路径>/test.sh`（`test_package/conanfile.py`
   取 `CONFIG_SHELL`、兜底 `/bin/sh`），shebang 在本链路不生效；直接执行
   不属于验证/交付链路；kcharselect / kcolorchooser 26.04.0 先例同为
   bash shebang，按家族形态保留。
3. （P3）`test_package/conanfile.py` 测试期重复遍历/ELF 重复整读——
   同 R1「记录不改」第 4 条，维持既有口径。
