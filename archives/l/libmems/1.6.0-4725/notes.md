# libmems 1.6.0-4725 适配笔记

## 基本信息

- 三方库：libmems（Mauve 项目 DNA 字符串匹配与比较基因组学库）
- 版本：1.6.0-4725（Debian 版本号 1.6.0+4725，Mauve SVN trunk r4725 快照）
- 上游仓库地址：http://sourceforge.net/p/mauve/code/HEAD/tree/libMems/trunk/
- 构建系统：Autotools（configure.ac + Makefile.am，无预生成 configure）
- 许可证：GPL-2.0-or-later（COPYING 为 GPLv2 全文，头文件声明 GPL）
- 申请人：gcw_6a3w2yXz，队伍：来都来了
- 状态：第四轮工作树（真机 compile：filesystem cached yes / program_options no 分裂探测修复待预检，manifest.yaml 状态暂标 failed 占位）

## 源码来源说明（PF7 例外）

上游本身不发布版本化 tarball（SVN trunk 直接开发），版本化快照由 Debian Med 团队发布，
本配方消费的 `libmems_1.6.0+4725.orig.tar.xz`（236796 字节，
sha256=67265e1eb1b85a04533be431b906cc8d4773c799fb1a7809b346209380c41e91，
取自 Debian .dsc 的 Checksums-Sha256）即 canonical 的上游版本源。
conandata.yml 使用 Ubuntu 官方归档镜像的 https 地址。因不存在上游 release 资产，
此处的 distro-pool URL 属于“官方托管例外”，随 PR 说明并请求显式跳过 PF7 源 URL 闸。
vendored 的 libgenome/libmuscle 同样使用 Debian 官方池 https 地址（与本仓已验证的
libgenome 配方同源），sha256 与各自 .dsc 一致，未为镜像改校验值。

## 编译环境（计划）

- 目标：HarmonyOS 6.0 / aarch64（armv8），clang 15，libc++
- 构建目录：`archives/l/libmems/1.6.0-4725/`
- 产物：libMems-1.6（libtool `-version-info 1:0:0`），头文件位于 `include/libMems-1.6/libMems/`，
  pkg-config 文件 `libMems-1.6.pc`，另合包 vendored 静态归档与头文件/.pc

## 编译步骤（配方逻辑）

1. `source()` 仅 `get()` 主源码（strip_root=True）；vendored 在 `build()` 内按需获取，
   避免依赖图解析阶段引用未发布远端包（L0i/R36 硬门禁）。
2. `build_requirements()` 声明 autoconf/2.72、automake/1.18、libtool/2.5.4.1、perl/5.42.2
  （与本仓 libgenome 已验证版本一致，制品仓已有发布证据）。
3. `build()` 内依次静态构建 vendored 到 `build_folder/private` 前缀：
   libgenome（先复刻 gnDefs.cpp abs 守卫补丁）→ libmuscle → 主 configure
  （`PKG_CONFIG_PATH/CPPFLAGS/LDFLAGS` 指向私有前缀，`--disable-shared` 静态默认）。
   三者均执行与各自 autogen.sh 相同的 `autoreconf --force --install -I config -I m4`，
   并在生成后给 config.guess 补 HarmonyOS 映射（复用 libgenome 已验证 stanza）。
4. `AutotoolsToolchain` 配置：`--disable-dependency-tracking`，静态默认时
   `--disable-shared --enable-static`。
5. `autotools.configure()` + `autotools.make(-j1)`，`autotools.install()` 后合入私有前缀的
   `include/*.a/*.pc`（.pc prefix 改写为 `${pcfiledir}/../..`），删除 `*.la` 与 `share/`，
   拷贝 COPYING 到 licenses。

