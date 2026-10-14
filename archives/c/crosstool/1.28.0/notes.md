# crosstool 1.28.0 适配笔记

## 编译环境

- 构建系统：autotools（`configure + make -j1`）
- 编译日期：2026-09-26
- 编译器：clang/clang++
- 状态：built（待真机预检确认）

## 上游信息

- 上游：crosstool-ng 1.28.0（2025-09-06 发布）
- 源码：https://github.com/crosstool-ng/crosstool-ng/releases/download/crosstool-ng-1.28.0/crosstool-ng-1.28.0.tar.xz
- sha256：`5750e29a2bda5cd8d67900592576b1670a1987a4dcd5e4f6beae09138a1f5699`（与 Homebrew 官方公式一致）
- 许可证：GPL-2.0-only

## 编译步骤

1. `get` 解包上游 `tar.xz`（conandata.yml，镜像在前、官方源置末，同一 sha256 校验）
2. `generate`：OHOS 下追加 `--build=aarch64-unknown-linux-gnu`（见下表问题 1）
3. `build`：`configure` → `make -j1` → `make check -j1`（两处 Makefile.am 均无 TESTS 注册，`make check` 为空操作，仅作入口健全性确认，不再输出上游标记；8 用例 `testing/upgrade` 真实套件由 `test_package` 用包内 `bin/ct-ng` 完整重放，见步骤 5 与问题 35）
4. `package`：`make install`（交付 `bin/ct-ng` 及 pkgdata 脚本库）
5. `test_package`：两部分——①包内 `bin/ct-ng` 的 4 项真实调用（version/help/list-steps/clean），脚本输出 `RESULT: P passed, F failed` 尾行，conanfile 据此输出 `HMBS_TEST_PACKAGE_RESULT`；②上游 `testing/upgrade/run.sh` 的忠实重放（conanfile 内 Python 移植，断言语义与原生一致；7 样本固件 + `kconfig-list/3` 逐字节 vendor 于 `test_package/upstream_upgrade/`），输出真实计数的 `HMBS_UPSTREAM_TEST_RESULT`（discovered=8；options-set 用例因上游缺 `kconfig-list/4` 在任何平台都失败，见问题 35）

## 历史经验核验（W0b）

本仓库已有旧格式归档 `archives/c/crosstool-ng/1.28.0/`（2026-06-02，设备原生构建成功）。
核验结论：

