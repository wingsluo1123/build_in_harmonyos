# pasystray 0.8.2 适配笔记

## 编译环境

- 构建系统：autotools（`autoreconf -fi` 引导，上游 tag archive 不含 configure/Makefile.in）
- 编译日期：2026-10-16
- 编译器：clang 15（`tools.build:compiler_executables`，来自仓库 profile `ci/conan/profiles/ohos-aarch64`）
- profile：`ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / Release），host 与 build 同一 profile（原生 build=host）
- 状态：`built`（`conan-verify` Verdict PASS；见版本级 manifest.yaml 与 `reports/`）

## 依赖冲突与选项(2)的处置

上游 `configure.ac:51` 硬需 `libpulse >= 1.0 libpulse-mainloop-glib >= 1.0`，`src/pulseaudio.c`
调用 `pa_glib_mainloop_new` / `pa_glib_mainloop_get_api` 把 PulseAudio mainloop 接到 GLib 上。

- 制品仓里只有 `pulseaudio/17.0.1` 提供 `libpulse-mainloop-glib`；`pulseaudio/17.0`
  以 `glib=disabled` 构建，不含该库。
- `pulseaudio/17.0.1` 钉 `glib/2.88.0`，而**全部** gtk3（3.24.38 / 3.24.38.1 / 3.24.43）
  钉 `glib/2.84.0.1`。朴素配方 `conan graph info` 报
  `Version conflict: Conflict between glib/2.88.0 and glib/2.84.0.1 in the graph`。
- **用户明确选择选项 (2)**，两步走。**注意口径**：第 1 步的 recipe 级 override 由**用户选项(2)**授权（机制另有先例，如 abiword-plugin-gdict 的 glib override），**并非** `pavucontrol-qt/2.4.0` 的做法（它是 Qt、无 override）；**只有第 2 步的“消费者测试容忍”** 才是照 `pavucontrol-qt/2.4.0` 先例：

  1. 在**本配方**内用 recipe 级 override 让 gtk3 的 glib 全局生效：

     ```python
     self.requires("glib/2.84.0.1", override=True)
     ```

     实测 `conan graph info` 输出 `glib/2.88.0: ['glib/2.84.0.1#75f29176...']`，图正常解析；
     `pulseaudio/17.0.1` 的 package_id 因依赖变化变为
     `f1794924e2d48e8bca558d128b7201bdb53b965a` → 由构建方从源码重建。
  2. 让**消费者测试容忍 OHOS 运行期限制**（先例：`pavucontrol-qt/2.4.0` 的
     `test_package/conanfile.py`）：`generate()` 把依赖 lib 目录前置进 `LD_LIBRARY_PATH`；
     `test()` 用 try/except，仅对已声明的 OHOS 限制特征打印
     `Execution skipped due to OHOS platform limitation: ...`，其余错误仍 `raise`。

- 为什么用 recipe 级 override 而非 profile `[replace_requires]`：profile 不随配方进 CI，
  而平台 CI 只在本目录 `conanfile.py`（ARCHIVE-SPEC v3.0：conanfile.py 是 CI 唯一构建输入）
  上做 `conan create`。recipe 级 override 随配方生效，CI 与本地一致。

### 越界事实（如实记录）

本条 override **改变了已发布依赖 `pulseaudio/17.0.1` 的构建语义**（glib 2.88 → 2.84，
package_id 变化），即“在交付一个库的同时重建了另一个已发布依赖”。这是与 `AGENTS.md`
「一库一任务、不改依赖」相冲突的越界做法，**由用户明确选择选项 (2)** 并经
`pavucontrol-qt/2.4.0`（已合入）先例确认。边界：

- 未修改 gtk / pulseaudio 配方；override 只在本配方内。
- 未覆盖远端已发布制品：原 package_id `c7777611…` 不受影响，本配方只让构建方生成
  另一个 package_id（`f1794924…`），其构建语义随依赖版本变化。
- 代价：任何消费方（含 CI）在本地无该 package_id 时都要做一次 pulseaudio 源码重建
  （meson+ninja）。pulseaudio 配方的 `build()` 直接调用裸 `meson` 且未声明
  `tool_requires(meson)`，因此该路径要求环境 PATH 上有 meson。

## 编译步骤

1. `get()` 下载上游 tag tarball（sha256 见 conandata.yml），`strip_root=True`。
2. `_patch_autotools_ohos()`（仅 OHOS）：给 automake 自带的 `config.guess` 补
   `__OHOS__` LIBC 探测与 `*:HarmonyOS:*:*` 分支（→ `aarch64-unknown-linux-ohos`），
   给 `config.sub` 补 `ohos-linux` 三元组。内联实现，不依赖 `OHC_SKILL_ROOT`。
3. `autoreconf -fi`（`env="conanbuild"`；`ACLOCAL_PATH` 由 generate() 注入：
   `/data/service/hnp/*/*/share/aclocal`（提供 `pkg.m4`）+ automake/1.18 的
   `share/aclocal{, -1.18}`）。
4. `_patch_configure_umask()`：`configure` 内 `umask 077` → `umask 022`（HMDFS）。
5. `configure`（AutotoolsToolchain；`--with-gtk=3 --disable-avahi --disable-notify
   --disable-x11 --disable-appindicator`）。
6. `make -j1`（`LIBS="-L<glib>/lib -lintl"`，见下）。不传 `--host/--build/--target`（铁律 R1）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan graph info` 报 `Conflict between glib/2.88.0 and glib/2.84.0.1` | pulseaudio/17.0.1 钉 glib/2.88.0，gtk3 全部钉 glib/2.84.0.1 | 配方内 `self.requires("glib/2.84.0.1", override=True)`；pulseaudio 由 `--build=missing` 源码重建 |
| 2 | `PKG_CHECK_MODULES(... libpulse-mainloop-glib ...)` 找不到模块 | PkgConfigDeps 按组件名生成 `pulseaudio-pulse*`，而上游要 `libpulse*` | generate() 里生成 `libpulse.pc` / `libpulse-mainloop-glib.pc` / `libpulse-simple.pc` 别名（`Requires:` 指向组件 .pc，并复制其 Version）|
| 3 | `meson: inaccessible or not found`（重建 pulseaudio 时） | pulseaudio/17.0.1 的 build() 直接调用裸 `meson`，而本机 PATH 上没有 meson（conan 缓存里有 meson/1.11.0）| 构建时把 meson 的 bin 前置到 PATH（模拟 CI 构建机）；**未修改 pulseaudio 配方** |
| 4 | 链接 `pasystray` 报 `undefined symbol: g_libintl_gettext`（systray.c）| glib 的 `gi18n.h` 把 `gettext()` 映射到 `g_libintl_*`，该符号由 glib 包内的 `libintl.so` 导出，而 glib 的 .pc 未列 `-lintl` | `make` 时传 `LIBS="-L<glib>/lib -lintl"`（l3afpad 同款）；不放进 configure 的 LIBS（否则 AC_PROG_CC conftest 链接失败）|
| 5 | `configure` 在 HMDFS 上创建 config.status 临时目录失败 | E011/E114：0700 目录在 setgid HMDFS 上不可写 | 生成 configure 后 sed `umask 077` → `umask 022` |
| 6 | 消费者测试全部失败：`Error loading shared library libpulse*.so`，rc=127 | OHOS 加载器拒绝加载**未签名**（无 `.codesign`）的共享库；pulseaudio/17.0.1 制品库未签名（gtk/glib 已签名）| **不在本任务内修依赖**：按用户选项(2)与 `pavucontrol-qt/2.4.0` 先例，让消费者测试如实声明并容忍该 OHOS 运行期限制；同时保留能真跑的断言 |
| 7 | 即使库签好，`--version` / `--notify=help` 仍 rc=1 | 上游 `main()` 先 `gtk_init_with_args()`，无显示后端时返回 FALSE，`parse_options()` 不执行 | 同 #6：消费者测试容忍 “Cannot open display” 这条 OHOS 运行期限制；不加“先解析选项再 gtk_init”的上游补丁（本任务不引入行为变更）|

