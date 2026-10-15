# ddccontrol 1.0.3 适配笔记

## 编译环境

- 构建系统: autotools（configure.ac + Makefile.am；**git tag 归档不含 configure，配方内现场 `autoreconf -fi`**）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（aarch64-linux-ohos）
- 状态: built（见文末收尾块与 `reports/`）
- 货源: `https://codeload.github.com/ddccontrol/ddccontrol/tar.gz/refs/tags/1.0.3`
  （官方 codeload 直链，实测 200 / 175621B；sha256 `4f3a3d9a…dd11d1e` 本机实测。
  ⛔ 不用 Debian 池址——PF7 拉黑 `deb.debian.org`。）

## 编译步骤

1. **W0 依赖发布检查**（`§12.60` 前置、SKILL W0）：
   `bash ci/scripts/preflight_check.sh ddccontrol/1.0.3 --deps "libxml2/2.15.3.1 pciutils/3.13.0"`
   → 两项 `[OK] 已发布`、版本号未占用、rc=0。
   **依赖真实版本来自 `git ls-tree upstream/main`**（`archives/l/libxml2/` → 2.15.3.1；
   `archives/p/pciutils/` → 3.13.0），未猜版本。
2. **源码**: `init-build ddccontrol 1.0.3 --url=<codeload 直链>` → rc=0，
   上下文 `.build-context-ddccontrol-1.0.3`、源码树 `~/builds/ddccontrol-1.0.3.work`。
3. **语言预检（R47）**: `lang-preflight ddccontrol 1.0.3 --src <源码树>` → rc=0，
   `task=cpp / detected=c`（c↔cpp 兼容族，20 个 C 源文件主体占比 100%）。
4. **配方首稿检索**: `recipe-search ddccontrol` → 无相似配方（语料 8245），首稿走 conan-init 模板 + 手写改写。
5. **`build` 一条龙尝试（卡片指定步骤）**: 实测**未**在 init 段失败（与派发卡预期
   `EXIT_REASON=init_build_failed` 不符，已按实测上报），实际：
   `[3/14] configure failed (RC=127)`——`sh …/.work/configure: No such file or directory`
   （git tag 源无 configure，驱动未做 bootstrap）。`BUILD_RC=1`、日志无 `EXIT_REASON` 标记。
   按 `§12.60①`（配方文件全量就位后不要跑完整 build 一条龙）**跳过 build，直走 conan-verify**
   （其 create 不触发 init，不会覆盖配方；跑前已全量备份 `~/tmp/uc2/ddccontrol-1.0.3/backup-recipe/`，
   跑后 `diff -r` 与备份 **IDENTICAL**，`§12.60①` 担心的 conan-init 覆盖未发生）。
