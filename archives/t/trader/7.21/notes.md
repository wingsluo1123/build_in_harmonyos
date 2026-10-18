# Star Traders (trader) 7.21 适配笔记

## 编译环境
- 构建系统: autotools（configure + make）
- 上游: John Zaitseff，官方发布页 https://www.zap.org.au/projects/trader/
- 目标: HarmonyOS PC aarch64（ohos-aarch64 profile，clang 15）
- 状态: 工作树就绪（真机 rule4 门禁待跑）

## 源码与校验
- 官方源码: https://ftp.zap.org.au/pub/trader/unix/trader-7.21.tar.xz
  （亦发布于 https://www.zap.org.au/projects/trader/unix/）
- sha256: `541d1180dde04173c071d5c59eaf72a6572f8dfc8065e184eaf7d14bccd0257d`
- **镜像回退（本轮新增）**：CI 日志显示配方下载官方归档时
  `Connection to ftp.zap.org.au timed out`（连接超时，非 404）。
  Debian 源码仓库保存的 `trader_7.21.orig.tar.xz` 与官方发布归档
  **位级相同**（实测 sha256 一致 = 上述值），由 Debian FTP masters 维护，
  国内镜像同步稳定。故 conandata.yml 的 `sources.url` 改为有序列表：
  清华 → 阿里 → 南大 → Debian 主站 → 官方 www → 官方 ftp。
  所有镜像继续用同一 sha256 校验，未修改校验值。

## 构建系统分析
trader 是标准 GNU Autotools 项目：
- `configure.ac`：`AC_INIT([Star Traders],[7.21])`，`AM_GNU_GETTEXT([external])`，
  gnulib 模块（`gl_INIT`），`AX_WITH_CURSES`（需要宽字符 Curses + colour），
  硬校验 `<monetary.h>` 存在 + X/Open SUSv4（`USE_LATEST_XOPEN_SOURCE`）。
- `src/Makefile.am`：`bin_PROGRAMS = trader`，链接
  `$(CURSES_LIBS) lib/libgnu.a $(HARD_LOCALE_LIB) $(MBRTOWC_LIB) ... $(LIBINTL)`。
- `lib/`：gnulib 生成的替换库 `libgnu.a`（含 monetary/wchar/locale 等替换头文件）。
- `po/`：gettext 翻译目录；`data/`：desktop/metainfo 经 `msgfmt-desktop` 从 po 生成。
- tarball 自带 configure / Makefile.in，无需 autoreconf。

## 关键适配决策
1. **`--disable-nls`（规避外部 gettext 链）**：
   上游 `AM_GNU_GETTEXT([external])` 需要 autopoint/msgfmt/libintl。OHOS 无该
   外部工具链。实测（本机 Linux 完整 configure+make）：`--disable-nls` 后
   `po/` 与 `data/` 的目标变成 no-op（"Nothing to be done for 'all'"），
   desktop/metainfo 不生成、不依赖 msgfmt——干净规避 gettext。
2. **ncurses/6.6 conan 依赖 + `--with-ncurses`**：
   `AX_WITH_CURSES` 需要宽字符、带 colour 的 Curses。ncurses/6.6 配方提供
   `ncursesw.pc`（pkg_config_name=ncursesw）；配方经 PkgConfigDeps 暴露该 .pc，
   `configure --with-ncurses` 走 pkg-config 探测 NcursesW。
3. **工具链/标志全部走 Conan**（R33）：不裸用 shell `${CC}/${CFLAGS}`；
   `AutotoolsToolchain` 从 profile `tools.build:compiler_executables` 取 clang，
   并自动把依赖 include/lib（ncurses）注入 CPPFLAGS/LDFLAGS。
4. **configure 临时文件目录**：`TMPDIR/TMP/TEMP` 指到 build_folder/tmp
   （OHOS /tmp 可能受限，abx/anubis 同款模式），并显式 mkdir。
5. **编译单 job**：`make -j1`，避免 HMDFS 上 make jobserver/FIFO 问题。

