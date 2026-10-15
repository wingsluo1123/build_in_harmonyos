# joyce 2.4.2 适配笔记（HarmonyOS PC / arm64）

## 概述

- **软件**：Joyce —— Amstrad PCW 系列（PCW8256/8512/9512 与 PCW16/Anne）模拟器
- **版本**：2.4.2
- **上游**：https://www.seasip.info/Unix/Joyce/（官方）源码包 `joyce-2.4.2.tar.gz`
- **许可证**：GPL-2.0-or-later
- **语言**：C++（GUI 前端 xjoyce/xanne）+ C（bundled LibDsk 等）
- **构建系统**：Autotools（configure / Makefile.am，`AC_DISABLE_SHARED` 全部静态）

## 依赖

| 依赖 | 说明 | 仓库内包 |
|------|------|---------|
| SDL 1.2 | xjoyce/xanne GUI 前端（`AM_PATH_SDL`） | `sdl12-compat/1.2.68` |
| libpng | GUI 菜单/图形 | `libpng/1.6.58.3` |
| libxml2 | 配置文件解析（`AM_PATH_XML2`） | `libxml2/2.15.3.1` |

joyce 自带 bundled `LibDsk` / `Lib765` / `LibLink` / `cpmredir` 子库，均随主
make 一并构建（in-source）。

## 适配要点

1. **`sdl-config` shim**：joyce 的 `configure.ac` 用 `AM_PATH_SDL` 调用
   `sdl-config`。`sdl12-compat` 只安装 SDL 1.2 头文件与 `libSDL-1.2`，未安装
   `sdl-config`。配方在 build 目录生成一个最小 `sdl-config` shim 并前置于 PATH，
   `--libs` 输出 `-L<SDLPrefix>/lib -lSDL-1.2`。`--cflags` 必须**同时**输出
   `-I<prefix>/include -I<prefix>/include/SDL` 两个路径：joyce 的 `AM_PATH_SDL`
   测试程序（及 `bin/PcwCommsW32.cxx`）用 `#include <SDL/SDL.h>`，只有父目录
   `<prefix>/include` 在搜索路径才能解析到 `<prefix>/include/SDL/SDL.h`；而 joyce
   主体源码用 `#include <SDL.h>` 等，需要 `<prefix>/include/SDL`。只给
   `-I<prefix>/include/SDL` 时 `AM_PATH_SDL` 的两个 conftest（run 测试与 link 诊断）
   都因 `<SDL/SDL.h>` 编译失败 → configure 报 "SDL version not found"（真机失败阶段
   compile）。
2. **`--disable-floppy`**：避免 `configure` 探测主机软驱与 `linux/fd.h`
   头文件（OHOS 无软驱、无该头，探测会失败）。
3. **In-source 构建**：joyce 的 configure 把 `CPPFLAGS/LDFLAGS` 指回
   `$(srcdir)` 子目录，属严格 in-source 构建，配方用 `basic_layout(src_folder=".")`。
4. **静态 bundled 库**：`AC_DISABLE_SHARED` 使 LibDsk/Lib765 等全部静态，
   便于打包自包含。
5. **TMPDIR 可写**：复用 hmbs 注入的任务独立 TMPDIR/TMP/TEMP，回退到构建目录内
   `.tmp`（autoconf/configure 需可写临时目录）。
6. **config.sub / OHOS triplet**：joyce 顶层 configure 用 2020 版
   `config/config.sub`，不认 `aarch64-unknown-linux-ohos` 的 `ohos` OS，在
   `checking build system type` 报 "OS 'ohos' not recognized"。joyce 无
   AC_CONFIG_SUBDIRS、且始终显式传 `--build=`（不触发 config.guess）。配方
   `_patch_config_sub_for_ohos()` 在 configure 前把该脚本 `case $# ... esac`
   后、字段切分前注入一段归一化：把 `*-linux-ohos`/`*-ohos` 尾部的 `-ohos`
   映射为 `-gnu`，使 autotools/libtool 把目标当普通 Linux（本机原生构建，编译器
   与 sysroot 仍来自 conan 工具链）。已在真机验证该段可越过 triplet 检测。
7. **`xml2-config` shim**：joyce 的 `AM_PATH_XML2` 只认 PATH 上的 `xml2-config`
   程序（不走 pkg-config），conan libxml2 不装它，configure 报 "libxml needed"。
   配方 `_xml2_config_shim()` 生成一个 `xml2-config`，`--cflags` 输出
   `-I<prefix>/include -I<prefix>/include/libxml2`（每项必须是完整 `-I<dir>`；
   曾有一版漏了 `-I` 前缀、只输出裸路径，configure 把裸路径当源文件名、探测
   报 "test program failed"——已修复），`--libs` 从 conan 依赖图收集 `-L`/`-l`，
   `--version` 读安装头的 `LIBXML_DOTTED_VERSION` 使 configure 版本对拍测试通过。
   与 `sdl-config` shim 一同前置到 PATH。
