# tgif 4.2.5 HarmonyOS 适配笔记

## 构建配置

- 上游版本：4.2.5（QPL 发布包 `tgif-QPL-4.2.5.tar.gz`；Debian 以
  `tgif_4.2.5.orig.tar.gz` 原样收录，无 dfsg 重打包，字节等价）
- 构建系统：autotools（上游自带**预生成** `configure` / `Makefile.in`，
  配方直接驱动它们，不重跑 autoconf/automake）
- 目标：HarmonyOS/OHOS 6.0、AArch64、Clang 15、musl、libc++
- 产物：`bin/tgif` + `lib/X11/tgif/`（`.Xdefaults`、图标、`*.sym` 符号库等）
  （`package_type = "application"`，CLI 见软件级 `commands.json`）
- 依赖：`libx11/1.8.13`、`libxt/1.3.1`、`zlib/1.3.2`
  （传递：`libsm/1.2.6`、`libice/1.1.2`、`xorgproto/2025.1`、`libxcb/1.17.0`、
  `libxau/1.0.11`、`libxdmcp/1.1.5`、`xtrans/1.6.0`）
- 源码：`https://downloads.sourceforge.net/project/tgif/tgif/4.2.5/tgif-QPL-4.2.5.tar.gz`
  —— **官方上游 SourceForge 原件**（`tgif-QPL-4.2.5.tar.gz`，3093619 B）。本机独立复算 sha256 = `2f24e9fe…c567ba`，与 Debian `.orig.tar.gz` **逐字节相同**，故采用**上游原始 URL**（避免 PF7「Debian 下游重打包源」判定，且源域名在 CI 镜像表内）。
  （3093619 字节，SHA-256
  `2f24e9fecafae6e671739bd80691a06c9d032bdd1973ca164823e72ab1c567ba`，本机实测复核）

## W0 依赖检查

`libxt/1.3.1` 的配方 pin `libx11/1.8.13`，而 `libxext/6.4.0` pin
`libx11/6.4.0`，两者在 `libx11` 上直接冲突。实测 tgif 源码**不引用任何
libXext/libSM/libICE/libXmu 符号**（见补丁 0002 说明），因此整图对齐到
`libxt` 所在的 `libx11/1.8.13` 轨，且不声明 `libxext`。`libx11/1.8.13` 与
`libxt/1.3.1` 在 `ohpcd` 均有 OHOS/armv8 预编译二进制（实测 `Already
installed` / `Downloaded`，无源码重建）。

## 补丁说明（`patches/`）

三个补丁均对非鸿蒙平台透明，且不含 `__OHOS__` 等平台宏。

### 0001-Makefile.am.patch / 0002-Makefile.in.patch（构建类）

上游 `Makefile.am` 用 `CFLAGS=...` 直接写死 tgif 自己的编译期定义
（`-DVERSION=... -DHAVE_CONFIG_H -DTGIF_PATH=...` 等）。GNU make 中
makefile 内赋值优先于环境变量，导致 Conan 工具链注入的 `CFLAGS`
（`--sysroot`、优化、目标标志等）被整体丢弃。补丁把这些定义改挂到
`AM_CPPFLAGS`（automake 编译规则同时使用 `$(AM_CPPFLAGS)` 与
`$(CFLAGS)`），使上游定义与工具链 `CFLAGS` 同时生效；顺带删去失效的
`-I/usr/X11R6/include`。

`Makefile.in` 是上游**预生成**文件（automake 产物），configure 只做 `@...@`
替换，因此实际构建使用的是 `Makefile.in`——0002 与 0001 内容镜像，
保证 intent 与产物一致。

### 0003-configure.patch（可移植性 / 平台）

`configure`（Autoconf 2.61）用 `(umask 077 && mktemp -d "./confXXXXXX")`
创建 `config.status` 的临时目录。HMDFS（鸿蒙用户卷）强制 setgid，umask 077
生成的目录**连属主都不可写**，`config.status` 随即报
`./confXXXXXX/...: Permission denied` 并生成不出 `Makefile`/`config.h`（E114）。
补丁去掉 `umask 077`，让临时目录以常规可写权限创建。

### 关于 `tgif_LDADD` 裁剪（并入 0002）

上游 `tgif_LDADD = -L/usr/X11R6/lib -lXext -lX11 -lXt -lSM -lICE -lXmu -lm -lz`。
`-L/usr/X11R6/lib` 是失效路径；`-lXext/-lSM/-lICE/-lXmu` 对应的库在
Conan 图中不存在（`libxext` 还会与 `libxt` 在 `libx11` 上冲突），而源码中
`grep -E '\bXShm|\bXShape|\bXmu|\bIceConn|\bSmc[A-Z]' *.c` 无任何命中
（`XSync` 属 libX11 本体）。补丁把该行裁剪为实际使用的
`-lX11 -lXt -lm -lz`，其余 X11 依赖由 Conan 的 `LIBS`/`LDFLAGS` 注入。

## R47 语言预检

`ohc-run.py lang-preflight tgif 4.2.5 --src <解包树>`：构建系统 autotools
（`configure.ac`/`Makefile.am` 存在），源文件 130 个（c:126，主体 97%），
判定 C/C++，通过。

## R51 上游测试三步法

### 1. 清点（证据：4.2.5 官方 tarball 全树）

