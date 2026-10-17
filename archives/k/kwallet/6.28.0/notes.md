# 适配笔记 — kwallet 6.28.0 (HarmonyOS PC / OpenHarmony)

## 任务类型
正式包名 kwallet/6.28.0：KDE Frameworks 6 KWallet（KF6::Wallet API 库
libKF6Wallet.so + kwalletd6/ksecretd 运行守护进程）向 OpenHarmony /
HarmonyOS PC (aarch64) 的 conan 适配升级。仓库已有 API-only 的
kwallet/6.18.0 基线（为 libkgapi 构建，BUILD_KSECRETD/KWALLETD=OFF）；
本条目交付 6.28.0 升级，采用 daemon-enabled 测试范围，使上游测试套件
在真实 D-Bus 栈上执行。上游同一 tarball（sha256
e21130c86ffa0be49065648f4e753d63d3d786fab876f511d9d09da16480f691）
此前曾按平台当时的派发名 `kio-kwallet/6.28.0` 交付（配方开发史见下文
对话记录）；本条目以正式包名 kwallet/6.28.0 重新交付同一验证形态，
并在本机对 6.28.0 全链重新执行 conan create 验证（见「本次交付」节）。

## 依赖拓扑结论（W0 只读分析）
- 上游 6.28.0 的依赖链：ECM、Qt6 Core/GUI/Widgets/DBus/Test、
  KF6Config（API 库本体：Core/GUI/Widgets + Config 直链），daemon 范围
  追加 KF6 CoreAddons/I18n/WidgetsAddons/DBusAddons/Crash/Colorscheme/
  WindowSystem/Notifications（kwalletd6/ksecretd 所需）。
- ohpcd 现有包：qtbase-sql-dbus/6.11.1（含 Widgets/Test/DBus，可满足）、
  kconfig/6.18.0 及 daemon 范围 KF6 组件 6.18.0 代；ecm/6.26.0；
  libsecret/0.21.7、libgcrypt/1.11.0、qca/2.3.10。全部命中制品仓
  （conan download --only-recipe 逐个核验 rc=0）。
- KF_DEP_VERSION / ECM 版本协商被补丁 0001 对齐到 ohpcd 已发布代
  （KF6 组件 6.18.0 / ECM 6.26.0），其余依赖按上游源码声明接受。

## 版本 pin 理由
- kconfig pin 6.18.0：ohpcd 当前已发布代；KF_DEP_VERSION 补丁让
  find_package(KF6Config 6.18) 通过。
- ecm pin 6.26.0（tool_requires）：与 daemon 范围 KF6 组件同代的发布
  基线。
- qtbase pin 6.11.1：仓库基线（6.18.0 kwallet 配方同源），向上兼容
  6.28 源码所需的 API。

## E018：symlink 域隔离与 copy-instead-of-link 方案
- 本机实测：conan 的 python 进程树整体被禁 symlink(2)——os.symlink 直接
  EPERM；make 阶段 `cmake -E cmake_symlink_library` 报 "Permission denied"。
  交互 bash 域不受限（`ln -s` 可用），即沙箱按进程域授予 symlink 权限。
- 关键陷阱：仅把 VERSION 属性置空串仍会生成尾部点号产物
  `libKF6Wallet.so.`（cmake 拼接 `<soname>.<version>`，空 version 也拼），
  随后创建 `libKF6Wallet.so.` -> `libKF6Wallet.so.6` 的 symlink 依旧触发
  E018。**必须整行删除 VERSION/SOVERSION 两个属性**（补丁 0002）。
- 保上游 soname 名（2026-10-17 readelf 实证后修正，见对话 #8）：交付 ELF
  实际携带 CMake 自动的**裸名** DT_SONAME（libKF6Wallet.so /
  libKF6WalletBackend.so）。曾尝试 configure() 注入
  `CMAKE_SHARED_LINKER_FLAGS=-Wl,-soname,libKF6Wallet.so.6`，被 CMake 在
  `-o` 前自动追加的 `-Wl,-soname,<输出名>` 静默覆盖（同对话 #7 的
  last-wins 机制），该注入已从配方删除。
- package() 在签名前物化 soname 名：`cp libKF6Wallet.so -> libKF6Wallet.so.6`
  （_materialize_soname_copy），两份 ELF 都走 OHOS 签名。消费者
  test_package 的运行时链接收集 glob `lib*.so*` 同时覆盖两个文件。
- 同族缺口（2026-10-17 正式包名构建实锤）：backend 共享库
  libKF6WalletBackend 带着同样的 VERSION/SOVERSION 属性，链接阶段
  `cmake_symlink_library` 在 `libKF6WalletBackend.so.6` 上同样
  Permission denied（构建在 cmake.build() 挂死）。补丁 0003 对 backend
  做同款整行删除处理；`_materialize_soname_copy` 同时对两个库物化
  soname 副本（libKF6Wallet.so.6 / libKF6WalletBackend.so.6），两份都
  走签名。
- 配方运行时设施同轮 E018 加固（消除配方中最后一处无守卫 symlink）：
  runtime-wrap 农场重构为真实目录 `<generators>/runtime-wrap/bin`
  （daemon 的 CWD 即其父，相对 DT_NEEDED `../../bin/<lib>` 无需任何
  symlink 即可解析）；农场条目创建统一改走 `_link_or_copy()`
  （symlink→hardlink→copy 依序回退）；ksecretd dbusfix 与陈旧绝对路径
  shim 同样容错。即今天这轮沙箱（进程域完全禁 symlink）下全链可跑。