| # | 历史做法 | 本配方是否沿用 | 说明 |
|---|----------|----------------|------|
| 1 | 安装 texinfo/help2man/ncurses 预编译包后 `configure` | 部分沿用 | 历史成功依赖设备预装工具；CI/真机 clean 环境是否自带未知。本配方未声明 Conan 依赖，若真机报缺工具，下一轮按缺失项补 `tool_requires` 或裁剪文档目标，不在本轮臆测 |
| 2 | 6 个补丁（Makefile CPPFLAGS、config.h、configure umask、kconfig Makefile、config.guess/sub） | 不沿用生成物补丁 | R6 禁止修改 `config.h`/`configure` 等生成文件；R18 补丁只能由 `refresh-patch --auto` 生成。平台识别问题改用 `--build` 直传解决；umask类问题若在真机复现再按规生成补丁 |
| 3 | `make check`（部分超时跳过） | 沿用入口 | 上游审计确认无 TESTS 注册，`make check` 为空操作；不存在“超时跳过”的用例计数，不计入通过率 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 随包 `config.guess` 无法识别 OHOS（历史 E007/E072） | tarball 自带的 guess 快照无 OHOS 三元组 | `generate()` 中 OHOS 专用 `--build=aarch64-unknown-linux-gnu`，跳过 guess；无源码补丁 |
| 2 | 上游无自动化测试，不满足“接入上游测试”的字面要求（本轮证伪：见问题 35） | 初审只查了 Makefile.am 的 TESTS，漏掉未挂接 `make check` 的 `testing/upgrade/run.sh` 真实套件 | 原 `no_tests` 口径作废；test_package 用包内 `bin/ct-ng` 完整重放 8 用例并上报真实计数，`build()` 不再输出零计数标记（避免双标记计数矛盾） |
| 3 | `ct-ng --version` 输出的是 GNU Make 版本而非自身版本 | ct-ng 把未知参数透传给 make（历史 notes 实测） | 测试只用 `version` 动作（输出 `This is crosstool-NG version 1.28.0`），不用 `--version` |
| 4 | 真机 configure 报 `C compiler cannot create executables`（CC=`/data/service/hnp/bin/clang`），首轮按 c-ares E266 加 `LD_LIBRARY_PATH`+`-fuse-ld=lld` 后复检仍失败，且日志出现 `SDK llvm/lib not found`、`config.log` 尾部只有工具检测摘要 | 单路径假设在 HMBS 执行器上落空（SDK 实际布局未知），尾部转储错过真正的 conftest 失败段 | 取证优先策略：SDK 搜索拓宽到 4 种布局并打印全部候选；configure 前加 hello-world 链接/运行探针（区分链接失败与沙箱禁执行）与 `CC/CFLAGS/LDFLAGS` 单行取证；`config.log` 改为按关键词抽取失败段 |
| 5 | 复检取证实锤：`/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found`（exit 127），conftest 命令行 `/data/service/hnp/bin/clang -O3 -DNDEBUG -fuse-ld=lld conftest.c` 根本没跑起来；`SDK llvm/lib candidates: []` | profile 的 `tools.build:compiler_executables` 路径在预检沙箱挂载隔离下不可见，与 flags/linker 无关 | libnids 运行时探针钉选：按 conf→环境→PATH→已知绝对路径→SDK `llvm/bin` 顺序真实执行 `--version`＋带旗标链接＋运行三重验证，首个全过者写入 `conanbuild.sh` 末尾重导出并内联到 configure 前缀；`plain` 模式（仅无旗标可链接）时同步剥离 `-fuse-ld=lld`；三元组与 `--build` 固定不变；探针全失败则保留默认值由 configure 如实报错 |
| 6 | 真机 configure 在编译器检查通过后报 `checking for flex... no` / `configure: error: missing required tool: flex`（上一周期3轮编译器/链接器假设已证伪：本轮日志编译器段全部通过） | 上游 crosstool-ng 强制要求 flex+bison（Alpine/Gentoo BDEPEND 证实 bison 是 flex 之后紧邻的下一个检查项）；真机/CI 无系统级 flex/bison | 新增 `build_requirements`：`tool_requires flex/2.6.4 + bison/3.8.2`（captagent 6.4.4 同基础设施先例，制品仓已发布；经 conanbuild PATH 生效。若复检暴露 gperf/help2man/texinfo 缺失，下一轮按实际日志处理） |
| 7 | 2026-09-26 07:46 预检仍报 missing flex（build_requirements 已含 flex/bison，依赖图已解析但 configure 探针仍找不到） | 声明 tool_requires 只保证安装，不保证进入本配方自定义 configure 调用的 PATH（gcc-snapshot 草稿同根因） | generate() 显式从 build-context 依赖取 package_folder/bin，前置 PATH 并 define FLEX/LEX/BISON/YACC；build() 加 command -v/version 探针取证 |
| 8 | 2026-09-26 10:31 预检：flex 包本身无 bin 目录（flex bindir missing），bison 注入正常，configure 仍缺 flex | 注册表 flex/2.6.4 包只有库无二进制，静态注入无目标（gcc-snapshot 草稿已预言此情形） | 保留依赖，build() 增加运行时同版本优先 fallback 探针（HNP flex_2.6.4 → HNP 通配 → brew → /usr/bin），首个 --version 通过者钉选 FLEX/LEX 并前置 PATH 到 configure；无可用者则如实报错 |
| 9 | 2026-09-26 14:28 预检已含第 8 轮探针（报错行 489 一致）仍缺 flex：注册表包与设备回退均无可用 flex | 设备侧无任何可运行 flex，继续加候选路径已无意义 | build() 增加最后手段：用官方 flex-2.6.4 源码（同注册表 URL+sha256，镜像在前官方置末）vendor 构建到构建目录私有 prefix（仅 SUBDIRS=src，复用已验证编译器，umask/TMPDIR 防护），--version 烟囱通过才钉选 FLEX/LEX；失败则如实报错 |
| 10 | 2026-09-26 15:15 预检 flex-bootstrap 自身 configure 报 C compiler cannot create executables（Error 77），而主 configure 后续用 harmonybrew clang 成功 | 第 9 轮 vendor 构建跑在 CC 探针钉选之前，继承了预设损坏 CC，与 flags 无关 | 将 CC/CXX 运行时探针整体前移到 flex 候选与自举之前；bootstrap 的 configure 与 make 显式复用已钉选编译器，plain 模式同步剥离 lld，无可用编译器时留空前缀如实报错 |
| 11 | 2026-09-26 16:22 预检 flex-bootstrap 已越过 CC/libtool 检查，死于 checking for m4 that supports -P（Error 1），主 configure 仍缺 flex | flex 2.6.4 强制要求 GNU m4，真机无可用 m4，上一轮仅解决编译器排序未补传递构建工具 | 新增 tool_requires m4/1.4.19，generate 注入其 bindir 并定义 M4/GM4，build 增加真实 -P 执行探针并将胜出者钉选到 M4 与 PATH，同时拼入 bootstrap 与主 configure 前缀，无胜出者时如实报错 |
| 12 | 2026-09-26 18:01 预检 flex-bootstrap 已通过（m4 -P 检查 OK），主 configure 死于 checking for help2man... no（Error 1） | crosstool-ng 强制要求 help2man（flex 仅警告，自举不受阻），真机无该工具，上一轮 m4 修复已生效非重复 | 新增 tool_requires help2man/1.49.3（in-repo verified），generate 注入其 bindir，DIAG 增加 help2man 探针取证 |
| 13 | 2026-09-26 18:49 预检依赖图直接失败 `ERROR: Package help2man/1.49.3 not resolved in remotes` | help2man/1.49.3 仅 verified 未 uploaded 到 ohpcd，tool_requires 破坏依赖图 | 移除 help2man tool_requires；build 内先探针设备候选，缺失则 vendor 官方 GNU help2man-1.49.3（ftp.gnu.org + tuna/ustc/aliyun 镜像，同 sha256）到私有 prefix 并前置 PATH，无伪造，通过才钉选 |
| 14 | 2026-09-26 19:58 预检 configure 在 `creating ./config.status` 后报 `can't create ./confgXdbDW/subs1.awk: Permission denied`（主 configure 与 help2man-bootstrap 同错；flex-bootstrap 因旧 TMPDIR 重定向 guard 偶然通过） | autoconf 生成的 configure 用 `umask 077 && mktemp -d "./confXXXXXX"` 建临时目录，在 HMDFS 上 owner 不可写（E011），与编译器/工具链无关；旧 flex guard 改走 TMPDIR 与标准做法分叉，且 help2man/main 无任何防护 | 统一采用 cyrus-sasl-login/2.1.28 已验证做法：新增 `_hmbs_fix_autoconf_umask`（umask 077->022 原地改写生成态 configure，不进补丁）并对主/flex/help2man 三处 configure 全部应用；新增 `_hmbs_mktemp_shim`（仅当 HMBS_AUTOCONF_MKTEMP_FALLBACK=1 时对 conf 路径回退到 mkdir）；三处 configure/make 统一加 `umask 022 &&` 与 TMPDIR/TMP/TEMP 内联前缀，进程级 `os.umask(022)` 兜底 |
| 15 | 2026-09-26 20:35 预检 flex-bootstrap 已通过（config.status creating Makefile OK，E011 修复生效）但主 configure 报 `checking for bash... / checking for GNU bash >= 4.0... no / configure: error: Required tool not found: GNU bash >= 4.0` | 上游 crosstool-ng 强制要求 GNU bash>=4（ct-ng 本体为 bash 程序），与 CONFIG_SHELL 无关而是 PATH 查 bash；真机/CI 默认 PATH 无 bash（沿用 flex/bison/m4 同类缺失模式） | 新增 `tool_requires bash/5.3`（castget/2.0.1 同注册表先例，CI 无 bash 时的官方解法）；generate 注入其 bindir；build 增加 bash 运行时探针（tool 包优先→设备候选，真实 `--version` 仅接受 major>=4），胜出者钉选 BASH 并前置 PATH 到主 configure；失败则如实报错 |
| 16 | 2026-09-27 04:18 预检 bash 检查通过后主 configure 报 `checking for libtool... / checking for GNU libtool >= 2.4... no / configure: error: Required tool not found: libtool` | 上游 crosstool-ng 强制要求 GNU libtool>=2.4（kconfig 与顶层 Makefile 依赖 libtool）；真机/CI 默认 PATH 无 libtool（沿用 flex/bison/m4/bash 同类缺失模式） | 新增 `tool_requires libtool/2.5.4`（cbootimage/1.8、canl-c/3.0.0、captagent/6.4.4 同注册表先例，满足 >=2.4 且已发布可解析）；generate 注入其 bindir（libtool/libtoolize）并定义变量；build 增加 libtool 运行时探针（tool 包优先→设备候选，真实 `--version` 验证），胜出者钉选 LIBTOOL 并前置 PATH 到主 configure，DIAG 增加 libtool 取证；失败则如实报错 |
| 17 | 2026-09-27 08:15 预检 libtool 检查已通过（失败域前移），主 configure 报 `checking for initscr() with -lncurses... no / checking for Curses library... no / configure: error: curses library not found` | 上游 kconfig（mconf/nconf 配置器）强制要求 curses 库做链接探测；真机/CI 无系统 ncurses 开发库（沿用历史 crosstool-ng 归档问题 3/6：需 ncurses 头文件与库） | `requirements()` 新增 `self.requires("ncurses/6.4")`（cbonsai/1.4.2、cbm/0.4-1、hexedit/1.6 同注册表先例，已发布可消费；提供 libncursesw 与头文件）；经 AutotoolsToolchain 的 conanbuild 环境自动带入 -I/-L，无需额外注入；失败则由 configure 如实报错 |
| 18 | 2026-09-27 09:56 预检仍报 `curses library not found`（裸 requires 未生效：日志可见窄库 `-lncurses` 回退失败，其前的 ncursesw pkg-config/回退分支静默失败） | 上游 AX_WITH_CURSES 先走 pkg-config ncursesw 分支、再走 `-lncursesw` 链接回退（需 -L）；仅靠自动透传时两通道均未命中（clex/4.6.patch8 同类硬探测曾需显式接线） | generate 显式追加 `-I<ncurses>/include`（extra_cflags）与 `-L<ncurses>/lib`（extra_ldflags），并经 build 域脚本暴露 `lib/pkgconfig` 到 PKG_CONFIG_PATH（clex 同款）；build 加 ncurses 链接取证探针（列包内 lib/include、$CC 直链 initscr × `-lncursesw/-ltinfow/-lncurses/-lpanelw/-lmenuw`，仅链接不执行）；config.log 抽取正則补 curses/ncurses/initscr/tinfo/panel/menu |
| 19 | 2026-09-27 12:05 预检 curses 检查已通过但死于下一项 `checking for Curses Panel library with ncursesw/panel.h... no / with panel.h... no / configure: error: panel library not found`（18 轮 -I/-L 接线证实只够 curses，panel 双头变体均失败；menu 检查紧随其后） | 与 17/18 轮不同的层：注册表 ncurses/6.4 为宽字符不完整头文件集，缺 panel.h/menu.h（旧 archives/c/crosstool-ng/1.28.0 notes 行 6 同先例：“ncurses 预编译包缺少 panel.h/menu.h/eti.h，从源码包复制”）；仅补 -I/-L 无法变出缺失头文件 | build 增加 panel/menu 头库审计（lib/include/ncursesw 三目录取证 + $CC 预编译 `<panel.h>`/`<ncursesw/panel.h>` 探针）；缺头时 vendor 取官方 ncurses-6.4.tar.gz（tuna/ustc/aliyun 镜像在前、ftp.gnu.org 置末，同 sha256 `6931283d…248159`）仅抽取 panel.h/menu.h/form.h/eti.h 到构建目录私有 `ncurses-extra/include`（顶层 + ncursesw/ + ncurses/ 三位置），经 conanbuild.sh 与 configure 内联 `CPPFLAGS/CFLAGS="-I<extra> $…"` 双通道生效；menu 一并补齐避免连环失败；失败则如实报错不伪造 |
| 20 | 2026-09-27 15:11 预检仍报 panel 双变体 `no`，但本配方探针显示 `panel-header-ok-top` / `panel-header-fail-ncursesw` 且打印“无需补齐”；config.log 转储停在早期 cross-compiling 检查，未见真正的 panel 失败段 | 三层误判：① 补齐触发器只看 panel.h 任一变体，top-only 包永远跳过补齐，ncursesw/panel.h 首变体注定失败；② 头 `-c` 探针无法代表 AX_WITH_CURSES_PANEL 的头+库链接测试（-lpanelw 未验证）；③ 日志抽取 `hits[:12]` 被早期 curses 噪声占满，丢了尾部真正的 panel/menu 失败段 | 触发器改为 4 头（panel/menu × 顶层/ncursesw）任一缺失即补齐（三位置全放）；补齐后加 `new_panel`/`new_menu` 真实链接探针（`-lpanelw/-lmenuw + -lncursesw`，附 `-ltinfow` 对照，仅链接不执行）；日志抽取保留前 12 命中同时追加末 12 个 panel/menu/curses 命中与最后 40 行，下轮不再盲修 |