6. **手动探索编译（配方固化依据）**：autotools 生态探测 + 源码树事实核验（详见问题表）。
7. **配方固化**: `conan-init` 生成首稿 → 按上表逐项改写 → `conan-verify`（G0–G4 + L2/L4/L5）。
8. **收尾**: `finish … built` → `submit`（预期停 W4 审计前）→ `graph validate` → push 分支。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `build` 的 `[3/14] configure RC=127`：`configure: No such file or directory` | 源是 **git tag 归档**（无预生成 configure），驱动 configure 步前没有 bootstrap | 按 `§12.60①` 跳过 build 一条龙，配方内 `build()` 先 `autoreconf -fi`；直走 `conan-verify` |
| 2 | 设备 `autoreconf` 在 aclocal 阶段报 `Can't locate Automake/Config.pm` | `~/usr/local/bin/aclocal` 是 1.17 driver 配 1.16 share dir（本机实测；与 l3afpad 同款） | `tool_requires("automake/1.18")`（+ `libtool/2.5.4`），conanbuild env 的 PATH 优先于设备坏 aclocal |
| 3 | `configure.ac` 用 `IT_PROG_INTLTOOL`，树内无 `intltool.m4`、设备无 `intltoolize` | git 树不带 m4/；intltool 未装系统 | `tool_requires("intltool/0.51.0")`；收集全依赖图 aclocal/m4 目录写进 `ACLOCAL_PATH`（l3afpad 模式）。`autoreconf -fi` 内 autopoint 自动装 `po/Makefile.in.in` + gettext m4（实测）；⚠ 早先「无需 intltoolize」的推断**被第 4 轮证伪** —— `autoreconf -fi` 的 known-programs 含 `intltoolize`（见 #14，shim 处置） |
| 4 | 上游 `PKG_CHECK_MODULES([GIO_UNIX], [gio-unix-2.0 >= 2.30.0])` 无条件必查，但 conan glib 只生成 `gio-2.0.pc` | conan glib 把 gio 组件 `pkg_config_name` 声明为 `gio-2.0`，无 gio-unix 别名 | `generate()` 内 `set_property("pkg_config_name", "gio-unix-2.0")` 改名（appres xproto 别名先例）；同一项目同一批头文件 |
| 5 | 设备 `<sys/io.h>` **存在且能编译，但没有 `inb`/`outb` 声明**（`probe: call to undeclared function 'inb'`） | OHOS 放的是空壳头；configure `AC_CHECK_HEADERS([sys/io.h])` 会判真 → `HAVE_SYS_IO` 拉入 `intel810.c`/`sis.c`（x86 legacy 端口 I/O VGA 后端）→ ddcpci 链接期 undefined `inb` | configure 参数 `ac_cv_header_sys_io_h=no`（缓存变量强制关，**不改上游源码**）；nvidia/radeon/via 后端与 libpci 路径不受影响 |
| 6 | `gdbus-codegen`（daemon BUILT_SOURCES 生成 interface.c/h）不在 PATH | 它随 conan glib 包的 bindir 走，非系统工具 | `generate()` 把 glib 包 `bin/` `prepend_path("PATH")`（VirtualBuildEnv 之前） |
| 7 | pciutils / libintl 是 `AC_CHECK_*` 直查（不吃 `.pc`） | PkgConfigDeps 只覆盖 libxml2/glib 两个 PKG_CHECK | `tc.environment()` 手工 append pciutils/gettext 的 `CPPFLAGS=-I`、`LDFLAGS=-L`（pmount 方式；**刻意不用 AutotoolsDeps**——它会把 gettext 的 cpp_info.libs 拍平成假 `-l`） |
| 8 | config.status 的 `umask 077 && mktemp -d ./confXXXXXX` 在 setgid HMDFS 建 700 目录不可写（E110/E112 族） | 同 l3afpad/appres/pmount | `build()` 内对**生成后的** configure 幂等替换 `umask 077`→`umask 022`（只动生成物，非上游源；无平台宏 R8/PF5） |
| 9 | `init-archive` 报「conanfile/conandata/test_package 模板不可用」告警（首建时未生成配方脚手架） | `scripts/ohc/init_archive.py` 找 `conanfile-autotools.py`，实际模板文件是 `.tmpl` 后缀（`conan_recipe.py` 的映射是对的）——框架小 bug | 非阻塞告警；配方由 `conan-init` 正确生成。**不改框架**（`scripts/` 只读），终报披露 |
| 10 | gnome GUI（gddccontrol）与 doc 构建 | 上游硬依赖 gtk+-2.0 开发件、xsltproc/docbook，OHOS 无打包 | `--disable-gnome`（不传 `--enable-doc`，默认关）；`gddccontrol.desktop.in` 不参与构建 |
| 11 | G2 首轮 `source()` 失败：`BadZipFile: File is not a zip file`（下载与 sha256 均过，挂在解压） | codeload URL 结尾是 tag 名（`…/tar.gz/refs/tags/1.0.3`）**无扩展名** ⇒ `get()` 从 URL 推文件名得 `1.0.3` ⇒ `unzip()` 对非 `.tar.*` 名字回落 zip 解码器 | `get(..., filename="ddccontrol-1.0.3.tar.gz")` 显式指定 tar.gz 解码器（**`abcmidi/20260609` 原样同坑同解，其注释逐字记录此机制**） |
| 12 | G2 次轮 `autoreconf` 内 `autopoint` 失败：`can't open //share/gettext/archive.dir.tar.xz` + `infrastructure files for version 0.18.1 not found` | conan gettext 包的 `autopoint` shell 脚本硬编码 `prefix="/"` 且重定位分支被编译掉（`if test "no" = yes` 恒假）⇒ `gettext_datadir` 恒为 `//share/gettext` | 该脚本第 32 行是 `: ${gettext_datadir="…"}` 环境变量默认值惯用法 ⇒ 设 `gettext_datadir=<gettext 包>/share/gettext`（**已在缓存包上实测该路径含 `archive.dir.tar.xz`**；env 覆盖实测 `autopoint --version`/`--help` 正常）。与 l3afpad 的 intltoolize `prefix=/` shim 属同族「烘死前缀」坑 |
| 13 | 第 12 条的 define **执行了却没进生成的 env 脚本**（`[dbg] DEFINED` 打了、`grep gettext_datadir` 仍 0 命中） | **conan 2.29.1 的 `VirtualBuildEnv` 只合成「依赖的 `buildenv_info`」（profile + build requires + host requires），根配方自己的 `buildenv_info` 被静默忽略** —— 读 `conan.tools.env.virtualbuildenv` 源码证实 + `conan install` 探针复现（消费者的 define 从不落盘）。⚠ 该死路连带使首轮写的 ACLOCAL_PATH 收集与 glib `PATH` prepend **同为无效** | 消费者侧环境一律改走 **`AutotoolsToolchain` 的 `env=tc.environment()`**（写进 `conanautotoolstoolchain.sh`，由 `conanbuild.sh` 聚合 source；`klavaro/3.14` 同通道先例）。三个变量（`gettext_datadir` / `ACLOCAL_PATH` 含 intltool.m4 / `PATH` 含 glib 的 gdbus-codegen）+ `CPPFLAGS`/`LDFLAGS` 全部改道后，`conan install` 探针实测四项齐落脚本 |
| 14 | G2 第 4 轮（autopoint 环节已过）挂在下一处：`intltoolize: cannot copy '//share/intltool/Makefile.in.in' to 'po/Makefile.in.in'`（伴 `grep: //share/aclocal/intltool.m4: No such file`） | `autoreconf -fi` 的 known-programs 含 `intltoolize`（`IT_PROG_INTLTOOL` 触发），而 **conan intltool 包的 `intltoolize` 脚本第 39 行烘死 `prefix=/`**（缓存包实测），且它**不从 `$0` 推导前缀** ⇒ PATH 包装无解 | **`l3afpad/0.8.18.1.11` 逐字同款 shim 先例**（其 docstring 原文：「`intltoolize` hardcodes `prefix=/` … always looks for its data under `//share/intltool` … no PATH wrapper or absolute-path exec can help」）：`build()` 内复制脚本到 `toolshim/`、`re.sub(r"^prefix=/", "prefix=<intltool 包目录>")`，以 `PATH="<shim>:$PATH" autoreconf -fi` 内联置前。**shim 只落我方 `conanfile.py`（配方件），不动官方 intltool 制品包**。**先例族**：#12 autopoint `prefix="/"` + 本条 intltoolize `prefix=/` —— gettext/intltool 系脚本「烘死前缀」同一机制面 |
| 15 | G2 第 5 轮（intltoolize shim 生效、configure 跑到中段）挂在 `configure: error: XML::Parser perl module is required for intltool` | `IT_PROG_INTLTOOL` 的 XML::Parser 探针：**设备 perl 无此模块**（`perl -MXML::Parser` 实测 rc=2 `Can't locate XML/Parser.pm`，hnp perl 同样无 ⇒ 探针在此设备**永远不可能通过**，非抖动）；本包 `--disable-gnome` + doc 关 ⇒ **xml.in 消费者 = 0**，探针对本包不适用 | **双出处机制旁路（非 mock）**：① **`intltool.m4:146` 自带官方开关** `if test "x$2" != "xno-xml"`（第二参 `no-xml` 即跳过探针）⇒ 生成物 configure 中该字面量全文件唯一（`grep -c` = 1），`_patch_configure_generated()` 反转 `!=` 为 `=` 使其走自己的旁路；② **`klavaro/3.14` patch0001 逐字同解先例**（其 docstring：「XML::Parser perl module cannot dlopen its XS extension from OHOS app-sandbox paths — **patch 0001 bypasses the configure check**」；klavaro 另配 `-x` merge shim 是为它自己的 `klavaro.appdata.xml.in`，本树无同类消费者故不需要）。与 #5 `ac_cv_header_sys_io_h=no` 同类：**对不适用探针的旁路**，不伪造模块加载、不改上游源、不产补丁件 |
| 16 | G2 第 6 轮（configure 全绿、`lib`→`daemon`→`ddccontrol` 三个子目录编过）挂在最后 `ddcpci` 的链接：`ld.lld: error: undefined symbol: libintl_gettext`（`referenced by main.c main.o:(main)`） | **上游 musl 缺口**：gettext 包 `libintl.h:169` `# define gettext libintl_gettext`（`:159 extern char *libintl_gettext`）⇒ 我们注入的 `-I<gettext>/include` 生效后每个 `gettext()` 都指向**只存在于 `libintl.{a,so}` 的符号**（`nm` 实测 `T libintl_gettext`）；`AM_GNU_GETTEXT` 把 `-lintl` 放 `INTLLIBS/LIBINTL`，上游只接进 `ddccontrol`/`service` 的 `$(LIBINTL)`，**`src/ddcpci/Makefile.am` 的 LDFLAGS 只有 `-Wl,-z,now`**（上游按 glibc 写：gettext 在 libc 里）⇒ musl + external gettext 下必然缺；链接行实测**有 `-L<gettext>/lib` 无 `-lintl`** | **双出处机制修复（非 mock）**：① **`klavaro/3.14` 逐字同法**（其 docstring：「recipe appends -L{glib libdir} **-lintl to LIBS**」）⇒ toolchain env `append("LIBS", "-lintl")`，经 configure 落 Makefile 全局 `LIBS`（automake 链接行末位，静态/动态序都对）；② **反例对冲**：`l3afpad` 警告「裸 `-lintl` 进 LIBS 会让 configure 的 conftest 链不过」——**本包不适用**，因为 `-L<gettext>/lib` 已在 `LDFLAGS`（ddcpci 链接行实测在）⇒ conftest 的 `-lintl` 同样可解析；运行期 `-lintl.so` 由 conanrun 注入（gettext 是 host requires） |
| 17 | G2 第 7 轮（**包体全绿**：`Packaged 4 files: ddccontrol_service, ddcpci, ddccontrol, COPYING`、包布局齐全）挂在 test_package：`test.sh: line 26: ddccontrol: command not found`（rc=127，0/4） | **conan `Require.run` 默认 False**（`requires.py:135` `_default_if_none(self._run, False)`），本包是静态 `library` ⇒ 被测 require `run=False` ⇒ `VirtualRunEnv` 源码硬门 `if require.run:` 跳过 `runenv_from_cpp_info` ⇒ **包自己的 `bin/` 从不进 conanrun PATH**。三对照坐实：生成的 conanrunenv 里 PATH 含 libxml2/glib/gettext（shared⇒run=True）**却无 pciutils（静态⇒run=False）**；`appres` 能过是因为它 `package_type="application"`（run 默认 True）；二进制本身在且可执行（`bin/ddccontrol` 108992B -rwx ⇒ 排除产物问题） | `test_package/conanfile.py` 改 **`self.requires(self.tested_reference_str, run=True)`** —— **仓内 29 件同款先例**，其中 **`depqbf/5.01` 注释逐字同根因**：「depqbf is a library package type (default run=False), otherwise test_bin.sh cannot find the depqbf command」。`test_package` 是我方配方件 ✓；LD_LIBRARY_PATH 已含三家 shared 依赖 |

