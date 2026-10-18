# gfbgraph 0.2.5 OHOS 适配记录

- 上游：https://gitlab.gnome.org/GNOME/libgfbgraph，版本 0.2.5（2021-10-30，含 CVE-2021-39358 修复）。
- 源码：https://download.gnome.org/sources/gfbgraph/0.2/gfbgraph-0.2.5.tar.xz，
  sha256 `9cb381b3f78ba1136df97af3f06e3b11dcc2ab339ac08f74eda0f8057d6603e3`
  （GNOME ftp-release-list 官方公布）。
- 构建系统：autotools（tarball 自带 configure，无需 autoreconf）。
- 依赖：glib + json-glib + librest + libsoup + gnome-online-accounts。
  制品仓现状迫使移植：librest/0.10.2 为 rest-1.0/libsoup3 世代（soup2=false），
  不提供 rest-0.7.pc；soup2 与 soup3 不可同进程共存（gnome-recipes 先例）。
  本配方整体移植到 rest-1.0 + libsoup-3.0：
  configure.ac / libgfbgraph.pc.in / GIR includes 改名；
  photo 下载 SoupRequester 改 SoupSession send；
  authorizer SoupURI 改 GUri 重建 query；
  tests teardown send_message 改 send_and_read。
  RestProxy/RestProxyCall 在两代间同名同参，Graph 调用代码零改动。
- 配置：`--disable-introspection --disable-gtk-doc`（OHOS worker 无 g-ir-scanner）。
  config.guess 运行时补 HarmonyOS 分支（E160）。
- 上游测试：tests/Makefile.am `TESTS = gtestutils autoptr`，共 2 个程序。
  gtestutils 的 Facebook 在线用例被上游 `#if 0` 禁用（需 credentials.ini），
  空跑退出 0；autoptr 为 4 个纯 GObject 构造用例。`make check` 在 build() 内
  真实执行，解析 tests/test-suite.log 的 `# TOTAL/# PASS/# FAIL/# SKIP`，
  输出 HMBS_UPSTREAM_TEST_RESULT（framework=autotools）。
- test_package：test_gfbgraph.c 离线构造 album/node/photo/user/simple-authorizer
  各 1 项，共 5 项检查；CMakeDeps 链接 gfbgraph::gfbgraph；输出
  HMBS_TEST_PACKAGE_RESULT（discovered=5/passedCount=5）。
- 适配路径：路径 C（高难度挑战）。 rest-0.7 不可用时的 soup3 整体移植，
  涉及网络库代际迁移与 GUri/SoupSession API 重写。
- 2026-10-16 预检链式阻塞记录（同 fingerprint 第 3 轮，换策略族）：
  前两轮 RREV 固定已先后解决 libffi、sqlite3 的 conancenter 影子配方问题；
  本轮阻塞转移到 libgoa/3.58.1 的 meson 源码构建：
  `Unknown compiler(s): [['/data/service/hnp/bin/clang']]`（Errno 2）。
  本配方内已适配经验 1（mailx 先例）：_resolve_cc() 对 profile 绝对路径做
  存在性校验，缺失时按 basename→clang→cc 做 PATH 回退并打 warning/info，
  以 `CC=` 命令行参数（autoconf/make 语义优先于环境与 Makefile 内建值）
  传入 configure/make/check。CI 上路径存在时行为不变。
  残留风险：libgoa 与 libsoup3/3.6.5-r3 在本 profile 下均无 ohpcd 二进制
  （11 种 cppstd 兼容配置均未命中），须从源码构建，而它们的远端配方
  （ohpcd 当前修订）未做同等 PATH 回退，meson 原生文件仍写绝对路径；
  工作树内改它们的文件不会进入预检（依赖走 ohpcd 远端解析），需由依赖侧
  配方修复发布或补发二进制后本链才能全绿。
