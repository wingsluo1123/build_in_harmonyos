# modemmanager (ModemManager) 1.24.2 适配笔记

## 编译环境
- 构建系统: meson（Conan MesonToolchain + PkgConfigDeps）
- 编译日期: 2026-10-05
- 编译器: clang 15 / llvm-ar（/data/service/hnp/bin）
- 目标平台: HarmonyOS PC (aarch64, os=OHOS)
- 状态: built

## 上游与版本

- 上游: https://gitlab.freedesktop.org/mobile-broadband/ModemManager
- 版本: 1.24.2（上游最新 tag，git ls-remote 实测）
- 源码 URL: 官方 gitlab archive tarball（`/-/archive/1.24.2/ModemManager-1.24.2.tar.gz`）
- sha256: `fbc75adcc0d7b0565f256e7ff4e8872b0a37c4413ff576665f7470932d9c1b68`（两次独立下载实测一致）
- 说明: freedesktop.org 的发布 tarball（ModemManager-1.24.2.tar.xz）被反爬 bot-check 页面拦截（返回 3877 字节 HTML "Checking you are not a bot"），不可用；采用 gitlab 官方 archive URL（与仓库内 accountsservice/libmbim 同源模式，R39 单条官方 URL）

## 交付范围（libmm-glib，daemon 裁剪）

ModemManager 是 freedesktop 的移动宽带调制解调器管理器，组件分两层：

1. **libmm-glib**（本包交付）：客户端 GObject 库，Mm* API 封装
   org.freedesktop.ModemManager1 D-Bus 接口。构建产物：
   - `lib/libmm-glib.so`（soname `libmm-glib.so.0`，libtool versioning c:r:a = 11:0:11）
   - `include/ModemManager/*.h`（ModemManager.h 主头 + ModemManager-enums.h /
     -errors.h / -compat.h / -names.h / -version.h，与 daemon 共享）
   - `include/libmm-glib/*.h`（libmm-glib.h、mm-modem.h、mm-manager.h、mm-object.h、
     mm-sim.h、mm-bearer.h、mm-sms.h、mm-call.h 等 60+ 客户端头）
   - 生成的类型层（构建期生成，安装进 include/libmm-glib）：
     mm-enums-types / mm-flags-types / mm-errors-types / mm-errors-quarks（mm-mkenums，python3 移植版）
     + mm-gdbus-{bearer,call,cbm,manager,modem,sim,sms}.h（gdbus-codegen）
   - `lib/pkgconfig/mm-glib.pc`（pkg.generate name='mm-glib'，requires gio/glib/gobject/ModemManager）
     + `lib/pkgconfig/ModemManager.pc`（headers-only，0001 补丁在 daemon 裁剪时生成）

2. **ModemManager daemon + mmcli**（不交付，中性裁剪）：src/ 下 daemon 硬依赖
   udev + libgudev（kernel device tracking）、可选 libmbim/libqmi/libqrtr、
   systemd journal/suspend-resume、polkit；运行期需要 D-Bus system bus、
   /dev/tty* 串口设备、厂商插件栈。HarmonyOS PC 无上述系统环境，且任务卡明确
   "配方侧只交付 libmm-glib 库+头文件，daemon 可裁剪"。

### 裁剪实现（0001 补丁，中性 portability）

上游 1.24.2 的顶层 meson.build 无条件 `subdir('src')` + `subdir('cli')` +
`subdir('examples/sms-c')`，无任何开关。0001 补丁加一个标准布尔选项
`-Ddaemon`（默认 true，上游行为不变）：

```meson
option('daemon', type: 'boolean', value: true, ...)

enable_daemon = get_option('daemon')
subdir('libmm-glib')
if enable_daemon
  subdir('src')
  subdir('cli')
endif
```

`-Ddaemon=false` 时只走 po/data/introspection/include/libqcdm/libmm-glib 五个
subdir（libqcdm 为 libmm-glib 无关的静态工具库，meson 照常构建不安装）。
补丁不改任何源码语义，Linux 上 `-Ddaemon=true` 与上游逐字节等价。

## 构建配置（configure_options 全集）

```
-Ddaemon=false              # 0001 补丁：只构建 libmm-glib
-Dudev=false                # OHOS 无 udev；daemon 裁剪后 libmm-glib 不引用 gudev
-Dudevdir=<pkg>/lib/udev    # 关 udev 时上游 assert 要求显式给 udevdir（install_data 无条件装 rules）
-Dsystemdsystemunitdir=no   # OHOS 无 systemd units
-Dsystemd_suspend_resume=false
-Dsystemd_journal=false
-Dpolkit=no                 # OHOS 无 polkit（daemon 侧可选依赖）
-Dmbim=false -Dqmi=false -Dqrtr=false   # daemon 侧协议后端，裁剪后无引用；同时让配方免引 libmbim/libqmi 依赖
-Dintrospection=false       # 免 gobject-introspection 工具链
-Dvapi=false -Dgtk_doc=false -Dman=false -Dbash_completion=false
-Dtests=false               # 上游测试需 D-Bus session + TTY 设备（见下）
-Dexamples=false
```