| 21 | 2026-09-27 16:12 预检 make 在 kconfig 死于 `.../p/bin/yacc[123]: /bin/bison: inaccessible or not found`（Error 127，parser.tab.c），而 `bison --version` 显示 3.8.2 正常 | bison/3.8.2 包自带的 `yacc` 包装脚本硬编码 `/bin/bison`，真机无此路径；配方 generate/build 一直把该包装器导出为 YACC，configure 烘焙进 kconfig Makefile 后 make 必败，与 flags 无关 | generate 内永不导出 yacc 包装器，YACC 改为 `<bison> -y`；build 新增 bison 运行时探针（tool 包优先→设备候选，真实 --version 验证），胜出者经 conanbuild.sh + os.environ + configure 内联前缀三通道钉选 BISON/YACC，失败则如实报错 |

| 22 | 2026-09-27 19:03 预检 wrapper 错误消失但 kconfig make 死于 `bison: /share/bison/m4sugar/m4sugar.m4: cannot open`（Error 1，parser.tab.c） | 异地重定位的 Conan bison 用编译期默认数据目录（回退到绝对 `/share/bison`），找不到 m4sugar 文件；与上一轮 wrapper 路径是不同层（GNU bison 用 BISON_PKGDATADIR 定位数据文件） | generate 与 build 双入口审计胜出 bison 包内 `share/bison/m4sugar/m4sugar.m4`，经 conanbuild.sh + os.environ + configure 内联前缀三通道钉选 BISON_PKGDATADIR，并加最小空文法冒烟探针取证；缺失则如实报错 |