E002（OHOS /tmp 只读）：generate/build/test 全链路注入可写 TMPDIR，
优先复用 hmbs 注入的 `HMBS_TMPDIR/TMPDIR/TMP/TEMP`。
R49：vendored 注入目标为 build_folder 私有目录，不污染共享 /usr/local。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案/状态 |
|---|------|------|---------------|
| 1 | 真机 `conan create` 在依赖图解析失败：`ERROR: Package 'libgenome/1.3.1' not resolved: Unable to find in remotes`（2026-10-14 预检，compile 阶段） | 配方 `requirements()` 直引未发布远端包 libgenome/1.3.1（libmuscle/1.0.0 同理）；ohpcd 无该版本，L0i/R36 硬门禁注定失败 | 本轮按聚合经验 #1 改为配方内私有静态子构建：删除远端 requires，conandata.yml `vendored` 新增官方 Debian 池源码（sha 不变），build() 内 get+静态构建到私有 prefix 并合包；package_info 捆绑 `Mems-1.6/Genome-1.3/MUSCLE-3.7`；待真机复检验证 |
| 2 | 快照无预生成 configure，需 autoreconf | 上游发布流程如此（仅 configure.ac + autogen.sh） | build() 内幂等执行 autoreconf；tool_requires 补齐 autoconf/automake/libtool/perl（版本与 libgenome 已验证一致） |
| 3 | 上游无任何测试套件 | historical：注释掉的 TestSML 草稿依赖 wx，从未接线 | 不伪造 make check；test_package/MANIFEST.yml 做 no_tests 显式审计，test() 每轮复发 no_tests 标记 |
| 4 | 对齐核心 API 的消费者测试需要 libGenome 头文件 | Interval.h/Match.h 等全部包含 libGenome/gnClone.h | 消费者测试仍选用零依赖的 twister.h C API（含 MT19937 公开参考向量断言）；合包后主库已含 genome/muscle 静态符号，twister 链接不受影响；依赖补齐后可扩展覆盖 MemHash 等核心类 |
| 5 | vendored libgenome 在 OHOS libc++ 下 `abs(int64)` 冲突 | 全局 `int64 abs(int64)` 与 libc++ `abs(long long) noexcept` 冲突（clang 15） | 复刻本仓 libgenome 0003 补丁逻辑：仅 legacy 编译器保留该定义（`__GNUG__<=2/__INTEL_COMPILER/_MSC_VER` 守卫）；测试类补丁 0001/0002 不复刻（私有依赖不跑其 check） |
| 6 | config.guess 不识别 HarmonyOS | 上游生成的 config.guess 无 HarmonyOS case | 复刻本仓 libgenome 已验证 stanza：`*:HarmonyOS:*:*` → `$UNAME_MACHINE-unknown-linux-ohos`；三份源码（genome/muscle/main）autoreconf 后均补 |
| 7 | 真机 `autoreconf` 在 `Cwd.pm line 82` 崩溃：`Cwd.so: Perl_my_cxt_init: symbol not found`（2026-10-14 预检，compile 阶段，vendored libgenome 自举时） | conanbuild 的 `PERL5LIB` 把 Conan perl/5.42.2 的 XS 目录暴露给 HNP 系统 `autoreconf`（`/data/service/hnp/bin/autoreconf`），宿主 perl 加载错 ABI 的 `Cwd.so`；仅设 `PERL` 不够 | 复刻本仓已验证 libgenome E8212 隔离逻辑：`_automake_entrypoints()` 取宿主 perl（拒绝 Conan perl）、显式调用 Autoconf 包内 `bin/autoreconf`、`PERL5LIB` 仅限 automake/autoconf 纯 Perl share 目录、aclocal/automake 走宿主 perl wrapper 保留 `--automake-acdir/--system-acdir/--libdir` 重定位；三份源码共用；待真机复检验证 |
| 8 | 真机 `./configure` 启动即刷屏 `shell-init/job-working-directory: getcwd: cannot access parent directories`（errno 五花八门）后 `configure: error: working directory cannot be determined`（2026-10-14 预检，compile 阶段，vendored libgenome） | 与 knowledge/drafts/cvsgraph-1.7.0-hnp-bash-getcwd-shell-probe 逐字同征：`/data/service/hnp/bin/bash` 在 conan 构建缓存 HMDFS 深路径下 getcwd 损坏，同一目录 `/system/bin/sh`（toybox）干净；`self.run("./configure...")` 经 hnp bash 启动且未固定 CONFIG_SHELL，configure 内 pwd 校验直接中止 | 复用 cvsgraph 真机实证修复：三份 configure（vendored x2 + 主）OHOS 下一律显式 `CONFIG_SHELL=<clean-sh> <clean-sh> <configure> ...` 并同步固定 CONFIG_SHELL/SHELL（generate+build 双链路），附带 `umask 077→022`（fcrackzip/cvsgraph 实证）防下一阶段 mktemp 失败；待真机复检验证 |
| 9 | 真机 vendored libgenome 编译 `gnDefs.cpp:8:2: error: unterminated conditional directive`（2026-10-14 预检，compile 阶段） | 本配方 `_fix_vendored_genome_portability` 用精确字面 `"\treturn...` 匹配函数尾，但文件 return 行为 `" \treturn..."`（前导空格，见本仓 0003 补丁上下文），`#endif` 从未写入，只剩无收尾的 `#if` | 改为空白容忍的正则整体匹配函数体并一次性写入 `#if/#endif`，`#endif` 缺失即 fail-closed 抛错，有 guard 无 endif 的复用缓存则自愈补 `#endif`；已过编译（本轮日志证实 libGenome-1.3.a 链接成功） |
| 10 | 真机 vendored `make install` 在批量头安装 `install-library_includeHEADERS] Error 64`（2026-10-14 预检，compile 阶段；lib 本体已链接成功） | HMBS 注入的 install shim 仅接受单文件双参调用，automake 的 `install -c -m 644 f1..fN dir/` 批量安装直接 EX_USAGE 64（E596/openfst、tnftpd、libnih 同征）；与源码无关 | 复用本仓 cxxtools 已验证形态：build 内写 cp/mkdir/chmod 容错 shim，configure 生成 Makefile 后把 `INSTALL = .../install` 重定向到 shim（INSTALL_DATA/PROGRAM 经 ${INSTALL} 自动重算，不经 make 命令行传参）；vendored 两次 `make install` 与主 `package()` 均走同一闸门；**已验证有效**（本轮日志越过 libgenome 安装进入 libmuscle 自举） |
| 12 | 真机 vendored libmuscle configure 完成后 SSH 传输中断：\`Connection to 47.122.125.180 closed by remote host\`（2026-10-15 预检，compile 阶段；日志无任何编译错误，libgenome 已链接安装成功） | 日志无编译器报错，中断点在 \`configure: creating ./config.status\` 之后、libmuscle make 之前；上一轮单作业单线程降载（MAKEFLAGS=-j1/XZ_OPT=-T1）已在位仍复现，故非单纯派生内存不足，而是长串行三 autotools 构建窗口内传输失稳叠加未来时间戳与 muscle 程序链接两处可缩减工作量 | 本轮改走工作量缩减路线（与上一轮降载不同）：新增 _normalize_mtimes 用 os.utime 将同步未来 skew（约0.65s）钳回 now，主源码与 vendored 每次构建前均执行；vendored libmuscle 改为命令行 bin_PROGRAMS= 空集的 lib-only 构建安装（静态库仍预建，.pc/头文件照常安装，不跳过任何 check 目标），缩短最重单 fork 与整体串行窗口；待真机复检验证 |
| 11 || 11 | 真机 vendored libmuscle `make -j1` 报 `No rule to make target '../libMUSCLE/libMUSCLE-3.7.la', needed by 'muscle'`（2026-10-15 预检，compile 阶段，本轮聚焦；在 `src/libMUSCLE` 内） | 该目录内 `../libMUSCLE/` 是自引用，但 make 按字面匹配目标，程序无法触发同 Makefile 内真正的 `libMUSCLE-3.7.la` 规则，仅文件已存在时可链接；与 libnfc-tools `../gcutter/libgcutter.la` 同族（依赖顺序问题） | 在 `_build_vendored` 内对 libmuscle 先显式 `make -C libMUSCLE libMUSCLE-3.7.la -j1` 再全量 `make -j1`，保留上游全部目标（含 `muscle` 程序）不删减；探针命中精确残留引用才动作，否则 fail-open 交由正常 make 报错；待真机复检验证 |
| 13 | 真机 vendored libgenome 自举 `.../autoconf/p/bin/autoreconf[2]: can't fork - try again`（2026-10-15 预检，compile 阶段，`_ensure_autoreconf` 内） | 该路径是 Conan 可重定位 shell  wrapper（sh 报错格式 `file[line]:`），非 perl 实体；经 invoking shell fork+exec 才起真实 perl，在单槽真机瞬时进程/内存压力下多一层 fork 即 EAGAIN；且此前经 wrapper shebang 启动，未显式固定 TMPDIR/SHELL | 本轮最小适配：`_automake_entrypoints` 优先取 `.autoreconf-real` 等真实 payload 并一律以宿主 perl 直接执行（去 wrapper fork 层，与 aclocal/automake 隔离同族），`_ensure_autoreconf` 显式固定 TMPDIR/SHELL/CONFIG_SHELL（generate/build 双链路一致）并加 3 次 backoff 重试（确定性错误连败 3 次原文上抛，不掩盖；瞬时 EAGAIN 给第二次机会）；不跳过任何测试目标；待真机复检验证 |
| 14 | 真机主 configure 报 `checking for Boost headers version >= 1.34.0... no` / `configure: error: cannot find Boost headers version >= 1.34.0`（2026-10-15 预检，compile 阶段；vendored genome/muscle 均已链入安装，主树自举成功） | 配方无任何 Boost 供给：requirements() 为空，主 configure 的 AX_BOOST_BASE 在系统路径（/usr 等）找不到 boost/version.hpp。属缺依赖（missing_dependency），按门禁必须补齐再测，不得豁免 | 本轮补远端 requires `boost/1.91.0.1.1`（已发布先例 abiword-plugin-sdw/bali-phy/ciftilib；含 filesystem/iostreams/program_options 编译组件，覆盖 configure.ac 隐含检查），主 configure 新增 `--with-boost/--with-boost-libdir` + CPPFLAGS/LDFLAGS 指向包目录（含 BOOST_ROOT），vendored 构建不动；已验证推进（头检查已过，进入下一检查） |
| 15 | 真机主 configure 报 boost/system/error_code.hpp yes 后 Boost system library no / cannot find the flags to link with Boost system（2026-10-15 第二轮，头检查已过） | 版本错配而非缺包：Boost.System 自 1.69 起为纯头库，boost/1.91.0.1.1 无 libboost_system 二进制，而 AX_BOOST_SYSTEM 仍链 -lboost_system | 本轮在 build_folder 隔离目录用 ar 物化空 libboost_system.a（归档头校验，fail-closed），-L 注入主 configure；隔离目录不进 package 合包；待真机复检验证 |
| 16 | 真机主构建 `make: *** No targets specified and no makefile found. Stop.`（2026-10-15 预检，compile 阶段，本轮聚焦；`autotools.make(args=["-j1"])`，line 873） | 主树 OHOS 下经 `_run_configure_safe` 在 source_folder 内执行 configure（Makefile 生成在 source_folder），而 `Autotools.make/install` 默认在 build_folder 执行空目录构建；vendored 因全程 `self.run(..., cwd=src_dir)` 未受影响 | 本轮最小适配：OHOS 主构建改显式 `self.run("make -j1", cwd=source_folder)`，package() 按 Makefile 位置分流（source_folder 有 Makefile 则显式 `make install DESTDIR=package_folder`，否则沿用 helper）；不跳过任何测试目标；**已验证有效**（本轮真机越过该错误进入主编译） |
| 17 | 真机主编译 `Files.h:82 no member named 'branch_path' / :86 no member named 'leaf'`（2026-10-16 预检，compile 阶段，本轮聚焦；`RepeatHash.lo`） | 上游 r4725 使用 Boost.Filesystem v2 API（`branch_path()/leaf()`），已在 Boost 1.48+ 移除；已发布 boost/1.91.0.1.1 仅提供 v3，非缺包 | 本轮新增 `_fix_boost_filesystem_v3` 在 build() 内对主源码树幂等改写 `.branch_path()->.parent_path()`、`.leaf()->.filename()`（`.string()` 后缀在 v3 仍合法）；无平台宏，不提交 .patch；待真机复检验证 |
| 18 | 真机主编译 `CompactGappedAlignment.h:811 error: 'swap<mems::CompactGappedAlignment<>>' is missing exception specification 'noexcept(...)'`（2026-10-16 预检，compile 阶段，本轮聚焦；`FileSML.lo` 等多个 libMems TU） | 工具链严格性而非缺包：libc++ 主模板 `std::swap` 带条件 noexcept，Clang 拒绝无异常规格的显式特化；2009 年上游头文件早于条件 noexcept，无平台宏可解 | 本轮新增 `_fix_libcxx_swap_noexcept` 在 build() 内对主源码树幂等追加诊断要求的 spec（`std::`/`mems::` 限定保证任意作用域可解析，声明/定义均覆盖，已用合成样例验证匹配+幂等）；未命中模式即 fail-closed 抛错；待真机复检验证 |
| 19 | 真机主编译 `GreedyBreakpointElimination.h:10 fatal error: 'boost/multi_array.hpp' file not found`（2026-10-16 预检，compile 阶段，本轮聚焦；`FileSML.lo`） | 缺依赖的包形态问题：主 configure 的 Boost 头探测已过（同一 -I 下 version.hpp 可见），说明该头在 boost/1.91.0.1.1 包内确实缺失——该配方仅安装 `BOOST_INCLUDE_LIBRARIES` 头文件闭包（filesystem/graph/iostreams/multiprecision/program_options/regex/thread），闭包外头文件一律缺失（arg_router 已实证 process 头缺失同类问题） | 本轮改走与前两轮不同的路线：不再沿用 1.91.x，requires 改为 boost/1.85.0（整棵 `boost/*` 头文件 + 三个编译组件，arg_router/unilog 已验证远端 OHOS binary；其传递 zlib/1.3.1 同属已发布族）；主 configure 的 -I/-L 改为 host 全依赖收集（含传递 zlib 及 `-lz` 供 iostreams 探测）；`_fix_boost_filesystem_v3` 与 Boost.System 空归档 stub 保留（1.85 同为 v3，system 同为头-only）；待真机复检验证 |