## 依赖关系（配方）

| 依赖 | 版本 | 用途 | 链接 |
|------|------|------|------|
| glib | 2.84.0.1 | glib/gobject/gio/gio-unix（libmm-glib 直接链接） | 是（transitive） |
| dbus | 1.14.10 | configure-time only：顶层 meson.build 读 dbus-1.pc 的 interfaces_dir/system_bus_services_dir/sysconfdir 变量定安装位置 | 否（visible=False） |

依赖版本选择说明：glib/2.84.0（无组件声明的老配方）只让 PkgConfigDeps 生成主
glib-2.0.pc，meson 解析 dependency('gio-2.0') 时回退到 glib 包内 prefix=/
的原始 .pc，gdbus_codegen 工具变量解析成 `//bin/gdbus-codegen` 直接 configure
失败（实测 meson-log.txt 取证）；glib/2.84.0.1 声明了 glib/gobject/gio/
gmodule/gthread 全套组件（pkg_config_name 各就各位），PkgConfigDeps 按组件
生成正确 prefix 的 .pc，accountsservice CI 实证同一模式可用。

libmbim/libqmi/libqrtr/gudev/polkit/libsystemd 全部是 daemon 侧依赖，
-Ddaemon=false 后 meson 不再探测，配方不引入（依赖断链零风险）。

## 构建期工具链要点（OHOS 环境适配）

1. **gdbus-codegen**（gnome.gdbus_codegen 生成 mm-gdbus-* 客户端绑定）：
   meson 经 gio-2.0.pc 的 `gdbus_codegen` 变量查找。Conan 安装的
   /bin/gdbus-codegen 直接运行时 `__file__` 解析不到 share/glib-2.0 下的
   codegen python 包 → 配方写 python wrapper（runpy）并把绝对路径注入
   .pc 变量（accountsservice 验证过的模式）。
2. **mm-mkenums**（枚举/flags/errors 类型生成）：上游自带 python3 移植版
   （build-aux/mm-mkenums），meson `find_program(源码内路径)` 直接命中，
   无外部依赖。
3. **xsltproc**（include/ModemManager-names.h 由 header-generator.xsl 生成）：
   /data/service/hnp/bin/xsltproc 在 PATH（profile 已配）。
4. **msgfmt/xgettext**（po/i18n.gettext preset glib）：hnp bin 内置。
5. **llvm-ar/llvm-ranlib**：Conan native file [binaries] 段手动注入
   （meson guess 链找不到无 -15 后缀的 llvm-ar）。
6. **dbus-1.pc 别名**：dbus/1.14.10 配方 pkg-config 名为 dbus → 生成 dbus.pc；
   上游 meson 查 dependency('dbus-1') → 配方复制为 dbus-1.pc 并补
   interfaces_dir/system_bus_services_dir/sysconfdir 变量（accountsservice
   同模式）。
7. **pkg_config_path 注入 native file**：PkgConfigDeps 生成的 .pc（glib 子
   模块）+ 依赖包内 lib/pkgconfig（gdbus-codegen 所需的原始 gio-2.0.pc
   含 gdbus_codegen 变量）都要进 meson 的 native file，不进 env。
8. **TMPDIR**：HMDFS 上 meson/ninja 偶发 /tmp 不可写 → 构建目录内 tmp/
   覆盖 TMPDIR/TMP/TEMP。
9. **ELF 签名**：OHOS 产物 .so 需 binary-sign-tool 自签（objcopy 去
   .codesign 段 + selfSign）。

## 上游测试说明（-Dtests=false 的依据）

上游测试套件分四处（清点实测）：
- `libmm-glib/tests`：test-common-helpers.c（g_test_add 68 项）+ test-pco.c（1 项）= 69 项
- `libqcdm/tests`：qcdm 单元测试（daemon 私有库，不随包安装）
- `test/`：mmsmspdu/mmsmsmonitor/mmcbmmonitor/mmrules/lsudev/mmtty——**需要真实
  TTY 设备与 udev 环境**
- `tools/tests`：test-stub.c（2 项）+ test-wrapper.sh——**需要 D-Bus daemon
  拉起 ModemManager stub**

OHOS CI 环境无 D-Bus session/system bus、无 TTY/udev 设备节点，test/ 与
tools/tests 运行期必然挂起或失败；libmm-glib/tests 69 项虽纯逻辑可跑，但
上游把四处测试挂在同一个 `-Dtests` 开关下，且 tools/tests 会在 meson test
阶段拉起 D-Bus wrapper。故整体 -Dtests=false，消费者侧覆盖由 test_package
补全（13 项断言，见下）。

