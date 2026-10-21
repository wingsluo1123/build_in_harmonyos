# libgfbgraph 0.2.5 适配笔记

## 结论

HarmonyOS aarch64 上 `conan create` 退出码 0。上游 `make check` 两个测试程序都通过，SKIP 0。活动测试用例 4 个，全部实跑通过；`gtestutils.c` 中另有 2 个 `g_test_add` 写在上游 `#if 0` 内，不属于活动套件。消费者测试 10/10。

## 源与依赖

- 上游：https://gitlab.gnome.org/Archive/libgfbgraph ，tag `v_0_2_5`
- 源码包 SHA-256：`3f53e548464dd64b0887b9f2d7093bd3367e1e4f6932a7c79f527b66255c0804`
- 直接依赖：glib/2.84.0.1.1（override + force，shared）、json-glib/1.10.6、libsoup3/3.6.5-r3、sqlite3/3.49.1、librest/0.10.2、gnome-online-accounts/3.56.5、libxml2/2.15.3、dbus/1.14.10、zlib/1.3.1.1（override）

## 适配

制品仓 librest 0.10.2 的 pkg-config 名是 `rest-1.0`，并且按 libsoup-3.0 编译。上游 configure 写的是 `rest-0.7` 和 `libsoup-2.4`。补丁 `patches/0001-rest-1.0-libsoup3.patch` 把探测名改成 `rest-1.0` / `libsoup-3.0`。核对过 rest 0.10 的 `rest_proxy_new`、`rest_proxy_new_call`、`rest_proxy_call_set_method`、`rest_proxy_call_set_function`、`rest_proxy_call_add_param`、`rest_proxy_call_sync`、`rest_proxy_call_get_payload`，签名与本库用法一致。libsoup 2 的 `SoupURI`、`SoupRequester`、`soup_session_send_message` 在 libsoup 3 中不存在，补丁改成 `GUri`、`soup_session_new`、`soup_message_new`、`soup_session_send`。

`tests/gtestutils.c` 里有一处 `soup_session_send_message`，不改则这个测试文件编不过。补丁只换了发送调用，断言 `status == 200` 和包住注册点的 `#if 0` 都保持原样。没有打开 Facebook 联网用例。

tag 归档没有 `configure`，也没有 gtk-doc。配方执行 `autoreconf -fi`，并从 `SUBDIRS` / `AC_OUTPUT` 去掉 `docs`，避免缺少 `gtkdocize` 时失败。

## CI 修复（2026-10-10）

`gnome-online-accounts/3.56.5` 已在 origin/main 和制品仓，本 PR 改不了那份配方。它的 `build()` 把 `PKG_CONFIG_PATH` 只设成 generators、dbus、glib。根配方把 glib 从 2.88.0 override 到 2.84.0.1.1 后 package_id 对不上，CI 从源码重编 GOA。`glib-2.0.pc` 的 `Requires.private` 要 `libpcre2-8`，`gio-2.0.pc` 要 `zlib`，`gobject-2.0.pc` 要 `libffi`。配方在同一进程的 meson setup 里把这几份 `.pc`（prefix 改成包目录）补进搜索路径。

## 真机测试（2026-10-10，全新 CONAN_HOME）

