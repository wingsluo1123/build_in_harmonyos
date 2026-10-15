# perdition 2.2 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-10-14
- 编译器: clang (HMBS 注入)
- 状态: built (待真机预检)

## 编译步骤

最小依赖路径 (Path A)：关闭 OHOS 不可用的全部可选后端，只保留
gdbm + SSL，保证真机一次通过：

```bash
./configure --prefix=/ --build=x86_64-unknown-linux-gnu \
  --disable-mysql --disable-odbc --disable-pg --disable-cdb --disable-bdb \
  --disable-nis --disable-ldap --disable-pam --without-libidn \
  --with-ssl-includes=<openssl include> --with-ssl-libraries=<openssl lib> \
  CPPFLAGS="$CPPFLAGS -I<private prefix>/include -I<gdbm,openssl includes>" \
  LDFLAGS="$LDFLAGS -L<private prefix>/lib -L<dep libs>" \
  PKG_CONFIG_PATH="<private prefix>/lib/pkgconfig:...:$PKG_CONFIG_PATH" \
  ac_cv_prog_cc_works=yes
make -j1
make check   # perdition 本体无套件 no-op（rc 0）；另执行 vanessa_adt 4 个回归程序作上游证据
make install DESTDIR=<package>
```

# CPPFLAGS/LDFLAGS 必须 APPEND 到工具链环境（$CPPFLAGS/$LDFLAGS 携带
# OHOS --target/--sysroot），只允许探测/覆盖 CC 本身；直接赋值会洗掉
# sysroot 导致 `C compiler cannot create executables`（2026-10-13 预检）。

vanessa 三件套（logger 0.0.10 → adt 0.0.9 → socket 0.0.12，
与 2.2 同目录发布）在 `build()` 内按序源码编译进
`build_folder/prefix` 私有前缀（R49，不污染共享 `/usr/local`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | vanessa_* 在制品仓无发布，configure 报 `vanessa-logger >= 0.0.10` 缺失 | 三个支持库从未适配发布 | 在 build() 内从 2.2 同目录下载 tarball、校验 sha256、按 logger→adt→socket 顺序编进私有 prefix，PKG_CONFIG_PATH 指向它 |
| 2 | 2016 版 config.guess 不认识 HarmonyOS | 无 ohos case | 复用 radcli 模式：显式 `--build=x86_64-unknown-linux-gnu` 跳过 guess，并在 config.guess 内联 HarmonyOS→Linux 映射 |
| 3 | configure/config.status `umask 077` 在 HMDFS 上 Permission denied | 077 目录 drwx--S--- 写不进 subs1.awk | 构建内把 `umask 077` 改 `umask 022`（源码树 configure/config.status）+ TMPDIR 钉到可写任务 tmp |
| 4 | install-exec-hook 用 `ln -f`/`ln -sf` 建协议别名 | HMDFS 无 symlink/hardlink | 构建内重写为 `cp -p`（只换安装工具，不碰二进制与测试） |
| 5 | NIS `yp_match`、libidn `stringprep` 在 OHOS 缺失 | 可选后端硬依赖 | `--disable-nis --without-libidn` 等全部可选后端关闭（见上） |
| 6 | 真机预检在依赖构图阶段即失败：`popt/1.16` 走 conancenter 重编，`configure: error: cannot run /data/service/hnp/bin/bash .../config.sub`（HMBS chmod=0，外部配方未做 CONFIG_SHELL=/bin/sh + 显式 --build 硬化） | 外部依赖配方不受 HMBS 沙箱约束，`requires("popt/1.16")` 边必然重编失败 | 删除 `requires("popt/1.16")`，将 popt-1.16 官方 tarball（与 archives/p/popt/1.16 同 sha）以内建方式编进 `build_folder/prefix` 私有前缀，复用 vanessa 三件套同套硬化（out-of-tree、CONFIG_SHELL=/bin/sh、仅 --build、无 --host、可写 TMPDIR、umask 022），perdition configure 经 prefix 的 CPPFLAGS/LDFLAGS 自动找到 vendored popt |
| 7 | 内建依赖后真机 `checking for gcc... /data/service/hnp/bin/clang` 接 `C compiler cannot create executables`（Error 77，vanessa logger build） | 自建 configure 把 `CPPFLAGS="-I..."`/`LDFLAGS="-L..."` 绝对赋值，洗掉了工具链环境的 OHOS `--target/--sysroot`，clang 即使路径正确也链不出可执行 | 改为 APPEND 形态 `CPPFLAGS="$CPPFLAGS -I..."`/`LDFLAGS="$LDFLAGS -L..."`/`PKG_CONFIG_PATH="<prefix>:$PKG_CONFIG_PATH"`，只探测/覆盖 CC（先用配置 CC `--version`，不行再回退 PATH 的 cc/clang/gcc），全程保留 flags；configure 失败时打印 CC/version/flags 并转储 config.log 尾部与库路径取证 |

## 源码修改