| 20 | main configure boost/program_options.hpp no (2026-10-16 preflight compile; filesystem probe same run cached yes) | flag aggregation gap, not missing remote: top-level cpp_info missed boost_headers component dirs plus duplicate-CPPFLAGS logic risked incomplete -I for AC_CHECK_HEADER | reworked to component-aware _dep_dirs (top-level plus components plus include/lib fallback), dict-based single CPPFLAGS/LDFLAGS exported to both os.environ and configure args, fail-closed verify include/boost/program_options.hpp exists with listing on miss;待真机复检验证 |
| 21 | preflight compile `exec request failed on channel 0`, discovered/executed 0, no compiler error (2026-10-16, 2nd same fingerprint; prior round was mtime-clamp + libmuscle lib-only work reduction) | SSH transport rejected the exec (sshd-side fork/resource pressure on the single-slot device), not a recipe compile error; prior -j1/XZ_OPT only lived in build() os.environ so autoreconf/configure child forks could miss it, and stale task-tmp files from interrupted runs accumulate | different route from prior round, no test scope change: (1) generate() now defines MAKEFLAGS=-j1 / XZ_OPT=-T1 via toolchain env set-if-absent so every child fork inherits it; (2) build() start cleans task-private tmpdir contents (contents only, fail-open) and logs it; pending preflight verification |
| 22 | 真机主 configure 同轮分裂：`Boost filesystem ... (cached) yes` 但 `boost/program_options.hpp... no`（2026-10-16 预检，compile 阶段，本轮聚焦；fail-closed 头验证已过） | 双因：(a) 复用槽残留 config.cache 使 filesystem 走旧缓存（boost 1.91.x 时代 -I），program_options 走新 -I 实测，口径分裂而非缺包；(b) AX_BOOST_* 用 BOOST_CPPFLAGS/BOOST_LDFLAGS 而普通 AC_CHECK_HEADER 用 CPPFLAGS/LDFLAGS，仅设后者时两类探测看到的 -I 不一致 | 与上一轮“只改 flag 聚合”不同路线：(1) `_run_configure_safe` 前删 config.cache/config.status/config.log/autom4te.cache（三树共用，fail-open）；(2) 同一 flag 集同时以 CPPFLAGS 与 BOOST_CPPFLAGS（LDFLAGS 与 BOOST_LDFLAGS）经 configure 参数 + os.environ 双通道导出；(3) configure 失败时转储 config.log 尾部 + program_options/BOOST_CPPFLAGS 命中行供下轮定因；不跳过任何测试目标；待真机复检验证 |