- 同族缺口之四——私有 dbus 总线栈（fix6，详见对话 #6）：dbus 子构建
  由 MacrosAutotools 解析出 VERSION/SOVERSION，同样撞
  cmake_symlink_library；处理=子构建源码树幂等改写，删属性 +
  `set(CMAKE_SHARED_LINKER_FLAGS "-Wl,-soname,libdbus-1.so")` 钉普通名
  soname（同时挡 KF6Wallet 的 soname 泄入）。
- 同族缺口之五——QCA 版本化名字链（fix7/fix8，详见对话 #7）：qca 源树
  同样有 `if(NOT ANDROID)` 下的 VERSION/SOVERSION 属性块；处理=删除该块
  并以**链接项**形式钉 `libqca-qt6.so.2` soname。此处不能用
  `CMAKE_SHARED_LINKER_FLAGS`：CMake 在 `-o` 前自动追加自己的
  `-Wl,-soname,<输出名>`，链接器取**最后一个** soname，变量式钉法被
  静默覆盖（fix7 实锤）。

## 上游测试真相（如实记录）
- 上游测试树用 add_executable + ecm_mark_as_test() 构建测试二进制；
  仅 fdo_secrets_test 与 blowfishtest 有 add_test() 注册（`ctest -N`
  注册数=2），其余测试目标的 "No tests were found" 是上游本态，非适配
  缺失。recipe 的 R51 三步法：`ctest -N` 盘点 + 构建后强制检查预期二进制
  存在 + 直接执行每个测试二进制并强制退出码判定。
- 终态（daemon 栈真实执行）：13 个测试二进制构建、11 个真实执行，
  kwalletpath ENV-BLOCKED（/tmp EROFS，详见下），全部在
  conan create 内实测，逐二进制结果以 BIN-RESULT 行记录（普查表见
  交付 MR 正文；原始构建日志不随档）。

## DISPLAY 守卫（Qt offscreen 陷阱）
- 本机无显示服务：真实 QPA 插件连接 X11 会 SIGSEGV；且上游
  KWalletTest::init() 自带 headless 守卫——DISPLAY 未设置时整组
  QSKIP（静默跳过；这正是 Totals 门必须解析 0 skipped 的原因）。
- recipe 的实际做法：`QT_QPA_PLATFORM=offscreen`（offscreen 插件
  永不打开 X11 连接）**+ 假值 `DISPLAY=:99`**，让上游 QSKIP 守卫
  通过、钱包 DBus 往返真实执行。test_package 同法
  （`env.define("DISPLAY", ":99")`；R3 检视 A 整改，原文曾误写为
  pop DISPLAY——与实现相反，且 pop 会命中 QSKIP 路径静默跳过全套）。
- **不能用 conan `Environment.unset()`** 去"取消"守卫：它把变量置空
  而不是删除，而 Qt 的 `qEnvironmentVariableIsSet` 对 set-but-empty
  返回 true（已用最小 envtest 包实证）。

