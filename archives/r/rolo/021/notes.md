# rolo 021 适配笔记

## 编译环境

- 构建系统: autotools（GitHub v021 tag 只带 `configure.ac` + 各 `Makefile.am`，无生成物，需 `autoreconf -fi`）
- 编译日期: 2026-10-13（首轮工作树，真机预检待跑）
- 编译器: clang/clang++ 15（OHOS aarch64，经 AutotoolsToolchain 注入 CC/CONFIG_SHELL）
- 状态: built（配方完整；真机验证待 HMBS 预检，见「验证结果」）

## 上游信息

- 上游仓库: https://github.com/libvc/rolo（vCard 联系人管理，ncurses 前端）
- 上游版本: v021（tag commit `61587842d051779cd90b76f10f123ce5a6ab583a`）
- 源码包: `https://github.com/libvc/rolo/archive/refs/tags/v021.tar.gz`，38248 字节，
  sha256 `eaf69f0d…77f946`（2026-10-13 下载实测，根目录 `rolo-021`，共 39 个文件）
- 许可证: GPL-2.0-or-later（`src/main.c` 头声明 "either version 2 … or (at your option) any later version"）
- 产物: 单一可执行文件 `bin/rolo`（`src/Makefile.am: bin_PROGRAMS = rolo`）→ `package_type = "application"`

## 上游测试申报表（R51 清点）

**结论：上游有 4 个 shunit2 单元测试，必须接入真机完整执行。**

| # | 测试函数 | 文件 | 行为 |
|---|----------|------|------|
| 1 | test_rolo_version | test/run-tests | 断言 `rolo -v` 输出 == configure.ac 中 AC_INIT 的 `rolo 021` |
| 2 | test_rolo_startup_and_help | test/run-tests | `echo hqq \| TERM=dumb rolo -f contacts.vcf`（无头驱动 curses） |
| 3 | test_rolo_search_and_delete | test/run-tests | mktemp 拷贝 fixture，搜索 `Burger` 后删除，grep 确认消失 |
| 4 | test_rolo_move_and_edit | test/run-tests | `ROLO_EDITOR=cat` 导出 `Alex Winter` 条目，断言 `FN:` 行 |

- 入口: `test/Makefile.am` 的 `check:` 目标（`HAS_SHUNIT2=yes` 时跑 `./run-tests`，否则打印 `Unit tests skipped`）；
  顶层 `SUBDIRS = src doc test`，故顶层 `make check` 递归执行。
- Fixture: `test/contacts.vcf`（真实 vCard，首条 `FN:Mr. John Q. Public, Esq.`）。
- 口径: `upstream_test_total = 4`，`upstream_test_count_method = auto`（单一 shunit2 框架：
  测试函数数 == shunit2 `Ran N tests.` 汇总行）；`upstream_test_in_build: true`。
- 证据链: build() 把 `make check` 输出重定向到 `make_check.log` 后回放，
  仅解析该文件的 shunit2 汇总行（`Ran N tests.` + `OK`/`FAILED`），落证到
  `share/doc/rolo/upstream-check.json`（单行 JSON），test_package 原样重发为
  `HMBS_UPSTREAM_TEST_RESULT`。无任何算术修补：无汇总行即报 error，绝不猜数。

## W0 — 依赖发布检查（适配前第一件事）

| 依赖 | 上游 configure 要求 | 本仓状态 | 结论 |
|------|--------------------|----------|------|
| libvc | `AC_CHECK_LIB(vc, vc_new)` 致命 | **无配方**（仅有无关的 libvcflib） | 配方内 vendoring：官方 v013 tag（sha256 `a43bf49f…821c2`）私有 prefix 静态编译（缺原生 yacc/lex 时先私有编译 m4/1.4.19+bison/3.8.2+flex/2.6.4 工具链，见问题表 #12），不发布 |
| ncursesw + menuw | `AC_CHECK_LIB` 致命 | ncurses/6.6（`--enable-widec`，含 menuw） | requires 已声明，待真机核验 |
| glib-2.0 | `PKG_CHECK_MODULES` 致命 | 仓内各 glib 版本在当前 profile 下均无二进制，任何 requires 都强制 meson+libffi 源码构建链 | 不再 requires：build() 原地改写 configure.ac+entry.c 消除 glib 边（等价本地实现，见问题表 #11） |
| libffi（原 glib 传递） | 曾 override 3.5.2，后回退规范 3.4.4，两者在当前 profile 下均无二进制可用 | 不再经 glib 引入：glib 边整体消除（见问题表 #11），图中已无 libffi 节点 |
| unac | `PKG_CHECK_MODULES` 致命 | unac/1.8.0（配方存在但 manifest 状态仅 built、无已发布二进制；且其 `tool_requires("libtool/2.5.4")` 所指版本本仓根本不存在） | 配方内 vendoring：Debian 官方 orig tarball（与 unac 配方同 URL/sha256）私有 prefix 静态编译，不再 requires（见问题表 #8） |
| shunit2 | 仅测试门（缺时 WARNING+跳过） | 无配方 | 配方在无系统副本时从官方源按 pin 哈希现取（见下），缺网则如实报 skipped |
| automake/aclocal/libtoolize | `autoreconf -fi` 所需 | automake/1.18、libtool/2.5.4（多已合入配方在用） | tool_requires 已声明 |

libvc 无仓内配方，`conan create` 若声明 `requires("libvc/013")` 会在依赖解析直接失败（本轮真机证据）。改法：不在 conan requires 声明，改为配方内用官方源码（https://github.com/libvc/libvc，v013，LGPL-2.1，sha256 `a43bf49ff2b9e17cf7e332f3aa9f218c46782400aa848e6af4589e6b244821c2`）在 `build()` 先静态编译到私有 `libvc-prefix`（R49），再以 `CPPFLAGS/LDFLAGS` 指给 rolo 的 configure/make；产物不进包、不导出。

## 编译步骤

```bash
# in-source（test/run-tests 用 $0 相对路径找 ../configure.ac、contacts.vcf、../src/rolo）
# 全程无 autoreconf/configure/make（第九策略，见问题表 #20）：
byacc -d vc_parse.y && mv y.tab.c vc_parse.c && mv y.tab.h vc_parse.h  # libvc 私有前缀
flex -i -o vc_scan.c vc_scan.l                                          # 同上（%option noyywrap，无需 -lfl）
cc -c vc.c vc_parse.c vc_scan.c && ar rcs libvc-prefix/lib/libvc.a *.o # 静态归档
cc -c src/*.c -DHAVE_CONFIG_H=1 -Irolo-cfg -Ilibvc-prefix/include -Iunac-prefix/include   $(ncursesw6-config --cflags)                                          # 9 个源文件，config.h 仅 PACKAGE_* 宏
cc *.o -o src/rolo -Llibvc-prefix/lib -Lunac-prefix/lib   -lvc -lunac -lmenuw $(ncursesw6-config --libs)                        # ROLO 即上游套件默认路径
sh test/run-tests > make_check.log 2>&1; rc=$?; cat make_check.log; exit $rc
# package(): copy src/rolo → bin/rolo，doc/rolo.1 → share/man/man1/（无 make install）
```

- `--build/--host` 显式三元组：config.guess 不识别 HarmonyOS（alpine 先例）。
- `SHELL=` 显式设备 shell：HarmonyOS 拒绝 shebang 直 exec，make 默认 `/bin/sh` 不可靠
 （bashdb 先例用 `SHELL=bash`；此处沿用 rancid 的 `SHELL=<HMBS 注入>` 写法）。
- `os.environ["PWD"]` 预置：HMFS 部分挂载点无 getcwd(3)（rancid/adms 先例）。
- `autoreconf`/`configure` 经 `bash` 显式调用（bashdb 先例）。
- shunit2 调配（`_ensure_shunit2`）：PATH 有则直用；否则取官方
  `https://raw.githubusercontent.com/kward/shunit2/v2.1.8/shunit2`（pin sha256
  `d8f8fb2c…43814c28`，2026-10-13 实测 39506 字节），验哈希后 chmod +x 并前置 PATH
  再跑 configure（此时 `AC_CHECK_PROG(HAS_SHUNIT2)` 方能命中）。哈希失配直接抛错；
  下载网络失败则 WARNING 继续（configure 判 no → 证据记 skipped + 原因，不伪装通过）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libvc 无处可链（configure 必报 `libvc not found`） | 本仓尚无 libvc（vCard 解析库）配方，且单 PR 不允许捎带新配方 | 官方 v013 源码在配方内私有静态 vendoring（`_build_libvc`），configure 经 `CPPFLAGS/LDFLAGS` 命中私有 prefix；绝不跳过 `AC_CHECK_LIB` 检查 |