8. **`AutotoolsDeps`（libpng AC_CHECK_LIB）**：joyce 的 configure 用裸
   `AC_CHECK_LIB(png, png_init_io)` 检测 libpng（无 `*-config` 程序），它只带
   `-lpng` 链接探针。conan libpng 是静态归档，其 `-L` 目录与传递依赖（zlib 等）
   不在 configure 初始 `LIBS/LDFLAGS` 里，探针链接失败 → configure 报
   "libpng not found - aborting"（真机失败阶段 compile）。配方 `generate()` 增加
   `AutotoolsDeps(self).generate()`：把整张依赖图的 `-I/-L/-l`（含传递依赖）聚合
   到 conanbuild 的 `CPPFLAGS/LDFLAGS/LIBS`，configure 以之作为初始值，令
   `AC_CHECK_LIB(png, ...)` 链接解析成功。`AutotoolsToolchain` 只提供工具链文件、
   不含依赖旗标，故必须加 `AutotoolsDeps`（仓库内 c-client/bambamc/cyrus-sasl2 等
   已有同款用法）。configure 运行用 `env="conanbuild"`，会自动读取生成的 conanbuild
   环境。
9. **`LD_LIBRARY_PATH` 清洗（musl loader el1 毒路径，编译阶段）**：joyce 的
   `AC_PROG_CXX` 在 `checking whether we are cross compiling` 时编译并运行最小 C++
   conftest（`.conan-configure`）。该 conftest 链接 `libc++_shared.so`（OHOS llvm C++
   运行库），而构建机系统默认 `LD_LIBRARY_PATH` 尾部带
   `/data/storage/el1/bundle/libs/arm64`（另一进程的应用沙箱目录）——目录存在但其
   文件对本进程不可访问，musl ldso 遇任一“存在但打不开”的条目会**放弃整条库搜索**
   （exit 127，报 `cannot run C++ compiled programs`）而不是跳过该条目，即使 SDK
   路径排在前面也无效。配方 `_sanitize_ld_library_path()` 在 build() 开头（configure
   前）清洗：剔除所有 `/data/storage/el1/bundle` 段，前置含 `libc++_shared.so` 的
   OHOS SDK llvm/lib 目录，并追加 host 依赖的 lib 目录（libpng/libxml2/sdl12-compat
   及其传递依赖），随后所有 `self.run(env="conanbuild")` 继承清洗后的值。与仓库内
   libcgroup/0.34 同款修复（musl-loader-el1 知识条目）。
10. **C++17 `register` 关键字（compile 阶段）**：joyce 2.4.2 是 2000 年代 C++，其
    bundled GUI 前端（`bin/JoycePcwTerm.cxx` 等 `bin/*.cxx`）仍使用 C++17 已移除的
    `register` 存储说明符。OHOS clang 工具链以 `-std=c++17`（SDK 默认）编译 C++，
    每个 `register` 都报 `error: ISO C++17 does not allow 'register' storage class
    specifier [-Wregister]`，10 处 error 直接中断 make（真机失败阶段 compile）。
    该诊断属于 `-Wregister` 警告组，配方 `generate()` 给 `AutotoolsToolchain` 追加
    `-Wno-register`（抑制）+ `-Wno-error=register`（防提升），并按 E293 同族追加
    `-Wno-error=dynamic-exception-spec`（防 `throw(Type)` 动态异常规范兄弟失败），经
    `CXXFLAGS` 传入 configure/AC_PROG_CXX。`register` 在 C++11 前仅是无操作提示，
    删除无行为影响。按知识 E293：`register` 仅存在于包自身内部 .cpp/.cxx（非安装
    公共头文件）时可用 toolchain-flag 降级，joyce 是 application、`register` 不在任何
    安装头里，故适用。同类先例：aiksaurus/coinor-vol（E293/Fallback）。