## 源码修改

**0 个补丁**（`conandata.yml` `patches: {}`）。全部构建期改写均为「生成物 / 参数 / 工具副本」层面，
不改上游源文件、不注入平台宏（R8/PF5）：

- `autoreconf -fi` 现场生成 configure/aclocal 机制（上游 git 树本无这些文件）；
- 对生成后的 `configure` 做幂等替换两处：`umask 077`→`umask 022`（E110/E112）；
  `test "x" != "xno-xml"`→`=`（intltool 官方 `no-xml` 开关，跳过本包不适用的 XML::Parser 探针，见 #15）；
- configure 参数 `ac_cv_header_sys_io_h=no`（x86 端口 I/O 后端，见问题 5）；
- `toolshim/intltoolize` 脚本副本改 `prefix=/`→包目录（只改我方 build 目录里的副本，官方包不动，见 #14）；
- 全局 `LIBS` 追加 `-lintl`（补上游 musl 缺口，见 #16，klavaro 同法）。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| libxml2 | 2.15.3.1 | host | `PKG_CHECK_MODULES([LIBXML2], [libxml-2.0])` 硬依赖（conf/monitor db 为 XML） |
| glib | 2.88.3.1 | host | `gio-unix-2.0 >= 2.30.0` 无条件硬依赖（D-Bus 服务/客户端走 GDBus）+ `gdbus-codegen` |
| pciutils | 3.13.0 | host | `--enable-ddcpci`（上游默认开）探 `<pci/pci.h>` + `-lpci` |
| gettext | 0.22.5.1 | host+tool | `<libintl.h>` + `bindtextdomain()`（musl libc 无 gettext ⇒ 真 libintl）；msgfmt/msgmerge 供 configure/po |
| automake | 1.18 | tool | 设备 aclocal 损坏（问题 2） |
| libtool | 2.5.4 | tool | `LT_INIT` / `ltmain.sh` |
| intltool | 0.51.0 | tool | `IT_PROG_INTLTOOL` 的 m4 与 configure 期工具 |