| 2 | tag 包无 configure | 上游只打源码 tag（39 文件，无生成物） | `autoreconf -fi`，tool_requires automake/1.18 + libtool/2.5.4（bashdb/abiword 先例） |
| 3 | 外树构建必坏上游测试 | run-tests 相对自身找 `../configure.ac`、`contacts.vcf`、`../src/rolo` | in-source 构建（`folders.build = "."`，alpine/rancid 先例） |
| 4 | shunit2 无配方 | 测试框架单 shell 文件，仓内缺失 | 按 pin 哈希现取官方文件；失败则证据记 skipped（宁缺毋假） |
| 5 | 双 marker 计数一致性 | 上游标记与消费者标记须同源、无矛盾 | 上游数只在 build() 解析一次落证 JSON，test.sh 逐字节重发；消费者数由 test.sh 计数器实时产生，conanfile 只做等值门（TOTAL==5、PASS==5、FAIL==0） |
| 6 | 真机 glib 链拖入 CCI libffi/3.4.4 源码构建失败（configure[139] Error 127） | 预检远端顺序 conancenter 在前，裸版本 libffi/3.4.4 命中 CCI 配方；其 configure 经 profile 的 CONFIG_SHELL（/data/service/hnp/bin/bash，本机不可达）重执行 | `requires("libffi/3.5.2", override=True)`（ohpcd 独有版本，CCI config.yml 无此版本；zurl/hyprpicker/kyua 先例）；自有 configure/make 改走 `_good_shell()`（永不信任 CONFIG_SHELL，首选 HMBS 保证的 /bin/sh）+ 行内 CONFIG_SHELL/SHELL 前缀（zurl #31：conanbuild.sh 会重导出毒化值）。**2026-10-14 第五策略周期已撤销该 override（见 #10）：它把 glib 包 ID 推离已发布二进制，强制两次源码构建** |
| 7 | 真机 tool_requires m4/1.4.19 同签名失败（autotools.configure build() line 110，configure[139] Error 127，补丁 1.4.19-0004，包 579a4b17） | 初判 m4 由 flex/2.6.4.2 的裸 `tool_requires("m4/1.4.19")` 拉入（后被下一轮证伪：flex 降级后 m4 仍在，见 #8）；RREV 锁定跨双层 build-of-build 无效（kyua/alberta 教训）；本仓 m4 加固 gated 在 is_ohos，Linux 构建域仍从源码同形死亡 | **减法路线（第二策略周期，不再 pin m4）**：删 m4 RREV pin，不再声明任何 m4 边；`build_requirements()` 改为原生优先探测；`_build_libvc()` 导出绝对 YACC/LEX，自有 configure/make 走 `_good_shell()` + 行内 CONFIG_SHELL 前缀 |
| 8 | flex 降级后同一 m4/1.4.19（包 579a4b17，configure[139] Error 127，补丁 1.4.19-0004）继续构建，证明 m4 与 flex 无关 | 真正的常量引入方是 unac/1.8.0（host requires）：状态 built、无已发布二进制 → 恒从源码构建，激活其 `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`；日志中出现无人声明的 `libtool/2.5.4` 节点（本仓只有 2.5.4.1/2.4.7）即铁证。CCI automake 的 requires + tool_requires 均指向 autoconf（已审计 CCI 配方原文），CCI autoconf 的 requires + tool_requires 均指向 m4（已审计 CCI 配方原文；连本仓 autoconf/2.72 都 tool_requires m4/1.4.19），链条 unac→automake→autoconf→m4 无条件成立，顶层 override/RREV 无法跨双层 build-of-build 统一（kyua/alberta 教训） | **第三策略（本轮）：不再 requires unac，改为配方内私有静态 vendoring（libvc 先例）**：同官方 Debian orig tarball（同 URL/sha256）、复刻 unac 配方的 autoreconf 流程（config.rpath 候选复制、ACLOCAL_PATH、autoreconf+aclocal/autoconf/autoheader --force、umask 077→022、TMPDIR 重定向、srcdir、make -j1、HELP2MAN=/bin/true）+ 本配方加固（显式三元组、SHELL 钉死、PWD 预置、私有 prefix）；其两个 aarch64 int→size_t 补丁改以精确匹配+计数校验实施（无需设备侧 patch 二进制）；rolo 经 `PKG_CONFIG_PATH` 行内前缀命中私有 unac.pc。毒化子树整体离图 |
| 9 | unac 离图后同一 m4（包 579a4b17，configure[139] Error 127）继续构建；且本轮日志证实 libtool 已是 2.5.4.1（我方声明），m4 与 unac/flex 均无关 | 逐一审计 CCI 配方原文：bison/3.8.2 的 `requires("m4/1.4.19")`、flex/2.6.4 的 requires + tool_requires m4；对照双方 config.yml：CCI 有 bison 3.8.2 / flex 2.6.4（故我方声明必命中 CCI），CCI 无 automake 1.18（仅 1.19/1.16.5）、无 libtool 2.5.x（仅 2.4.7），故 automake/libtool 走 ohpcd 安全。flex/2.6.4.2 虽不在 CCI 但其本仓配方自带裸 m4 边——两个 flex 版本都是死路，bison 同理 | **第四策略（本轮）：yacc/lex 改为纯原生，不再声明任何 bison/flex 边**：探测面从 3 个写死目录拓宽为 PATH + 合并 bin + HNP 按包 `*/bin`/`*/*/bin` glob，并记录 `ls` 地形与 8 组工具解析结果进日志，缺失时在 `_build_libvc` fail closed 报出全部搜索位置；libtool 回退改与 bashdb 完全对齐的 2.5.4（已合入先例；CCI 仅有 2.4.7，无遮蔽） |
| 10 | m4 链已消除后新失败：glib/2.84.0.2 在 meson configure 死于 `Unknown compiler [['/data/service/hnp/bin/clang']]`（No such file），HNP 挂载 `ls /data/service/hnp → Permission denied`，构建机仅有 cmake/make/ninja/python3 | 上一周期三轮（flex 降级→unac 整库 vendoring→yacc/lex 纯原生）已把 m4/libtool-2.5.4 节点清出图（本轮日志无 m4、无陌生 libtool 节点即证据），故禁止沿用 m4 根因假设。新根因：我方 `requires("libffi/3.5.2", override=True)` 把 glib 包 ID 推离其规范依赖（libffi/3.4.4，manifest 状态 published、有 ohpcd 二进制）→ libffi/3.5.2（状态 built、无二进制）+ glib 两次源码构建；在 HNP clang 不可达的 runner 上 meson 检编译器即死。另 test_package 沿用硬编码 HNP bash（shebang + CONFIG_SHELL 回退）同样在该 runner 上不可达 | **第五策略（减法+去硬编码，与前三轮不同路线）**：①删 libffi override，不再声明任何 libffi 边，让 glib 走规范 leg 以命中已发布二进制（零/一次源码构建）；②test.sh 改 `#!/bin/sh` + `set -u`（去 pipefail bashism，POSIX clean）；③test_package/conanfile 改经 `SHELL→PATH bash→/bin/sh` 解析执行器，永不硬编码 HNP 路径、不信任毒化 CONFIG_SHELL。**下一轮证伪（libffi/3.4.4 包 e80f2bcb 同样 configure[139] Error 127）：规范 leg 在该 profile 下同样无二进制，减法不够，需消边（见 #11）** |
| 11 | 删 override 后 libffi/3.4.4（包 e80f2bcb）同样从源码构建并死于同一 `configure[139]: /data/service/hnp/bin/bash: inaccessible` Error 127 | 凡在该 runner 上从源码构建的 autotools 节点（m4→libffi→glib 全链）都死于同一毒化 profile CONFIG_SHELL，而所有依赖配方（libffi/3.4.4 等已发布配方）均无 `_good_shell` 式自救，本 PR 又不能改别家配方（单 PR 单库）。published≠该 profile 包 ID 有二进制：canonical leg 在当前 profile 下同样 miss → 构建。审计上游源码：全仓仅 `src/entry.c` 用 glib（`#include <glib.h>` + `set_menu_print_format` 内 3 次 `g_utf8_strlen(fn/gn/em, -1)`，NUL 结尾 UTF-8 字符计数，用于菜单列宽补偿）；其余 12 个源文件零 glib 符号 | **第六策略（依赖消除，与前五轮 pin/降级/vendoring/减边均不同）**：不再 requires 任何 glib，build() 在 `autoreconf` 前原地改写源码（exact-match+计数校验+stamp 幂等，复用 unac 类型修复模式，不走 .patch 文件）：configure.ac 删 GLIB 的 PKG_CHECK_MODULES 块及 `$GLIB_LIBS/$GLIB_CFLAGS` 接线（UNAC 块不动）；entry.c 删 `#include <glib.h>`，增 `rolo_utf8_strlen()`（计非续接字节，与 glib 同语义），3 处调用改名。功能等价（列宽补偿逻辑不变），重依赖只剩零传递依赖的 ncurses/6.6 叶子节点。**首轮预检证伪：调用点改名计得 4 处——系先插入的实现注释自带旧符号名；修复为先改调用点、注释避用旧符号名，计数仍锚定上游 3 处** |
| 12 | yacc/lex 纯原生 fail-closed：真机 `rolo libvc yacc/lex: YACC=MISSING LEX=MISSING`（`_expose_native_lex_yacc` 直接抛错），构建机仅有 cmake/make/ninja/python3，HNP 挂载 `Permission denied` | 上一周期假设“runner 自带 yacc/lex，原生优先即可”被证伪：本 runner 无原生对，且任何 Conan bison/flex 边都必经 CCI m4（已审计：bison/3.8.2 requires m4、flex/2.6.4 requires+tool_requires m4、flex/2.6.4.2 自带裸 m4 边），而 flex/bison 在生成期还要调用 m4——Conan 路线无解。fail-closed 诊断正确但不是修复 | **第七策略（工具链 vendoring，与前六轮 Conan 边/原生优先/依赖消除均不同）**：缺原生时把 GNU m4/1.4.19 + bison/3.8.2 + flex/2.6.4 官方源码（与本仓三配方同 URL/sha256）私有静态编译到 `yl-tools-prefix`（release 包自带 configure，无需 autoreconf，不新增任何 Conan 图节点；复用本配方加固：显式三元组、SHELL 钉死、PWD/TMPDIR/umask、stamp 幂等、`--version` 烟囱验签）。顺序 m4→bison→flex（flex 自举用随包 scan.c 且生成期经 `M4`+PATH 命中私有 m4）；原生双全时仍零成本直用。libvc 随后经绝对 `YACC`/`LEX` 命中该私有前缀 |
| 13 | 私有 m4 configure 死于 `C compiler cannot create executables`（`aarch64-unknown-linux-gnu-gcc = /data/service/hnp/bin/clang`，Error 77），同 runner `ls /data/service/hnp → Permission denied` | profile 把 CC 钉死到 HNP clang，但该 runner 上该路径不可达；vendored 构建经 `conanbuild` 继承毒化 CC（与 mdk/1.3.1 同签名；此前 SHELL 加固只修 shell 未修编译器） | **第八策略（编译器可运行性解析，mdk/1.3.1 经验 adapt）**：generate() 经 `tools.build:compiler_executables` 取配置值并做 `--version` 子进程实测，可运行则复用（健康机零变化），否则回退 PATH 发现的 clang/cc/gcc（含 Harmonybrew 合并 bin）；仅覆盖 CC/CXX 变量，所有 flags 原样保留；另按 mdk 前例预置 SDK llvm/lib 到 LD_LIBRARY_PATH（lld 缺 lib 同样报本错，保留该分支）；m4 configure 失败时落证 config.log 尾部 + CC/LD_LIBRARY_PATH，供下轮直接定位 |
| 14 | 私有 m4 1.4.19 在 `lib/freadahead.c:101` 报 `#error "Please port gnulib freadahead.c ..."`（make Error 1，Error 2 连锁） | m4 1.4.19 自带 gnulib 早于 musl opaque-FILE 支持，HarmonyOS 用 musl（FILE 不透明、无 __freadahead），configure 能过但编译期必死；与已合入 coreutils/9.10 同签名（其 0002 补丁即此文件） | **第八策略之续（gnulib-musl 原地补丁，coreutils 0002 adapt）**：新增 `_patch_vendored_gnulib_for_musl`，在 m4/bison/flex 三个私有源码解包后扫描 `**/freadahead.c`，exact-anchor 插入 `#elif defined __linux__ && !defined __GLIBC__` 分支（`<stdio_ext.h>` + `__fwriting` 判写模式，否则回 0，与 coreutils 0002 同语义），幂等跳过、锚点漂移抛错；不升级 m4 版本、不新增 Conan 边 |
| 15 | 私有 m4 `make install` 死于 `doc/install-info-am` Error 64（`install -c -m 644 ./m4.info ./m4.info-1 ./m4.info-2 .../share/info`）,make 阶段本身已过（freadahead.o 编译通过） | info 文档安装用多源 install 调用，在本 runner 的 HMBS install shim 下报 EX_USAGE(64)；且私有前缀只需 bin/m4，info/man 均为附带物 | **与前轮不同策略（跳过 info 安装，flex SUBDIRS=src 先例）**：m4/bison 的 `make install` 加 `INFO_DEPS= info_TEXINFOS=` 使 install-info-am 空运行，bin/man/data 仍正常安装；不动 make 阶段，不升级版本 |
| 16 | 私有 bison configure 死于 `no acceptable m4 could be found in $PATH`（m4 私有编译已过，bison 首个 C++ 检查后即死） | `_build_vendored_m4` 装到 `yl-tools-prefix/bin/m4`，但 PATH 前置只在 `_ensure_vendored_lex_yacc` 末尾执行；`_build_vendored_bison` 未接收/导出 M4（flex 构建器有，bison 没有），configure 在 PATH 中找不到 gm4/m4 | **补齐 bison 侧 M4/PATH 透出（flex 先例对齐）**：`_build_vendored_bison(tools_prefix, m4_bin)`，构建期间导出 `M4=<私有m4>` 并前置 `bin/` 到 PATH，finally 恢复；调用侧传入刚建好的 m4_bin |
| 17 | 私有 m4 顶层 `make` 死于 `tests/vma-iter.o` 的 `/bin/sh: can't fork - try again`（make[4] Error 1 连锁到顶层 Error 2，-j1） | 顶层 `make all` 递归进自带 gnulib 自测树 `tests/`（数十个 CC 编译），在共享 runner 上 fork/进程资源耗尽；私有前缀下游只需 `bin/m4`（flex/bison 生成期 M4），tests/doc 均为附带物 | **只建所需目录（flex SUBDIRS=src 先例对齐）**：`_build_vendored_m4` 改为 `make -C lib` + `make -C src` + `make -C src install`（仍带 SHELL 钉死/INFO_DEPS 空运行），不再进 `tests/`；非上游套件跳过，rolo 自身 `make check` 仍完整执行 |
| 18 | 真机 compile 阶段报 harmonybrew rm 内存不足（2026-10-14 本轮） | 共享 runner 内存压力下 rm 中转垫片的多余进程开销先失败；另 vendored bison 全树构建是最大内存消费者，profile 默认高优化与调试信息推高编译器峰值 | 直通加缩容（不做重试循环）：私有 rolo-bin 目录符号链接系统 rm 并前置 PATH，全部 make 行内覆盖 RM 变量；bison 改为仅构建安装 lib 加 src 加 data（沿用 m4 分目录与 flex 缩容先例）；五个私有构建的 configure 与 make 行内以 shell 展开追加低优化去调试尾旗，rolo 本体标志不动，测试口径不动 |bison full-tree make is biggest consumer, profile -O2/-g raises cc1 peak | Bypass+shrink (no retry loop): _prefer_system_rm symlink rolo-bin/rm, RM on all make lines; bison lib+src+data only; shell-inline -O1 -g0 on 5 vendored builds; rolo flags untouched |
| 19 | flex libfl.la link Error 127: libtool runs 'libfl.so.2' / 'libmain.o' as commands; make var RM was the literal shell text ${RM:-rm} (single quotes) which make expands to empty and exports empty to libtool | make passed RM thru single quotes so libtool $RM resolved to empty | double-quote the fragment: RM="${RM:-rm}" so /bin/sh expands it to the concrete _prefer_system_rm path before make sees it; same 14 make lines, intent unchanged |
| 21 | 真机 compile 在私有 m4 configure 的编译器探测中掉线：`checking whether clang understands -c and -o together...` 后 `Connection to 47.122.125.180 closed by remote host`（外部 SSH 在共享 runner 内存压力下被断开，非配方断言失败） | 琐碎 conftest 编译即掉线，指向 cc1/进程峰值触发 OOM 连锁，而非配置错误；既有 `-O1 -g0` 行内尾旗只覆盖 $CFLAGS，生成脚本内嵌的 `-O2/-O3/-g/-march=native` 字面仍推高峰值，且无任何瞬时故障重试 | **双层降优+签名重试（sptag/mdk 经验 adapt）**：①新增 `_downgrade_opt_in_tree`，对 m4/byacc/flex/unac/libvc 五个私有源码树做 `-O3/-O2→-O1`、`-g3/-g2→-g0`、`-march/-mcpu=native→generic` 文本改写（仅私有树，rolo 本体与测试口径不动）；②libvc 直接 cc 行补 `-O1 -g0` 尾旗（与其它私有构建对齐）；③新增 `_run_retry`（仅当异常文本命中 out-of-memory/can't fork/try again/Killed/closed by remote host 等签名才重试，最多 3 次、cooldown 8s，非签名失败立即重抛），全部私有 configure/make/install/生成步骤与 rolo 直接编译经其调用，上游套件与 autoreconf 遗留路径保持原样 |
| 22 | m4 configure tail drop: config.status depfiles then SSH closed (checks all passed) | depfiles step is automake fork/file burst under shared-runner pressure; inner retry cannot revive dead outer SSH | dep-tracking off: add --disable-dependency-tracking to 4 vendored configures (m4/byacc/flex/unac); -j1 from-scratch needs no depfiles; code and test scope untouched |
| 25 | 真机 compile 在新增 bison/2.7 边后死于私有 m4 configure[478]：`printf/sed/expr: inaccessible or not found`（Error 1，`_build_vendored_m4:2016` 经 `_run_retry:1737`；同期 `CC=None CXX=None` 系外层 env 取值，conanbuild 内仍由 toolchain 注入，非根因） | 同 runner 指纹下前轮同命令 configure 曾成功（40 文件合并 bin、全原生 MISSING 一致），唯一增量是 tool 边改变 conanbuild 聚合后的 PATH（bison runenv PATH 定义疑似替换语义），裸名 shell 工具全部失联；与 m4 源码语义无关 | **第十一策略（与换 YACC 路线不同的正交加固，bison 边保留）**：新增 `_util_path_prefix/_with_util_path`（外层 `shutil.which` 解析 sh/sed/expr/printf/grep/awk/rm/mkdir 所在目录 + `/bin`、`/usr/bin`、harmonybrew bin、合并 bin，去重拼接为行内 `PATH="<dirs>:$PATH"` 前缀，赋值前缀在 conanbuild.sh source 之后求值故不受聚合替换影响）；`_run_retry` 集中自动前置（覆盖全部私有 configure/make/生成/编译命令），上游套件 `test/run-tests` 的直接 `self.run` 手工前置；`_ensure` 末尾打 `rolo util-path` 证据行；rolo 本体 flags 与测试口径不动 |
| 24 | 真机 compile 死于私有 byacc 生成步骤：`yl-tools-prefix/bin/yacc -d vc_parse.y` 报 `yacc: f - cannot open "action_file"`（Error 2，`_build_libvc:1064` 经 `_run_retry:1700`） | 前轮 m4/autoheader 修复已生效（本轮 m4/byacc/flex 三私有构建全部安装成功），新失败域是 byacc 运行时在其 cwd（`libvc-src/src`）创建固定名临时文件 `action_file` 失败，原因在摘要层不透明；byacc 路线已无低成本探针 | **第十策略（换路线，不重试 byacc）**：YACC 改走仓内 OHOS 已验证的 `tool_requires("bison/2.7")`（ohpcd 独有版本，CCI 无 2.7 故不拖 CCI m4 链；审计其配方零 requires、无 m4 边；manifest 状态 passed、上游 293/293）；`_ensure` 内顺序 Native > Conan bison（含 `BISON_PKGDATADIR` 导出）> 私有 byacc 兜底；LEX 仍私有 vendoring（本轮 flex 安装成功）；rolo 本体与测试口径不动 |
| 23 | 真机 compile 死于私有 m4 `make -C lib` 的 `config.hin` 重制：`build-aux/missing autoheader: inaccessible or not found`（Error 127，`Makefile:2524: config.hin`） | mtime 偏斜触发 maintainer 重制，非缺依赖：`_downgrade` 跳过 `config.h.in` 但 m4 生成文件叫 `config.hin`（无点），既未跳过也未被 `_freeze` 触新；`make -C lib` 只传 `MAKEINFO=true`，未屏蔽 `AUTOHEADER/AUTOCONF/AUTOMAKE/ACLOCAL`，故 `missing` 试图调缺席的 autoheader（runner 原生 autoconf/automake 均 MISSING） | 双保险（rolo 本体与测试口径不动）：① `_downgrade` 跳过名单与 `_freeze` 触新名单均补 `config.hin`（顶层名 + `**/config.hin` glob）；②全部 9 个私有 make 行追加 `AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true`（m4×3/byacc×2/flex×2/unac×2，含 unac 无 MAKEINFO 行），重制即空转不再调 `missing` |
| 20 | 真机 compile 死于 libvc 的 `autoreconf -fi`：`RUN: autoreconf -fi` 后 `/bin/sh: autoreconf: inaccessible or not found`（Error 127），此前 yacc/flex/m4 私有构建全部已过；上一轮“去 bash 前缀”只改调用方式未触及根因 | 重读本仓源码证伪旧假设：ohpcd automake/1.18 的 requirements() 为空（pass），与 CCI automake 不同、从不引入 autoconf；而 autoreconf 归属 autoconf 包（本仓 autoconf/2.72 在 _wrap_perl_tools 中包装 autoreconf，automake 只包装 automake/aclocal），故图中根本无节点提供该二进制。补 autoconf 边会拖回 CCI m4（其 requires+tool_requires m4），私有 vendoring autoconf 需 perl（其全套工具皆 perl 脚本）而合并 bin 33 文件清单证实无 perl——autoreconf 在本 runner 上不可达 | **第九策略（消除而非修复，与前三轮 RM/-C src/去bash 均不同路线）**：零 tool_requires；libvc 直接编译（$YACC -d + flex -i + cc + ar rcs，复刻 AM_YFLAGS/AM_LFLAGS/SOURCES，HAVE_VISIBILITY 未定义即为 0、无需 config.h）；unac 用自带 configure（缺失则 fail-closed，不再调必死的 autoreconf）；rolo 直接编译（全源码 grep 证实仅 main.c 消费 config.h 且仅用 PACKAGE_STRING，手写 rolo-cfg/config.h 复刻 AC_INIT 值，cc 逐文件编译后按 -lvc -lunac -lmenuw + ncursesw6-config --libs 链接到上游套件默认路径 src/rolo，-v 门（精确 rolo 021）前置失败关闭）；上游套件经 sh 直跑进同一 make_check.log，证据链不变 |