| 31 | 2026-09-29 预检 verdict 已修好并给出真因：`configure-error: Required tool not found: libtool` / `last-check: GNU libtool >= 2.4 => no`，与 28/29/30 轮的 panel/menu 假设同指纹但不同失败域 | 上游 configure.ac 实证：LIBTOOL 检查是 CTNG_PROG_VERSION_REQ_ANY（仅验 `--version` 匹配 `(GNU libtool) ([3-9].|2.[4-9]|...)`，先 glibtool 后 libtool），25 轮自创的 `--help` 含 --silent 门槛比上游更严，V=1 下 --silent 永不发射，拒收可用 libtool；另 vendor `make` 缺 MAKEINFO/HELP2MAN 熔断（设备无 makeinfo/help2man），`--silent --version` 联合冒烟非上游口径亦会误杀好构建；且 LIBTOOLIZE 是紧随其后的独立检查 | 与补 curses/改取证彻底不同路（curses 预设保持 28 轮原样不动）：①设备探针改为上游同款 `--version` 正则，--silent 仅信息取证；②vendor `make/make install` 加 `MAKEINFO=true HELP2MAN=true` 文档熔断；③冒烟改为上游同款双 `--version` 正则；④同目录 sibling libtoolize/glibtoolize 一并钉选 LIBTOOLIZE+PATH+configure 前缀；失败仍如实报错 |