私有 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-gfg13934c`，profile `ohos-aarch64`，`--build=missing`。GOA 从源码构建（nju 镜像，补丁 0001 已打上），日志有 `gfg13934: GOA meson pkg-config extra dir ... files=libpcre2-8.pc,libffi.pc,zlib.pc,expat.pc`，meson 的 `pkg_config_path` 含该目录，随后 GOA 打包成功。制品仓 json-glib 二进制在这台开发机上 dlopen 失败（与本地链接器产物 md5 不同）；`--build=json-glib/*` 从源码重编后，配方原有的构建树符号链接能加载。最终 `conan create` 退出码 0。

`make check`：

```text
PASS: gtestutils
PASS: autoptr
# TOTAL: 2
# PASS:  2
# SKIP:  0
# FAIL:  0
# ERROR: 0
```

`./tests/autoptr`：TAP `1..4`，四项 `ok`。`./tests/gtestutils`：TAP `1..0`（2 个 `g_test_add` 仍在上游 `#if 0`，没有活动用例）。活动上游用例通过率 4/4，SKIP 0。`CONSUMER_RESULT 10/10`。

## 真机测试（2026-10-09）

私有 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-gfg13934`，profile `ohos-aarch64`。最后一次 `conan create` 日志 `create.log` 165686 字节，`CREATE_EXIT:0`。

`make check`：

```text
PASS: gtestutils
PASS: autoptr
# TOTAL: 2
# PASS:  2
# SKIP:  0
# FAIL:  0
# ERROR: 0
```

`./tests/autoptr -k --verbose`：TAP `1..4`，Album / Node / Photo / User 四项均为 `ok`，随后配方打印 `UPSTREAM_CASE_END autoptr`。

`./tests/gtestutils -k --verbose`：TAP `1..0`，随后 `UPSTREAM_CASE_END gtestutils`。其中两个 `g_test_add` 是上游自己用 `#if 0` 关掉的 `/GFBGraph/Me` 和 `/GFBGraph/Album`，需要 Facebook 账号和 `credentials.ini`，因此不计为活动用例或跳过项。程序能启动并退出 0。

`test_package`：`CONSUMER_RESULT 10/10`。

## 取数

```text
tests/Makefile.am: TESTS = gtestutils autoptr
tests/autoptr.c: 活动 g_test_add_func × 4
tests/gtestutils.c: g_test_add × 2，位于 #if 0 内
```

上游活动套件为 4 个用例；`make check` 运行两个测试程序，结果 2/2、SKIP 0。按源代码宏取数得到 6 个 `g_test_add*` 调用，其中 2 个在上游 `#if 0` 内，未注册，也不是被本适配跳过的用例；活动套件仍是 4/4。

## 已知限制

本机加载器会拒绝一部分「安装复制」出来的 `.so`，链接器刚写出的文件可以加载。2026-10-15 的修复已使 json-glib 测试运行库从固定 SHA-256 的官方源码重建，因此不再依赖 Conan 缓存中偶然存在的 json-glib 构建树。

## Perl/autotools 修复与最终真机复验（2026-10-13）

Conan 的 `perl/5.42.2` 工具需求会导出自己的 `PERL5LIB`。原配方只在 `/data/service/hnp/bin/perl` 不存在时清理该变量；CI worker 有这个 Perl 时，系统 Perl 会尝试加载 Conan Perl 的 `Cwd.so`。现在 `generate()` 与每个 shell 命令都清除 `PERL5LIB`、`PERL5OPT`、`PERL_LOCAL_LIB_ROOT` 等变量，并显式设 `PERL` 为可用的 Harmonybrew Perl（没有时回退到 HNP Perl）。设备上的 Harmonybrew Perl 5.44 加载 `Cwd` 成功。

配方同时把 `M4`、`ACLOCAL`、`AUTOMAKE`、`AUTOCONF`、`AUTOHEADER`、`AUTOM4TE`、`AUTORECONF` 与 `LIBTOOLIZE` 固定到 Harmonybrew/HNP 可用工具，避免自动落到 Conan 的 `aclocal` wrapper（该缓存包缺 `.aclocal-real`）。命令 PATH 保留 Harmonybrew 优先级，并补上 `/usr/bin` 与 `/system/bin` 供 configure 使用系统工具。`make` 并行度读取 `tools.build:jobs`。

最终实跑命令使用独立 `CONAN_HOME=~/work/psj/ch-libgfbgraph`、`tools.build:jobs=2`，并在 HarmonyOS AArch64 真机上强制从源码构建 `json-glib`，以便测试加载设备生成的共享库。`conan create` 退出码 0；`make check` 两个测试程序全部通过（TOTAL 2 / PASS 2 / SKIP 0 / FAIL 0）；活动上游用例 4/4（`autoptr` TAP `1..4`，四项均 `ok`）。`gtestutils` TAP `1..0`，其中两个上游调用仍处于 `#if 0`，不是活动用例或 skip。`test_package` 消费者断言通过 `10/10`。

## CI 修复（2026-10-15，构建 #92302 @ CI-019）

GOA 已从源码编过并打包。失败发生在 libgfbgraph 自己的 `configure`：`Package 'sqlite3', required by 'libsoup-3.0', not found`。同一份日志里 `sqlite3/3.49.1` 出现在 `Skipped binaries`（只作为 libsoup3 的传递依赖，二进制没装上），而 sqlite3/3.49.1 的 `package()` 只装静态库和头文件，没有 `sqlite3.pc`。日志末尾的 429 / 依赖未构建提示与这次 configure 输出对不上。配方把 `sqlite3/3.49.1` 列为直接依赖，并在 `pc-fix` 写入 `sqlite3.pc`，让 libsoup-3.0 的 pkg-config 依赖能被解析。消费者测试走同一条 `Requires` 链，`test_package` 同样补这份文件。

## CI 修复（2026-10-15，构建 #92572 @ CI-020）

完整 Buildbot `conan-build-test` 日志显示源码编译和两个测试程序链接均成功；`make check` 的 `gtestutils` 与 `autoptr` 都 FAIL（TOTAL 2 / PASS 0 / SKIP 0）。末尾 429、缺依赖、编译失败三条提示是通用提示，和本次失败原因不符。CI 没有打印 `tests/test-suite.log`。在真机以下载的 json-glib 二进制作为 `runtime-libs/libjson-glib-1.0.so.0` 目标重跑两个程序，均退出 127，加载器报告该库无法加载；指向链接器产出的 json-glib `.so` 后两者均通过。旧版配方扫描 Conan 缓存构建树，08:51 的通过依赖于此前强制从源码构建 json-glib 留下的 `.so`；CI 下载二进制，没有该构建树。

新配方在自己的 `build()` 中下载官方 json-glib 1.10.6 源码（SHA-256 `77f4bcbf9339528f166b8073458693f0a20b77b7059dbc2db61746a1928b0293`），以 `-j2` 编译测试运行库，并让 `runtime-libs` 指向新链接产物。Conan 依赖版本不变。使用 `CONAN_HOME=~/work/psj/ch-libgfbgraph`、`--build=missing`（**没有** `--build=json-glib/*`）的真机 `conan create` 退出 0；`make check` TOTAL 2 / PASS 2 / SKIP 0 / FAIL 0 / ERROR 0，活动上游用例 4/4，消费者 `CONSUMER_RESULT 10/10`。日志确认本次链接了 `json-glib-test-runtime/build/json-glib/libjson-glib-1.0.so.0.1000.6`。

## GOA CI 并行度与 EAGAIN 重试（2026-10-16）

CI #94039 的日志确认 GOA 因 glib override 无可用二进制而从源码构建。GOA 的 95 项 Ninja 构建被限为 `-j1`，随后虽然打包成功，整次 `conan create` 仍在 3600 秒限制处超时。现在只把 GOA 的 Meson compile 限在 `-j2`，以减少串行构建时间，同时约束 worker 进程数。CI #94114 又在 GOA Meson setup 遇到 `/system/bin/sh: can't fork - try again`；setup 现在捕获并回放 stderr，识别该信息为 EAGAIN，并按现有策略最多重试两次。配方仍保留针对 GOA 的 pkg-config 补齐。

设备复验使用 `CONAN_HOME=~/work/psj/ch-libgfbgraph`、`ohos-aarch64`，并以 `--build=gnome-online-accounts/* --build=libgfbgraph/* -c tools.build:jobs=2` 强制重编 GOA 与本配方。日志显示 GOA 从源码构建并打包，Meson 调用 `ninja ... -j 2`；整次 `conan create` 退出 0。`make check` 为 2/2（SKIP 0），活动上游用例 4/4，消费者 `CONSUMER_RESULT 10/10`。