| 24 | 真机 compile 死于 unac 私有构建的 fail-closed：`vendored unac tarball ships no configure (sdir holds [...25 项...]) and this runner provides no autoreconf`——Debian orig 包只有 configure.ac/Makefile.am/autogen.sh，无 configure、无 Makefile.in；且 runner 原生 autoconf/automake/libtool 均 MISSING，ohpcd automake/1.18 的 requirements() 为空故无 Conan 边可供应 autoreconf，perl 虽在 harmonybrew 存在但无 autoconf 宏树仍跑不动 autogen.sh | 第九策略“unac 用自带 configure”假设错误：记忆中 6 月 unac 曾跑通 ./configure，但 orig 包本就没有生成物（configure 是 autoreconf 产物、不进包），上一周期从未证实 configure 存在；fail-closed 信息正确但路线已死。按第 7 策略周期要求换路线 | **第十一策略（与第九策略的 libvc/rolo 直接编译同路线，不再假设生成物存在）**：unac 消除 autotools——unac.c 单文件已内嵌约 1.3 万行 Unicode 表（0002 补丁锚在 13875 行附近），仅 unaccent CLI 需 autotools 而 rolo 不消费；config.h 由构建期 mini-configure 按源码实际引用的 HAVE_* 逐项 $CC 探测生成（PACKAGE_* 复刻 AC_INIT 并校验版本为 1.8.0，大小端按真机判定）；rolo 引用的 unac* 符号由 grep 发现并经取地址 TU 做 -lunac 闭包链接门禁（-liconv 仅探测必需时采用并透传给 rolo 链接）；自带 configure 的树仍走遗留 configure 路径（官方 CI 用）。rolo 本体与测试口径不动 |

