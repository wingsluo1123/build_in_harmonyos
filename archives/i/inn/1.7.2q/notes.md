# inn 1.7.2q 适配笔记

## 编译环境

- 构建系统: custom-make（INN 1.x 自有配置机制：config.data + subst，无 configure 脚本）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4 (HarmonyOS PC / aarch64)
- 状态: built（首轮工作树；待 HMBS 真机预检验证后更新）

## 上游版本说明

上游 ISC 从未发布名为 `1.7.2q` 的压缩包（其历史归档只有
`inn-1.7.2.tar.gz`，见 `https://downloads.isc.org/isc/inn/OLD/1.7/`）。
`1.7.2q` 是 Debian/Ubuntu 发行版线对 INN 1.x 的 canonical 版本号
（Debian 源码包 `inn_1.7.2q.orig.tar.gz`，经 pristine-tar 在 Debian 与
Ubuntu 间共享同一字节流；Ubuntu Launchpad 仍可直接下载，2026-10-15
实测 1231867 字节，sha256 见 conandata.yml）。因此 conandata 指向
发行版官方归档——官方源在此版本号下不存在对应字节的归档，
沿用 R39 字面要求反而会造成 sha256 失配。

## 编译步骤

```bash
# 1. config.data 由配方按 conan conf 生成（config.dist 为模板）
#    关键取值：CC=<hnp clang> CFLAGS='$(DEFS) -std=gnu17 -O2 -g'
#    LIBS 为空，PERL_SUPPORT/TCL_SUPPORT=DONT，安装根全部指向包目录
# 2. 构建 subst 工具（C 版失败时自动回退到 subst.sh）
make subst -j1                          # 顶层目标，实际在 config/ 执行
# 3. 只做替换，跳过需要 perl 的 interpreters 步骤（本机无系统 perl）
make substitutions -j1                  # 在 config/ 执行
sh ./checkconf.sh config.data           # 先行：TAB 分隔校验（配方内自动跑）
# 4. dbz.c 需要的 <dbz.h> 由上游规则显式生成
make ../include/dbz.h -j1               # 在 lib/ 执行
# 5. 按依赖顺序构建（lib 最先，其余目录经 $(LIBNEWS) 规则自保障）
for d in lib frontends innd nnrpd backends expire doc site; do
    make -j1 all   # lib 用 install 目标亦可，效果相同
done
# 6. 逐目录安装（从不执行顶层 make install，见下表问题 3）
for d in lib frontends innd nnrpd backends expire doc site; do
    make -j1 install
done
cp libinn.a <包>/lib/ ; cp include/*.h <包>/include/
```