无 `.patch` 文件（`patches: {}`）。全部可移植改动在 `build()` 内完成：
config.guess 映射、umask 022、install ln→cp、vanessa_logger syslog extern 宏守卫。无 `__OHOS__` 宏注入。

## 依赖版本

- gdbm/1.24（makegdbm + perditiondb_gdbm）
- openssl/3.5.6.1（SSL/TLS）
- popt 1.16（vendored：conancenter popt/1.16 在 HMBS 沙箱内重编失败
  `configure: error: cannot run /data/service/hnp/bin/bash .../config.sub`
  （2026-10-13 预检，chmod=0/hardlink=0），故与 vanessa 三件套同样编进
  `build_folder/prefix` 私有前缀，不再保留 `requires("popt/1.16")` 边；
  tarball 与 archives/p/popt/1.16 同源，sha256 校验）
- vanessa_logger 0.0.10 / vanessa_adt 0.0.9 / vanessa_socket 0.0.12（vendored）

## 验证结果

- 上游测试：perdition 2.2 本体无套件（`make check` no-op，rc 0，日志见
  hmbs_make_check.log）；可计数证据 = 内建 vanessa_adt 0.0.9
  test/Makefile.am noinst_PROGRAMS（4 个：dynamic_array/list/hash/config_file），
  配方在 build() 内构建并真机执行，退出码唯一计数源，
  输出 `HMBS_UPSTREAM_TEST_RESULT` status `passed` (4/4)。审计见
  `test_package/MANIFEST.yml` 的 `upstream_test_audit`（total 4、
  口径 autotools_tests）。
- 新增测试：`test_package/test.sh` 2 项（`perdition --help` 横幅 +
  `makegdbm` gdbm 写读回环），输出 `HMBS_TEST_PACKAGE_RESULT`
  discovered 2 / passedCount 来自 `^ok N: ` 行计数。
- 在 HarmonyOS aarch64 环境实测（以真机预检日志为准）。

## 交付物