| 25 | 上一轮直编路由首跑真机：在 audit 通过后死于自设门禁 `AC_INIT package drift (no [unac] match)`；同日志证实审计部分已生效（`unac.c includes ['config.h','errno.h','iconv.h','stdarg.h','stdio.h','stdlib.h','string.h','unac.h']`，getopt 引用为空） | 门禁正则只接受现代 `[bracket]` 形式 `AC_INIT([unac],[ver])`，而该 2002 年代 configure.ac 疑用裸 `AC_INIT(unac, 1.8.0)` 或版本仅在 AM_INIT_AUTOMAKE——路线本身无误，是门禁假设过窄（与 #24 的性质不同：#24 是路线错误，本轮是同路线内的门禁修正） | 门禁改为多模式版本发现：configure.ac 前 1200 字符先记审计日志，再依次试 AC_INIT、AM_INIT_AUTOMAKE（括号可选），候选全部打印；零命中或版本不一致仍 fail-closed，版本仍须精确等于 1.8.0；std 探测头补 `stdarg.h`（unac.c 直接包含）。测试口径不动 |

| 26 | 上一轮门禁放宽后真机：`version candidates [('unac', '$VERSION', '')]` → `version drift '$VERSION'`；多模式匹配本身已生效（终于抓到 AC_INIT），新证据是版本号根本不在 configure.ac 里——`AC_INIT(unac, $VERSION)`，而 sdir 清单早有 `.version` 文件 | 前两轮都是门禁假设过窄，但每次都是不同假设（#24 路线错；#25 括号形式错；本轮变量未解析）。按“同指纹禁用重复修改”要求，本轮不动匹配模式，只加变量解析：$VAR 只认树内来源 | 版本 token 以 `# rolo 021 适配笔记

## 编译环境

- 构建系统: autotools（GitHub v021 tag 只带 `configure.ac` + 各 `Makefile.am`，无生成物，需 `autoreconf -fi`）
- 编译日期: 2026-10-13（首轮工作树，真机预检待跑）
- 编译器: clang/clang++ 15（OHOS aarch64，经 AutotoolsToolchain 注入 CC/CONFIG_SHELL）
- 状态: built（配方完整；真机验证待 HMBS 预检，见「验证结果」）

## 上游信息

- 上游仓库: https://github.com/libvc/rolo（vCard 联系人管理，ncurses 前端）
- 上游版本: v021（tag commit `61587842d051779cd90b76f10f123ce5a6ab583a`）
- 源码包: `https://github.com/libvc/rolo/archive/refs/tags/v021.tar.gz`，38248 字节，
  sha256 `eaf69f0d…77f946`（2026-10-13 下载实测，根目录 `rolo-021`，共 39 个文件）
- 许可证: GPL-2.0-or-later（`src/main.c` 头声明 "either version 2 … or (at your option) any later version"）
- 产物: 单一可执行文件 `bin/rolo`（`src/Makefile.am: bin_PROGRAMS = rolo`）→ `package_type = "application"`

## 上游测试申报表（R51 清点）

**结论：上游有 4 个 shunit2 单元测试，必须接入真机完整执行。**

| # | 测试函数 | 文件 | 行为 |
|---|----------|------|------|
| 1 | test_rolo_version | test/run-tests | 断言 `rolo -v` 输出 == configure.ac 中 AC_INIT 的 `rolo 021` |
| 2 | test_rolo_startup_and_help | test/run-tests | `echo hqq \| TERM=dumb rolo -f contacts.vcf`（无头驱动 curses） |
| 3 | test_rolo_search_and_delete | test/run-tests | mktemp 拷贝 fixture，搜索 `Burger` 后删除，grep 确认消失 |
| 4 | test_rolo_move_and_edit | test/run-tests | `ROLO_EDITOR=cat` 导出 `Alex Winter` 条目，断言 `FN:` 行 |

- 入口: `test/Makefile.am` 的 `check:` 目标（`HAS_SHUNIT2=yes` 时跑 `./run-tests`，否则打印 `Unit tests skipped`）；
  顶层 `SUBDIRS = src doc test`，故顶层 `make check` 递归执行。
- Fixture: `test/contacts.vcf`（真实 vCard，首条 `FN:Mr. John Q. Public, Esq.`）。
- 口径: `upstream_test_total = 4`，`upstream_test_count_method = auto`（单一 shunit2 框架：
  测试函数数 == shunit2 `Ran N tests.` 汇总行）；`upstream_test_in_build: true`。
- 证据链: build() 把 `make check` 输出重定向到 `make_check.log` 后回放，
  仅解析该文件的 shunit2 汇总行（`Ran N tests.` + `OK`/`FAILED`），落证到
  `share/doc/rolo/upstream-check.json`（单行 JSON），test_package 原样重发为
  `HMBS_UPSTREAM_TEST_RESULT`。无任何算术修补：无汇总行即报 error，绝不猜数。

## W0 — 依赖发布检查（适配前第一件事）

| 依赖 | 上游 configure 要求 | 本仓状态 | 结论 |
|------|--------------------|----------|------|
| libvc | `AC_CHECK_LIB(vc, vc_new)` 致命 | **无配方**（仅有无关的 libvcflib） | 配方内 vendoring：官方 v013 tag（sha256 `a43bf49f…821c2`）私有 prefix 静态编译（缺原生 yacc/lex 时先私有编译 m4/1.4.19+bison/3.8.2+flex/2.6.4 工具链，见问题表 #12），不发布 |
| ncursesw + menuw | `AC_CHECK_LIB` 致命 | ncurses/6.6（`--enable-widec`，含 menuw） | requires 已声明，待真机核验 |
| glib-2.0 | `PKG_CHECK_MODULES` 致命 | 仓内各 glib 版本在当前 profile 下均无二进制，任何 requires 都强制 meson+libffi 源码构建链 | 不再 requires：build() 原地改写 configure.ac+entry.c 消除 glib 边（等价本地实现，见问题表 #11） |
| libffi（原 glib 传递） | 曾 override 3.5.2，后回退规范 3.4.4，两者在当前 profile 下均无二进制可用 | 不再经 glib 引入：glib 边整体消除（见问题表 #11），图中已无 libffi 节点 |
| unac | `PKG_CHECK_MODULES` 致命 | unac/1.8.0（配方存在但 manifest 状态仅 built、无已发布二进制；且其 `tool_requires("libtool/2.5.4")` 所指版本本仓根本不存在） | 配方内 vendoring：Debian 官方 orig tarball（与 unac 配方同 URL/sha256）私有 prefix 静态编译，不再 requires（见问题表 #8） |
| shunit2 | 仅测试门（缺时 WARNING+跳过） | 无配方 | 配方在无系统副本时从官方源按 pin 哈希现取（见下），缺网则如实报 skipped |
| automake/aclocal/libtoolize | `autoreconf -fi` 所需 | automake/1.18、libtool/2.5.4（多已合入配方在用） | tool_requires 已声明 |

libvc 无仓内配方，`conan create` 若声明 `requires("libvc/013")` 会在依赖解析直接失败（本轮真机证据）。改法：不在 conan requires 声明，改为配方内用官方源码（https://github.com/libvc/libvc，v013，LGPL-2.1，sha256 `a43bf49ff2b9e17cf7e332f3aa9f218c46782400aa848e6af4589e6b244821c2`）在 `build()` 先静态编译到私有 `libvc-prefix`（R49），再以 `CPPFLAGS/LDFLAGS` 指给 rolo 的 configure/make；产物不进包、不导出。

## 编译步骤

```bash
# in-source（test/run-tests 用 $0 相对路径找 ../configure.ac、contacts.vcf、../src/rolo）
# 全程无 autoreconf/configure/make（第九策略，见问题表 #20）：
byacc -d vc_parse.y && mv y.tab.c vc_parse.c && mv y.tab.h vc_parse.h  # libvc 私有前缀
flex -i -o vc_scan.c vc_scan.l                                          # 同上（%option noyywrap，无需 -lfl）
cc -c vc.c vc_parse.c vc_scan.c && ar rcs libvc-prefix/lib/libvc.a *.o # 静态归档
cc -c src/*.c -DHAVE_CONFIG_H=1 -Irolo-cfg -Ilibvc-prefix/include -Iunac-prefix/include   $(ncursesw6-config --cflags)                                          # 9 个源文件，config.h 仅 PACKAGE_* 宏
cc *.o -o src/rolo -Llibvc-prefix/lib -Lunac-prefix/lib   -lvc -lunac -lmenuw $(ncursesw6-config --libs)                        # ROLO 即上游套件默认路径
sh test/run-tests > make_check.log 2>&1; rc=$?; cat make_check.log; exit $rc
# package(): copy src/rolo → bin/rolo，doc/rolo.1 → share/man/man1/（无 make install）
```

- `--build/--host` 显式三元组：config.guess 不识别 HarmonyOS（alpine 先例）。
- `SHELL=` 显式设备 shell：HarmonyOS 拒绝 shebang 直 exec，make 默认 `/bin/sh` 不可靠
 （bashdb 先例用 `SHELL=bash`；此处沿用 rancid 的 `SHELL=<HMBS 注入>` 写法）。
- `os.environ["PWD"]` 预置：HMFS 部分挂载点无 getcwd(3)（rancid/adms 先例）。
- `autoreconf`/`configure` 经 `bash` 显式调用（bashdb 先例）。
- shunit2 调配（`_ensure_shunit2`）：PATH 有则直用；否则取官方
  `https://raw.githubusercontent.com/kward/shunit2/v2.1.8/shunit2`（pin sha256
  `d8f8fb2c…43814c28`，2026-10-13 实测 39506 字节），验哈希后 chmod +x 并前置 PATH
  再跑 configure（此时 `AC_CHECK_PROG(HAS_SHUNIT2)` 方能命中）。哈希失配直接抛错；
  下载网络失败则 WARNING 继续（configure 判 no → 证据记 skipped + 原因，不伪装通过）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libvc 无处可链（configure 必报 `libvc not found`） | 本仓尚无 libvc（vCard 解析库）配方，且单 PR 不允许捎带新配方 | 官方 v013 源码在配方内私有静态 vendoring（`_build_libvc`），configure 经 `CPPFLAGS/LDFLAGS` 命中私有 prefix；绝不跳过 `AC_CHECK_LIB` 检查 |