`make check` 不存在——上游无测试套件（见“上游测试审计”）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure 可调，平台/路径如何注入 | INN 1.x 用 config.data + subst 做配置，不认 --build/--host | 配方从 config.dist 生成 config.data：工具链取自 Conan conf（R33），安装根指向包目录 |
| 2 | `make all/quiet` 在 config 步需要 perl | `interpreters` 目标跑 `perl fixinterps.pl`，本机无系统 perl（同 inn2 的 --without-perl 原因） | 只跑 `make substitutions`，跳过该步；PERL_SUPPORT=DONT 使 perl.c 编译为空桩 |
| 3 | 顶层 `make install` 在沙箱必失败 | `makedirs.sh` 无条件 `chown news`，环境无 news 账号/chown | 逐目录 `make install`（Debian 的 DESTDIR 补丁思想，见 0006）；`installit.sh -O/-G` 非 root 自动跳过 chown |
| 4 | `dbz.o` 编译找不到 `<dbz.h>` | `dbz.c` 用尖括号包含它，但上游只在 `depend` 链里生成 | 构建 lib 前显式执行上游 `make ../include/dbz.h` 规则 |
| 5 | `nnrpd/loadave.c` 在非 glibc 上无 `<nlist.h>` | 上游 `#ifdef linux` 分支假设 glibc，Debian 改用的 `__GLIBC__` 在 musl 下走向 nlist 分支同样失败 | 自研补丁 0007：`linux \|\| __linux__` 走 /proc/loadavg 分支（无平台宏，PF5 干净） |
| 6 | `config/subst.c` 的 `xstrerror` 依赖 `sys_errlist` | 该符号已移出 POSIX，部分现代 libc 不再提供 | 自研补丁 0008：无条件使用 POSIX `strerror()` |
| 7 | `lib/Makefile` 把 `ar` 写死 | 真机 ar 可能只有 llvm-ar 名字 | 自研补丁 0009：新增 AR 配置钮，配方注入 |
| 8 | K&R/隐式声明在新编译器下告警成灾 | 1997 年 C 代码，大量 K&R 原型 | Debian -52 方案：`-std=gnu17`（clang 15 默认即 gnu17，配方显式钉死）+ 0001~0005 编译器兼容补丁 |
| 9 | `sh ./checkconf.sh config.data` 在真机报 Error 1（补丁全过之后首次暴露） | 生成的 config.data 按构造不可能缺 TAB（本地复算 0 缺行）；checkconf.sh 走 sed/grep/diff 管线，真机为 toybox 用户态（见 knowledge E010 及 toybox-grep BRE 笔记），疑为 shell 工具差异致误报；已核实脚本内 grep 用的是字面 TAB而非 `\t` 转义 | 配方 `_write_config_data` 后加无 shell 依赖的 Python TAB 自检（已在真机验证通过而 shell 检查仍失败，坐实文件无缺陷），与 0010 补丁将 checkconf.sh 改写为仅用 shell 内建的同等检查（保留生产环境执行该脚本的原有调用）（缺行报 repr 明细，通过记行数；shell 原检查保留，make 的 substitutions 内也会再跑一次） |

| 10 | Clang absolute path ENOENT | profile pins CC to DevBox path missing on preflight | conf verifies executable then PATH/SDK fallback |


| 11 | subst Line 918 too long after compiler fix | appended AR key left config.data without trailing newline; subst fgets treats unterminated last line as too long | always terminate config.data with newline |
| 12 | subst link EPERM on backends Makefile | subst mv() uses link()+unlink(), preflight FS hardlink=0 | 0011 patch enables upstream USE_RENAME rename() path |
| 13 | `lib/parsedate.y` 构建报 `yacc: No such file or directory` | 真机 PATH 无 yacc/bison；曾改 `tool_requires bison/3.8.2`，但其经 conancenter 解析并拉起 m4/flex 源码构建，在预检报 `/data/service/hnp/bin/bash: inaccessible or not found`（Error 127） | 改走预生成路线：`files/parsedate.c` 为已打 0001 补丁的 parsedate.y 经 `bison -y` 产物（与 Makefile 期待一致：6 shift/reduce 冲突，`int date_lex()` 全局），build() 内 `_stage_parsedate()` 覆盖到 `lib/parsedate.c` 并 touch 到新于 .y，使 `parsedate.c: parsedate.y` 恒最新，YACC 永不执行；无新增外部依赖 |
| 14 | `lib/remopen.o` 报 `conflicting types for 'ntohs'/'htons'`（`make -j1 all` 在 lib 目录 Error 1；同文件 `innd/rc.c` 含同类 `htons` 旧声明，修 lib 后必爆） | 1997 年 K&R 写法 `extern unsigned short ntohs()/htons();`（无参原型）在 C2x 下被视为零参声明，与 musl `<arpa/inet.h>` 的 `uint16_t ntohs(uint16_t)` 真原型冲突；0003 只补了头文件未删旧声明，`!defined(ntohs)` 对函数名恒真故旧声明仍生效 | 自研补丁 0012：删 `lib/remopen.c` 两处旧声明（以 0003 引入的 `<arpa/inet.h>` 为准）、删 `innd/rc.c` 的 `htons` 旧声明（以 0002 经 `innd.h` 引入的同头文件为准，保留 `#if 0` 的 `htonl` 注释块不动）；无平台宏，PF5 干净 |
| 15 | `make install` 在 frontends 报 `cp: .../bin/rnews/<tmp>: Not a directory`（`.../bin/rnews/c7unbatch` Error 1） | 配方把 `_PATH_RNEWS`（rnews 二进制文件）与 `_PATH_RNEWSPROGS`（c7unbatch/decode/encode 脚本目录）都配成包内 `bin/rnews`；先装上的 rnews 文件挡住同名目录创建，上游默认本就是 `bin/rnews`（文件）vs `bin/rnews.libexec`（目录） | `_PATH_RNEWSPROGS` 改为包内 `bin/rnews.libexec`（恢复上游命名区分），package() 预建该目录；`_PATH_RNEWS` 保持 `bin/rnews` 不动 |