| 文件 | 说明 |
|------|------|
| sbin/perdition 及 pop3/pop3s/imap4/imap4s/imaps/managesieve 别名 | 邮件代理主程序 |
| bin/makegdbm | gdbm 建库工具 |
| lib/perdition/*.so | map 库（含 gdbm 后端） |

## 注意事项

- tremendously old autotools（2016）：不要升级 config.guess/sub 文件本身，
  用 `--build` + 内联映射即可。
- vanessa trio 必须按 logger→adt→socket 顺序装进同一个私有 prefix，
  否则 adt/socket 的 configure 找不到 vanessa-logger.pc。
| 8 | 上轮探针未触发回退：`if ! "$CC" --version 2>&1 | head` 以 head 状态为准，坏 CC 恒判可用，日志 `probe CC=/data/service/hnp/bin/clang` → `inaccessible or not found` → 仍 `using CC=...` → Error 77 | 管道掩盖版本探测失败；且 profile 的 `/data/service/hnp/bin/clang` 在预检沙箱内不可执行， bare `command -v` 首选也可能命中同一坏路径 | 版本测试去掉管道（`>/dev/null 2>&1` 无 pipe），显示才用 `| head`；回退改为逐个验证 clang/cc/gcc 可运行性，首个不可用即扫描余下，皆无则 exit 99 明示；取证扩展 PATH/which/conanbuild.sh 与 toolchain 命中行，便于下轮确认真机可用编译器 |
| 9 | vanessa_logger 编译失败：`vanessa_logger.c:680:14: error: expected ')'` + `extern CODE facilitynames[]` 被展开为 `((CODE *)(const CODE []){...}`（OHOS syslog.h:82 宏定义），连带 9 errors | OHOS syslog.h 把 facilitynames/prioritynames 定义为宏（compound literal），而 vanessa_logger-0.0.10 沿 glibc 假设做 `extern CODE facilitynames[]` 声明；configure 的 `AC_CHECK_DECLS` 在未含头时判未声明，保留 extern，预处理后成非法代码 | 双保险：① configure 追加 `ac_cv_have_decl_facilitynames=yes ac_cv_have_decl_prioritynames=yes`（复用 FreeBSD r323950 同类修复），跳过 extern；② 构建内对 `vanessa_logger.c` 的 extern 加 `#ifndef facilitynames/prioritynames` 守卫，宏存在时跳过声明、后续使用走宏，非宏 libc 保持原声明 |
| 10 | perdition configure fail: checking for pkg-config... no + VANESSA_LOGGER... no (2026-10-13 preflight) | true machine has no pkg-config binary; recipe only exported PKG_CONFIG_PATH, PKG_CHECK_MODULES hard-errors without the tool | vendor minimal python3 pkg-config shim into build_folder/prefix/bin (answers --exists/--cflags/--libs/--modversion/--atleast-version for vendored .pc), pass PKG_CONFIG=shim + PATH prefix/bin prepend, plus direct VANESSA_*/LIBVANESSA_*/POPT *_CFLAGS/_LIBS overrides as fallback |
| 11 | vanessa_logger configure 即失败且无 config.log（2026-10-13 预检：conanbuild*.sh missing 伴随、`vanessa_logger/config.log missing`、`_build_vanessa_trio` line 568 Error 1；HMBS chmod=0/hardlink=0） | ① tarfile 解出的 `configure` 无 +x 而 `os.chmod` 在 HMDFS 上是 no-op，直接执行 `./configure` 报 Permission denied，还没写 config.log；② 真机无 pkg-config，adt/socket 的 configure 即使到下一步也会因找不到 logger .pc 而失败，但 shim 在 trio 之后才写；③ shim 本身 open() 默认 0644，无 +x 则 `PKG_CONFIG=<path>` 不可执行 | ① 三处 configure（trio/popt/perdition）一律经 `/bin/sh "configure"` 显式解释执行，不依赖 exec 位；② `_write_pkg_config_shim` 提前到 trio 之前，trio/popt 亦传 `PKG_CONFIG="<HMBS_PYTHON3> <prefix>/bin/pkg-config"`（无需 +x）+ PKG_CONFIG_PATH；③ shim 改用 `os.open(...,0o755)` 建时即带执行位，chmod 仅作 best-effort；perdition 侧 `PKG_CONFIG` 改引号包裹的 `"<py> <shim>"` 并追加 `ac_cv_path_PKG_CONFIG` 缓存 |
| 12 | `package()` 的 `make install` 在 `etc/perdition` 报 `install-perditionconfDATA Error 64`（2026-10-14 预检；trio/主构建/`make check` 已过） | 上游 `etc/perdition/Makefile.am` 的 `perditionconf_DATA = perdition.conf popmap Makefile.popmap` 是 3 文件一批的 `install -c -m 644` 调用，而 HMBS 宿主 install 垫片仅支持单文件、不支持 `-c/-m` 分离参数（同类已收录：SKILL_FEEDBACK_9b98d363 第 5 条 pkginclude 多文件头 Error 64；b93877d6 `cp: bad '755'`） | `package()` 的 `make install DESTDIR` 改用上游自带 `install-sh` 经 `/bin/sh` 驱动：`INSTALL="/bin/sh <src>/install-sh -c" MKDIR_P="/bin/sh <src>/install-sh -c -d"`（不碰上游 Makefile 与测试口径；`install-data-hook` 的 `ln -sf` 保持，HMBS symlink=1 支持） |
| 13 | CI #91049 在 vanessa_logger configure 报 `checking whether the C compiler works... no` + `C compiler cannot create executables`（Error 77），伴随 `configure: can't fork - try again`；而紧邻其上的探针 `clang --version` 成功，CFLAGS/CPPFLAGS/LDFLAGS 来自 conanbuild 且 `Generators folder: .../build-release/conan` 证明工具链已生成 | 配方把 CONFIG_SHELL/SHELL 及显式解释器全部硬编码为 `/bin/sh`：CI profile buildenv 指定的工作 shell 是 `/data/service/hnp/bin/bash`（gdbm 等成功包经 Autotools helper 默认用它），硬编码 sh 在 CI worker 上 fork 失败，连带编译器存活检查失败；反之 HMBS 真机只有 `/bin/sh` 可用（hnp bash 路径不存在，见 #6），硬编码任一端都会破坏另一端。另取证有两处误导：① 在 build_folder 直查 conanbuild.sh 报 missing，实际生成在 build_folder/conan/ 子目录；② config.log 只转储尾部 40 行（恒为变量 dump 区），真正的 conftest 错误在文件前部 | 新增 `_config_shell()`：优先用环境自带的 CONFIG_SHELL/SHELL（CI 即 hnp bash，HMBS 即 /bin/sh），校验可执行后回退到 `/bin/sh`→hnp bash；trio/popt/主构建/make check/package 全 10 处调用改用该值（含显式 `\"<sh>\" \"configure\"` 与 INSTALL/MKDIR_P 的 install-sh 驱动），并打印 `using shell ...` 便于下轮核对；取证同步修正（conan/ 子目录双路径 + config.log 错误段上下文 60 行）。未动测试口径与 flags 语义 |
| 14 | CI #91093 vanessa_logger configure `can't fork - try again`（line 33），探针 CC=/data/service/hnp/bin/clang --version 成功后仍失败，`using shell /bin/sh` | build() 内 `os.environ` 拿到的是外层 worker 环境（SHELL=/bin/sh），不是 Conan profile buildenv（CONFIG_SHELL/SHELL=hnp bash，仅在 self.run(env=conanbuild) 内生效）；“优先环境”仍选到 CI 上不能 fork 的 /bin/sh | `_config_shell()` 改为按文件系统存在性优先 hnp bash（CI 存在即用，HMBS 缺失则回退 /bin/sh）；test_package 同步同规则，不再把 hnp 强制改回 /bin/sh |