| 2 | tag 包无 configure | 上游只打源码 tag（39 文件，无生成物） | `autoreconf -fi`，tool_requires automake/1.18 + libtool/2.5.4（bashdb/abiword 先例） |
| 3 | 外树构建必坏上游测试 | run-tests 相对自身找 `../configure.ac`、`contacts.vcf`、`../src/rolo` | in-source 构建（`folders.build = "."`，alpine/rancid 先例） |
| 4 | shunit2 无配方 | 测试框架单 shell 文件，仓内缺失 | 按 pin 哈希现取官方文件；失败则证据记 skipped（宁缺毋假） |
| 5 | 双 marker 计数一致性 | 上游标记与消费者标记须同源、无矛盾 | 上游数只在 build() 解析一次落证 JSON，test.sh 逐字节重发；消费者数由 test.sh 计数器实时产生，conanfile 只做等值门（TOTAL==5、PASS==5、FAIL==0） |
| 6 | 真机 glib 链拖入 CCI libffi/3.4.4 源码构建失败（configure[139] Error 127） | 预检远端顺序 conancenter 在前，裸版本 libffi/3.4.4 命中 CCI 配方；其 configure 经 profile 的 CONFIG_SHELL（/data/service/hnp/bin/bash，本机不可达）重执行 | `requires("libffi/3.5.2", override=True)`（ohpcd 独有版本，CCI config.yml 无此版本；zurl/hyprpicker/kyua 先例）；自有 configure/make 改走 `_good_shell()`（永不信任 CONFIG_SHELL，首选 HMBS 保证的 /bin/sh）+ 行内 CONFIG_SHELL/SHELL 前缀（zurl #31：conanbuild.sh 会重导出毒化值）。**2026-10-14 第五策略周期已撤销该 override（见 #10）：它把 glib 包 ID 推离已发布二进制，强制两次源码构建** |
| 7 | 真机 tool_requires m4/1.4.19 同签名失败（autotools.configure build() line 110，configure[139] Error 127，补丁 1.4.19-0004，包 579a4b17） | 初判 m4 由 flex/2.6.4.2 的裸 `tool_requires("m4/1.4.19")` 拉入（后被下一轮证伪：flex 降级后 m4 仍在，见 #8）；RREV 锁定跨双层 build-of-build 无效（kyua/alberta 教训）；本仓 m4 加固 gated 在 is_ohos，Linux 构建域仍从源码同形死亡 | **减法路线（第二策略周期，不再 pin m4）**：删 m4 RREV pin，不再声明任何 m4 边；`build_requirements()` 改为原生优先探测；`_build_libvc()` 导出绝对 YACC/LEX，自有 configure/make 走 `_good_shell()` + 行内 CONFIG_SHELL 前缀 |
| 8 | flex 降级后同一 m4/1.4.19（包 579a4b17，configure[139] Error 127，补丁 1.4.19-0004）继续构建，证明 m4 与 flex 无关 | 真正的常量引入方是 unac/1.8.0（host requires）：状态 built、无已发布二进制 → 恒从源码构建，激活其 `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`；日志中出现无人声明的 `libtool/2.5.4` 节点（本仓只有 2.5.4.1/2.4.7）即铁证。CCI automake 的 requires + tool_requires 均指向 autoconf（已审计 CCI 配方原文），CCI autoconf 的 requires + tool_requires 均指向 m4（已审计 CCI 配方原文；连本仓 autoconf/2.72 都 tool_requires m4/1.4.19），链条 unac→automake→autoconf→m4 无条件成立，顶层 override/RREV 无法跨双层 build-of-build 统一（kyua/alberta 教训） | **第三策略（本轮）：不再 requires unac，改为配方内私有静态 vendoring（libvc 先例）**：同官方 Debian orig tarball（同 URL/sha256）、复刻 unac 配方的 autoreconf 流程（config.rpath 候选复制、ACLOCAL_PATH、autoreconf+aclocal/autoconf/autoheader --force、umask 077→022、TMPDIR 重定向、srcdir、make -j1、HELP2MAN=/bin/true）+ 本配方加固（显式三元组、SHELL 钉死、PWD 预置、私有 prefix）；其两个 aarch64 int→size_t 补丁改以精确匹配+计数校验实施（无需设备侧 patch 二进制）；rolo 经 `PKG_CONFIG_PATH` 行内前缀命中私有 unac.pc。毒化子树整体离图 |
| 9 | unac 离图后同一 m4（包 579a4b17，configure[139] Error 127）继续构建；且本轮日志证实 libtool 已是 2.5.4.1（我方声明），m4 与 unac/flex 均无关 | 逐一审计 CCI 配方原文：bison/3.8.2 的 `requires("m4/1.4.19")`、flex/2.6.4 的 requires + tool_requires m4；对照双方 config.yml：CCI 有 bison 3.8.2 / flex 2.6.4（故我方声明必命中 CCI），CCI 无 automake 1.18（仅 1.19/1.16.5）、无 libtool 2.5.x（仅 2.4.7），故 automake/libtool 走 ohpcd 安全。flex/2.6.4.2 虽不在 CCI 但其本仓配方自带裸 m4 边——两个 flex 版本都是死路，bison 同理 | **第四策略（本轮）：yacc/lex 改为纯原生，不再声明任何 bison/flex 边**：探测面从 3 个写死目录拓宽为 PATH + 合并 bin + HNP 按包 `*/bin`/`*/*/bin` glob，并记录 `ls` 地形与 8 组工具解析结果进日志，缺失时在 `_build_libvc` fail closed 报出全部搜索位置；libtool 回退改与 bashdb 完全对齐的 2.5.4（已合入先例；CCI 仅有 2.4.7，无遮蔽） |
| 10 | m4 链已消除后新失败：glib/2.84.0.2 在 meson configure 死于 `Unknown compiler [['/data/service/hnp/bin/clang']]`（No such file），HNP 挂载 `ls /data/service/hnp → Permission denied`，构建机仅有 cmake/make/ninja/python3 | 上一周期三轮（flex 降级→unac 整库 vendoring→yacc/lex 纯原生）已把 m4/libtool-2.5.4 节点清出图（本轮日志无 m4、无陌生 libtool 节点即证据），故禁止沿用 m4 根因假设。新根因：我方 `requires("libffi/3.5.2", override=True)` 把 glib 包 ID 推离其规范依赖（libffi/3.4.4，manifest 状态 published、有 ohpcd 二进制）→ libffi/3.5.2（状态 built、无二进制）+ glib 两次源码构建；在 HNP clang 不可达的 runner 上 meson 检编译器即死。另 test_package 沿用硬编码 HNP bash（shebang + CONFIG_SHELL 回退）同样在该 runner 上不可达 | **第五策略（减法+去硬编码，与前三轮不同路线）**：①删 libffi override，不再声明任何 libffi 边，让 glib 走规范 leg 以命中已发布二进制（零/一次源码构建）；②test.sh 改 `#!/bin/sh` + `set -u`（去 pipefail bashism，POSIX clean）；③test_package/conanfile 改经 `SHELL→PATH bash→/bin/sh` 解析执行器，永不硬编码 HNP 路径、不信任毒化 CONFIG_SHELL。**下一轮证伪（libffi/3.4.4 包 e80f2bcb 同样 configure[139] Error 127）：规范 leg 在该 profile 下同样无二进制，减法不够，需消边（见 #11）** |
| 11 | 删 override 后 libffi/3.4.4（包 e80f2bcb）同样从源码构建并死于同一 `configure[139]: /data/service/hnp/bin/bash: inaccessible` Error 127 | 凡在该 runner 上从源码构建的 autotools 节点（m4→libffi→glib 全链）都死于同一毒化 profile CONFIG_SHELL，而所有依赖配方（libffi/3.4.4 等已发布配方）均无 `_good_shell` 式自救，本 PR 又不能改别家配方（单 PR 单库）。published≠该 profile 包 ID 有二进制：canonical leg 在当前 profile 下同样 miss → 构建。审计上游源码：全仓仅 `src/entry.c` 用 glib（`#include <glib.h>` + `set_menu_print_format` 内 3 次 `g_utf8_strlen(fn/gn/em, -1)`，NUL 结尾 UTF-8 字符计数，用于菜单列宽补偿）；其余 12 个源文件零 glib 符号 | **第六策略（依赖消除，与前五轮 pin/降级/vendoring/减边均不同）**：不再 requires 任何 glib，build() 在 `autoreconf` 前原地改写源码（exact-match+计数校验+stamp 幂等，复用 unac 类型修复模式，不走 .patch 文件）：configure.ac 删 GLIB 的 PKG_CHECK_MODULES 块及 `$GLIB_LIBS/$GLIB_CFLAGS` 接线（UNAC 块不动）；entry.c 删 `#include <glib.h>`，增 `rolo_utf8_strlen()`（计非续接字节，与 glib 同语义），3 处调用改名。功能等价（列宽补偿逻辑不变），重依赖只剩零传递依赖的 ncurses/6.6 叶子节点。**首轮预检证伪：调用点改名计得 4 处——系先插入的实现注释自带旧符号名；修复为先改调用点、注释避用旧符号名，计数仍锚定上游 3 处** |
| 12 | yacc/lex 纯原生 fail-closed：真机 `rolo libvc yacc/lex: YACC=MISSING LEX=MISSING`（`_expose_native_lex_yacc` 直接抛错），构建机仅有 cmake/make/ninja/python3，HNP 挂载 `Permission denied` | 上一周期假设“runner 自带 yacc/lex，原生优先即可”被证伪：本 runner 无原生对，且任何 Conan bison/flex 边都必经 CCI m4（已审计：bison/3.8.2 requires m4、flex/2.6.4 requires+tool_requires m4、flex/2.6.4.2 自带裸 m4 边），而 flex/bison 在生成期还要调用 m4——Conan 路线无解。fail-closed 诊断正确但不是修复 | **第七策略（工具链 vendoring，与前六轮 Conan 边/原生优先/依赖消除均不同）**：缺原生时把 GNU m4/1.4.19 + bison/3.8.2 + flex/2.6.4 官方源码（与本仓三配方同 URL/sha256）私有静态编译到 `yl-tools-prefix`（release 包自带 configure，无需 autoreconf，不新增任何 Conan 图节点；复用本配方加固：显式三元组、SHELL 钉死、PWD/TMPDIR/umask、stamp 幂等、`--version` 烟囱验签）。顺序 m4→bison→flex（flex 自举用随包 scan.c 且生成期经 `M4`+PATH 命中私有 m4）；原生双全时仍零成本直用。libvc 随后经绝对 `YACC`/`LEX` 命中该私有前缀 |
| 13 | 私有 m4 configure 死于 `C compiler cannot create executables`（`aarch64-unknown-linux-gnu-gcc = /data/service/hnp/bin/clang`，Error 77），同 runner `ls /data/service/hnp → Permission denied` | profile 把 CC 钉死到 HNP clang，但该 runner 上该路径不可达；vendored 构建经 `conanbuild` 继承毒化 CC（与 mdk/1.3.1 同签名；此前 SHELL 加固只修 shell 未修编译器） | **第八策略（编译器可运行性解析，mdk/1.3.1 经验 adapt）**：generate() 经 `tools.build:compiler_executables` 取配置值并做 `--version` 子进程实测，可运行则复用（健康机零变化），否则回退 PATH 发现的 clang/cc/gcc（含 Harmonybrew 合并 bin）；仅覆盖 CC/CXX 变量，所有 flags 原样保留；另按 mdk 前例预置 SDK llvm/lib 到 LD_LIBRARY_PATH（lld 缺 lib 同样报本错，保留该分支）；m4 configure 失败时落证 config.log 尾部 + CC/LD_LIBRARY_PATH，供下轮直接定位 |
| 14 | 私有 m4 1.4.19 在 `lib/freadahead.c:101` 报 `#error "Please port gnulib freadahead.c ..."`（make Error 1，Error 2 连锁） | m4 1.4.19 自带 gnulib 早于 musl opaque-FILE 支持，HarmonyOS 用 musl（FILE 不透明、无 __freadahead），configure 能过但编译期必死；与已合入 coreutils/9.10 同签名（其 0002 补丁即此文件） | **第八策略之续（gnulib-musl 原地补丁，coreutils 0002 adapt）**：新增 `_patch_vendored_gnulib_for_musl`，在 m4/bison/flex 三个私有源码解包后扫描 `**/freadahead.c`，exact-anchor 插入 `#elif defined __linux__ && !defined __GLIBC__` 分支（`<stdio_ext.h>` + `__fwriting` 判写模式，否则回 0，与 coreutils 0002 同语义），幂等跳过、锚点漂移抛错；不升级 m4 版本、不新增 Conan 边 |
| 15 | 私有 m4 `make install` 死于 `doc/install-info-am` Error 64（`install -c -m 644 ./m4.info ./m4.info-1 ./m4.info-2 .../share/info`）,make 阶段本身已过（freadahead.o 编译通过） | info 文档安装用多源 install 调用，在本 runner 的 HMBS install shim 下报 EX_USAGE(64)；且私有前缀只需 bin/m4，info/man 均为附带物 | **与前轮不同策略（跳过 info 安装，flex SUBDIRS=src 先例）**：m4/bison 的 `make install` 加 `INFO_DEPS= info_TEXINFOS=` 使 install-info-am 空运行，bin/man/data 仍正常安装；不动 make 阶段，不升级版本 |
| 16 | 私有 bison configure 死于 `no acceptable m4 could be found in $PATH`（m4 私有编译已过，bison 首个 C++ 检查后即死） | `_build_vendored_m4` 装到 `yl-tools-prefix/bin/m4`，但 PATH 前置只在 `_ensure_vendored_lex_yacc` 末尾执行；`_build_vendored_bison` 未接收/导出 M4（flex 构建器有，bison 没有），configure 在 PATH 中找不到 gm4/m4 | **补齐 bison 侧 M4/PATH 透出（flex 先例对齐）**：`_build_vendored_bison(tools_prefix, m4_bin)`，构建期间导出 `M4=<私有m4>` 并前置 `bin/` 到 PATH，finally 恢复；调用侧传入刚建好的 m4_bin |
| 17 | 私有 m4 顶层 `make` 死于 `tests/vma-iter.o` 的 `/bin/sh: can't fork - try again`（make[4] Error 1 连锁到顶层 Error 2，-j1） | 顶层 `make all` 递归进自带 gnulib 自测树 `tests/`（数十个 CC 编译），在共享 runner 上 fork/进程资源耗尽；私有前缀下游只需 `bin/m4`（flex/bison 生成期 M4），tests/doc 均为附带物 | **只建所需目录（flex SUBDIRS=src 先例对齐）**：`_build_vendored_m4` 改为 `make -C lib` + `make -C src` + `make -C src install`（仍带 SHELL 钉死/INFO_DEPS 空运行），不再进 `tests/`；非上游套件跳过，rolo 自身 `make check` 仍完整执行 |
| 18 | 真机 compile 阶段报 harmonybrew rm 内存不足（2026-10-14 本轮） | 共享 runner 内存压力下 rm 中转垫片的多余进程开销先失败；另 vendored bison 全树构建是最大内存消费者，profile 默认高优化与调试信息推高编译器峰值 | 直通加缩容（不做重试循环）：私有 rolo-bin 目录符号链接系统 rm 并前置 PATH，全部 make 行内覆盖 RM 变量；bison 改为仅构建安装 lib 加 src 加 data（沿用 m4 分目录与 flex 缩容先例）；五个私有构建的 configure 与 make 行内以 shell 展开追加低优化去调试尾旗，rolo 本体标志不动，测试口径不动 |bison full-tree make is biggest consumer, profile -O2/-g raises cc1 peak | Bypass+shrink (no retry loop): _prefer_system_rm symlink rolo-bin/rm, RM on all make lines; bison lib+src+data only; shell-inline -O1 -g0 on 5 vendored builds; rolo flags untouched |
| 19 | flex libfl.la link Error 127: libtool runs 'libfl.so.2' / 'libmain.o' as commands; make var RM was the literal shell text ${RM:-rm} (single quotes) which make expands to empty and exports empty to libtool | make passed RM thru single quotes so libtool $RM resolved to empty | double-quote the fragment: RM="${RM:-rm}" so /bin/sh expands it to the concrete _prefer_system_rm path before make sees it; same 14 make lines, intent unchanged |
| 21 | 真机 compile 在私有 m4 configure 的编译器探测中掉线：`checking whether clang understands -c and -o together...` 后 `Connection to 47.122.125.180 closed by remote host`（外部 SSH 在共享 runner 内存压力下被断开，非配方断言失败） | 琐碎 conftest 编译即掉线，指向 cc1/进程峰值触发 OOM 连锁，而非配置错误；既有 `-O1 -g0` 行内尾旗只覆盖 $CFLAGS，生成脚本内嵌的 `-O2/-O3/-g/-march=native` 字面仍推高峰值，且无任何瞬时故障重试 | **双层降优+签名重试（sptag/mdk 经验 adapt）**：①新增 `_downgrade_opt_in_tree`，对 m4/byacc/flex/unac/libvc 五个私有源码树做 `-O3/-O2→-O1`、`-g3/-g2→-g0`、`-march/-mcpu=native→generic` 文本改写（仅私有树，rolo 本体与测试口径不动）；②libvc 直接 cc 行补 `-O1 -g0` 尾旗（与其它私有构建对齐）；③新增 `_run_retry`（仅当异常文本命中 out-of-memory/can't fork/try again/Killed/closed by remote host 等签名才重试，最多 3 次、cooldown 8s，非签名失败立即重抛），全部私有 configure/make/install/生成步骤与 rolo 直接编译经其调用，上游套件与 autoreconf 遗留路径保持原样 |
| 22 | m4 configure tail drop: config.status depfiles then SSH closed (checks all passed) | depfiles step is automake fork/file burst under shared-runner pressure; inner retry cannot revive dead outer SSH | dep-tracking off: add --disable-dependency-tracking to 4 vendored configures (m4/byacc/flex/unac); -j1 from-scratch needs no depfiles; code and test scope untouched |
| 25 | 真机 compile 在新增 bison/2.7 边后死于私有 m4 configure[478]：`printf/sed/expr: inaccessible or not found`（Error 1，`_build_vendored_m4:2016` 经 `_run_retry:1737`；同期 `CC=None CXX=None` 系外层 env 取值，conanbuild 内仍由 toolchain 注入，非根因） | 同 runner 指纹下前轮同命令 configure 曾成功（40 文件合并 bin、全原生 MISSING 一致），唯一增量是 tool 边改变 conanbuild 聚合后的 PATH（bison runenv PATH 定义疑似替换语义），裸名 shell 工具全部失联；与 m4 源码语义无关 | **第十一策略（与换 YACC 路线不同的正交加固，bison 边保留）**：新增 `_util_path_prefix/_with_util_path`（外层 `shutil.which` 解析 sh/sed/expr/printf/grep/awk/rm/mkdir 所在目录 + `/bin`、`/usr/bin`、harmonybrew bin、合并 bin，去重拼接为行内 `PATH="<dirs>:$PATH"` 前缀，赋值前缀在 conanbuild.sh source 之后求值故不受聚合替换影响）；`_run_retry` 集中自动前置（覆盖全部私有 configure/make/生成/编译命令），上游套件 `test/run-tests` 的直接 `self.run` 手工前置；`_ensure` 末尾打 `rolo util-path` 证据行；rolo 本体 flags 与测试口径不动 |
| 24 | 真机 compile 死于私有 byacc 生成步骤：`yl-tools-prefix/bin/yacc -d vc_parse.y` 报 `yacc: f - cannot open "action_file"`（Error 2，`_build_libvc:1064` 经 `_run_retry:1700`） | 前轮 m4/autoheader 修复已生效（本轮 m4/byacc/flex 三私有构建全部安装成功），新失败域是 byacc 运行时在其 cwd（`libvc-src/src`）创建固定名临时文件 `action_file` 失败，原因在摘要层不透明；byacc 路线已无低成本探针 | **第十策略（换路线，不重试 byacc）**：YACC 改走仓内 OHOS 已验证的 `tool_requires("bison/2.7")`（ohpcd 独有版本，CCI 无 2.7 故不拖 CCI m4 链；审计其配方零 requires、无 m4 边；manifest 状态 passed、上游 293/293）；`_ensure` 内顺序 Native > Conan bison（含 `BISON_PKGDATADIR` 导出）> 私有 byacc 兜底；LEX 仍私有 vendoring（本轮 flex 安装成功）；rolo 本体与测试口径不动 |
| 23 | 真机 compile 死于私有 m4 `make -C lib` 的 `config.hin` 重制：`build-aux/missing autoheader: inaccessible or not found`（Error 127，`Makefile:2524: config.hin`） | mtime 偏斜触发 maintainer 重制，非缺依赖：`_downgrade` 跳过 `config.h.in` 但 m4 生成文件叫 `config.hin`（无点），既未跳过也未被 `_freeze` 触新；`make -C lib` 只传 `MAKEINFO=true`，未屏蔽 `AUTOHEADER/AUTOCONF/AUTOMAKE/ACLOCAL`，故 `missing` 试图调缺席的 autoheader（runner 原生 autoconf/automake 均 MISSING） | 双保险（rolo 本体与测试口径不动）：① `_downgrade` 跳过名单与 `_freeze` 触新名单均补 `config.hin`（顶层名 + `**/config.hin` glob）；②全部 9 个私有 make 行追加 `AUTOHEADER=true AUTOCONF=true AUTOMAKE=true ACLOCAL=true`（m4×3/byacc×2/flex×2/unac×2，含 unac 无 MAKEINFO 行），重制即空转不再调 `missing` |
| 20 | 真机 compile 死于 libvc 的 `autoreconf -fi`：`RUN: autoreconf -fi` 后 `/bin/sh: autoreconf: inaccessible or not found`（Error 127），此前 yacc/flex/m4 私有构建全部已过；上一轮“去 bash 前缀”只改调用方式未触及根因 | 重读本仓源码证伪旧假设：ohpcd automake/1.18 的 requirements() 为空（pass），与 CCI automake 不同、从不引入 autoconf；而 autoreconf 归属 autoconf 包（本仓 autoconf/2.72 在 _wrap_perl_tools 中包装 autoreconf，automake 只包装 automake/aclocal），故图中根本无节点提供该二进制。补 autoconf 边会拖回 CCI m4（其 requires+tool_requires m4），私有 vendoring autoconf 需 perl（其全套工具皆 perl 脚本）而合并 bin 33 文件清单证实无 perl——autoreconf 在本 runner 上不可达 | **第九策略（消除而非修复，与前三轮 RM/-C src/去bash 均不同路线）**：零 tool_requires；libvc 直接编译（$YACC -d + flex -i + cc + ar rcs，复刻 AM_YFLAGS/AM_LFLAGS/SOURCES，HAVE_VISIBILITY 未定义即为 0、无需 config.h）；unac 用自带 configure（缺失则 fail-closed，不再调必死的 autoreconf）；rolo 直接编译（全源码 grep 证实仅 main.c 消费 config.h 且仅用 PACKAGE_STRING，手写 rolo-cfg/config.h 复刻 AC_INIT 值，cc 逐文件编译后按 -lvc -lunac -lmenuw + ncursesw6-config --libs 链接到上游套件默认路径 src/rolo，-v 门（精确 rolo 021）前置失败关闭）；上游套件经 sh 直跑进同一 make_check.log，证据链不变 |