## 源码修改

| 补丁 | 来源 | 修改内容 |
|------|------|----------|
| `0001-parsedate-yacc-prototype.patch` | Debian `parsedate_gcc4` 原样 | `date_lex` 去 static + 原型，供现代 yacc/bison 生成代码调用 |
| `0002-use-system-prototypes.patch` | Debian `use_system_prototypes` 原样 | 删冲突的自声明（optind/exit/malloc/strcpy…），补系统头文件；NORETURN 改 attribute 写法 |
| `0003-implicit-declarations.patch` | Debian `implicit_decls` 改编 | 只保留非 perl 部分（缺的头文件 + `static int` 修正 + RCfix_options 原型）；Debian 版中依赖 insync 的 timer.c/nc.c/DO_PERL  hunks 在本树无着落，已剔除 |
| `0004-inet-addr-return-type.patch` | Debian `inet_addr_is_int` 原样 | `inet_addr` 返回 int 而非 long（LP64 正确性） |
| `0005-overlapping-strcpy-memmove.patch` | Debian `overlapping_strcpy` 原样 | nnrpd 发文路径的重叠拷贝改 memmove |
| `0006-makefile-destdir-support.patch` | Debian `misc_makefiles` 原样 | frontends 安装支持 DESTDIR、makedirs DESTDIR 感知、subst 构建透传 CPPFLAGS/CFLAGS/LDFLAGS |
| `0007-loadave-linux-proc.patch` | 自研 | 见上表问题 5 |
| `0008-subst-strerror-portable.patch` | 自研 | 见上表问题 6 |
| `0009-lib-makefile-ar-knob.patch` | 自研 | 见上表问题 7；config.data 由配方追加 AR 键 |
| `0010-checkconf-builtins-tab-check.patch` | 自研 | checkconf.sh 的 TAB 检查改用 shell 内建命令（while/read/case），不再依赖 sed/grep/diff；与原脚本在好/坏文件上行为一致（rc 0/1 与上报格式相同） |
| `0011-subst-use-rename.patch` | 自研 | subst 落盘改用上游预留 USE_RENAME 的 rename() 路径，不再 link()+unlink()（见上表问题 12） |
| `0012-byteorder-system-prototypes.patch` | 自研 | 见上表问题 14；`lib/remopen.c` 删 `ntohs`/`htons` 旧声明，`innd/rc.c` 删 `htons` 旧声明，均以系统 `<arpa/inet.h>` 原型为准 |

12 个补丁已用 `git apply --check` + `--apply` 在原始树上按序验证通过。
真机曾报 0003 在 lib/tempname.c 打不上（hunk 起始行 -39 实为 -37，conan 严格校验不容忍偏移）；已将 0002/0003/0004/0007/0008 的 hunk 头按顺序应用位置精确化并修复 0007 第二 hunk 头前导空格，现 12 补丁零偏移通过（0012 已用 `git apply --check` 在 0003 应用后状态验证通过）。
Debian 原补丁统一归一化为 `a/`/`b/` 前缀（strip=1）；0002 保留了上游
subst.c:40 的 formfeed 上下文行（字节级核对过）。

## 依赖版本