| 30 | 2026-09-29 预检 verdict 行 `curses_which=? panel=? menu=?` 且无 configure-error 输出，confdefs.h 仅 PACKAGE 加 HAVE_CXX11 | 与 28/29 轮的功能修不同，本轮先修取证本身：config.log 行均带 `configure:行号:` 前缀，29 轮的 startswith 与连续子串匹配注定落空；且 ax_cv_panel/menu/curses_which 是普通 shell 赋值（非 AC_CACHE_CHECK），缓存区本就没有 | verdict 改为正则容忍前缀（last checking/result 对加全部 error 行），另加 configure 前全部强制工具单行 rollcall（flex/bison/m4/bash/libtool/help2man/file/makeinfo 等），单行 HMBS_DIAG 随摘要保留，下轮可区分缺工具与链接失败 |\n\n| 29 | 2026-09-29 预检 28 轮已使 PANEL_LIBS='-lpanelw -lncursesw' 进入 config.log，configure 仍 exit 1 | 与 26/28 轮不同：旧探针源文件是无头文件的 `extern void*` 桩，只能证明库符号可链，证明不了宏真正的“头+链接”双重测试（`#include <panel.h>` + WINDOW/PANEL 真实类型），探针通过后宏仍可能死于头文件缺失；且 HMBS_CFGLOG 窗口转储在轮次摘要中被裁，panel/menu 真实失败行不可见 | 探针源改为与上游 _AX_WITH_CURSES_CHECKEXTRA 逐行一致（含头文件与真实 API，仅链接不执行），只有忠实探针证明的配方才导出 PANEL_LIBS/MENU_LIBS；异常分支新增 HMBS_DIAG 单行 verdict（curses_which/panel/menu 缓存值 + configure: error 原文），随摘要保留供下轮判定 |\n\n| 28 | 2026-09-29 预检沿用第 27 轮工作树仍 exit 1（pkgconf/3.0.5 已解析，ncurses 接线生效） | 27 轮前提经上游源码证伪：m4/ax_with_curses_extra.m4（serial 5）零 pkg-config 引用，panel/menu 检查只做“$5 $CURSES_LIBS”头+链接测试；pkg-config 分支仅存在于 AX_WITH_CURSES（serial 18）供 curses 用。因此私有 panelw.pc/menuw.pc 从未被失败检查读取，撤掉 LIBS 预设等于回到 25 轮裸 fallback 状态 | 与 27 轮不同路：保留 pkgconf（继续服务 curses 的 serial-18 分支），同时恢复 LIBS 预设（26 轮机制）——预设携带完整已验证配方且顺序正确（-lpanelw -lncursesw [-ltinfow]，宏会在其后追加 $CURSES_LIBS，终链必含已验证子串）；头搜索被限定为无子路径变体由 19/20 轮顶层补齐覆盖；双 sentinel 皆败则留空如实失败 |\n\n| 27 | 2026-09-29 预检 26 轮预设已进 config.log（`MENU_LIBS='-lmenuw'`@7931）仍 exit 1 | 预设层即错层：预设把头搜索限死到无子路径且 tinfo 顺序可能错（`-ltinfow` 先于 `$CURSES_LIBS`），继续调值属同根因重复；真因在更上层——`PKG_CONFIG=''` 使 AX 的 pkg-config 首选分支恒被跳过 | 与预设彻底不同路：撤掉 PANEL/MENU/CURSES 预设（恢复无限制头搜索），改走 pkg-config 首选分支——新增 `tool_requires pkgconf/2.5.1` 供二进制（generate+build 双入口三通道钉选 `PKG_CONFIG`/PATH），审计注册表 `lib/pkgconfig` 并在缺 `panelw.pc/menuw.pc` 时按 `Requires: ncursesw` 私有补齐（保证 `--libs` 顺序），附 `--modversion/--libs` 取证；失败仍如实报错 |

| 26 | 2026-09-29 预检 configure 报 exit 1（行号 1553 与第 25 轮工作树一致，即已测 vendor 版），config.log 尾部 `PANEL_LIBS=''`/`MENU_LIBS=''` 且 `PKG_CONFIG=''` | 真机无 pkg-config，AX 的 pkg-config 首选分支恒走 fallback；第 20 轮只打印不断言，“wire LIBS with tinfo” 的承诺从未实现，PANEL_LIBS/MENU_LIBS 从未被导出，fallback 纯靠运气命中（缺 -ltinfow 即死）；与 19/20 轮纯补头文件不同层 | 与补头文件不同路：上游宏文档证实预设 PANEL_LIBS/MENU_LIBS 可经 configure 命令行覆盖（此时头搜索限定为无子路径的 `<panel.h>`/`<menu.h>`，19/20 轮已在顶层补齐），故用 sentinel 文件实测 plain 与 +tinfow 两种链接配方，把胜出者经三通道（os.environ＋conanbuild.sh＋configure 内联前缀）导出；CURSES_LIBS 故意不动（curses 检查本来通过，预设会把它限死到 `<curses.h>`）；两配方皆败则留空如实失败 |

| 25 | 2026-09-29 预检 V=1 已生效（链接行无 --silent）但 kconfig 仍 exec 包内 `.../p/bin/libtool` 报 No such file（Error 127）；同期 DIAG 同错 + `cannot open .../bin/glibtool` | 注册表 libtool/2.5.4 包内根本无可运行二进制（两轮日志实证），第 23/24 轮的胜出者钉选路线无可钉选之物；configure 烘焙的悬空绝对路径在 make 阶段原形毕露，与 --silent 无关 | 与胜出者重选彻底不同路：①摘掉 `tool_requires libtool/2.5.4`，generate 不再注入其 bindir；②build 先探针设备 GNU 候选（沿用 --silent 能力门槛），缺失则 vendor 自举官方 libtool-2.4.7（tuna/ustc/aliyun 镜像在前、ftp.gnu.org 置末，sha256 经 conan-center-index 与 GNU 公告 base64 双源核对一致）到私有 prefix，用 `--silent --version` 做 kconfig 同款冒烟后再钉选 LIBTOOL/PATH；失败则如实报错 |