11. **`config.status` mktemp 临时目录不可写（`unsafe_local_mktemp`，compile 阶段）**：
    joyce 的 autoconf（config.status）在 `(umask 077 && mktemp -d "./confXXXXXX")`
    创建临时目录并在其中写 `subs*.awk`。真机文件系统上 `mktemp -d` 建出的
    0700 目录后续无法写入 → `can't create ./confXXXXXX/subs1.awk: Permission denied`
    → `could not setup config files machinery` 中断（配方 `_configure_ohos` 退出码 1）。
    前期曾用 `_mktemp_fallback_shim_for_ohos()`（PATH 前置 `mktemp` shim，参数含
    `conf` 就 `exit 1` 触发 autoconf `mkdir` 回退）连续三轮未生效：真机日志目录名仍为
    mktemp 风格 `confbfPpbI`，说明 shim 未拦截（`self.run(env="conanbuild")` 的子进程
    PATH 由 conanbuild env 覆盖 os.environ）；且即便 mktemp 失败，autoconf 自带的
    `mkdir` 回退仍用 `umask 077` 重建同款不可写 0700 目录（知识 E114）。改为**确定性
    `umask 077 → 022` 补丁**：新增 `_patch_autoconf_umask()`，在 `_configure_ohos` 把
    configure 拷成 `.conan-configure` 后用只读文本把 `umask 077`/`umash 077` 替换为
    `umask 022`/`umash 022`（configure 的 heredoc 模板会把该值带进生成的 config.status，
    临时目录随之变成 0755、属主可写），同时 best-effort 补源 configure。幂等、不跳测试。
    同类先例：zurl / darkice / dcfldd / dap / nagios 等（E011/E114 家族）。
12. **`package()` 中 `copy(delete=True)` 非法参数（package 阶段）**：原配方在
    `package()` 用 `conan.tools.files.copy(..., delete=True)` 删除 `*.la`/`*.dylib`，
    但 Conan 2.30 的 `copy()` **无 `delete` 关键字参数**，真机报
    `TypeError: copy() got an unexpected keyword argument 'delete'`（package() 阶段
    中断、conan create 退出码 1）。改为显式删除：`Path(package_folder/lib).rglob()`
    匹配 `*.la`/`*.dylib` 后 `p.unlink()`（best-effort），语义与原先一致（清掉携带
    构建树路径的 libtool 归档）。同类教训：conan `copy()` 只做"拷贝/keep_path/exclude"
    ，删除须用 rm/unlink。

## 上游测试（必须接入并如实运行）

上游测试位于 bundled LibDsk 的 `LibDsk/tools/Makefile.am`：

```
check_PROGRAMS = check1 check2 check3   # 顶层 make check 会构建并运行
```

- **check1**：纯几何计算 —— `dg_ps2ls`/`dg_ls2ps` 在 80 柱面 × 2 头 × 9
  扇区上做往返校验。**可在 HarmonyOS PC 通过**。
- **check2**：`dsk_open("/dev/fd0")` + `dsk_pread` 读真实软驱扇区。
- **check3**：`dsk_open("/dev/fd0")` + `dsk_ptread` 读真实软驱扇区。

`SdlTerm` 的 `test`/`psf2inc` 是 `noinst_PROGRAMS`（`make check` 不运行），
不计入 automake 测试注册。

**统计口径**：`upstream_test_total = 3`（`autotools_tests`——上游在
`LibDsk/tools/Makefile.am` 注册的 `check_PROGRAMS = check1 check2 check3`，共 3 个
测试程序）。**注意**：该 Makefile 只有 `check_PROGRAMS`、没有
`TESTS = $(check_PROGRAMS)`，因此 automake 的 `make check` 目标**只构建**这三个
测试二进制、**不会运行它们**（无 `# TOTAL/# PASS/# FAIL` 汇总输出）。真机上一轮
证明：`make check` 后 `HMBS_UPSTREAM_TEST_RESULT` 报 `discovered/executed/passed
全 0`。故配方 `_run_upstream_check` 改为：`make -j1 && make -j1 check`（构建
check1/2/3），然后**逐个直接执行** `check1 check2 check3` 二进制，用每个二进制的
真实退出码判定通过/失败（0=过，非 0=败），这是确定性的单一数据源：
- check1 通过；
- check2/check3 因 OHOS 无 `/dev/fd0`（无软驱硬件）失败 —— 属 `ohos_feature`
  缺口，带具体技术原因与证据（`dsk_open /dev/fd0` 返回驱动错误）。

`HMBS_UPSTREAM_TEST_RESULT` 由三个 check 二进制的真实退出码确定性得出
（discovered=3, executed=3, passed=1, failed=2），`gaps` 如实注明 2 个软驱用例。

## 新增测试（test_package）

joyce 安装 bundled LibDsk 的磁盘 CLI 工具（`dskconv` 等）与模拟器前端。
test_package 真机执行安装产物 `dskconv`（纯 CLI，无 SDL 显示依赖，稳健）：

1. `dskconv -formats` —— 输出包含支持的磁盘格式 "PCW / IBM 180k"；
2. `dskconv -formats` —— 退出码为 0。

`assertion_count = 2`，输出 `HMBS_TEST_PACKAGE_RESULT`。GUI 前端 xjoyce/xanne
需 SDL 显示（头less 环境无法可靠运行），故不纳入自动冒烟。

## 验证命令（真机）

```sh
cd archives/j/joyce/2.4.2
conan create . --build=missing -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# 期望：configure + make 成功；make check 跑 check1（过）、check2/check3（gap）
# 后打印 HMBS_UPSTREAM_TEST_RESULT 与（test_package 阶段）HMBS_TEST_PACKAGE_RESULT
```