（`conan graph info` 可解性读数见「验证结果」。）

## 能力面披露（运行期 · 实测 · 逐项）

> **`/dev/i2c-*` 与 `/sys/class/i2c-dev` 不存在（ENOENT）、`/dev/dri` 不存在、
> `/sys/class/drm` 本进程 EACCES、内核无 i2c/drm/smbus 模块 ⇒ 运行期无法打开
> DDC/CI 设备节点、核心寄存器读写路径在本设备不可用；消费者测试仅覆盖
> `-h`/`-V` 等非设备路径。**

实测命令与读数（B 机，2026-10-07 ST 取证 + 本会话亲测一致）：

```bash
glob /dev/i2c-*            → 无
open /dev/i2c-0            → ENOENT
ls /sys/class/i2c-dev      → ENOENT
open /dev/dri              → ENOENT
stat /sys/class/drm        → EACCES（目录存在但本进程不可访问）
grep -E 'i2c|drm|smbus' /proc/modules → 无
```

- 这是**运行期能力面、不是编译墙**：上游 i2c 支持是 `open()` 期探测、
  编译只依赖 `<linux/types.h>`/`<linux/i2c-dev.h>` 头（本机 clang 实测可编译）⇒ 编译可过。
- ⛔ **不谎称 DDC 可用**：DDC/CI 的 i2c-dev 与 drm fallback 两条硬件路径在本设备
  **运行期全不可用**；`test_package` 据此只断言参数解析阶段的文本路径（下表 4 条）。