| 24 | 真机 compile 死于 unac 私有构建的 fail-closed：`vendored unac tarball ships no configure (sdir holds [...25 项...]) and this runner provides no autoreconf`——Debian orig 包只有 configure.ac/Makefile.am/autogen.sh，无 configure、无 Makefile.in；且 runner 原生 autoconf/automake/libtool 均 MISSING，ohpcd automake/1.18 的 requirements() 为空故无 Conan 边可供应 autoreconf，perl 虽在 harmonybrew 存在但无 autoconf 宏树仍跑不动 autogen.sh | 第九策略“unac 用自带 configure”假设错误：记忆中 6 月 unac 曾跑通 ./configure，但 orig 包本就没有生成物（configure 是 autoreconf 产物、不进包），上一周期从未证实 configure 存在；fail-closed 信息正确但路线已死。按第 7 策略周期要求换路线 | **第十一策略（与第九策略的 libvc/rolo 直接编译同路线，不再假设生成物存在）**：unac 消除 autotools——unac.c 单文件已内嵌约 1.3 万行 Unicode 表（0002 补丁锚在 13875 行附近），仅 unaccent CLI 需 autotools 而 rolo 不消费；config.h 由构建期 mini-configure 按源码实际引用的 HAVE_* 逐项 $CC 探测生成（PACKAGE_* 复刻 AC_INIT 并校验版本为 1.8.0，大小端按真机判定）；rolo 引用的 unac* 符号由 grep 发现并经取地址 TU 做 -lunac 闭包链接门禁（-liconv 仅探测必需时采用并透传给 rolo 链接）；自带 configure 的树仍走遗留 configure 路径（官方 CI 用）。rolo 本体与测试口径不动 |