- 申请人：gcw_uQ09W7jl，队伍：干。
- 2026-10-16 第 7 策略周期换路线说明（上一方案为何无效）：
  前三轮沿用“编译器绝对路径/RREV”同族假设（libffi/sqlite3 的 RREV 固定 +
  本配方 _resolve_cc 的 PATH 回退），但本轮真机仍以完全相同的
  `libgoa/3.58.1 meson.configure: Unknown compiler(s):
  [['/data/service/hnp/bin/clang']]`（Errno 2）失败。重读日志与源码后确认：
  conan 先构建全部依赖、最后才执行本配方的 build()，_resolve_cc 只影响本包
  自身的 configure/make/check，永远触及不到 libgoa 的 meson native file，
  故同族补丁不可能收敛。本轮改走“依赖图与生成器”路线，不再动编译器假设：
  (1) libsoup3 与 librest 锚定同一 r3 RREV（3bbc75da…，librest 配方案内原文），
  消除同版本双 RREV 漂移；(2) glib 根统一加 force=True（librest 图解析先例）；
  (3) generate() 首行做 glib 构件名归一（gnome-recipes/2.0.4 同款机制，按本闭包
  改写）：实测确认 glib/2.84.0.1.1 用后缀名（glib-2.0/gio-2.0…），而
  libgoa/3.58.1 与 librest/0.10.2 的 cpp_info.requires 均为裸名
  （glib::glib/glib::gio，面向 glib/2.88.3 的裸构件），否则本包 generate() 的
  PkgConfigDeps 必以 “Component 'glib::gio' not found” 中止——该失败点排在
  libgoa 构建之后，是之前轮次从未抵达的潜伏缺陷。
  残留：libgoa 在统一图下（glib 2.84 vs 其发布二进制的 2.88.3）仍须在沙箱源码
  构建，而远端 libgoa 配方无 PATH 回退，meson 沿用 profile 绝对路径即死；
  该构建失败只能由依赖侧修复（libgoa 加 mailx 式回退后重发，或补发
  2.84 基准二进制），本 PR（一库一改）不越界改依赖配方、不断 GOA 公共 API。
  manifest.yaml 与 pr-body 草稿中残留的 gnome-online-accounts/3.56.5 已订正为
  配方实际依赖的 libgoa/3.58.1。
- 2026-10-16 同指纹第 2 次修复（换策略：摘除 libgoa 腿，替代编译器/RREV 同族补丁）：
  上轮“图对齐 + 构件归一”修改已被预检取到（libgoa 构建目录哈希变化）但失败原样复现，
  证明只要 libgoa 留在图中、沙箱 meson 必死，任何本配方侧编译器/生成器改动都够不着它。
  本轮删除 `self.requires("libgoa/3.58.1")`，新增 _excise_goa_backend() 在 build() 内
  裁剪：Makefile.in/am 按 token 删源并修复续行（本地纯字符串单测 4/4 通过）、伞头去掉
  goa 引入、libgfbgraph.pc.in 用精确行断言去 goa-1.0（兼证 0001 已应用）、configure
  用 GOA_CFLAGS/GOA_LIBS 环境短路跳过探测（pkg.m4 标准行为）、收尾用编译输入级
  grep 门禁兜底（布局变化则大声失败，绝不静默半裁）。test_package 与上游两个程序均
  不触 GoaAuthorizer，口径不变。manifest.yaml 去掉 libgoa 依赖行，pr-body 草稿同步
  并新增裁剪声明。py_compile 通过，保持未提交待预检。
- 2026-10-16 同指纹第 3 次修复（0001 补丁 8 个 hunk 计数笔误，解析期失败）：
  上轮摘除 libgoa 后失败域如预期前移到本包 build()，但卡在 apply_conandata_patches：
  `extra lines for hunk ... patch stream is incomplete`。此前轮次均死于依赖构建，
  0001 从未被实际应用过，问题一直潜伏。本轮用严格计数器逐 hunk 核对（上下文+删除
  行=old 数，上下文+新增行=new 数），确认仅计数头笔误（正文连贯完整，非截断；
  文件为干净 LF、无 BOM、有结尾换行）：configure.ac(9→10)、Makefile.am(9→10)、
  photo.c 大 hunk(27,27→37,33)、simple/goa 主 hunk(17→18)、gtestutils(12,16→19,21)、
  两个 string.h 小 hunk(7,8→6,7)。只改计数头、不动正文；本地复核 10/10 hunk
  合法。hunk 正文相对上游的上下文匹配度本地无法验证（无 tarball），若仍有出入，
  下一轮真机会给出精确到 hunk 的 apply 错误。
- 2026-10-16 同指纹第 4 次修复（换路线：删除 0001 补丁文件、改为配方内碰码移植）：
  上轪“修计数头”后真机仍报 hunk 失配（photo.c 第 2 段期望 GInputStream*实际为函数签名行、simple/goa 偏移 2 行）。本地下载官方 tarball 核对后确认：补丁路线本身脆弱，且只改 configure.ac/Makefile.am，而构建消费的是预生成的 configure/Makefile.in（含 9+9 处 rest-0.7/libsoup-2.4 探针），即便 hunk 对齐也无法重定向 pkg-config 探针。故删除 patches/0001 及 conandata 补丁声明，新增 _port_to_soup3_rest1()：对 configure.ac+configure、Makefile.am+Makefile.in、pc.in、photo.c、双 authorizer、gtestutils 做精确 token 替换（每处断言 count==1、生成文件用全局替换），收尾用 soup2 token 门禁兜底；顺序为移植先于 GOA 裁剪（裁剪断言的 soup3/rest1 Requires 行保持不变）。所有旧串在下载的 0.2.5 原包中验证为唯一出现，本地 py_compile 通过，保持未提交待预检。