## 已知限制与风险

- **源码下载（seasip.info Content-Encoding 陷阱，已解决）**：`www.seasip.info`
  把 `joyce-2.4.2.tar.gz`（其正文本身就是 gzip 流）错误标记为
  `Content-Encoding: gzip`。conan 的 HTTP 下载（requests）会据此**自动按 gzip
  解压**，把归档变成裸 `.tar`，导致 sha256 恒等于 `cddef0402...`，永远对不上
  配方记录的官方值 `85659a6a...`。配方 `source()` 不再直接调 conan 的
  `get(url)`，而是用 urllib（`Accept-Encoding: identity`，不解压）取回原始字节、
  自行校验 sha256 == `85659a6a...`，再写到本地临时文件后走 `get(file://...)`
  完成 strip_root 解包。这样绕开 conan 的自动解压，不依赖不存在的镜像，也**不改
  校验值**。注意：`source()` 阶段 `self.build_folder` 为 `None`（布局在 source
  后才解析），官方归档暂存目录用 `tempfile.mkdtemp`（复用 hmbs 注入的可写
  TMPDIR/TMP/TEMP）而非 build_folder，解包后清理。
- `xjoyce`/`xanne` 是 SDL GUI 前端：在无显示的头less CI / 真机只能编译、
  安装并做 `--version` 冒烟，无法真正渲染窗口；此乃应用运行期限制（对应
  sdl12-compat 的无头 dummy 驱动），不影响配方构建/打包正确性。
- check2/check3 依赖物理软驱设备，HarmonyOS PC 无此硬件，属平台客观缺口
  （ohos_feature）。
- **config.sub / OHOS triplet**：joyce 2.4.2 顶层 `config/config.sub` 是 2020 年脚本，
  不认 `aarch64-unknown-linux-ohos` 的 `ohos` OS。配方 `_patch_config_sub_for_ohos()`
  已在 configure 前把 `-ohos` OS 归一化为 `-gnu`（Linux），真机已验证可越过
  `checking build system type`（详见「适配要点 6」）。- `AM_PATH_SDL` 依赖 `sdl-config`（配方注入 shim）；若真机 SDL 探测仍失败，
  按实际报错补 XML2/PNG 的 pkg-config 传递（AutotoolsDeps 在 generate 侧可按需加入）。

## CI L0 门禁修复（test_package 反空壳，本轮）

CI #88299 在包构建前的 L0 质量门禁失败，两项：
- `L0c: No test source files in test_package/` —— 门禁用
  `find test_package -maxdepth 2 -name "*.c/.cpp/.cc/.cxx/.sh/.py" -not -name conanfile.py`
  找测试源文件；此前 test_package 只有 `conanfile.py` + `MANIFEST.yml`，无独立测试源文件。
- `L0d: test() method has no self.run() call — likely a stub` —— 门禁对
  `test_package/conanfile.py` 做文本检查：存在 `def test` 但不存在字符串 `self.run`
  即判空壳；此前 `test()` 用 `subprocess.run()` 真实执行 dskconv，文本上不含
  `self.run` 被误判。

**修复（两条门禁同时满足，不降低测试真实性）**：
1. 新增真实测试源文件 `test_package/test.sh`（POSIX sh）：对已安装的
   `dskconv` 做两项内容级断言——`dskconv -formats` 输出包含
   `PCW / IBM 180k`（LibDsk 标准格式，来自 `LibDsk/lib/dsksgeom.c`）且退出码为 0；
   脚本内自维护计数器，末尾输出唯一确定性的
   `RESULT: <passed> passed, <failed> failed` 汇总行。
2. 重写 `test_package/conanfile.py`：`test()` 改用 Conan 的
   `self.run('"$SHELL" test.sh <bindir>/dskconv > log 2>&1', env="conanrun")`
   真实执行脚本（`self.run` 命中 L0d），随后仅从脚本的 `RESULT` 汇总行解析
   passed/failed，discovered=passed+failed 单一来源，输出
   `HMBS_TEST_PACKAGE_RESULT`（discovered/passedCount）。删除不再使用的
   `subprocess` 导入。脚本非 0 退出会记录到日志，conanfile 据 RESULT 判定并
   在失败时 raise，保留真实执行语义。
3. `test_package/MANIFEST.yml` 的 `test_package_tests` 由 `conanfile.py` 改为
   指向 `test.sh`，描述其经 `self.run` 调用。

以门禁同款逻辑复检：L0c 命中 `test.sh`，L0d `def test` 与 `self.run` 均命中；
`ast.parse` 语法通过；`test.sh` 为 LF、shebang `#!/bin/sh`。上游测试接入与
统计口径未改动（`upstream_test_total=3`，autotools_tests）。