## 测试口径（三处同源：本件 / `test_package/MANIFEST.yml` / PR 正文两表）

- **上游 N = 0（注册口径）**：`§12.72` 四口径 2026-10-08 于 git tag 源码树实测——
  `test*/` 框架 0 · `*/res` 语料 0 · `**/*RUNTEST*` 0 · `src/demo|examples/*.c` 0；
  全部 `Makefile.am` 无 `TESTS=`/`check_PROGRAMS=`、`configure.ac` 无测试宏。
- **未注册测试脚本资产 = 5**（双口径申报，照 osip 先例）：
  `scripts/common_test.sh` + `scripts/valgrind_{ddccontrol,dbus_service}{,_launcher}.sh`。
  **2026-10-15 返修轮已逐条真实执行 → 执行 5 / 通过 0**（逐项首条真实错误见「对话 #2」；
  ①–④ 为各项失败的先决条件，均属**本次适配以外**的因素）：① `common_test.sh` 首段强制 root
  （`EUID != 0 → Run as root`，本进程非 root）；② 需要 `valgrind` 二进制（`command -v valgrind` → MISSING，
  制品仓 `conan download valgrind -r=ohpcd --only-recipe` → `Recipe 'valgrind' not found`）；
  ③ 对真实 DDC/CI 设备做寄存器读写（`ddccontrol -p` 扫 `/dev/i2c-*`，本机 ENOENT + 无 i2c 内核模块，
  见能力面披露）；④ 用 `mktemp /tmp/...` 写日志（设备 `/tmp` 只读，E002）。
  ⇒ 如实记 **执行 5 / 通过 0**（**不记 pass、不降分子、⛔ 不把「没跑」写成「通过」**）。