## 源码修改

无源码补丁（`patches: {}`）。所有适配都在配方内以确定性代码完成（config.guess/sub、
umask、pkg-config 别名），以保证 CI 与本地结果一致。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| gtk | 3.24.43 | broadway 后端，传递提供 glib/pango/cairo/gdk-pixbuf/atk |
| glib | 2.84.0.1 | 被 override 强制（压制 pulseaudio 的 2.88.0）|
| pulseaudio | 17.0.1 | 提供 libpulse + libpulse-mainloop-glib；package_id `f1794924e2d48e8bca558d128b7201bdb53b965a`（需源码重建）|
| automake | 1.18 | tool_require（aclocal/automake）|

## 运行期限制（决定性）

- OHOS 加载器**拒绝加载未签名（无 `.codesign`）的共享库**。实测：
  - `dlopen(<conan 缓存>/libpulse-mainloop-glib.so.0)` → `Permission denied`（`.codesign` 计数 0）；
  - 同目录结构下把该文件用 `binary-sign-tool sign -selfSign 1` 重签后 → 加载成功；
  - 链接 `libpulse.so.0` 的最小程序在 `LD_LIBRARY_PATH` 指向签名副本时正常运行（rc=0），
    指向未签名副本时 `Error loading shared library libpulse.so.0`（rc=127）。