## test_package（13 项消费者断言）

`test_package/test_modemmanager.c`（CMake + CMakeDeps，链接
ModemManager::ModemManager + glib::glib）：

1-7. 核心对象 GType 注册：mm_modem/mm_manager/mm_object/mm_sim/mm_bearer/
   mm_sms/mm_call_get_type() 非零且 g_type_name 可解析（覆盖 mm-gdbus 生成
   代码 + 手写客户端对象的类型系统初始化）
8. 共享枚举值：MM_MODEM_STATE_REGISTERED == 8（ModemManager-enums.h）
9-11. 版本宏：MM_MAJOR/MINOR/MICRO == 1/24/2；MM_CHECK_VERSION(1,24,2) 真；
   MM_CHECK_VERSION(1,24,3) 假（ModemManager-version.h 由 meson configure
   生成，验证版本注入链路）
12. 错误域注册：mm_core_error_quark() 非零（mm-errors-types 生成层）
13. 生成枚举类型注册：mm_modem_capability_get_type() 非零（mm-enums-types
   生成层）

全部为可离线运行的纯库断言，不碰 D-Bus。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 meson 无条件构建 daemon+mmcli | 上游无开关 | 0001 补丁加 -Ddaemon 布尔门控（中性 portability，默认 true 不改上游行为） |
| 2 | freedesktop.org 发布 tarball 下载得到 bot-check HTML | 反爬拦截 | 改用 gitlab.freedesktop.org 官方 archive URL（sha256 双源实测） |
| 3 | -Dudev=false 时 configure 断言 "udevdir must be explicitly given" | 上游 install_data udev rules 无条件执行，rules 目录来自 udevdir | -Dudevdir 显式给包内 lib/udev（rules 装进包内不污染系统） |
| 4 | meson dependency('dbus-1') 找不到 | dbus 配方 pc 名为 dbus | dbus-1.pc 别名 + interfaces_dir/system_bus_services_dir/sysconfdir 变量补全 |
| 5 | gdbus-codegen 经 .pc 变量调用失败 | conan 安装脚本的 __file__/相对资源解析 | python runpy wrapper + 变量注入（accountsservice 模式） |
| 6 | meson 找不到 static linker | [binaries] 段无 ar | native file 手动注入 llvm-ar/llvm-ranlib |
| 7 | 上游 tools/tests 需要 D-Bus 拉起 stub | 运行期环境缺失 | -Dtests=false，test_package 13 项消费者断言补全 |

## 运行期限制（如实申报）

- 本包只交付 libmm-glib 客户端库。要在 OHOS 上真正管理调制解调器需完整
  ModemManager daemon + D-Bus system bus + udev + 厂商插件，属于系统级
  移植工程，不在本包范围。
- libmm-glib 的运行时调用（如 mm_manager_new 同步连接）在无 D-Bus 环境下
  返回 G_IO_ERROR，客户端按标准 GLib 错误路径处理（库本身完全可用——
  这是客户端库的设计语义）。

## 上游测试启用与分口径实测（2026-10-14 修复 rule4 少报）

审核复扫口径确认：上游 1.24.2 全仓 `g_test_add_func(` 注册数 = **377**
（libmm-glib/tests 69 + src/tests 143 + src/plugins 165；另 tools/tests 2 例走
`g_test_add()` 宏、src/tests/test-modem-helpers.c 182 例走 `g_test_suite_add`
宏、libqcdm 36 例走自定义 TESTCASE 宏，均不在 377 计数口径内）。

分口径（按 0001 补丁门控后的可执行性）：
- **可离线跑（69）**：libmm-glib/tests —— test-common-helpers（68）+ test-pco（1），
  纯单元逻辑（key-value 解析/带宽数组比较/PCO 编解码），无 D-Bus/TTY/udev 依赖；
  `-Ddaemon=false -Dtests=true` 下 meson 正常构建并注册 `meson test`。
- **不可离线（308）**：src/tests 143 + src/plugins 165 —— 挂在 src/（daemon）树下，
  链接 src/meson.build 内部声明的 libhelpers/libkerneldevice/libport 静态库，
  且 test-modem-helpers 系列运行期需 openpty PTY 设备、test-udev-rules 需 udev
  设备树；`-Ddaemon=false` 时整个 src/ 不进构建图（构建即豁免，非跳过）。

0001 补丁 v2 增量：把顶层 `test/` 与 `tools/tests/`（D-Bus 会话总线 wrapper 的
服务级套件）门控进 enable_daemon——上游无此门控时 `-Dtests=true -Ddaemon=false`
会在 configure 阶段引用未定义变量（libhelpers_dep 等）直接报错。

## 已知限制