- 2026-10-16 同指纹第 5 次修复（换策略：CONFIG_SHELL 沙箱回退）：上轮 in-code 移植已被预检取到（日志显示 soup3 port + GOA excision 均 pass），失败域前移到 configure 执行期：configure[159] 调 /data/service/hnp/bin/bash 报 inaccessible/Error 127。重读日志确认与本包代码无关，是 profile 导出的 CONFIG_SHELL 在沙箱不可见（与备注中 libffi 同款路径）。本轮在 build() 内 configure 前用 /bin/sh 覆盖 CONFIG_SHELL/SHELL（c-ares-dev/1.34.5 同款，HMBS 平台能力 shell=/bin/sh），CI 上 /bin/sh 同样存在故为 no-op。保持未提交待预检。
- 2026-10-16 同指纹第 6 次修复（换策略：Conan Environment 作用域覆盖 CONFIG_SHELL）：上轮裸 os.environ 覆盖已被预检取到（build 目录哈希变化、行号 192->201）但失败逐字复现，证明 conan 在 Autotools.configure() 周围重新应用 profile buildenv，冲掉裸 environ。重读原包 configure 确认机制：139-154 行 `exec $CONFIG_SHELL` 非空即重执行，死路径即为 159 行报错。本轮改用 c-client 同款 Environment 内层 vars(self) 作用域包裹 configure+make，并在 configure 命令行追加 CONFIG_SHELL/SHELL= /bin/sh（autoconf 命令行覆盖环境）双保险；make check 的 build_env 同步增加两项。保持未提交待预检。
- 2026-10-16 同指纹第 7 次修复（换路线：放弃 Autotools 辅助类、改用 self.run 环境前缀 + 明确 /bin/sh 调用）：上轮 Environment 内层作用域 + configure 命令行 CONFIG_SHELL=/bin/sh 已被预检取到但失败逐字复现（configure[159] 仍 exec 死路径）。下载官方 tarball 核对确认机制：configure 139-154 行非空 CONFIG_SHELL 即 exec 重执行，而该检查发生在参数解析之前，命令行 VAR=VALUE 永远够不到第一次 exec；唯有进程环境才有效。本轮改走 ballandpaddle 路线： build()/check()/package() 全部改用 self.run(..., env="conanbuild")，CONFIG_SHELL/SHELL/_as_can_reexec=no 作为 shell 命令前缀环境（非 configure 参数），configure 明确用 /bin/sh 解释器调用（不依赖执行位，HMBS chmod=0 安全），--prefix/--bindir 等与工具链默认保持一致手写；CC/GOA 仍为命令行赋值。CI 上 /bin/sh 同样存在故为 no-op。保持未提交待预检。
- 2026-10-16 pkg-config缺失修复：预检configure报 The pkg-config script could not be found。HMBS仅注入cmake/make/ninja/python3。新增build_requirements pkgconf/3.0.5（ctpl/zurl/ekg2先例）并在_shell_env_prefix显式导出PKG_CONFIG绝对路径（自研self.run绕过Autotools辅助类，需手动转发）。保持未提交待预检。
- 2026-10-16 unsafe_local_mktemp修复：预检config.status报 `can't create ./confyMkIQf/subs1.awk: Permission denied`（平台能力 hardlink=0/chmod=0/local_mktemp=1，诊断码 unsafe_local_mktemp）。主修为 _patch_autoconf_umask() 把 configure/build-tree config.status 的 umask 077→022（buildtorrent/zurl先例，mkdir回退同带077故shim不能单用），configure/make/check/install 命令行统一 `umask 022 &&` 前缀；辅修为 HMBS_AUTOCONF_MKTEMP_FALLBACK=1 时仅configure期前置 `*conf*→exit 1` 的 mktemp shim（cyrus-sasl/cxxtools先例，/bin/sh shebang + os.open 0o755 兼容chmod=0，非conf调用委托真实mktemp）。保持未提交待预检。
- 2026-10-16 maintainer模式修复（换策略）：上轮umask+shim已被预检取到（configure补2处并走完探针），失败域前移到make期的 `missing aclocal-1.16: inaccessible or not found`（Error 127）。根因为配方内碰码移植/裁剪改了configure.ac+Makefile.am却未跑autoreconf，模板mtime新于自带aclocal.m4/configure/Makefile.in，触发maintainer重生成规则，而设备无aclocal/perl。新增_stabilize_autotools_mtimes()用os.utime把configure.ac钉回aclocal.m4、各Makefile.am钉回同目录Makefile.in（juise/3.0.0 touch -r先例的无shell实现），生成文件保持最新。保持未提交待预检。
- 2026-10-16 maintainer补强（同指纹第3次，前次只钉顶层）：前次钉回后顶层aclocal.m4报错消失，但子目录 `gfbgraph/Makefile.in` 仍触发 `missing automake-1.16`（Error 127）。改为双层整数秒方案：模板层（configure.ac/acinclude.m4/全部Makefile.am）统一钉回aclocal.m4所在整数秒，生成层（aclocal.m4/configure/config.h.in/全部Makefile.in）统一触到now+5的同一整数秒，保持aclocal→configure→Makefile.in链序且杜绝float纳秒舍入残留1ns newer；另加 `--disable-maintainer-mode` 作双保险（不支持的包仅多一句无害警告）。保持未提交待预检。
- 2026-10-16 sanity-clock fix: previous stabilize touched generated files to now+5, distributed files in future so configure sanity fails newly created file older. Changed to past-only pin templates to min-generated-minus-2s, generated untouched. Keep uncommitted for preflight.
- 2026-10-16 no-closing-quote fix: make died at the first CC line (`gfbgraph-connectable.lo`) with `/bin/sh: no closing quote` after configure fully passed. Root cause in own tree: `_drop_make_tokens` used a bare `\S*needle\S*` regex that can swallow one half of a shell-quoted span (same failure class as the cvsgraph `-L` regex lesson in knowledge/). Rewrote it quote-parity-safe: comment/recipe/`target:`-block lines holding the token are dropped outright (target drops its attached TAB/`@cond@`-TAB recipe block), other lines only lose even-parity tokens, parity-breaking lines are dropped, emptied `include` directives and lone-`\` lines are removed; a fail-loud audit aborts on newly introduced odd-quote logical lines with exact text. Also added `V=1` to build/check/install make calls so any future shell failure prints the exact command instead of a hidden silent-rules line. Keep uncommitted for preflight.

- 2026-10-16 E236换路线修复（上一方案为何无效）：上轮la-free只拷.so/.a、靠-L顺序抢赢的假设被真机证伪，链接仍报libffi.la was moved后跟grep //lib/libpcre2-8.la不存在。重读日志确认libtool会扫描全部-L目录找.la，无.la的la-free无法屏蔽缓存毒.la。本轮改走影子.la路线：_prepare_la_free_dir同时拷贝*.la并消毒（//lib->la-free、libdir钉到la-free），靠-L首位让影子优先命中，缓存保持不动。py_compile通过，保持未提交待预检。
- 2026-10-16 E522闭环修复（影子.la仍失败，换中和路线）：影子.la修订版仍在tests/gtestutils链接死于同一`'//lib/libpcre2-8.la' is not a valid libtool archive`（前有libffi/pcre2 .la was moved）。根因为libtool经dependency_libs绝对路径递归打开传递.la，绕过-L顺序，影子永远够不到缓存原文件（E522）。本轮改走中和路线：la-free只留.so*/.a（不再拷贝任何.la），新增_neutralize_poisoned_la()把任务级preflight conan-home内全部依赖*.la重命名为*.la.hmbs-bak（per-client隔离，不影响他人），libtool全程见不到.la、经pkg-config -L/-l直链.so；package()删除自产*.la（hwloc先例，防libdir='/lib'毒.la流向下游）。py_compile通过，保持未提交待预检。
- 2026-10-16 lld劫持修复（换路线：LD_LIBRARY_PATH只进测试进程）：上轮la中和已被预检取到（configure探针走完、la-free/neutralize日志均在），失败域前移到conftest链接：`clang ... -L.../la-free conftest.c`死于`Error loading shared library libxml2.so.16 (needed by .../native/llvm/bin/lld)` + xmlFreeDoc等20+符号not found → lld无法启动 → `C compiler cannot create executables`。根因在本配方：_shell_env_prefix把全依赖图libdirs经LD_LIBRARY_PATH导出到configure/make全阶段（旧注释称“对configure无害”），而OHOS SDK的lld动态链接系统libxml2.so.16，被劫持到conan的libxml2不兼容拷贝后直接起不来。本轮改走作用域路线：_shell_env_prefix默认不再导出LD（with_loader_path=False），_run_upstream_tests改经automake的TESTS_ENVIRONMENT=`LD_LIBRARY_PATH=<dep libdirs>`把加载路径只前置到各测试命令（link步骤仍用干净loader）；test_package走VirtualRunEnv/conanrun测试期执行，无需改动。py_compile通过，保持未提交待预检。