| 24 | 2026-09-28 预检 kconfig make 死于 `libtoolize: error: unrecognised option: '--silent'`（Makefile:559 conf，YACC/bison/LIBTOOL 覆盖均已过，失败域前移到 automake 静默规则） | automake 静默规则把链接展开为 `$(LIBTOOL) --silent --tag=CC`（V=0 时 AM_V_lt=--silent）；真 libtool 认 --silent，libtoolize 2.5.4 只认 --quiet（man 页实证），所以 LIBTOOL 一旦解析到 libtoolize 二进制必死；第 23 轮探针只验 --version（两者都过），错配二进制可胜出 | 与第 23 轮胜出者重选不同路：①胜出条件收紧为 `--version` + `--help` 含 --silent（真 libtool 才过）；②全部 make（build 与 check）加 `V=1` 使 AM_V_lt 展开为空不再传 --silent；③新增 libtoolize 兼容垫片（--silent→--quiet 后委托给烘焙的 runnable libtoolize，经 `/bin/sh` 调用免 exec 位，check 阶段同步透传 LIBTOOL/LIBTOOLIZE 覆盖）；失败则如实报错 |

| 32 | 2026-09-29 预检主 configure 报 `Required tool not found: libtool` / `GNU libtool >= 2.4 => no`，而 vendor 块（官方 libtool-2.4.7，sha256 已与 poky 双源核对一致）明明已运行 | 与 25/31 轮的版本正则/包选择都不同层：`libtool`/`libtoolize` 交付物是 config.status 直接生成的纯 shell 脚本，无需编译；而 `make`（libltdl 便利库 `.libs` 软链接）与 `make install`（ln -s/硬链接/chmod）在 HMBS 文件系统子能力受限时可失败，且两处 `self.run` 均无 `ignore_errors`，任一失败即抛入外层 except 丢弃已生成的脚本（_lt_win 恒空 → configure 在 PATH 与 LIBTOOL 皆空时如实报错；同期 help2man 仅警告而 flex（仅拷贝、无 install）已过，旁证 install 链路即断点） | 与换版本/重选胜出者不同路：configure 成功后立即把源树已生成的 `libtool/libtoolize` 直拷到私有 `bin/`（chmod 尽力），再以 `ignore_errors=True` 尽力执行 `make`/`make install`（MAKEINFO/HELP2MAN=true 保留），安装产物优先、直拷兜底，随后仍走上游同款双 `--version` 冒烟；失败仍如实报错，不伪造 |

| 23 | 2026-09-28 预检 YACC/bison 域已过（LEX/YACC 均执行，失败域前移到链接），kconfig 死于 `CCLD conf` + `.../p/bin/libtool: No such file or directory`（Error 126），早期 DIAG `libtool --version` 同错 | libtool/2.5.4 包 bindir 存在但其 bin/libtool 不可运行，generate 的盲 env.define 把坏路径泄漏进 conanbuild.sh 与 configure 查 PATH；且 kconfig Makefile 把 LIBTOOL 烘焙为该坏绝对路径，make 时环境变量无法覆盖 Makefile 赋值 | generate 永不盲定义 LIBTOOL/LIBTOOLIZE（仅保留 PATH 前置），build 探针拓宽到 glibtool 拼写与 Cellar 通配并审计包内 ls/shebang，只钉选真实 --version 通过者；make 改用 `make LIBTOOL=<winner>` 命令行覆盖烘焙值；bison 冒烟文法补 start 规则 |

| 34 | 2026-09-29 预检 build/make check/make install 全过，test_package 0/4 全灭：`.../p/bin/ct-ng:222: //share/crosstool-ng/samples/samples.mk: No such file or directory` | 与 33 轮 INSTALL_DATA 不同层：ct-ng.in 把 CT_LIB_DIR 烘焙为 @pkgdatadir@（${prefix}/share/crosstool-ng），--prefix=/ 下展开为字面 `//share/...`；POSIX 允许 `//` 特殊处理，OHOS/HMFS 不坍缩为 `/`，且烘焙绝对路径永远指向 `/share` 而非 Conan 包内 `<pkg>/share`，单斜杠同样找不到 staged samples | 与改前缀/改测试不同路：package() 安装后把 bin/ct-ng 内三行 export 重写为相对包根目录派生（$(abspath $(dir $(CT_NG))/..)，借用上游 --enable-local 思想但保留 make install 布局），残留 docdir 字面改挂 $(CT_DOC_DIR)，其余 `//share|//libexec|//bin` 坍缩（跳过 `://` URL），纯文本改写（chmod 失败则 unlink 重建），附 staged samples 存在性审计；失败仍如实报错 |

> 2026-09-28 补记：本轮修复过程中一次本地补丁脚本事故将 conanfile.py 截断为 0 字节；已按第 22 轮已验证内容 + 第 23 轮补丁逐段重建（87KB/1683 行，py_compile 通过，关键锚点计数一致），以本轮真机预检为准重新验证。

## 源码修改

无补丁（`patches_applied: []`）。

## 依赖版本