- **适配后 N′ = 4**（`test_package/test.sh` 消费者断言，`conan create` 内实测）：
  ① `-h` stdout 含 `ddccontrol version 1.0.3`（版本横幅在 getopt 之前无条件打印）；
  ② `-h` stderr 含 `Usage:`（usage 打到 stderr）；③ `-h` 退出码 = 1（上游 `usage()` 即 `exit(1)`，如实按上游断言）；
  ④ 裸调用（无参）→ rc=1 + 版本横幅。**全部在参数解析阶段返回，先于 `ddcci_init()`/D-Bus/`open()` 任何设备访问**。
- N′(4) ≥ N(0) ⇒ 满足「适配后合计 ≥ 上游」。
- **披露：配方 `build()` 未调 `make check`** —— 注册口径 0（无 `TESTS`/`check_PROGRAMS`），
  `make check` 空转（实测见「验证结果」）；上游 5 个脚本**已逐条真实执行（执行 5 / 通过 0）**、
  先决条件逐条在上（未降测试、未删夹具、未改上游任何用例）。

## 路径 B 查重读数（四范围 · 2026-10-08 实测；`B判定` 归主理，此处只给读数 + 建议）

- **范围1 历史归档**：`archives/` 无 `ddc*` 目录（`ddccontrol` 首配实证）；notes 含 i2c/ddc 关键词 **12 件**
  （`m1ddc`×2 为 DDC 工具先例、`c-periphery`/`periphery`/`lcdproc`/`owfs`/`libusbsio` 等 i2c 面、
  `xf86-video-savage` drm 面）；**libdrm/2.4.133 已归档**（drm 域有包、无 i2c-dev 空白区条目）。
- **范围2 知识图谱**：`index.tsv` 对 `i2c|ddc|drm|smbus` **0 命中**；全部 `E*.kv` 全文仅 `E358` 出现 1 次
  子串 `ddc`（该条内容是 Rust/Cargo 锁迁移，与本域无关，判误配）；`pre-scan-rules.yaml` 对 i2c/drm **0 规则**。
- **范围3 经验库**（含 `14-最终防错清单.md`）：`i2c|ddc|drm|smbus` **0 命中**（14-清单单独 grep 亦 0）；
  `适配经验汇总.md` 索引 0 命中。
- **范围4 B 草稿库**：22 对草稿 + README/预派发命中表，`i2c|ddc|drm|smbus` **0 命中**。
- **附**：`OHOS行为探针清单.md`（SCT 空白区机制表）对 `i2c|drm|smbus` **0 命中** ⇒ **i2c-dev 运行期能力面
  确为未探空白区**，与登记表 `B潜力=B中` 的依据一致。
- **建议（归主理裁）**：四范围 0 真命中 ⇒ 无既有条目可 `hit`；i2c-dev/drm 能力面属空白区机制候选
  （`B方向=create` 的事实基础齐），或按 appres 同夜先例记 `none` + 全量披露；**判读归主理**。

## 验证结果

```bash
# W0（rc=0）
$ bash ci/scripts/preflight_check.sh ddccontrol/1.0.3 --deps "libxml2/2.15.3.1 pciutils/3.13.0"
[OK] 已发布: libxml2/2.15.3.1 / pciutils/3.13.0 · [OK] 版本号未被占用: ddccontrol/1.0.3

# 语言预检（rc=0）
$ ohc-run.py lang-preflight ddccontrol 1.0.3 --src <源码树>
语言匹配: task=cpp, detected=c — 继续适配主流程

# 构建期实测（详见问题表 1–16）
$ ohc-run.py build ddccontrol 1.0.3            # → BUILD_RC=1 [3/14] configure RC=127（git tag 源无 configure）⇒ 按 §12.60① 跳过
$ ohc-run.py conan-verify ddccontrol 1.0.3     # → 9 轮收敛（A-F 六类别，逐轮取证修复）
                                               #   r8: ✅ 配方验证通过 —— G0/G1/G2/G3 PASS + G4/L2/L4/L5 无阻塞
                                               #   r9: 证据恢复轮（与 r8 结果 IDENTICAL；日志共 9 份 conan-verify{,-r2..r9}.log）
                                               #   reports/conan-verify-report.md Verdict=PASS（r9 实测 Date=2026-10-08T05:34:13.897439）
$ grep -c 'Calling build' reports/conan-create.log      → 1   # 真编译非缓存命中（cava 口径）
$ grep -c 'Building from source' reports/conan-create.log → 1
# 消费者测试（conan create test 阶段，同轮）
test ddccontrol 1.0.3: 4/4 checks PASS

$ ohc-run.py finish ddccontrol 1.0.3 built     # → EXIT_REASON=finish_success；W3 本地 CI 模拟通过
                                               #   （.ci-result.json 落盘；JUNK_PR_DIFF=pr.diff 压掉 stale 基线 JC6）
$ grep -c 'Calling build' reports/w3-local-ci.log → 1   # W3 亦真编译

# 上游 make check 实跑（reports/make-check.log，Duration 3s）
$ make check -j1                               # → RC=2
src/{lib,daemon,ddccontrol,ddcpci}: Nothing to be done for 'check'   ← 注册用例 0 实证
po/: intltool-update -m 检出 po/POTFILES.in 漏登记 3 个含翻译源文件（dbus_client.c/service.c/printing.c）→ exit 1
                                                # 上游清单缺陷、环境无关；非测试用例 —— 归因见 reports/test-report.md「问题1」
```