- gtk/glib 的制品共享库是签过名的（`.codesign` 计数 1），**pulseaudio/17.0.1 的
  `libpulse*.so` / `libpulse-mainloop-glib.so*` 计数为 0**，且本配方重建出来的同样未签名
  （pulseaudio 配方的 `package()` 不做签名，本任务不修改该配方）。
- 第二个、互相独立的限制：无显示后端时 `gtk_init_with_args()` 直接失败，
  `parse_options()`（`--version` 打印与 `--notify=help` 帮助都在其中）根本不执行。
  （签名诊断见 `$HOME/tmp/ohpc-porting/pasystray-signprobe/probe.txt`：签名副本下
  `--version`/`--notify=help`/无参数 均 rc=1、`option parsing failed: Cannot open display`。）

结论：交付二进制 DT_NEEDED 记录 `libpulse.so.0` 与 `libpulse-mainloop-glib.so.0`，
在本机因上述两条限制无法完成 CLI 契约执行；按用户选项(2)与先例如实声明、容忍。

## 验证结果

| 门禁 | 结果 | 证据 |
|---|---|---|
| `conan create`（含图解析、构建、打包、test_package）| **PASS**（rc=0）| job `pasystray-try2-create-20261016-1`；package_id `b8d42349b9b24f56b3457e9f63040859f051f993` |
| 消费者测试：结构性/链接性（硬断言）| **PASS 5/5** | `HMBS_TEST_PACKAGE_STRUCTURAL={"total":5,"passed":5,"failed":0,"skipped":0}` |
| 消费者测试：CLI 契约（真实执行 + 限制容错）| **tolerated 2/2**（`--version`、`--notify=help`，rc=127 加载拒绝）| `Execution skipped due to OHOS platform limitation: ...` |
| `conan-verify`（G0–G4；L2/L4/L5 跳过）| **PASS**（rc=0）| job `pasystray-try2-verify-20261016-2`（提交后，head 绑定本提交）；报告 `reports/conan-verify-report.md` |
| CI 同构门禁（build_and_test.sh）| **PASS**（rc=0）| job `pasystray-try2-ci-20261016-2`（提交后，head 绑定本提交）：`JC pass` / `L0 pass` / `L1 pass` / **`L1e` 确认测试真实依赖被测包** / `L4 pass` / `L5 pass` / `L2 skip（[warn] 非阻塞）`；`Build Summary: Total 1 / Success 1 / Failed 0` |

详见回执 `claude-control/receipts/pasystray-try2-20261016-1.md`（真实命令、退出码与证据绝对路径）。

## 注意事项

- 完整 GUI 功能在当前环境不可用：OHOS PC 无 X11/Wayland（gtk 为 broadway 后端，E527），
  pasystray 的托盘图标依赖 `GtkStatusIcon`（X11 系统托盘协议）。
- 本适配**未**配置 `--disable-statusicon`：GtkStatusIcon 正是该程序的实际托盘后端，
  关闭它等于交付一个无功能的程序。
- 交付物依赖未签名的 pulseaudio 共享库：真机可运行性的前提是
  `pulseaudio/17.0.1` 制品侧补 `.codesign`（属依赖侧任务，不在本任务范围）。
- `conan-verify` 的 L2/L4/L5 因 G4 无法解析 package id 而**跳过**：**没有**做可运行性、
  安全属性与产物基线扫描，不等于这些项通过。