| 25 | 上一轮直编路由首跑真机：在 audit 通过后死于自设门禁 `AC_INIT package drift (no [unac] match)`；同日志证实审计部分已生效（`unac.c includes ['config.h','errno.h','iconv.h','stdarg.h','stdio.h','stdlib.h','string.h','unac.h']`，getopt 引用为空） | 门禁正则只接受现代 `[bracket]` 形式 `AC_INIT([unac],[ver])`，而该 2002 年代 configure.ac 疑用裸 `AC_INIT(unac, 1.8.0)` 或版本仅在 AM_INIT_AUTOMAKE——路线本身无误，是门禁假设过窄（与 #24 的性质不同：#24 是路线错误，本轮是同路线内的门禁修正） | 门禁改为多模式版本发现：configure.ac 前 1200 字符先记审计日志，再依次试 AC_INIT、AM_INIT_AUTOMAKE（括号可选），候选全部打印；零命中或版本不一致仍 fail-closed，版本仍须精确等于 1.8.0；std 探测头补 `stdarg.h`（unac.c 直接包含）。测试口径不动 |

 开头时按名解析：先读树内 `.version` 文件首词，再试 configure.ac 的 `VERSION=` 赋值，两者来源与取值全部记日志；非 VERSION 变量名或两源皆无仍 fail-closed；解析值仍须精确等于 1.8.0（否则仍报 drift）。测试口径不动 |
| 27 | 直编路由真机 compile：`unac.c:13792/13817: error: expected ')'`（`(ICONV_CONST char **)` 处）+ `unac.c:13899: use of undeclared identifier 'UNAC_VERSION'`；同日志 `unac probe f_iconv_const -> OK` 与 `config.h (21 defined, 21 total)` | 通用 `extern int <suffix>()` 取地址探测把非特性宏当函数探：`ICONV_CONST` 被误判为存在→误发 `#define ICONV_CONST 1`（`(1 char **)` 非法），`UNAC_VERSION` 探测失败→留 `/* #undef */`（`return UNAC_VERSION` 无定义）。而上游语义是 gettext iconv.m4 的 `AC_DEFINE_UNQUOTED([ICONV_CONST])`（值只能是空或 `const`）与 `return UNAC_VERSION` 字符串字面 | 与前三轮门禁修正不同路线（改发射语义而非匹配模式）：① `ICONV_CONST` 走 iconv.m4 同款 POSIX 签名编译探测（`char **` 声明能编则空，否则 `const`），发射 `#define ICONV_CONST const` 或 `#define ICONV_CONST /**/`，永不发 `1`/留空；② `UNAC_VERSION` 发射 AC_INIT 已校验版本的引号字符串；③通用函数探测仅限 `HAVE_` 前缀，非特性宏未知项记日志留 undef（不再做 `extern int` 猜测）。rolo 本体与测试口径不动 |
| 28 | 上一轮之后真机复跑：`ICONV_CONST` 错误消失（新日志 `unac probe ICONV_CONST -> '' (no iconv.h, POSIX default)`，13792/13817 通过），但 `unac.c:13899: use of undeclared identifier 'UNAC_VERSION'` 仍在；且新日志全程无 `unac probe UNAC_VERSION` 行 | 上一轮假设“`UNAC_VERSION` 在 config.h.in 的 `#undef` 清单里、只是探测失败”被新日志证伪：`if "UNAC_VERSION" in set(undefs)` 从未命中，说明随包的 config.h.in 早于 configure.ac 的 `AC_DEFINE`（stale 生成文件），按清单发射永远覆盖不到它。路线（专用发射分支）无误，覆盖面假设过窄 | 与上一轮不同策略（补覆盖面而非改探测）：`_write_unac_config_h` 在逐项发射后加带 `#ifndef` 守卫的无条件兜底（值仍取 AC_INIT 已校验版本，tegrarcm/1.8 经验 adapt：向生成头补包标识定义；其 limits 头部分本案无证据，不适用），清单内命中时仍走原分支（flag 去重，drift 校验仍只比对解析集）。rolo 本体与测试口径不动 |
| 32 | 本轮真机新失败域：ncurses调用已通，`src/entry.c:557/559/561: too many arguments`——`rolo_utf8_strlen(fn,-1)`传2参但本地实现仅声明`(const char *s)`单参 | glib消除时把`g_utf8_strlen(p,max_len)`简化为单参NUL计数，但调用点仍传`(s,-1)`（-1即NUL截断约定的第二个实参）；上轮只验证了存在性未核对元数 | 与上轮调用约定修复不同（改被替换函数签名而非调用方）：本地实现改为`(const char *s,long max_len)`双参，max_len<0走NUL截断否则限长计数，返回long与原语义对齐；注释避用旧符号名以保3处计数锚定，测试口径不动 |
| 31 | 本轮真机新失败域：unac直编已过（`vendored unac 1.8.0 direct-built extra=''`、`unactest.c ran green`），`_build_rolo_direct`死于`_ncurses_direct_flags`的`ncursesw6-config --cflags failed to execute: FileNotFoundError(2)`；此前isfile检查已过 | 上轮门禁修复生效（失败点后移即证据）。新根因是直接exec脚本：其shebang解释器与exec位在chmod:0 runner上无保证（平台能力hardlink:0/chmod:0），存在但不可直接执行即ENOENT；与unac符号误报不同域 | 与上轮双侧清洗不同路线（改调用约定而非过滤）：经显式shell调用（/bin/sh优先，HMBS保证，SHELL/which sh回退），同时绕过shebang与exec位两故障；记所用shell，输出语义不变，测试口径不动 |
| 30 | 本轮真机复跑：unac.o/归档仍建成，但消费者链接门禁全败：`probe_gate_link.c:5: use of undeclared identifier 'unac'`，门禁抛 `consumer link gate failed for symbols ['unac', 'unac_string']`；同日志 `raw rolo unac* tokens ['unac', 'unac_string']` 且 `size_t` 错误已消失 | 上轮“声明式过滤（后随 `(`）”假设被证伪：新证据是随包 unac.h 第 23 行注释 `See the unac(3) manual page` 含裸 `unac(` 文本，恰满足旧正则，裸头文件名词元被误留；另 rolo 侧 `#include <unac.h>` 行自身亦贡献裸 `unac`。非归档问题，门禁误报 | 与上轮不同路线（双侧清洗而非再调发射/探针头）：①rolo 扫描侧先去块/行注释再丢 `#` 预处理行，后做词元收集；②声明检查侧对 unac.h 同样去注释后判定。本地仿真旧逻辑得 `['unac','unac_string']`、新逻辑得 `['unac_string']`；空集仍 fail-closed，归档与测试口径不动 |
| 29 | 上一轮之后真机复跑：unac.c 编译通过、静态归档建成，但消费者链接门禁全败：`probe_gate_link.c:1: unac.h:78: unknown type name 'size_t'`×4 + `probe_gate_link.c:4: use of undeclared identifier 'unac'`，门禁抛 `consumer link gate failed for symbols ['unac', 'unac_string']` | 新失败域（门禁探针自身缺陷，非被测归档问题）：①门禁 TU 只含 `#include <unac.h>`，而 unac.h 用 `size_t` 却不自含 `<stddef.h>`（依赖消费者先提供，rolo 本体经 stdio/stdlib 间接满足）；②符号发现用裸词匹配，`#include <unac.h>` 行自身的 `unac` 词元及注释词通过过滤（unac.h 某处含裸词 `unac`），`(void)&unac` 非函数故未声明。前两轮的 config.h 路线已生效（unac.o 建成即证据），本轮不动发射逻辑 | 与前轮不同策略（修门禁探针而非配置发射）：①门禁 TU 改为先 `#include <stddef.h>` 再含 unac.h（与 rolo 本体一致）；②符号过滤改为声明式（词元在 unac.h 内须后随 `(`，即函数声明/定义点），裸 `unac` 被记日志丢弃、`unac_string` 保留，空集仍 fail-closed。归档内容与测试口径不动 |
| 33 | 本轮真机 compile 已过全部编译（libvc/unac/rolo 直编、`rolo -v`门禁均绿），死于上游套件执行行：`conan/rolo_pkgconfig.sh[13]: printenv: inaccessible or not found` + `test/run-tests[70]: .: shunit2: No such file or directory`（Error 1，build()套件行） | 双根因不同域：① generate() 的 Environment.save_script 发射 conan/rolo_pkgconfig.sh，其第13行调 printenv，而该 runner 无 printenv（conanbuild 聚合替换语义下 sourcing 先于任何行内 PATH 加固，故 _with_util_path 救不了）；且该脚本唯一内容（PKG_CONFIG_PATH 指空 generators_folder）本就无用（PkgConfigDeps 是 no-op，unac.pc 走显式 -I/-L）。② shunit2 经 _ensure_shunit2 只改外层 os.environ PATH，而 self.run(env=[conanbuild...]) 用聚合后 PATH（同 #25 替换语义），行内加固又未携带 rolo-tools/系统 shunit2 目录，故 run-tests 的 `. shunit2` 在聚合 PATH 下失联 | 与前轮门禁/调用约定修复不同路线（做减法+补携带）：①删 rolo_pkgconfig 脚本（generate 不再 save_script，build 改 env=[conanbuild]，与此前全绿的 vendored 步骤一致；无 flags 变化）；②_util_path_prefix 补 cat/mktemp/cmp/mv/cp/chmod/printenv/env 目录，并必带 rolo-tools（存在时）与系统 shunit2 所在目录（which 分支时），上游套件行继续经 _with_util_path 前置。rolo 本体与测试口径不动 |
| 34 | 上轮双门修复生效（printenv/shunit2 门过，套件真实执行 `Ran 4 tests.`），新失败：`test_rolo_startup_and_help` 中 `ncurses: cannot initialize terminal type ($TERM="dumb"); exiting`，`FAILED (failures=1)` | 上游 run-tests 以 `TERM=dumb` 无头驱动 curses（initscr 仍需解析 terminfo），ncurses/6.6 的 terminfo 库（share/terminfo，2899 条）仅经 runenv TERMINFO[_DIRS] 暴露，而 build() 套件行用 env=["conanbuild"]，runenv 缺席故连 dumb 条目都解析不到；与二进制/链接无关（-v 门与直编全绿即证据） | 与前轮环境门不同路线（补数据路径而非工具 PATH）：新增 `_ncurses_terminfo_exports`，在套件行内 `export TERMINFO/TERMINFO_DIRS="<ncurses pkg>/share/terminfo"`（isdir 校验+条目数日志，缺失则警告后如实失败不断言跳过），上游 inline TERM 不动；test_package 经 conanrun 原生带 runenv，无需改动。测试口径不动 |
| 35 | 上轮 terminfo 修复生效（dumb 初始化门过，套件真实执行 `Ran 4 tests.`），新失败：`Signal 6 (core dumped)` + `expected:<FN:Alex Winter> but was:<>`，`FAILED (failures=2)`——仅深入 UI 的两例失败，原地 quit 的两例绿 | 审计上游源码锁定唯一平台相关硬编码：src/add.c 与 src/edit.c 均以 `char filename[PATH_MAX] = "/tmp/rolo-XXXXXX"` 做 mkstemp 且无返回值检查，而 HMBS 只保证 per-task TMPDIR（test.sh 亦明示 /tmp 可能只读）；move_and_edit（`ROLO_EDITOR=cat` 编辑路径）恰走 edit.c 该分支，空输出+core 与其一致，search_and_delete 走同目录可写的 datafile.tmp 故另寻他因待探针区分 | 与前轮数据路径修复不同路线（改模板来源而非环境变量）：新增 `_fix_tmpdir_templates`，两文件改由 getenv(TMPDIR) 组模板（空则回 /tmp，仅用两者都已含的 stdlib/string，无新头文件，不改控制流，仍响亮失败）；build() 在套件前加只读探针（TMPDIR 取值、ls -ld、/tmp touch，恒 exit 0 不设门），供下轮区分 tmpdir 与 curses/libvc 域。测试口径不动 |
| 36 | run-tests 无 Ran 汇总行（4 discovered/0 executed，readonly_tmp） | 驱动两处裸 mktemp 默认落 /tmp，只读下 set -e 直接 abort，shunit2 无汇总；#35 只修了本体 add.c/edit.c 未覆盖脚本 | 最小根目录适配：两处改用 TMPDIR 模板（want 2、幂等、fail-closed）+ suite TMPDIR 解析与行内 export，本体与口径不动 |
| 37 | 同指纹第2次：上轮mktemp改写已进真机（报错581行与树吻合）仍无汇总；日志中孤立绿色OK | shunit2 2.1.8按tput决定着色（缺tput回退16色恒开），跨runner输出时为Ran着色行，旧正则恒 miss；mktemp是误诊 | 换路线：回滚驱动为 pristine（复用缓存兜底恢复）；解析器先剥ANSI CSI再匹配（单源无猜数）；套件行内export SHUNIT_COLOR=none；本地三样本仿真着色OK/着色FAIL/纯文本全对 |
| 38 | CI（官方 worker CI-018，build #91603）conan-build-test 死于 libvc 生成步：`RUN: .../bison_3.8.2/bin/bison -d vc_parse.y` 后 `m4: cannot open '.../bison3d52.../p/usr/share/bison/skeletons/bison.m4'`，最终 `RuntimeError: libvc yacc: no parser/scanner C output`；同 head 真机预检 passed | CI worker 与预检 runner 是不同机器：预检机原生 yacc/lex 全 MISSING（走 Conan bison/2.7，绿），CI 机原生 bison/flex 存在故取 native 分支，但该 bison 是骨架目录已被 GC 的 stale 安装——能启动、m4 能跑，但 skeletons/bison.m4 缺失故零输出。存在性/X_OK 探测对此类坏安装恒绿，非 flags/依赖问题 | **存在性改可用性（与换 YACC 路线/调用约定修复均不同）**：新增 `_smoke_yacc_ok/_smoke_lex_ok`（build 文件夹内最小语法真实 `-d/-o` 生成、C 文件出现才算过，从不抛错只回 bool，tail 日志）；`_ensure` 内原生双候选各自验证，坏即弃入回退；Conan bison 先导 `BISON_PKGDATADIR` 再 smoke（绿则用，红则清变量入 byacc）；byacc 兜底同样 smoke，仍红则 fail-closed 早报（原在 `_build_libvc` 报同错）。预检路径（原生 MISSING→Conan bison）零变化；rolo 本体与测试口径不动 |
## 源码修改

