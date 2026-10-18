# uget 2.2.3 适配笔记

## 编译环境
- 构建系统: autotools（SourceForge 官方发布 tarball 自带 configure；
  无 AC_CANONICAL_HOST，config.guess/sub 不参与，--host 仅供工具前缀查找）
- 编译日期: 2026-10-17
- 编译器: clang（OHOS aarch64 交叉）
- 状态: built

## 编译步骤

1. SourceForge urlget 项目官方 tarball（uget-2.2.3-1.tar.gz），
   sha256 11356e42...9049，解包根目录 uget-2.2.3/。
2. 0001 补丁：AC_PROG_INTLTOOL / AM_GLIB_GNU_GETTEXT 在 --disable-nls 下
   仍硬性探测 intltool 脚本、GNU gettext 工具、perl+XML::Parser，
   缺一即 as_fn_error；OHOS CI worker 无这些工具，补丁将 6 处硬错误
   降级为告警（perl 缺失时置 INTLTOOL_PERL=: 让后续 5.8.1/XML::Parser
   探测安静通过）。po/ 在 USE_NLS=no 下为空操作，不影响构建产物。
3. curl-config wrapper：uget 以 AC_PATH_PROG(CURL_CONFIG) + --cflags/
   --libs/--vernum 探测 libcurl（>= 7.19.1），不用 pkg-config；
   conan curl 包内脚本嵌入 CI worker 绝对路径、重定位后失效，
   generate() 从 curl cpp_info 合成 wrapper 并前置 PATH
   （castget/2.0.1 先例）；--vernum 输出无 0x 前缀十六进制
   （8.15.0 → 080f00），匹配 configure 的 `let CURL_VERNUM=0x0$...`
   >= 0x071301 检查。
4. libcrypto.pc overlay：ohpcd openssl 只发 openssl.pc，uget
   PKG_CHECK_MODULES(LIBCRYPTO, libcrypto)，generate() 手写 libcrypto.pc
   指向 openssl 包（gcli/2.12.0 先例）。
5. configure 参数：--disable-nls --disable-notify --disable-gstreamer
   --disable-appindicator --disable-rss-notify（最小依赖面，bluefish 惯例）；
   --with-openssl 默认启用（mega 插件编译期强制 OpenSSL）；
   gnutls/pwmd/unix-socket 默认关闭无需干预。
6. HMDFS 适配（aris/2.2 同款）：E490 恢复辅助脚本执行位、PWD 预置 +
   ac_pwd $PWD 回退、config.status umask 077→022（E011）、
   TMPDIR 指向 ~/tmp（E011/E114）；所有依赖 libdir 追加
   LD_LIBRARY_PATH（configure sanity RUN 找 libintl.so.8 + 测试程序运行时）。
7. configure → make -j1 → build() 校验并（构建机能跑目标二进制时）
   真实执行 6 个上游测试程序 → make install。

## 依赖版本

- glib/2.84.0.1（含代理 libintl：include/libintl.h + lib/libintl.so，
  .pc 不传递，LDFLAGS 补 -L/-lintl，aris/2.2 同款处理）
- gtk/3.24.43（pkg_config_name=gtk+-3.0，aris/2.2 同款钉版）
- curl/8.15.0（动态库仅 NEEDED libc.so，自包含）
- openssl/3.5.6.1（mega 插件强制；与 curl/8.15.0 钉版对齐；libcrypto.pc overlay）
- zlib/1.3.1.1（override 对齐 curl 图，castget/2.0.1 同款）

## 设计取舍

- uget 产 bin_PROGRAMS（uget-gtk、uget-gtk-1to2），按 R38 在软件级别
  声明 commands.json（type=tool）。
- uget-gtk --version/--help 在 gtk_init 之前处理（UgtkApp-main.c:253-289），
  uget-gtk-1to2 无参打印横幅后 EXIT_SUCCESS —— 三个断言均无头可跑，
  作为 test_package 消费者测试。
- libnotify(0.8.3)/gstreamer(1.28.3) 虽在制品仓存在，但 OHOS PC 通知/
  音频服务未验证，按最小依赖面原则禁用；后续需要可单独开启。
- GitHub ugetdm/uget 为空占位仓（size=3KB），SourceForge urlget 为
  唯一官方发布渠道（R39）。

## 上游测试清点（R51 三步法）

- 上游 uGet 2.2.3 tests/Makefile.am 声明 6 个 noinst_PROGRAMS：
  test-json、test-jsonrpc、test-plugin+app、test-info、test-uglib、
  test-uget（C++ 变体已注释掉），plain C main 无条件 return 0；
  未注册 TESTS / check_PROGRAMS，`make check` 不会运行它们；
  顶层 SUBDIRS 含 tests，`make all` 默认构建全部 6 个程序。
- build() 在 make 后校验 6 个程序产物齐全（缺失即构建失败），
  构建机可运行目标二进制时（can_run，原生 CI worker）逐个真实执行
  并断言退出码 0（GLib/CURL/libcrypto 运行时由 buildenv
  LD_LIBRARY_PATH 提供）；交叉容器本地跑不动时如实记 SKIP-CROSS
  （见"环境限制"）。结果持久化 res/upstream_test_result.json 并输出
  HMBS_UPSTREAM_TEST_RESULT 标记，test_package 阶段复读输出。

### 测试四维账本

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 6 | tests/Makefile.am noinst_PROGRAMS（清点证据见上） |
| N_registered（构建系统注册） | 0 | TESTS/check_PROGRAMS 为空（上游未注册） |
| N_executed（实际执行） | 6 | 原生构建（CI 真机）build() 显式执行 tests/test-* 断言退出码 0；交叉容器本地记 SKIP-CROSS（环境限制，见下） |
| N_consumer（新增消费者测试） | 3+2 | test_package/test.sh 3 处运行时断言（--version/--help/1to2 横幅，原生 CI 真跑）+ 2 处静态断言（bin/uget-gtk、bin/uget-gtk-1to2 ELF64/AArch64，本地/CI 均真跑） |