无外部库依赖（LIBS 为空；crypt/setproctitle 等均走 libc 自带或已关闭）。
`lib/parsedate.c` 由 `files/parsedate.c` 预生成产物直供（已打 0001 补丁的 parsedate.y 经 `bison -y` 生成，68KB，`int date_lex()` 全局，6 shift/reduce 冲突与 Makefile 回显一致），
build() 内 `_stage_parsedate()` 将其覆盖到 `lib/` 并 touch 到新于 `parsedate.y`，使 `parsedate.c: parsedate.y` 规则恒跳过——真机无需 yacc/bison（此前两条路线均已证伪：PATH 探测回退为字面 `yacc` 必 ENOENT；`tool_requires bison/3.8.2` 经 conancenter 拉起 m4 源码构建报 `bash: inaccessible or not found`）。

## 上游测试审计

`inn_1.7.2q.orig.tar.gz`（381 项，顶层 `inn-1.7.2/`）无 `tests/` 目录；
全部 10 个 Makefile（顶层 + config/lib/frontends/innd/nnrpd/backends/
expire/doc/site）无 `check`/`test` 目标（严格规则 `^(check|test)\s*:`；
唯一沾边的是 lib 的
`parsedate` 手工调试 helper，不是测试；config 的 `sedtest` 是 sed 能力
探针，`lib/checkart.c` 是库源文件，`samples/inncheck` 是运行时脚本，
均不构成测试）。配方在真机 build() 内重复
该扫描并输出 `HMBS_UPSTREAM_TEST_RESULT`（status `no_tests`，
discovered/executed 均为 0），test_package 复发该标记。

## 验证结果（待真机预检回填）

```bash
$ clang test_inn.c -o test_inn -I$PREFIX/include $PREFIX/lib/libinn.a && ./test_inn
# 预期：20/20 ok（wildmat 9 + Radix32 6 + GetTimeInfo/parsedate 4 + INNVersion 1）
$ convdate -n "Thu, 01 Jan 1970 00:00:00 GMT"
0
```

以上为设计值：RFC 822 向量 `Sun, 06 Nov 1994 08:49:37 GMT = 784111777`
与 epoch 边界向量均与时区无关（含显式 GMT），Radix32 向量经手工验算。
真机实测数字以预检日志为准，本轮不预填通过率。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libinn.a` | 基础库：wildmat/parsedate/qio/dbz/clientlib 等 |
| `bin/` | innd/inndstart/nnrpd/inews/rnews/ctlinnd/convdate/expire 系/backends 系等约 40 个可执行文件及配套脚本 |
| `etc/` | inn.conf/hosts.nntp 等示例配置（site 安装产物） |
| `include/*.h` | 公开头（libinn.h/clibrary.h/configdata.h/paths.h 等，均为已替换后版本） |
| `share/man/` | man1/3/5/8 文档页（SOURCE 风格纯拷贝，无需 nroff） |
| `res/upstream_test_result.json` | 真机上游审计结果（供 test_package 复发标记） |

## 注意事项

- 许可证：1.x 源码携带历史 Rich Salz/ISC 许可文本（见上游 COPYRIGHT），
  conanfile.py 的 license 字段沿用同系列 inn2/2.7.4 的 `ISC` 声明。
- 本包同时提供库与可执行文件，`package_type = "application"`，软件级目录带 `commands.json`（R38）；`cpp_info.libs = ["inn"]`，`bindirs = ["bin"]`。
- 二进制内 baked 的默认路径指向包目录（与 inn2 相同的不可重定位权衡）；spool/log 等运行时目录保持上游默认（/var/news…），由部署时创建。
- `inews -m 02555` / `rnews -m 04550` 的 setuid 安装位由属主 chmod 设置，hmdfs 下 chmod 被忽略但返回成功，不阻塞安装。
- 含 perl/tc l 的示例脚本（innmail/innlog.pl 等）随包安装但需 perl5 才能运行，本机无 perl——与 Debian 删除 innmail 的处理不同，这里选择保留脚本+文档说明（test_package 不覆盖它们）。
- Debian 的 insync 功能升级补丁（dbz 3.3/largerhash/actived 等）属行为变更，未纳入本次基础适配；如真机/CI 需要再议。
- `makedirs.sh` 从未执行：包内目录由配方预建，`make install` 的各目标目录均已存在故跳过 chown 逻辑。