## 源码修改

无主源码补丁（patches_applied 为空）。vendored genome 的 gnDefs.cpp 守卫与三份
config.guess 映射均在 build() 内对构建目录副本执行，不提交 .patch 文件；
configure 阶段的其余平台适配待真机本轮日志再按证据添加。

## 依赖版本

- 远端 requires（L0i/R36 合规）：boost/1.85.0（整棵 headers + filesystem/iostreams/program_options
  编译组件，arg_router/unilog 先例，远端 OHOS binary 已验证；1.91.x 系仅装头文件闭包，
  缺 multi_array 等闭包外头文件，已弃用）；vendored 私有静态：
  libgenome 1.3.11+svn20110227.4616（满足 configure.ac `libGenome-1.3 >= 1.3.1` 下限的新版，
  复用本仓已验证 OHOS 补丁）、libmuscle 3.7+4565（满足 `libMUSCLE-3.7 >= 1.0.0`）。
- Boost 接线：主 configure 经 `--with-boost/--with-boost-libdir` + CPPFLAGS/LDFLAGS
  指向包目录（AX_BOOST_BASE 语义，复用 abiword-plugin-sdw/arg_router 的 dependencies 路径模式），
  BOOST_ROOT 同步注入；-I/-L 按 host 全依赖收集（boost + 传递 zlib，LDFLAGS 追加 `-lz`
  供 iostreams 探测）；vendored 两依赖不消费 Boost，不注入。