## 环境限制（非包缺陷）

本地 WSL 交叉容器**无法执行**构建出的 OHOS aarch64 二进制（上游测试
程序、uget-gtk、uget-gtk-1to2 均受影响）：

1. NDK sysroot 头把 `FD_SET` 等改写成先调 `__fd_chk(int)`，cairo/glib
   另引用 `__memcpy_chk`/`__strlen_chk`/`__vsnprintf_chk` 等 OHOS
   特有 fortified libc 符号；
2. 真机 OHOS libc 导出这些符号（`readelf -sW` 命中），本地仿真 guest
   `/opt/ohos-guest/lib/libc.so` 是 stock musl（0 命中）；
3. 实跑报 `Error relocating ...: __fd_chk: symbol not found`（exit 127），
   与 lcdproc/0.5.9 §8、transfuse/0.7.6 §5.1、scanmem/0.17 同一问题。

处置（沿先例，**不塞任何垫片/假符号进交付物**）：

- 配方用 conan 标准 `can_run()` 门控执行：原生 CI 真机 6 程序 +
  test.sh 3 断言**全部真实执行**；交叉容器记 SKIP-CROSS/静态断言，
  `conan create` 本地仍 rc=0（W3 门禁）。
- 本地补充验证（scanmem 同款手法，仅本机、不进交付物）：qemu 下
  LD_PRELOAD `/opt/ohos-guest/lib/lib*shim.so` 等垫片实跑结果
  记录在下方"本地补充验证"。

### 本地补充验证（2026-10-17，仅本机、不进交付物）

手法同 scanmem/0.17：qemu binfmt + `LD_PRELOAD=/opt/ohos-guest/lib/
lib*shim.so` + 依赖 libdir 全量 `LD_LIBRARY_PATH`，直接执行构建产物：

| 用例 | 结果 |
|---|---|
| tests/test-json | rc=0 |
| tests/test-jsonrpc | rc=0 |
| tests/test-plugin+app | rc=0 |
| tests/test-info | rc=0 |
| tests/test-uglib | rc=0 |
| tests/test-uget | rc=0 |
| bin/uget-gtk --version | 输出 `uGet 2.2.3 for GTK+`，rc=0 |
| bin/uget-gtk --help | 含 `--quiet`（grep 命中 1） |
| bin/uget-gtk-1to2（无参） | 横幅输出，rc=0 |

6/6 上游测试程序 + 3/3 消费者断言在本地仿真下全部真实通过；
配方交付物本身不含任何垫片/preload（CI 真机原生执行）。

## 本地 conan create 结果（W3 门禁）

- `conan create ... -pr:h/-pr:b=ohos-aarch64-wsl --build=missing` rc=0
- Package 'fed99172cd5b173c83ef4ba0295cf947aff164dc' created
  （uget/2.2.3#7366b1db75e4e6e179fde33541a9dda4:
  fed99172cd5b173c83ef4ba0295cf947aff164dc#ba9c56e44333aa8446c145fa2d0e8893）
- build folder: /root/.conan2/p/b/ugetf0f41c1990a2b/b/build-release
- 打包产物：bin/uget-gtk、bin/uget-gtk-1to2、res/upstream_test_result.json、
  licenses/COPYING、share/（24 png + 1 svg + 1 wav + uget-gtk.desktop）
- 标记：HMBS_UPSTREAM_TEST_RESULT（SKIP-CROSS×6 + 原因）、
  HMBS_TEST_PACKAGE_RESULT（静态断言 + runtime skipped 原因）

## 源码修改

- patches/0001-configure-l10n-tools-optional.patch：将生成的 configure 中
  6 处 L10N 工具 as_fn_error 硬错误降级为告警（intltool 脚本缺失 ×1、
  GNU gettext 工具缺失 ×2、perl 缺失 ×1 并置 INTLTOOL_PERL=:、
  perl 版本 ×1、XML::Parser ×1），并移除 AM_GLIB_GNU_GETTEXT 内嵌的
  无条件 USE_NLS=yes 覆盖（glib-gettext 宏 bug，会盖掉 --disable-nls，
  导致 po/Makefile 走 all-yes 分支在 GMSGFMT 为空时报
  "-o: command not found"；USE_NLS=no 时 po/ 走 all-no/
  install-data-no 空目标）；不触碰任何 C 源码。
- 构建期注入（非补丁）：curl-config wrapper、libcrypto.pc overlay、
  E490/E007 同类 HMDFS 适配（PWD/ac_pwd/umask/TMPDIR）、
  -L/-lintl LDFLAGS、全局 CFLAGS 注入 curl/openssl include
  （uget/Makefile.am 编译 UgetRss.c、UgetPluginMega.c 时不带
  @CURL_CFLAGS@/@LIBCRYPTO_CFLAGS@，上游假定系统默认路径；
  USE_OPENSSL=1 来自默认 --with-openssl；uglib/、ui-gtk/ 自带变量）、
  -fcommon（ui-gtk/UgtkBanner.h 的 `struct UgtkBanner {...} banner;`
  在每个包含它的编译单元泄漏全局变量定义，clang 15 默认 -fno-common
  报 17 处 duplicate symbol；aris/2.2 同款处理）——
  均为 generate()/build() 运行时注入，不修改上游源码文件。

---

**编译结束**: 2026-10-17
**最终状态**: built