## 注意事项

- **`/dev/i2c` 打不开不是停手理由**：按 appres #14953 先例交付，但测试**不碰真设备**（见能力面披露）。
- 运行期必需 `LD_LIBRARY_PATH`（libxml2/glib/libintl 来自 conan 缓存）——`test_package` 经
  `VirtualRunEnv`（`env="conanrun"`）注入，裸跑二进制会 rc=127。
- 软件级 `commands.json` 已建（R38：`bindirs=["bin"]` ⇒ CLI 型）。⚠ 已知互斥：本地 PF9 对软件级文件
  报「缺版本目录层」属 `§12.82` 记档的系统性误报（PF8/R38 反向要求它存在），建 PR 时按 `§12.82` 走法处理。
- `status` 工作区出现 `archives/l/libXext/*` 两行为**已知幻影**（派发卡记档），不提交、不回滚。

## 对话记录

### 对话 #1 — 2026-10-08 适配全程（ddccontrol 1.0.3）

- **W0/预检**：`preflight --deps "libxml2/2.15.3.1 pciutils/3.13.0"` rc=0（版本取自 `git ls-tree upstream/main`，未猜）；
  另实测 `configure.ac` 无条件要求 `gio-unix-2.0` ⇒ 实际依赖含 **glib/2.88.3.1**（卡片两依赖面之外的实测扩展，已报主理）。
- **configure 参数**（最终形态，写回 manifest `build.configure_options`）：
  `--disable-gnome --build=aarch64-linux --host=aarch64-linux ac_cv_header_sys_io_h=no --enable-static --disable-shared`
  （+ toolchain env：`gettext_datadir` / `ACLOCAL_PATH` / `PATH`(glib gdbus-codegen) / `CPPFLAGS`·`LDFLAGS`(pciutils·gettext) / `LIBS=-lintl`）。
- **conan-verify 9 轮收敛**（每类首错逐字取证、逐轮报主理拿 go）：
  r1 `BadZipFile`（filename=）→ r2/r3 `autopoint //share/gettext`（⚠ r2+r3 同类 2 轮我未停 = 违规，已认；env 覆盖 + VirtualBuildEnv 死路改道）
  → r4 `intltoolize //share/intltool`（l3afpad shim）→ r5 `XML::Parser`（intltool.m4 no-xml 开关 + klavaro patch0001 先例）
  → r6 `libintl_gettext`（上游 musl 缺口，`LIBS=-lintl`，klavaro 同法 + l3afpad 反例对冲）
  → r7 `ddccontrol: command not found`（`Require.run` 默认 False，`run=True`，29 件先例）→ **r8 PASS**（4/4）
  → **r9 证据恢复轮 PASS**（与 r8 结果 IDENTICAL；`conan remove` 后强制重建，`Calling build=1` 复核）。
- **finish**：r1 挂 stale-基线 JC6（131 包，`origin/main` 落后 3266）⇒ r2 带 `JUNK_PR_DIFF=pr.diff`（8 文件纯 ddccontrol）
  ⇒ **W3 本地 CI 通过**；Step6 README/tar.gz、Step7 `E219/E253/E305` 空 root_cause、Step8 `gen_summary`、W2「2104 配方+框架」
  = 卡面已知基线假阳性，照报不修。