## 验证结果

第二轮工作树，待 HMBS 后台预检复跑 `conan create`：

- 上游测试：无（no_tests，审计见 test_package/MANIFEST.yml）
- 新增测试：test_mems.c，设计 4 项 CHECK-OK 断言（RESULT 行解析，单确定性数据源）
- HMBS 标记：`HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT` 均由
  test_package/test() 在真机实际执行后输出，数字来自测试二进制输出解析

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 主配方（Autotools，R26/R32/R33/R49 合规，vendored 私有合包） |
| conandata.yml | 主源码 + vendored 官方源码 URL/sha256 |
| manifest.yaml | 版本元数据（状态占位 failed，待真机更新；dependencies 为空，vendored 另列） |
| test_package/conanfile.py | 消费者测试入口（含双标记输出） |
| test_package/CMakeLists.txt | 消费者构建 |
| test_package/test_mems.c | 真实调用 libMems API 的测试源码（4 断言） |
| test_package/MANIFEST.yml | no_tests 显式审计 + 总数声明 |

## 注意事项

1. manifest.yaml 的 `status: failed` 是未验证占位，绝非“已失败”的伪装，
   真机通过后更新为 built（验证通过未上传）或 published 流程状态。
2. 产物库名为 `Mems-1.6`（非 `mems`），`package_info` 已按 libtool 归档名与
   `libMems-1.6.pc` 对齐并捆绑 vendored `Genome-1.3/MUSCLE-3.7`；头文件目录含
   `include/libMems-1.6` 及 vendored 对应目录。