- `find . -type d -iname '*test*'`：0
- `find . -maxdepth 1 -iname '*test*'`：仅 `testdrive.c`、`testdrive.pl`
- `Makefile.am`：无 `TESTS`、无 `check_PROGRAMS`、无 `check-local`
- `testdrive.c` 是 Prolog 外部函数接口（FFI）驱动，**不在 `tgif_SOURCES`
  中、从不参与构建**，不是测试套件

源码声明的上游测试数 **N = 0**。

### 2. 运行

配方 `build()` 在构建后执行 `make check -j1`。上游未注册任何 `TESTS`，
automake 的空 `check` 目标正常退出 0；实际可运行上游测试数 **N′ = 0**。

### 3. 回填

上游 **0/0**；未删除、未修改、未跳过任何上游测试，也未用消费者测试冒充
上游测试。新增消费者测试 2 层、共 14 条确定性断言：

- `test_tgif.py`（10 条）：`tgif -print -justversion` 退出 0 且输出精确版本行
  `Tgif Version 4.2 (patchlevel 5)` 与上游作者串；无 `DISPLAY` 时
  `tgif -version` 打印版本横幅后以 `Can't open display` 确定性失败；裸启动
  同路径；未知选项被拒（非零退出）。
- `test_package/conanfile.py`（4 条）：产物为 AArch64 ELF；`DT_NEEDED` 含
  `libX11.so`/`libXt.so`（证明经 Conan X11 栈实际解析）；**鸿蒙特有：ELF
  段表内恰好 1 个 `.codesign` 段**。

**鸿蒙特有测试（OHOS-specific）**：`test_package/conanfile.py` 的
`_verify_ohos_elf()` 用 `readelf -S` 统计 `.codesign` 段，要求**恰好 1 个**。
该段是签名后的鸿蒙 ELF 才有的段：OHOS 工具链的 `ld.lld` 默认写入
（`--code-sign`，设备实测：普通 clang 输出计 1、`-Wl,--no-code-sign` 计 0），
配方 `package()` 再用 SDK 的 `binary-sign-tool` 自签名。**通用 Linux ELF
不含此段**，故该断言在非 OHOS 平台必然失败——是真正的鸿蒙平台特有属性。
实现为 **fail-closed**：未签名产物段计数为 0 → 直接 raise，不静默放行。

## 已知运行边界

- HarmonyOS PC 无 X server，tgif 的交互绘图/区域编辑等真实功能**未在设备上
  实测**；本适配不把它写成“已实测通过”。消费者测试覆盖公共 CLI 的非 GUI
  路径、完整二进制加载、选项解析与确定性无显示失败路径。
- 产物 `bin/tgif` 动态链接 Conan X11 栈且**不带 RPATH**，运行时依赖
  `LD_LIBRARY_PATH`（即 conanrun 环境）。CI 的 L2 冒烟不注入该环境，故其报告
  中为非阻断 `warn`（与同仓其它 X11 二进制表现同构）。
- tgif 的默认临时目录是编译期写死的 `TMP_DIR="/tmp/"`（上游 `Makefile.am`
  原样）。鸿蒙 `/tmp` 只读；本适配**不改写**该上游默认（避免为非 OHOS 平台
  改变行为），运行时可用 `Tgif.TmpDir` X 资源或 `Tgif.TmpDirInHomeDir: true`
  重定向到可写目录。该路径在本次消费者测试中未被触发。
- `libidn` 仅在运行时 `dlopen("libidn.so")` 尝试加载（`inmethod.c`），不参与
  链接，故未声明为依赖；缺失时相应转码功能自动降级。

## 内存声明

`test_package/MANIFEST.yml` 的 `max_rss_mb: 512` 与 `build_mem_budget_mb: 1000`
是沿用同仓既有声明的**保守预算值**（如 maim/5.8.0），**非本次实测峰值**；
构建以 `make -j1` 单作业进行，消费者测试只执行轻量 CLI 路径。

## 结束标记

tgif 4.2.5 配方、补丁、test_package、manifest（软件级+版本级）、commands.json、
README 完成；本地 conan-verify 与 CI 同构门禁结果见交付回执 **（状态/门禁结果
以本次回执为准，未上传、未提 PR）**。

## 门禁覆盖范围与签名（如实披露，勿读作"全通过"）

- **conan-verify 的 L2/L4/L5 实为 skip**：工具侧 G4 报「无法找到程序包 ID」后，L2/L4/L5 走的是
  「无 cache 路径 → 跳过」分支，字段虽显示 PASS，**不等于已冒烟/已安全检查**。有效覆盖为 **G0–G3**。
- **CI 同构的 L2 冒烟为 skip（非阻断）**：设备无 X server，`tgif` 需显示；同 maim/xshogi 惯例。
- **ELF 签名是 fail-closed 的**（`package()` 的 `_sign_ohos_binary`）：打包后可执行文件缺失、
  `binary-sign-tool`/`llvm-readelf` 缺失、签名器非零退出、或签名后 `.codesign` 计数 ≠ 1 —— 任一情况
  **直接 raise**（`ConanInvalidConfiguration`）。参考同仓 `archives/p/pan/0.165` 与 `archives/a/abx/0.1`。
- **`.codesign` 断言仅在 `settings.os == "OHOS"` 时执行**：该段是 OHOS 专有属性
  （设备实测：普通 clang 产物 = 1，`-Wl,--no-code-sign` = 0），非 OHOS 平台跳过并明确打印跳过原因。
  注意：该断言校验的是「段存在且计数正确」，**不单独证明重签动作成功**——重签是否成功由
  `package()` 的 fail-closed 检查保证。