- **`make check` 实跑 RC=2**：src 注册用例 0（空转实证）；po/ 为上游 `POTFILES.in` 漏 3 文件的维护检查（环境无关），
  非测试用例 ⇒ 未改上游清单、如实记（`reports/test-report.md` 问题1 + `reports/make-check.log` 原文）。
- **`.staging-verified` 未生成的处置（披露）**：该标记由 build 驱动 Step8 对 staging `bin/*` 逐个跑 `--version` 产生，
  本包按 `§12.60①` 跳过驱动故未走该步；**且不可安全复刻** —— 实读 `src/ddcpci/main.c`：`main()` 首两行即
  `pci_alloc(); pci_init(); pci_scan_bus()`，**在参数校验之前就扫 PCI 总线** ⇒ 跑 `ddcpci --version` 等于碰设备面，
  与「测试不许碰真设备」冲突 ⇒ **不伪造该标记**；`submit` 无此硬门（源码 Gate 0-4 不含 staging），finish Step10 仅 WARN。
- **能力面**：`/dev/i2c-*`、`/sys/class/i2c-dev` ENOENT；`/dev/dri` ENOENT；`/sys/class/drm` EACCES；内核无 i2c/drm/smbus
  ⇒ 运行期 DDC/CI 全不可用（编译不受影响）；测试零碰设备（横幅在 getopt 前、usage 先于任何 open()）。

---

### 对话 #2 — 2026-10-15 返修轮（rule4 真实执行上游用例）

- **触发**：外部审查 2026-10-14 VERDICT=FAIL，rule4 原文「上游有用例 5 个但一个也没测（0/5），无论任何理由
  均不通过，请解决后真实执行上游测试用例」；同刻行级意见「⚠ test_package 需复核」。
- **静态复核**（第一手，tarball sha256 `4f3a3d9a…11d1e` 与 conandata 逐字一致）：全树
  `TESTS =|check_PROGRAMS =` **0 命中**、`test*` 目录 **0** ⇒ automake 注册用例仍 = 0；测试脚本资产仍 = 5。
- **真实执行**（本机、bash 5.3.9、每条独立进程执行，输出留档 `~/tmp/uc2/ddccontrol-fix/runlogs/`）：
  1. `bash scripts/common_test.sh` → rc=1，首行 `Run as root`
  2. `bash scripts/valgrind_ddccontrol_test.sh` → rc=1，首行 `Run as root`
  3. `bash scripts/valgrind_ddccontrol_test_launcher.sh` → rc=1，错误链条：
     `make: jobserver mkfifo: …/GMfifo39096: Operation not permitted` →
     `make: *** No targets specified and no makefile found.  Stop.` →
     `fatal: Authentication failed or Permission denied !`（clone GNOME.supp）→ `open /dev/tty for write failed`（sudo）
  4. `bash scripts/valgrind_dbus_service_test.sh` → rc=1，首行 `Run as root`
  5. `bash scripts/valgrind_dbus_service_test_launcher.sh` → rc=1，同 3) 链条（make → clone → sudo）
  ⇒ **执行 5 / 通过 0**。
- **先决条件穷尽探针**：`sudo -n true` → rc=1（`open /dev/tty for write failed`，无免密 sudo）；`su` 不存在；
  `command -v valgrind` → MISSING、`conan download valgrind -r=ohpcd --only-recipe` → `Recipe 'valgrind' not found`；
  `/dev/i2c-*` 与 `/sys/class/i2c-dev` → ENOENT；`/proc/modules` 无 i2c/drm/smbus；`/dev/dri` → ENOENT；
  `mktemp /tmp/probe.XXXX` → `Read-only file system`。
- **结论**：5 个脚本的硬前置（root + valgrind + 真实 DDC/CI 硬件 + 可写 /tmp）在本平台全部不可得
  ⇒ 如实申报 **执行 5 / 通过 0 + 逐项技术原因**；`test_package` 保持 4 条行为断言不变
  （CI #88930「Conan test_package: 通过」实证）—— libddccontrol 公开 API 全部以已打开 i2c 设备为前置、
  **无 device-free API**，二进制行为断言即本平台诚实上限。
- **本轮改动面**：仅本 `notes.md` + `manifest.yaml` 注释 + PR 正文/讨论回复；⛔ 未改上游任何测试用例、
  ⛔ 未 resolve 行级意见（resolve 归 CIW）。

---

**编译结束**: 2026-10-08 05:15
**最终状态**: built