3. 本机未运行 conan（规程要求真机验证）；Windows 侧仅做源码审计与文件编写。
| 24 | 真机主编译 Aligner.lo 报 algebras.h:190/209/216/229/236 error: ISO C++17 does not allow register storage class specifier（2026-10-17 预检，compile 阶段，本轮聚焦；3 warnings and 5 errors） | 语言移除而非缺包：register 在 C++11 弃用、C++17 移除；上游 r4725（2009 年）仍拼写 register BFloat/register double，仅为优化提示 | 新增 _fix_register_keyword 在 build() 内对主源码树 C/C++ 文件幂等删除词界 register+空白（保留语义），与 filesystem/swap 修复同链路；不降 std、不跳过任何测试目标；待真机复检验证 |
| 23 | preflight compile `Boost filesystem ... (cached) yes` + `boost/program_options.hpp... no` (2026-10-16, same fingerprint 2nd time; config.log shows compiler DID open options_description.hpp then failed at :16, fail-closed header verify passed) + local conanfile.py truncated at 1036 lines (unclosed try, no package()/package_info()) after a truncated tool-output restore | Triple cause, all different from prior flag-aggregation/file-deletion rounds: (a) local file truncated mid-try by restoring from a truncated read cache; (b) stale autoconf cache survived file deletion (cache file lives elsewhere); (c) flag set carried only -I/-L, never -D: boost/1.85.0 exports BOOST_SP_NO_PTHREAD_SETCANCELSTATE via boost_headers (musl has no pthread_setcancelstate) and the AC_CHECK_HEADER test compiles boost headers through shared_ptr chain, so the probe compile fails and AX reports it as header-not-found while -I is actually correct | New route: (1) rebuilt missing tail from the pre-truncation __pycache__ pyc (disassembled build/package/package_info, py_compile verified, stale pyc removed); (2) _dep_dirs now returns (incs, libs, defs) incl. top-level + component defines, merged as -D into CPPFLAGS and BOOST_CPPFLAGS (args + environ dual channel); (3) --cache-file=/dev/null in _run_configure_safe + OHOS args (file deletion kept); (4) quoted multi-flag VAR=... args entries; inner-header diagnostics (options_description.hpp:16) + full error-window config.log dump; package()/package_info() restored (Mems-1.6/Genome-1.3/MUSCLE-3.7); no test scope changed; pending preflight verification |
| 25 | 真机主编译 ProgressiveAligner.lo 报 ProgressiveAligner.cpp:1602 error: no matching member function for call to push_back（2026-10-17 预检，compile 阶段，本轮聚焦；3 warnings and 1 error） | tuple 库错配而非缺包：cga_list 为 vector<boost::tuples::tuple<...>>，实参为无限定 make_tuple 产生的 std::tuple，libc++ 严格拒绝转换 | 新增 _fix_boost_tuple_pushback 在 build() 内把各 <vec>.push_back(make_tuple( 改写为 <vec>.push_back(decltype(<vec>)::value_type(，按容器自身 value_type 直接构造（boost/std 通用，不猜命名空间），幂等，fail-open；不跳过任何测试目标；待真机复检验证 |
| 26 | CI build 97047 vendored libgenome bootstrap autom4te cannot-fork, all 3 backoff retries failed consecutively (2026-10-17 compile, focus of this round; same recipe passed true-machine preflight) | Nested fork layer, not a deterministic error: top-level autoreconf already runs via host-perl direct exec, but overlay aclocal resolves autom4te by bare name via PATH and hits the Conan relocatable shell wrapper, costing one extra fork+exec per nested tool (EAGAIN under shared CI worker pressure); retry only waits, it does not lower per-attempt fork cost | Same direct-exec family one level down: _automake_entrypoints now shadows autom4te/autoconf/autoheader/autoscan/autoupdate/ifnames with host-perl direct-exec wrappers (fail-closed when autom4te payload missing, fail-open for the rest per installed revision); _ensure_autoreconf resolves them via PATH prepend plus explicit AUTOCONF/AUTOHEADER/AUTOM4TE env; 3-retry semantics unchanged; no test target skipped; pending CI re-verification |
| 27 | 真机 vendored libmuscle configure 中 `Connection to 47.122.125.180 closed by remote host`（2026-10-17 预检，compile 阶段，本轮聚焦；libgenome 已链接安装、libmuscle 自举成功后 configure 在 `checking for objdir... .libs` 后掉线，无编译器错误）+ CI 97047 同配方 vendored libgenome 自举 `autom4te[2]: can't fork` 连败 3 次（2026-10-17 compile） | 双端同因：单槽真机/共享 CI Worker 瞬时 exec 通道资源压力（EAGAIN/sshd 掉线），非确定性 configure.ac 错误；autoreconf 已有重试但 configure 为单次直跑，一次瞬时抖动即葬送整个三 autotools 串行构建；且 CI 侧 3 次*10s 退避不足以熬过持续压力 | 与上一轮“降 fork 层数/换 wrapper 形态”不同路线：不改 wrapper 形态（保留 shell-wrapper 的 pkgdatadir 重定位，避开 m4sugar 回归），改走韧性路线——(1) `_run_configure_safe` 新增 3 次*15s 退避重试（确定性错误连败原文上抛，仅终败时转储 config.log）；(2) `_ensure_autoreconf` 由 3 次扩至 5 次、退避 10s*attempt 扩至 20s*attempt（CI 持续压力需更长窗口）；m4/1.4.19 显式 tool_requires 保留；不跳过任何测试目标；待真机+CI 复检验证 |