## 上游测试审计（status=no_tests）
逐文件审计（Linux + 官方发布包）：
- 顶层 `Makefile.am` `SUBDIRS = lib src po data doc m4`，无 tests/ 目录；
  全树无 test/、tests/、regress/、*_test 测试目录或测试源文件。
- `src/Makefile.am`：仅 `bin_PROGRAMS`/`SOURCES`/`CPPFLAGS`/`LDADD`，
  无 TESTS/check_PROGRAMS/check-local。
- `lib/Makefile.am`（gnulib）：`TESTS_ENVIRONMENT =` 为空，全树无 TESTS 赋值、
  无测试程序登记，`check-am: all-am` 为 automake 默认空操作。
- `configure.ac`：无 AC_CONFIG_TESTDIR、AC_ARG_ENABLE(enable-tests) 等测试宏。
- 完整 `make check` 实测：所有子目录与顶层 `check` 均 "Nothing to be done"，
  退出码 0 但零用例执行。
⟹ `upstream_tests_exist: false`，`upstream_test_total: 0`，
`upstream_test_count_method: "autotools_tests"`（见 test_package/MANIFEST.yml 审计）。

## test_package（R34 实质验证）
- `test.c`：真实执行安装产物 `bin/trader`，4 项确定性断言：
  ①二进制存在/可执行 ②`--version` 退出码 0 且含 "7.21" ③`--help` 退出码 0 且
  含 Usage/Star Traders ④`--no-color --version` 组合正常。
- `conanfile.py`（test_package）：clang 编译 test.c → 运行；
  输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=4, passedCount=4，来自 test.c
  真实断言数）与 `HMBS_UPSTREAM_TEST_RESULT`（no_tests）。两个标记均用裸
  `print` 直接写 stdout，避免 conan 日志前缀导致采集遗漏。上游测试标记由
  test_package test() 复发，避免包缓存命中时 build() 不重跑而拿不到 evidence
  （asterisk-flite 同模式）。

## 历史真机预检修复记录（沿用并已收敛）

### configure_args 属性修复
- 症状：`build()` 用 `autotools.configure_args` 抛
  `AttributeError: 'Autotools' object has no attribute 'configure_args'`。
- 根因：Conan 2.x 的 `Autotools` 不暴露 public `configure_args`（属
  `AutotoolsToolchain`）。修复：改用自有静态列表 `_configure_args()` 拼进
  configure 命令（同 adns/quagga/tlog/anubis 模式）。

### HMDFS getcwd 失败修复
- 症状：configure 刷 `getcwd: cannot access parent directories` →
  `configure: error: working directory cannot be determined`（[shell_getcwd]）。
- 根因：profile buildenv 注入的 `CONFIG_SHELL`（OHOS 系统 bash）在 HMDFS
  构建目录 getcwd() 失败。修复：把 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`
  就近内联在 configure 命令前缀（anubis 已验证模式），并以 in-source build
  在 source_folder 执行 `sh ./configure` + `make -j1`。

### readonly_tmp / 编译器无法生成可执行文件
- 症状：`C compiler cannot create executables`、`sed: can't read conftest.c`
  （[readonly_tmp]）。根因：`TMPDIR` 只 define 未 mkdir。修复：显式
  `os.makedirs(tmpdir)`，并加 `AutotoolsDeps` 注入依赖 CPPFLAGS/LDFLAGS、
  `_restore_helper_modes()` 恢复辅助脚本 +x。

### package 布局修复
- `make install DESTDIR=staging prefix=/usr/local` 后把 `usr/local/bin/*`
  映射到 `package_folder/bin`（anubis 同模式），保证 test_package 以
  `bin/trader` 定位安装产物。

### unsafe_local_mktemp 修复
- 症状：`./config.status[...]: can't create ./confXXXXXX/subs1.awk:
  Permission denied`、`could not setup config files machinery`
  （[unsafe_local_mktemp]）。
- 根因：autoconf 的 config.status 用 `umask 077 && mktemp -d ./confXXXXXX`
  建临时目录；setgid 的 HMDFS 挂载上 umask 077 目录 owner 不可写（E129）。