无 `.patch` 文件（`patches_applied: []`；真机预检若暴露 musl/curses 平台问题再按 `refresh-patch --auto` 补）。
无 `.patch` 文件之外，另有构建期生成物（不进包）：build/rolo-cfg/config.h （手写，仅 PACKAGE_* 六宏，复刻 configure.ac AC_INIT 值；全源码 grep 证实仅 main.c 消费 config.h 且仅用 PACKAGE_STRING）。
有两处配方内原地改写（build() 内 exact-match+计数校验+stamp 幂等，不走 patch 文件）：
- unac 私有 vendoring 的两个 aarch64 int→size_t 类型修复（与 unac 配方 0001+0002 同 hunk，见问题表 #8）；
- glib 边消除：configure.ac 删 GLIB PKG_CHECK_MODULES 块及接线，entry.c 以等价 `rolo_utf8_strlen` 替代 `g_utf8_strlen`×3（见问题表 #11）。
- gnulib-musl 原地补丁：私有 m4/bison/flex 解包后对 `**/freadahead.c` 插入 musl 分支（与 coreutils 0002 同语义，见问题表 #14）。

## 依赖版本

- ncurses/6.6（ncursesw + menuw，widec；零传递依赖叶子节点）
- glib：不再 requires（上游仅 entry.c 用 `g_utf8_strlen`×3 做菜单列宽补偿，已在 build() 原地改写为等价本地 `rolo_utf8_strlen` 并去掉 configure.ac 的 GLIB 接线，见问题表 #11；此前 2.84.0.2 在本仓各版本均无二进制，任何 requires 都强制 meson+libffi 源码构建链）
- unac/1.8.0（PKG_CHECK_MODULES UNAC；never published，二进制缺失且其 tool_requires 链恒拖入 CCI m4，改私有 vendoring，见问题表 #8）
- libvc v013（官方源码 vendoring，sha256 `a43bf49f…821c2`，私有静态，不发布）
- 构建期工具：无 tool_requires（第九策略：autoreconf 已消除；yacc/lex 缺原生时配方内私有编译，不进 Conan 图）
- 自举工具链：无 m4/bison/flex 的 Conan 边（见问题表 #9/#12）；yacc/lex 原生优先，缺失时配方内私有编译 GNU m4/1.4.19 + byacc/2.0 + flex/2.6.4（与本仓三配方同源同哈希，不进图）；automake/1.18、libtool/2.5.4 仍为仅有的 tool_requires（bashdb 已合入先例；CCI 无 automake 1.18、无 libtool 2.5.x，均走 ohpcd）
- shunit2 v2.1.8（测试期现取，pin sha256，不进包）

## 验证结果

（首轮工作树在 Windows 本机完成，未跑 conan/真机；以下待 HMBS 真机预检回填）

- [ ] `conan create` 全绿（含 libvc 直接编译 → unac 直接编译 → rolo 直接编译 → sh test/run-tests）
- [ ] `make_check.log` 含 `Ran 4 tests.` + `OK`（或如实 FAILED）
- [ ] `HMBS_UPSTREAM_TEST_RESULT` 与 `HMBS_TEST_PACKAGE_RESULT` 双标记齐全且计数自洽
- [ ] 上游 4/4 通过；消费者 5/5 通过
- [x] 前置阻塞已消除：libvc 改为配方内 vendoring，不再有缺依赖解析失败

## 注意事项

- `rolo -v/-V/-h` 在 `initscr()` 之前即退出，消费者用例 (B)(C)(D) 无需终端；
  用例 (E) 与上游 3 个 curses 用例需 `TERM=dumb` 无头终端（terminfo 缺失会在日志明示，
  按 environment 缺口如实记 gaps，不记为通过）。
- 本机 Windows 检出说明：仓内 `archives/g/gama/...patch??`（文件名尾带 `\r\r`）与
  `archives/l/libXext`/`libxext` 大小写碰撞无法共存于 Windows；已用
  `assume-unchanged` 屏蔽该 4 项差异，远端 Linux 不受影响。本 PR 只含 `archives/r/rolo/`。

## 本轮修复 (#38, 2026-10-14 test_package readonly_tmp)

- 现象: 主包直编 + 上游 4/4 已绿, test_package 阶段 `test.sh` Error 1, HMBS 诊断 `[readonly_tmp]`.
- 根因: test.sh 选择的可写目录未 `export` 给 rolo 子进程, 刚修的 add.c/edit.c `getenv(TMPDIR)` 回退到只读 `/tmp`; 且只看 TMPDIR 不看 TMP/TEMP, `rolo-tp.$` PID 后缀写错为单 `$`.
- 修改: test.sh 改为 TMPDIR/TMP/TEMP 优先选可写目录并 `export`, 修复 `$$`; conanfile `_fix_tmpdir_templates` 升级为 v2 (TMPDIR->TMP->TEMP->/tmp, 带 v1 stamp 升级路径); 主包探针 `touch/rm` PID 修复为 `$$`. 测试口径不变, 不删断言不跳过测试.

| 27 | bison/2.7 边引入后真机 compile 仍死于 yacc 冒烟：Conan bison 报 `m4 subprocess failed: No such file or directory`（rc=1），随后私有 byacc 报 `yacc: f - cannot open "action_file"`（rc=2），`_ensure_vendored_lex_yacc` 抛 `vendored byacc fails generation smoke` | bison 在生成期 spawn m4（真机原生 m4 MISSING），但 `_ensure` 先对 Conan bison 做生成冒烟、之后才编译私有 m4，健康 bison 因缺 m4 被误判拒绝，退到本 runner 上必死的 byacc；且 libvc 生成命令经 self.run(env=["conanbuild"]) 可能丢失 M4/BISON_PKGDATADIR | **m4 前置+生成环境透出（与第十策略换路线不同，是同路线内的时序修正）**：`_ensure` 改为先编译私有 m4 并立即导出 M4+PATH，再重试原生与 Conan bison 冒烟（BISON_PKGDATADIR 照常导出）；`_build_libvc` 的 yacc/flex 生成命令行内 `export M4/PATH/BISON_PKGDATADIR`，不依赖 conanbuild 继承；byacc 仍为最后兜底，冒烟门禁不动。rolo 本体与测试口径不动 |

## CI round 2026-10-15 (build #92544 download timeout + #92578 flex fork)

- #92544 source() download: gh-proxy.com returned forbidden + official github.com connect timeout x3. Fix: conandata.yml url expanded from 2 entries to ordered 7-mirror list (gh-proxy / mirror.ghproxy / ghproxy / gitclone / moeyy / kkgithub + official last), same sha256, following jsonnet v0.20.0 / erofs-utils 1.9.3 precedent and CI hint set.
- #92578 build() libvc flex step: native /data/service/hnp/flex.org/flex_2.6.4/bin/flex died with "flex: fork failed" (Error 1, transient fork/resource pressure; true-machine preflight on same head passed). Root cause in recipe: _MEM_RETRY_SIGNS lacked "fork failed" and _run_retry matched only str(exc) (generic Conan Error 1, no tool stderr) so no retry ever fired. Fix: added "fork failed" signature; _run_retry now redirects each command to build_folder/rolo-retry-<label>.log, replays via cat (POSIX sh, no pipefail), and matches signatures against exception + log tail. Non-signature failures still raise immediately; rolo flags/test scope untouched.