## 本地 CI 模拟（W3）在此设备上的运行时事实（供后续包参考）
- 设备沙箱按进程域授予 exec/symlink：conan/W3 python 域可 exec
  /data/service/hnp/*、/system/bin/*（toybox 全套）与 .pi/agent/bin/*，
  不可 exec /usr/bin、$HOME/tmp、$HOME/usr/local/bin 之下"新创建"的脚本；
  且域内无 exec 转移，链式 exec 无法越界。
- 设备自带 zsh（/usr/bin/zsh，真 zsh 5.x）python 域不可达；可达的
  .pi/agent/bin/zsh 是完整 zsh 5.9，但 heredoc 临时文件硬编码 /tmp/zsh
  （无视 TMPDIR），而 /tmp 在此设备只读。
- 解法：`$HOME/.zshenv` 设 `TMPPREFIX=$HOME/tmp/zsh; export TMPPREFIX`
  （zsh 每次启动无条件 source .zshenv），heredoc 即落可写目录；toybox
  applet 经 PATH 首位的 /system/bin 正常解析。CI worker 无此文件、行为不变。
- 另外：本机清理会丢 export 的自定义变量并重写 TMPDIR/TMPPREFIX，运行
  finish 时 TMPPREFIX 依赖 .zshenv 兜底；TMPDIR 给 bash heredoc 用（置为
  $HOME 亦可写）。

## G0/归档说明
- 源码核验：kwallet-6.28.0.tar.xz sha256
  e21130c86ffa0be49065648f4e753d63d3d786fab876f511d9d09da16480f691
  （download.kde.org 官方归档，顶层目录 kwallet-6.28.0/，strip_root）。
- conan create 全绿证据见 reports/conan-verify-report.md（BIN-RESULT
  普查表在交付 MR 正文；原始构建日志不随档）。

### 对话 #1 [2026-09-20]（配方开发史，kio-kwallet 派发名时期）
- 问题：本地 CI 模拟（W3）在此设备上无法运行——CI 脚本是 zsh 专用
  （glob 限定符 `(N)`），而 conan 进程域可达的唯一 zsh（pi-agent 自带）
  heredoc 临时文件硬编码 `/tmp/zsh`（无视 TMPDIR），且 `/tmp` 只读
- 操作：定位设备沙箱的 exec 域规则（/system/bin toybox 可 exec、新创建
  脚本不可），用 `$HOME/.zshenv` 设 `TMPPREFIX=$HOME/tmp/zsh` 注入
  （zsh 每次启动无条件 source），不改 CI 脚本
- 结果（✅）：setup.sh + build_and_test.sh 在本地全部通过，CI worker
  行为不变

### 对话 #2 [2026-09-20]（配方开发史）
- 问题：cmake 阶段 `cmake_symlink_library` Permission denied（E018），
  置空 VERSION 仍生成尾部点号产物 `libKF6Wallet.so.` 并再次触发 symlink
- 操作：补丁 0002 整行删除 VERSION/SOVERSION；configure() 注入
  `-Wl,-soname`；package() 物化 soname 副本并签名
- 结果（✅）：libKF6Wallet.so + libKF6Wallet.so.6 双文件签名，运行期双名
  可解析（注：当时"DT_SONAME 保持上游"的说法被 2026-10-17 的 readelf
  证伪——实为裸名、注入被 CMake 覆盖；双文件签名与解析结论不受影响，
  见对话 #8）

### 对话 #3 [2026-09-24]（配方开发史，daemon 栈上线）
- 问题：审查 FAIL：上游 3 个用例只执行了 2/3——testWallet 被 DISPLAY
  平台守卫 QSKIP，未做真实 DBus round-trip
- 操作（配方升级为 daemon-enabled 测试范围）：
  1. 补丁 0001 重写：BUILD_KSECRETD=ON + BUILD_KWALLETD=ON
     （KF_DEP_VERSION 放宽到 6.18.0，daemon-scope KF6 组件对齐 ohpcd
     已发布的 6.18.0 代；test_package 的 kconfig 同步对齐到 6.18.0）；
  2. conanfile 新增运行时设施：dbus/1.14.10 自建会话总线（OHOS 禁文件域
     unix socket → loopback TCP + EXTERNAL/ANONYMOUS）、ksecretd 走上游
     `--pam-login` 无头解锁协议（pipe 喂 56B PBKDF2 哈希 + unix socket
     环境通道，绕开 KPasswordDialog GUI）、pw_shim LD_PRELOAD、
     runtime-wrap symlink 农场、qca-ossl 插件自建（Botan 双加载统一路径）；
  3. **确定性 harness**（关键经验）：整段 daemon 生命周期写成自包含
     python 脚本由 conan build() 以独立进程运行——直接在 conan build()
     内 spawn 时 ksecretd 注册 bus name 会迟滞数分钟（conan 子进程环境
     干扰 PAM/DBus 握手时序），独立进程则确定；warmup pass 先跑
     kwallettest 写入阶段并等 ksecretd 自身 5s _syncTime 落盘，再对
     物化后的钱包状态（3 个 seed 文件级快照，规避 OHOS rmtree 不可靠）
     做正式 run，最多 3 次 attempt。
- 结果（✅）：kwallettest Totals: 3 passed, 0 failed, 0 skipped，
  testWallet 做了真实 DBus round-trip（DISPLAY=:99 +
  QT_QPA_PLATFORM=offscreen，offscreen 插件不触 X11）；W3 本地 CI
  setup.sh + build_and_test.sh 全绿（L2 skip 非阻塞：daemon 二进制无
  --version 入口）。
- 上游 6.28 自身 race（文档化于配方 docstring）：ksecretd 仅在启动时
  物化 fdo collections，kwalletd6 连接时快照 collection 列表；空状态
  启动会让上游自身的 close 后查找丢 folder（无本地补丁可复现）——
  warmup seeding 即为对冲此上游行为。

### 对话 #4 [2026-09-25]（配方开发史，全量普查整改）
- 问题：检视判四条 FAIL：rule4（上游实测 N > 声明 N，少报）、rule6/7
  （提交晚于检视/CI）、rule12（鸿蒙特有测试仅纯校验点，缺完整端到端
  消费者用例）。
- 操作（配方升级为全量普查执行）：
  1. **全量普查**：build/bin 实测清点 13 个测试二进制；11 个真实执行
     （standalone：blowfishtest/backendtest/testbf/testsha；daemon 栈：
     kwallettest/async/sync/path/both/many/cbc/fdo_secrets_test），
     kwalletwizardtest 排除（交互式 GUI，理由文档化），
     kwallet-example-asynchronous 为示例非测试。
  2. **判定分型**：Qt Totals（blowfishtest）、legacy 退出码+无 Error
     （testbf/testsha）、smoke exit 0（backendtest，上游无失败条件、
     恒 exit 0，如实留档）。
  3. **ENV-BLOCKED 机制**：kwalletpath 上游硬编码 /tmp/test.kwl，本机
     /tmp 对所有进程域 EROFS（touch 实测）；测试仍执行，结果如实上报
     （BIN-RESULT kwalletpath ENV-BLOCKED + reason），不修改上游测试
     源码、不计入通过。
  4. **库遮蔽发现（新知识）**：glib 包自带精简版 libintl.so.8 缺
     libintl_bind_textdomain_codeset，在 LD_LIBRARY_PATH 中遮蔽
     gettext 完整版导致 libKF6I18n.so 加载失败（Error relocating）；
     修复 = gettext 包 lib 目录置于 LD_LIBRARY_PATH 最前。另：conan
     self.run() 会套 conanbuild env 脚本覆盖 LD_LIBRARY_PATH，
     standalone 测试改用 subprocess 直跑。
- 终态结果：22/23 Qt 测试函数 passed（fdo_secrets_test 16/0、
  kwallettest 3/0、async/sync/both/many 各 3/0、cbc 4/0、blowfish 3/0；
  kwalletpath ENV-BLOCKED），legacy 3/3，`KWALLETTEST-PASS`，
  test_package 1/1，conan create exit 0。
- rule12：PR 正文将 daemon-stack 生命周期 harness（真实 D-Bus 会话
  总线 + ksecretd --pam-login 解锁 + kwalletd6，open→写→读→close
  完整生命周期）明确为鸿蒙特有完整消费者用例。

### 对话 #5 [2026-10-17]（正式包名交付，backend E018 缺口修复）
- 问题：kwallet/6.28.0 正式包名首轮 conan create 在 cmake.build() 失败：
  `cmake_symlink_library` 建 `../../../bin/libKF6WalletBackend.so.6`
  报 Permission denied——backend 目标的 VERSION/SOVERSION 属性未做处理
  （kio-kwallet 交付期该目标未触发同一步骤，当时构建通过；本次沙箱
  域下实锤同族缺口）。
- 操作：
  1. 补丁 0003 对 backend 做与 0002 同款的整行删除（含 E018 注释）；
     conandata 登记；包内 soname 副本物化扩到两个库。
  2. 配方全链 E018 加固（见上方「E018」节）：农场真实目录化 +
     `_link_or_copy` 三级回退 + dbusfix/陈旧 shim 容错。
  3. patch_ng 本地预检：0001 strip=0 / 0002 strip=1 / 0003 strip=1 全部
     APPLIED，结果文件内容核验通过；conanfile.py py_compile SYNTAX-OK。
- 结果（fix5 实测，设备端）：backend E018 修复有效——主库构建通过、
  standalone 测试真实执行（blowfishtest `Totals: 3 passed, 0 failed,
  0 skipped` 等）；随后 daemon-stack 的私有 dbus 构建暴露第二个 E018
  同族缺口（见对话 #6），fix6 修复后重跑取证。readelf 复核 DT_SONAME
  与解析路径随 fix6 重跑取证。

### 对话 #6 [2026-10-17]（私有 dbus 总线栈 E018 缺口：版本化名字链）
- 问题：fix5 实测在 `_build_bus_stack()` 的 cmake 构建失败：
  `cmake_symlink_library` 建 `../lib/libdbus-1.so.3` 报 Permission
  denied。设备端 `--trace-expand` 溯源（全新配置目录复现）：
  dbus 源树 `dbus/CMakeLists.txt` 的 `if(DEFINED DBUS_LIBRARY_REVISION)`
  恒为真——该变量由 dbus 自带 `cmake/modules/MacrosAutotools.cmake`
  从源码内 autotools 版本宏解析而来（trace 实证 `math(EXPR
  DBUS_LIBRARY_MAJOR 35 - 32)`、`set_target_properties(dbus-1
  PROPERTIES VERSION 3.32.4 SOVERSION 3)`），于是产出
  libdbus-1.so.3.32.4 实体 + `.so.3`/`.so` 符号链接链；沙箱域拒
  symlink(2)，该步骤必然失败。同时实证工具链级
  `CMAKE_SHARED_LINKER_FLAGS`（当时为 KF6Wallet pin 上游 soname 的注入，
  已按对话 #8 删除）的 `-Wl,-soname,libKF6Wallet.so.6` 会泄入该子构建。
- 操作（配方内幂等源码修正；对象是构建期下载的 dbus 源树，非
  patches/ 下的 kwallet 上游源码补丁）：
  1. `_build_bus_stack()` 在 conan_get 提取后对 `dbus/CMakeLists.txt`
     做精确 3 行块替换（`OHOS-E018` 标记幂等；计数≠1 即 raise 快速
     失败）：删除 VERSION/SOVERSION 属性，改为
     `set(CMAKE_SHARED_LINKER_FLAGS "-Wl,-soname,libdbus-1.so")`——
     既拆除符号链接链，又钉住普通名 DT_SONAME（防 KF6Wallet soname
     泄入）。
  2. 运行期解析核查：buswait 经 `LD_LIBRARY_PATH=<bus>/lib` 按
     `libdbus-1.so` 解析、dbus-daemon 走构建树 RPATH，普通名链下
     均成立。
- 结果（fix6 实测，设备端）：私有总线栈构建通过、daemon 栈起栈流程
  推进到真实执行——dbus-daemon/ksecretd/kwalletd6 全部拉起，
  `org.freedesktop.secrets` 的等待有真实响应路径。同轮重跑暴露下一个
  进程域缺口：ksecretd 报 "createDLGroup failed: maybe libqca-ossl is
  missing"（QCA 插件未构建、PBKDF2 派生失败）→ 见对话 #7。

### 对话 #7 [2026-10-17]（QCA 插件：版本化名字链 + "两次加载"根因与 soname 钉法）
- 问题链：fix5→fix6 修完后，daemon 栈全部拉起但所有钱包用例在
  openWallet 失败（kwallettest 快速失败 28–39ms、异步路径 29.6s 超时、
  fdo_secrets_test 等到 180s 后 rc=-6 SIGABRT）。daemon 日志 23 处
  `libc++abi: terminating due to uncaught exception of type
  QCA::Botan::Invalid_State: Botan: Library was not initialized
  correctly`——ksecretd 崩溃导致钱包无法解锁/注册。
- fix7（第一版）：qca 源树删 VERSION/SOVERSION 属性块 +
  `set(CMAKE_SHARED_LINKER_FLAGS "-Wl,-soname,libqca-qt6.so.2")` 钉
  soname，构建 qca-ossl 插件（QCA_PLUGIN_PATH 指向插件目录）。构建
  全通过，**运行期仍崩**。
- 根因（设备端 readelf + link.txt 实证，本单最深的坑）：
  1. `link.txt` 显示核心库链接命令里我们的
     `-Wl,-soname,libqca-qt6.so.2` 在、但 CMake 在 `-o` 前又自动追加
     了 `-Wl,-soname,libqca-qt6.so`，链接器取最后一个 → 构建树内
     `libqca-qt6.so` 的实际 SONAME=**裸名**。
  2. 插件链接的是构建树路径 `../../lib/libqca-qt6.so` → 记下的
     DT_NEEDED=**裸 `libqca-qt6.so`**（实测 readelf 证实）。
  3. 运行期解析：插件 RUNPATH = `$ORIGIN : <build>/qca-ossl-build/lib :
     <pkg>/lib : <qtbase>/p/lib`，裸名首个命中 = 构建树副本（SONAME
     裸名）；而 ksecretd 自身 NEEDED `libqca-qt6.so.2`、经 RPATH 命中
     `<pkg>/lib/libqca-qt6.so.2`。→ **同进程加载了两个 QCA 核心**
     （不同绝对路径、独立 Botan 全局态）→ 插件初始化与守护进程看到
     的不是同一个库 → Invalid_State 崩溃链。
  4. 决定性佐证（diag8）：全树只有 ksecretd 与 fdo_secrets_test 两个
     二进制 NEEDED libqca——恰是仅有的两个崩溃进程。
- fix8（本版）：
  1. soname 钉法改为**链接项**——注入点（删掉的上游 VERSION/SOVERSION
     块原位，位于 add_library 之后）
     `target_link_libraries(${QCA_LIB_NAME} PRIVATE
     "-Wl,-soname,libqca-qt6.so.2")`：链接项区域在 `-o` 之后、CMake
     自动 soname 之后 → **最后一个 soname 是我们想要的**；文件名保持
     `libqca-qt6.so`（无版本化符号链接需求）。
  2. 插件 DT_NEEDED 变为 `libqca-qt6.so.2`；运行期 RUNPATH 对 `.so.2`
     的搜索：`$ORIGIN`（仅插件本体）→ 构建树 lib（无 `.so.2` 文件）→
     **`<pkg>/lib/libqca-qt6.so.2`**——与守护进程解析到的绝对路径
     字符串完全一致 → 单实例 QCA。
  3. 构建后 fail-loud 断言（纯 Python ELF 动态节解析
     `_elf_dynamic_names`，无外部工具依赖）：核心 SONAME 必须恰为
     `libqca-qt6.so.2`；构建树 lib 不得存在 `.so.2*` 文件；插件
     NEEDED 必须含 `.so.2` 且不含裸名。任何一条不满足即 raise（不再
     把静默错误留给运行期）。
  4. 源码改写双路径幂等：原始形态（形状匹配）+ 已含 fix7 旧钉法的树
     （精确文本升级），写入后回读校验标记。
  5. 插件复用加 `.soname2.stamp` 守卫：旧版（裸 NEEDED）插件不满足
     标记条件，必被重建；配合发射脚本先删整个 qca 子构建树
     （qca-src/qca-ossl-build/qca-plugins）保证清洁重建。
  6. 解析器先行验证：把 `_elf_dynamic_names` 逐字节拷出成
     `elftest.py` 发到设备，对 fix7 现存核心/插件实测——核心
     soname `'libqca-qt6.so'`、插件 needed 含裸名，与 readelf 输出
     逐项一致（解析器保真），再发 fix8 全链重跑。

### 对话 #8 [2026-10-17]（离线 AI 检视整改：6 项发现全闭环）
- 触发：MR #16421 首次 head（656cfd90d4）离线检视，6 项发现：P2×3
  （wait_bus_name 门恒真 / passwd shim _r 变体不合成 / soname pin 声明与
  实际不符）+ P3×3（重复谓词 / 死辅助函数 / 死方法）。全部复核采纳。
- #1（P2，行为）：嵌入守护进程脚本 `wait_bus_name` 的
  `if name in last` 子串匹配被 buswait 超时诊断
  （`timeout waiting for <NAME>`，stderr 并流）满足 → 就绪门恒真、
  `return False` 分支死。修复=按行精确匹配
  `name in (line.strip() for line in last.splitlines())`，docstring
  记录退出码故意不用与子串不可用的两处理由。
- #2（P2，行为）：pw_shim 的 `getpwuid_r`/`getpwnam_r` 把
  POSIX「未找到」形态（rc==0 且 *out==NULL）当成功返回 → 合成条目永不
  产生、dbus 凭据查询仍见 unknown user。修复=仅当
  `rc == 0 && out && *out` 才直返，其余落到合成分支（两个变体同改）。
- #3（P2，声明-实际不符）：configure() 的
  `-Wl,-soname,libKF6Wallet.so.6` 注入被 CMake 自动 soname 覆盖
  （对话 #7 同机制）——设备 readelf 四个交付核全为裸名。处置=删除该
  惰性注入，docstring 与本节注释改为告知实情（裸名 soname + package()
  物化 `.so.6` 签名副本，双名运行期可解析）；manifest 同步修正。
- #4（P3）：`"Error" not in out and "Error" not in out` 去重（行为等价）。
- #5（P3）：死辅助 `fresh_home/snapshot_home/restore_home/seed_files`
  删除（生命周期由嵌入脚本 make_home/snapshot_seed/restore_seed 承担；
  `seed_home` 仍在用，保留）。
- #6（P3）：死方法 `_wait_for_bus_name` 删除，其判据（rc==0 且名在列
  表）折入 #1 的修复。
- 复验：py_compile ✓；wait_bus_name 五幕仿真（超时诊断/真列表
  rc≠0/真列表 rc=0/子串诱饵/空输出）全符合预期；设备端全链重跑
  见「本次交付」节及 MR 正文。

### 对话 #9 [2026-10-17]（R2 全链重跑失败根因：buswait「清理」改动
自吞列表 → 就绪门恒假；同批次二次整改）
- 现象：R2 字节设备端 conan create 失败（daemon-stack 测试跑步器
  超时；各 180s 就绪门恒报 `bus name org.freedesktop.secrets did not
  appear`）。
- 定位（设备端受控换件矩阵，全部以逐票 DBGPOLL 记录）：
  1. f8 跑步器流程 PASS / r2 跑步器流程 FAIL（其余要素同改
     kwallettest-only、门 75s）→ 故障随流程。
  2. f8 流程 + R2 的 ksecretd 二进制 → 全绿（3/3 用例 610ms）
     ⇒ R2 构建的 ksecretd 无问题。
  3. r2 流程 + f8 的 ksecretd → 487 票全 rc≠0（0 票 rc=0）
     ⇒ 故障不随任何单个二进制，随「r2 流程」本身。
  4. pw_shim（R2/F8 两版）与 Qt 插件路径均非因子（换件后现象不变）。
- 代码级实锤：#8 的「完整清理」found 路径对 **共享连接**（来自
  `dbus_connection_open`）调用 `dbus_connection_close(c)` → libdbus
  `_dbus_warn_check_failed` → abort（rc=-6）；且 abort 在
  `fflush(stdout)` 之前，stdout 经管道为全缓冲 → 列表整体丢弃。
  再叠加 #1 的逐行精确匹配 → 成功列表永远到不了 Python → 就绪门
  恒假、零成功轮询。f8 版 found 路径是裸 `return 0`（退出时 stdio
  自动冲刷），故旧链不受影响。
- 二次整改（并入同一 R2 批次）：
  1. buswait found 路径改为
     `dbus_message_unref(m); dbus_connection_unref(c); fflush(stdout);
     return 0;`——共享连接一律 unref 不得 close；超时/重试路径的
     关闭同样改为 `dbus_connection_unref(c)`，使进程内重试循环真正
     可用，`timeout waiting for <NAME>`（stderr）经正常退出冲刷，
     收尾 `return 1` 退出码恢复语义。
  2. wait_bus_name 门加入 `probe.returncode == 0` 前置条件（退出码
     恢复可信后直接采纳检视意见本意）；docstring 改述为「并流的
     stderr 诊断行含名字，故须精确行匹配 + 成功退出码」。
- 复验：py_compile ✓；设备端全链 conan create 重跑（见本次交付
  节）。踩坑留档：中继断连不终止端侧命令（`$HOME/tmp/*.out` 事后
  取回可证）；`cat $空变量` 会吞脚本剩余输入（一律 `[ -f ]` 守卫）。

## 本次交付 (2026-10-17)：kwallet/6.28.0 正式包名刷新

- 触发：平台以正式包名 kwallet 派发 6.28.0（taskBranch
  feat/kwallet-6.28.0）。W0 核验：官方 main 无 archives/k/kwallet/6.28.0
  目录；ohpcd 制品仓仅有 kwallet/6.18.0（kwallet/6.28.0 不存在，
  conan download --only-recipe 实测未命中）→ 无需版本递增（R37 不触发）。
- 交付形态：以已验证的 daemon-enabled 配方（上游同一 tarball、同一
  sha256、同一补丁集）按正式包名重构——包名/类名/docstring/manifest/
  test_package 二进制名同步改名，配方逻辑与依赖 pin 零改动。
  `kwallet/6.18.0` 基线保留不动（仓库版本目录共存惯例——kguiaddons/
  ki18n 均多版本并存；kaccounts-integration 等仓内消费者仍按 6.18.0
  接线），本条目为纯新增目录。
- 本机全链重跑（conan create，包名 kwallet/6.28.0）：见
  reports/conan-verify-report.md（G0-G4 判决；逐二进制 BIN-RESULT
  普查表在交付 MR 正文）。

### 对话 #10 [2026-10-17]（R2 整改头检视：9 发现 → P2 三项 + 文档/死代码落地，加固项记录）

- 触发：新头 004798777f（R2 根因整改后）的离线 AI 检视：12 文件
  2636 行，9 个独立发现，无 P0/P1。
- A（P2，Totals 子串门）：上游 qt 门（`"0 failed" in totals`）与
  runner 逐二进制门（`"0 failed" in last_totals`）均为子串匹配——
  全部用例 QSKIP 时 QtTest 打印 `Totals: 0 passed, 0 failed, N
  skipped` 且退出码 0 → 零覆盖被判全通过（对话 #3 已否决过一次
  同款 DISPLAY 守卫 QSKIP）。修：解析式门——conanfile 侧
  `_qt_totals_ok`（passed>0 且 failed==0）；runner 侧 `totals_ok`
  （另加 skipped==0）。设备 R3 日志全票 `0 skipped`（含 ENV-BLOCKED
  的 kwalletpath 2p/1f 走豁免路径），收紧对既有证据零回归。
- B（P2，buswait 空值直入 replace）：`_build_bus_wait()` 在缺
  clang/gcc/cc 或 libdbus 时 return None，返回值直入
  `script.replace(token, value)` → `TypeError: replace() argument 2
  must be str, not None`，掩盖真实缺件原因（同函数 pw_shim 有
  `if pw_shim:` 守卫，此处漏了）。修：先取 `buswait` 变量，None 即
  抛 ConanException 并点名缺 cc 还是缺 libdbus。
- C（P2，陈旧路径正则缺 `/b/` 层级）：`_stage_runtime_libs` 的 ELF
  字节扫描正则 `conan2/p/[a-z0-9]+/p/lib/...` 缺 build 层级，与
  `_fix_dependency_cmake_paths` 的正则 `conan2/p/b/[a-z0-9]+/p`
  不一致 → `needed` 恒空、"重建依赖 ELF 引用的陈旧绝对路径"静默
  空转。设备实布局 `~/.conan2/p/b/<id>/p/lib`（R2/R3 conv 目录
  kwall15ccdfa6b6427 / kwallea33cd907c0d3 同构实证）。修：补 `b/`。
  激活面三重防呆（路径已存在即跳过；rt_libs 无同名目标即跳过；
  makedirs OSError 兜底），重跑复核无回归。
- D（P3，文档矛盾）：patch 0002 注释仍称"经 linker flags 恢复上游
  DT_SONAME"，与现状（CMake 末尾自动 `-Wl,-soname,<输出名>` 出裸名，
  包内字节复制出 .so.6 文件名；对话 #8 已修正）及姊妹补丁 0003 的
  措辞矛盾。修：改写为与 0003 同款表述；conandata.yml 中同源失真
  表述（"keeps the upstream DT_SONAME"）一并修正。
- I（P3，死代码三处）：`_dbus_bin()`（全文件无引用）、
  `dbus_log_path`（赋值未用；注释所述需求由 runner 自持实现）、
  `_PAM_HASH_SIZE`（未引用，脚本内 `dklen=56` 系双事实源）全清；
  56 的出处注释（kwalletbackend.h PBKDF2_SHA512_KEYSIZE）随 dklen
  行保留。
- E/F/G/H（P3，记录不改）：E=对 Conan 缓存依赖 .cmake 就地改写
  （加固项，牵动 generators 架构，本单不动）；F/G=测试总线
  TCP+ANONYMOUS 与 LD_PRELOAD passwd shim——平台约束下的测试基建
  （HMDFS 禁 AF_UNIX bind、沙箱无真实 passwd 库），作用域限测试
  进程树；H=`_quote` 仅转义 `"`（profile 值域受控、可达性低）。
  四项在检视评论记录，本轮不改。
- 本地三验：全文件 compile + 嵌入 runner 脚本 compile（token 占位
  替换后）+ 双门真值表 10 例 + 死代码针检 + patch_ng 链验（0002
  改动后仍 APPLIED；补丁 +9/-2 行与 `@@ -20,8 +20,15 @@` 头不变）。
- 整改头重跑取证：conan create 全绿（conv 目录
  kwall5f23c2e2fe105；`Package '...' created` ×1）；runner 8 二进制
  全票 0 skipped（7 OK + kwalletpath ENV-BLOCKED 2 passed/1 failed
  如实豁免）；KWALLETTEST-PASS ×1、Invalid_State=0；包内 4 个 ELF
  readelf SONAME 全为裸名，`.so.6` 与 `.so` 同尺寸字节副本
  （223808/285248 B）。告警口径 1081 行：-Wunknown-warning-option
  799（较 R3 的 800 少 1 行，属探测回显浮动），-Wdeprecated 139 /
  -Wcast-align 89 / -Wzero-as-null 20 均不变；日志无 stale 命中
  （设备上目标路径均存在 → 陈旧路径重建与 cmake 修路径特性静默跳过，
  符合预期）。conan-verify rc=0：G0–G3 PASS、G4 PASS（含"无法找到
  程序包 ID"提示项）、L2/L4/L5 跳过（无 cache 路径）、"可标记
  status: published"；报告 md5 357933bbbe007f374b448c4ef69c47dc
  （1184 B，设备 ↔ 本地字节一致）。

### 对话 #11 [2026-10-17]（R3 整改头检视：10 独立发现全 P3 → 5 项落地 + 3 项记录；B 项证据化重设计）

- 触发：新头 2f4099be56（R2 整改后）的离线 AI 检视：12 文件 2639 行，
  12 条原始 → 10 个独立发现，无 P0/P1。
- B（测试诚信，唯一影响验证可信度项）：kwalletpath 的 ENV-BLOCKED
  豁免仅按二进制名匹配——任何失败（openWallet 崩溃、构建问题等真实
  回归）都会被判豁免放过。检视建议"匹配捕获输出中的 EROFS 文本"，但
  复核实证该路径不可行：捕获输出中并无 EROFS/阻塞文本（阻塞发生在
  daemon 域），测试二进制实际只打印 `FAIL! : KWalletPathTest::
  openWallet() 'wallet != nullptr' returned FALSE`；而上游
  tests/kwalletd/kwalletpath.cpp 在 openWallet("/tmp/test.kwl", 0,
  Wallet::Path) 前会向 stdout 打印该硬编码路径。修：双证门——失败
  二进制的捕获输出须含 `/tmp/test.kwl` 标记 **且** 运行期对 /tmp 的
  写探针（同进程域）须得 EROFS；任一证据缺失即判 FAIL。设备实证
  BIN-RESULT 行 `ENV-BLOCKED (probe-confirmed: captured
  /tmp/test.kwl, open(/tmp) -> EROFS)`，summary/TOTALS 同步标注
  probe-confirmed。
- A（文档/元数据，同一 diff 自相矛盾）：①许可证——conanfile 记
  LGPL-2.0-or-later、manifest 记 LGPL-2.1-or-later。检视建议"统一为
  2.1"，但其前提与普查不符：上游 6.28.0 源树 68 个 .cpp/.h 头 SPDX
  计数 = 2.0-or-later 53 / 2.0-only 6 / 2.1-or-later 4 / 3.0-or-later
  3 / MIT 1 / OR 表达式 1；LICENSES/ 同时含 2.0-or-later 与
  2.1-or-later。按占比改 manifest.yaml:19 为 LGPL-2.0-or-later（与
  conanfile 一致）。已合入姊妹包 kio-kwallet/6.28.0（同上游同 tarball
  sha256 e21130c8…）存在同样的 manifest/conanfile 分歧，本单不越界
  改动已合入包，仅在检视评论说明。②DISPLAY——notes/manifest 旧文称
  实现"pop DISPLAY"，与实现相反（现状 = QT_QPA_PLATFORM=offscreen +
  假值 DISPLAY=:99；pop/不设 DISPLAY 会让上游 KWalletTest::init() 的
  QSKIP 守卫把整套测试静默跳过）。旧文已改写。
- C（正确性/环境）：wait_bus_name 的 subprocess.run(timeout=25) 未
  捕获 TimeoutExpired（helper 自身 atoi 预算可超该上限 → traceback
  崩掉整个 runner）；两处 LD_LIBRARY_PATH 拼接会把继承值/预置里的
  空元素带进结果（空元素 = 当前目录，CWD 同名库可遮蔽目标包库）。
  修：TimeoutExpired 续轮询至外层 deadline；两处 join 先过滤空元素
  再拼接。
- D1（死代码）：模块级 hashlib/socket/time 全部引用都在嵌入 runner
  字符串内（脚本自带 import）→ 删。
- D2/D3/E（记录不改）：D2=passwd shim 每次 dlsym 重解析（性能微优化，
  牵动安全敏感 LD_PRELOAD shim）；D3=test_package ctest 与直接执行双跑
  （双路径各验注册契约/直接执行契约，且 CLI L0d 门要求 self.run 存在）；
  E=私有总线 ANONYMOUS/own="*"/eavesdrop 面（OHOS 无 peer-cred 必须
  ANONYMOUS；仅测试窗口、仅 127.0.0.1 绑定；与 R2-E/F/G/H 同款）。
- F（一致性）：test_package/conanfile.py 的 env.unset("DISPLAY") 恰为
  本包文档判为失效的写法 → 改 env.define("DISPLAY", ":99") 与主配方
  一致。
- 本地预检（kwl-check-r4fix.py）：全文件 + 嵌入脚本 compile；豁免门
  真值表 5 例（marker×探针全组合 + 非豁免名 + 探针文件无残留）；
  LD_LIBRARY_PATH join 5 例（无尾随/前导空元素）；死导入与旧文案针检
  （no hashlib/socket/time、"ENV-BLOCKED rc="、"(documented)"）——全绿。
- 整改头重跑取证：conan create 全绿（conv kwall2914e95a4e618；
  `Package 'f7bcf9eb0921a44cc00a5efcbeb1e85e2038ddde' created`）；
  runner 8 二进制全票 0 skipped（7 OK + kwalletpath ENV-BLOCKED
  probe-confirmed，rc=1 Totals 2p/1f 如实记录）；TOTALS `7 passed,
  0 failed, 1 env-blocked (probe-confirmed)`、KWALLETTEST-PASS ×1；
  test_package 1/1（0.09s，PASS: KF6Wallet API kdewallet kdewallet
  Passwords Form Data）；包内 4 ELF readelf SONAME 仍全裸名
  （.so.6 为 .so 同尺寸字节副本 223808/285248 B）。告警口径 1082 行：
  -Wunknown-warning-option 800（较上轮 +1，属探测回显浮动）、
  -Wdeprecated 139 / -Wcast-align 89 / -Wzero-as-null 20 不变；ERROR
  计数 2 = cmake `-- Looking for LOG_PERROR` 探测回显（1524/1551
  两行），非真实错误。conan-verify rc=0：G0–G4 PASS（G4 含"无法找到
  程序包 ID"提示项）、L2/L4/L5 跳过（无 cache 路径）、"可标记
  status: published"；报告 md5 c7bcabee762dbbc8e05f7d539b04eac6
  （1184 B，设备 ↔ 本地字节一致；分片 md5 逐段核验通过）。