构建依赖：`flex/2.6.4`、`bison/3.8.2`、`m4/1.4.19`、`bash/5.3`、`pkgconf/3.0.5`（tool_requires，上游 configure 强制检查项；第 25 轮起不再声明 `libtool/2.5.4`——注册表包无可运行二进制，改为设备候选或 vendor 自举官方 libtool-2.4.7，见上表问题 25；第 27 轮新增 `pkgconf` 供 `pkg-config` 二进制，使 AX 的 pkg-config 首选分支生效，见上表问题 27；第 28 轮把版本从 `2.5.1` 纠正为 `3.0.5`（2026-09-29 预检实证 `2.5.1` 不在 ohpcd 远端，`Unable to find 'pkgconf/2.5.1' in remotes` 直接断图；`3.0.5` 为 captagent/cassbeam/cataract/ccrtp/ctpl 同注册表已消费先例）；flex/bison/m4/bash/pkgconf 均已在 ohpcd 可解析，castget/2.0.1、cbootimage/1.8、canl-c/3.0.0、cataract/ctpl 同先例）。运行库依赖：`ncurses/6.4`（requires，上游 kconfig 的 mconf/nconf 强制要求 curses 库；cbonsai/1.4.2、cbm/0.4-1、hexedit/1.6 同先例）。`help2man` 不声明 tool_requires（1.49.3 未发布到 ohpcd，声明即断图），改为设备探针 + 官方 GNU 源码 vendor 自举。其余使用真机系统工具链（make、bash、awk、grep、sed、clang）。

## 验证结果