- 修复：对 OHOS 目标，在源码树把 `configure` 与 `config.status` 里的
  `umask 077` 就地改写为 `umask 022`（truncate+write 保留 inode +x，
  HMBS_CAP_CHMOD=0 安全；cyrus-sasl-scram 同款已验证）。仅 OHOS 生效。

### strfmon 缺失链接修复
- 症状：链接 `src/trader` 报 `ld.lld: error: undefined symbol: strfmon`，
  引用点 `trader-utils.o:(xwcsfmon)`。
- 根因：OHOS libc 为 musl 系（非 glibc），未导出 POSIX `strfmon()`；
  gnulib 只探测 `strfmon_l`，不替换普通 `strfmon`。
- 修复：新增补丁 `patches/0001-utils-c-strfmon-ohos.patch`，在 `src/utils.c`
  提供自包含 POSIX strfmon 兼容实现，用 `#if !defined(__GLIBC__)` 守卫
  （勿用 `__OHOS__`，部分 OHOS clang 目标不预定义；OHOS 非 glibc 已由链接
  错误证明）。同时新增同守卫前向声明，避免
  "static declaration of 'strfmon' follows non-static declaration"。
- 本地验证：`patch -p1 --dry-run` 对官方 7.21 源码零 fuzz 干净应用；
  最小 TU 复现并确认前向声明消除冲突；glibc 下 shim 与前向声明均被排除，
  行为与原版一致。

## 本轮新增修复：源码下载可靠性（CI timeout）
- 症状：CI 构建日志（buildbot）显示 `conan create` 的 `source()` 阶段
  `Error downloading file https://ftp.zap.org.au/pub/trader/unix/trader-7.21.tar.xz:
  ... ConnectTimeoutError ... Connection to ftp.zap.org.au timed out`。
  分类为「源码下载超时」，属配方下载可靠性问题（守则例外条款）。
- 修复：`conandata.yml` 的 `sources.url` 改为有序列表，可信镜像在前、官方
  URL 在最后回退：
  1. `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/t/trader/trader_7.21.orig.tar.xz`
  2. `https://mirrors.aliyun.com/debian/pool/main/t/trader/trader_7.21.orig.tar.xz`
  3. `https://mirror.nju.edu.cn/debian/pool/main/t/trader/trader_7.21.orig.tar.xz`
  4. `https://deb.debian.org/debian/pool/main/t/trader/trader_7.21.orig.tar.xz`
  5. `https://www.zap.org.au/projects/trader/unix/trader-7.21.tar.xz`
  6. `https://ftp.zap.org.au/pub/trader/unix/trader-7.21.tar.xz`
- 镜像可信性：Debian 源码仓库的 `.orig.tar.xz` 即上游原始发布归档，实测
  6 个来源（含官方两处）sha256 全部等于
  `541d1180dde04173c071d5c59eaf72a6572f8dfc8065e184eaf7d14bccd0257d`，
  位级相同。**未修改 sha256 校验值**。Conan 2.x `get()` 原生支持 url 列表
  多源 fallback，逐项尝试直到成功。

## 待真机核验的点
1. **config.guess / 主机三元组**：trader 自带 config.guess（2024-07-27）
   未含 HarmonyOS 分支；config.sub 已识别 `linux-ohos`。显式传
   `--build/--host=aarch64-unknown-linux-gnu`（anubis 同模式）让 AC_PROG_CC
   探针走通；编译器/ABI 由 Conan OHOS profile 提供。
2. **monetary.h / X/Open 校验**：configure.ac 硬校验 `<monetary.h>` 与 SUSv4；
   gnulib 的 monetary-h/xopen-source 模块提供替换头。
3. **gnulib 替换库构建**：`libgnu.a` 涉及 iconv/locale/wchar 等替换。
4. **运行期 terminfo**：test_package 只做 CLI 自检（--help/--version 不初始化
   curses），不依赖 terminfo，避免运行时脆弱性。

## 依赖版本
- ncurses/6.6（conan，默认静态 shared=False，NcursesW 宽字符 + colour）