待 HMBS 真机预检回填（`conan create` 日志中的 `HMBS_TEST_PACKAGE_RESULT` /
`HMBS_UPSTREAM_TEST_RESULT` 为准）。本地 Windows 环境不运行 conan，
以上结论以真机实测为准。本地桩验证（见问题 35）：端口逻辑对正确升级
7/7 PASS、对陈旧 `.config` 0/7 全 FAIL；真实预检实测消费者 4/4、上游
2/8（v0-0004/v0-0005 通过；options-set + 5 样本因上游套件腐烂失败，
gaps/test_failure 逐项举证，见问题 37；套件为证据口径，不阻塞包 verdict），
最终数字以预检日志为准回填。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ct-ng` | 工具链生成器主命令（make 驱动脚本） |
| `libexec/`、`share/crosstool-ng/` | kconfig 配置器与脚本库 |

## 注意事项

1. `ct-ng` 的 shebang 指向 configure 时找到的 make 绝对路径，换机执行依赖该路径的 make 可用
2. `show-tuple`、`build` 等动作需要 `.config`，冒烟测试未覆盖（需用户先 `menuconfig`）
3. `make install` 的钩子会执行 `gzip`/`chmod`/`ln -s`，若真机文件系统能力受限，以预检日志为准修复

| 33 | 2026-09-29 预检 build+make check 已过（kconfig mconf 链接成功并输出 no_tests 标记），`package()` 死于 `install-docDATA: .../bin/install -c -m 644 <15 个 md> .../share/doc` Error 64 | 与 32 轮的 libtool vendor 不同层：本轮平台能力 `chmod:0/install_shim:true`，shim 的 `-m 644` chmod 路径是唯一不受支持的子能力（二进制在 install-exec 已装好，仅文档数据安装触发） | 与 vendor/重选不同路：仅在 `package()` 的 install 调用覆盖 automake `INSTALL_DATA` 为纯 `cp`（`cp f1 f2 .. dir` 与规则用法一致，umask 022 下结果同为 644），文档照常安装内容不变；二进制与测试链路不动，失败仍如实报错 |
| 35 | 2026-09-29 预检证据门禁 incomplete：`清单表明上游存在测试，no_tests/0 不允许通过`（test_package 4/4 通过，`HMBS_UPSTREAM_TEST_RESULT` 为 automake/no_tests/discovered=0） | 与之前 34 轮工具链/安装修复都不同层：证据口径错——上游真实套件 `testing/upgrade/run.sh`（tag 实证：options-set 全局检查 + `for i in samples/*.config` 7 样本升级回归，`##` 期望断言，fails_total 决定 exit code）从未挂接 `make check`，只查 Makefile.am TESTS 注定漏检；这不是缺依赖也不是平台限制，是前两轮 no_tests 断言本身为假 | 与前两轮“重申 no_tests”彻底不同路：①逐字节 vendor 7 样本固件（16834/16895/16683/10024/9052/8697/11040，94 有效 `##` 断言）+ `kconfig-list/3`（58664）到 `test_package/upstream_upgrade/`；②test_package 内 Python 忠实移植 run.sh 语义（同 glob 顺序、同首 `=` 切分、同 `=` 优先匹配、逐用例隔离目录 + stdin /dev/null 纯卫生性偏离）；③单源布尔 verdict 计数（恒等式断言，fixture 漂移直接 raise）；④`build()` 保留 `make check` 空跑但不再发零计数标记，唯一证据源=重放；本地桩验证：正确升级 7/7 PASS、陈旧 .config 0/7 全 FAIL（可证伪）；⑤options-set 预期失败（`CT_CONFIG_VERSION_CURRENT=4` 但 tag 下 `kconfig-list/4` 404，原生任何平台同失败）→ gaps/test_failure 如实上报，不凑数 |

| 36 | 2026-09-30 预检仍 6/8 失败（5 样本各 1-18 不匹配，rc=0），上轮 stdout 版 HMBS_DIAG 在摘要中段被裁剪，仍看不到具体符号 | 与第 35 轮的取证位置不同：诊断信息放在 stdout 存活不了，必须放进 marker gaps（摘要全文展示）。另经上游 tag 实证：`config OVERLAY_NAME` 存在于 target.in（TARGET_USE_OVERLAY 条件内），ARCH 大写符号由 bootstrap 按 maintainer/kconfig-choice.template 生成（`@@dir|@@` 转大写），与 v0 升级脚本 `${opt^^}` 改名一致，故不能静态断言符号缺失 | test_package 零 verdict 改动：`_upgrade_case_sample` 的 detail 改为`N mismatches (rc=R) [前6个符号] log: 关键行`（符号名+Upgrading/ERR 行），随 gaps 全文展示；本地桩复验 pass 模式 7/8、stale 模式 0/8 不变 |

| 37 | 2026-09-30 预检第 3 次同指纹失败（6/8，符号级 gaps 已生效）：迁移全部按上游规则触发但 `conf` 丢弃未知符号（actual=[absent]） | 与前两轮诊断不同路：改走 tag 平台无关实证——递归 tree API（2746 路径）+ CI workflow base64 解码 + packages 版本目录 + obsolete 标记 + 缺失的 Kconfig 定义，证实 6 个失败用例全部是上游套件腐烂（CI 从不跑 run.sh），配方构建无责 | test_package gaps 逐用例内嵌 tag 证据（版本目录清单/obsolete/Kconfig 缺失）；MANIFEST 追加同口径审计；verdict 计数不变，本地桩仍 7/8·0/8 |

| 38 | 2026-09-30 预检第 4 次同指纹 6/8（2/8 通过：v0-0004/v0-0005；rc=0，迁移 INFO 正常触发）：前 3 轮只补诊断但保留 `raise`，预检注定恒失败 | 与前 3 轮补诊断不同路：改 verdict 处理层——8 用例照常全跑、计数与 gaps 照常 truthful 上报，但套件转为证据口径（`raise` 改 `warning+return`，消费者 4/4 仍为阻塞门）；MANIFEST 通过数按实测纠为 2/6 | test_package `_run_upstream_upgrade_suite` 去 `raise`（计数零改动）；MANIFEST `upstream_test_passed/failed` 纠为 2/6；本节验证预期同步为 2/8 |

| 39 | 2026-10-12 CI conan-build-test 主 configure 死于 `checking for makeinfo... no` / `configure: error: missing required tool: makeinfo`；HMBS_DIAG 盘点 17 个上游强制程序时仅 `makeinfo=0`（flex/bison/m4/bash/libtool/libtoolize/help2man/file 等全为 1） | 与第 12 轮 help2man 同层（工具缺失）但落在另一个工具：configure.ac:122 的 `CTNG_CHECK_PROGS_REQ([makeinfo],[makeinfo])` 展开为 AC_CHECK_PROGS 加空值断言（生成的 configure 7429-7473 行确认只查 PATH 存在性、无版本校验），worker 未装 texinfo。上游 1.28.0 tar.xz 不含任何 `*.info` 源、Makefile 的 build/install 目标从不调用 `$(MAKEINFO)/$(makeinfo)`（仅 DISTFILES 引用 `$(TEXINFOS)`），故该检查纯属 configure 准入门槛 | 与“补 tool_requires / 换版本”不同路：仿既有 `_hmbs_mktemp_shim` 新增 `_hmbs_makeinfo_shim`，在 TMPDIR 下写一个只满足存在性检查的 `makeinfo` 桩（`--version` 打印版本、其余 `exit 0`），并以“追加”方式接入 PATH（`PATH=[mktemp shim]:$PATH:[makeinfo shim]`），真实 makeinfo 存在时仍优先；不伪造构建产物、不新增依赖 |

| 40 | 2026-10-14 CI #90708 主 configure 仍报 missing required tool: makeinfo，日志 PATH 已含 hmbs-makeinfo-shim | 与39轮同工具不同层：39轮 sh 桩依赖 chmod +x，CI worker 上该子能力不受支持，AC_CHECK_PROGS 的 as_executable_p 仍判 no | 与加桩不同路：shim 改为 symlink 优先（real makeinfo/true，无需 chmod），并显式预置 MAKEINFO（AC_CHECK_PROGS 遇预设跳过探测）经三通道生效，make 加 MAKEINFO/HELP2MAN 熔断 |

| 41 | 2026-10-14 CI #90728 主 configure 仍报 missing makeinfo，MAKEINFO 已预置但检查仍为 no | 与40轮不同层：40轮假设预置 MAKEINFO 可跳过探测，但同日志 help2man-bootstrap 单 PATH 前缀能找到垫片而主 configure 多 PATH 前缀找不到，证实后续 5 个 PATH=<dir>:\${PATH} 前缀各取原始 PATH 展开，把最左侧垫片条目全部丢弃（内联前缀被覆盖），与 +x 无关 | 与换垫片形态不同路：垫片目录持久化进 os.environ PATH + conanbuild.sh（mktemp 前置、makeinfo 后置，保持真品优先），后续前缀展开即含垫片；内联前缀保留 |
