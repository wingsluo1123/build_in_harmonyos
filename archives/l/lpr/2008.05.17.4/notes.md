# lpr 2008.05.17.4 适配笔记

## 编译环境
- 构建系统：**手写 Makefile（无 configure）**。顶层 Makefile 只是
  `for dir in $(SUBDIR); do $(MAKE) -C $$dir; done` 一层循环；真正的规则在
  `common_source/Makefile.in`，被 8 个子目录 Makefile 用 `include ../Makefile.in` 引入。
- 编译日期: 2026-10-05
- 编译器: OHOS SDK clang 15.0.7，target `aarch64-unknown-linux-ohos`（`-pr:h=ohos-aarch64-wsl-xbuild -pr:b=default`）
- 状态: **built**（conan create 干净构建 rc=0 + test_package 静态段 72/72 通过；
  本地 qemu-aarch64 真机模拟下 8 个程序全部实际执行过，见下"执行验证"）

## 取源
- URL: https://deb.debian.org/debian/pool/main/l/lpr/lpr_2008.05.17.4.tar.xz
  sha256=`2f65cb4097b5386ffbce6051785576b7dfb40ac5951e69ca86ed2ad6b564a608`（81804 字节）
- 2026-10-05 实测 HTTP 200；sha256 与同目录 `lpr_2008.05.17.4.dsc` 的
  Checksums-Sha256 段逐字节一致（`2f65cb40…64a608`），本地重算同值。
- **为什么取 Debian 而不是上游 OpenBSD**：任务串版本 2008.05.17.4 就是这个
  **native** tarball 的上游版本号（dsc: `Format: 3.0 (native)` /
  `Version: 1:2008.05.17.4`，维护者 Michael Tokarev 2026-02-04 采用并重传）。
  上游 OpenBSD 的 CVS 归档早已下线、GitHub 无对应 tag/发布件，Debian 归档是目前
  唯一能 HTTP 200 取到该版本原样源码的一手渠道。native tarball 内自带 `debian/`，
  因此不存在单独的 `.debian.tar.*` 组件 —— 这与 `lpr_2008.05.17.3+nmu*` 那些非 native
  上游包不同，判版本时别按 3.x 的经验去 pool 里找 `-2.debian.tar.xz`（实测 404）。

## 编译步骤
1. `conan create . --name=lpr --version=2008.05.17.4 -pr:h=ohos-aarch64-wsl-xbuild
   -pr:b=default --build=missing`（WSL 原生盘 ext4，构建目录在 conan 缓存
   `/root/.conan2/p/b/lpr15889e219e562/b`）。
2. 配方逐个子目录跑 `make CC=<驱动包装> CFLAGS=<见下>`，共 8 轮，全部 rc=0。
3. 产物 8 个程序：`bin/{lpr,lpq,lprm,lptest}` + `sbin/{lpc,lpd,lpf,pac}`
   （切分沿用上游 `debian/install`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 6 个程序全部 `error: unknown type name 'u_int'`（lp.h:102） | musl 的 `<dirent.h>` 直接 `#include <bits/alltypes.h>`，**不经过 `<sys/types.h>`**；而 `lp.h` 只 include 了 `<dirent.h>`。glibc 侧的同名代码因为 dirent.h 拉到了 sys/types.h 才没事 | 编译旗标 `-include compat/lpr_ohos_compat.h`，该头第一件事就是 `#include <sys/types.h>`。同时 `setresuid/setresgid/getifaddrs/freeifaddrs` 在 musl 里关在 `_GNU_SOURCE` 后面，一并 `-D_GNU_SOURCE` |
| 2 | `lpd` 编译报 `TTYDEF_CFLAG / TTYDEF_IFLAG / TTYDEF_LFLAG / TTYDEF_OFLAG` 未声明，且 `CTRL()` 被当成未声明函数 | glibc 的 `<termios.h>` 会 include `<sys/ttydefaults.h>`（glibc termios.h:104）；musl 的不会 | 同一头里 `#include <sys/ttydefaults.h>`。**该头文件在 OHOS sysroot 里本来就有**（`/mnt/c/Users/13909/ohos-sysroot/usr/include/sys/ttydefaults.h`，值就是 Linux 那套：TTYDEF_CFLAG = CREAD\|CS7\|PARENB\|HUPCL），所以这是"复现 Debian 在 glibc 上得到的同一组宏"，不是自己编值 |
| 3 | `lpr`/`lprm`/`lpc`/`pac` 链接失败：`undefined symbol: rresvport_af` | glibc 从 2.2.5 起导出 4.4BSD 遗留接口 `rresvport_af`（`<netdb.h>` 声明，`nm -D` 可见 `U rresvport_af@GLIBC_2.2.5`——反向核对：Debian 官方 `lpr_2008.05.17.4_amd64.deb` 的 lpd 就是这么链上的）。musl 既不声明也不导出 | `compat/lpr_bsd_compat.c` 按 4.4BSD/OpenBSD 语义实现（绑定 `*alport`，EADDRINUSE 就往 IPPORT_RESERVED 递减）。这是协议要求的功能不是可选装饰：lpd 必须能在特权端口上接受回连 |
| 4 | `lpd` 链接失败：`undefined symbol: innetgr` | 同上，`innetgr()` 也是 glibc 导出的 BSD netgroup 遗留接口（`<netdb.h>`），musl 没有。调用点在 `lpd/rcmd.c:165,182,199,212`，处理 `/etc/hosts.lpd`、`/etc/hosts.equiv` 里 `+`/`-` 与 `@`（domain）条目 | 同一文件里实现：解析 `/etc/netgroup`，host/user 为 NULL 表示"任意列匹配"，`@domain` 与 fqdn 尾段比较。简化边界（不做 NIS、不解释 netgroup 字段里的 `+`/`-`）写在该文件头注释里 |
| 5 | 兼容目标文件没地方塞 | 上游链接规则是 `$(CC) -o ${PROG} ${OBJ}`，**既不吃 `LDLIBS` 也不吃 `LDFLAGS`**，命令行上没有位置 | 配方生成编译器驱动包装脚本 `cc-ohos-wrap`：编译/预处理步骤（`-c`/`-E`/`-S`/`-M`/`-MM`）原样 exec 真驱动；**仅**当是链接步骤且 `-o` 目标程序在白名单里时在末尾追加兼容 .o。白名单 = 6 个真正引用这两个符号的程序。`lpf`/`lptest` 是单文件程序、不引用，因此完全不被注入 |
| 6 | 子目录 Makefile 的 `CFLAGS+=-I${.CURDIR}/../common_source` 失效 | `${.CURDIR}` 是 **BSD make** 语法，GNU make 把它当成名为 `.CURDIR` 的空变量，于是 CFLAGS 里留下悬空的 `-I/../common_source` | 用绝对路径 `-I<source>/common_source` 从命令行整段覆盖 CFLAGS。Debian 是靠 `debian/rules` 传 `-I../common_source` 补的（GNU make 下那个相对路径恰好对每个子目录都成立），配方用绝对路径更稳 |
| 7 | 顶层 Makefile 的 `all` 在 POSIX sh 下会炸 | 失败分支用了 `return 2` —— 这是 csh 的关键字，dash/busybox sh 直接报 "return: can only `return' from a function" | 配方不调顶层 `all`，改为逐个子目录 `make`，既能定位到具体失败目录，也绕开这条 csh 残留 |
| 8 | 第一次 conan create 报 `compat/lpr_ohos_compat.h was not exported` | 配方写了 `basic_layout(self, src_folder="src")`，于是 `source_folder` = `<cache>/s/src`，而 `export_sources()` 的产物落在 `<cache>/s/compat` —— 两者错开 | 改回默认 `basic_layout(self)`（`archives/a/abiword-plugin-clarisworks/3.0.8` 第 127-128 行记的就是这条） |

## 源码修改
**无**（`patches_applied=[]`）。全部适配在配方层：
编译旗标（`-D_GNU_SOURCE -D__KAME__ -include compat/lpr_ohos_compat.h -O2`
+ 绝对 `-Icommon_source`）、`compat/` 下两个新文件、链接期注入的驱动包装脚本。
`-D__KAME__` 是照抄 `debian/rules` 的 `DEB_CPPFLAGS_MAINT_APPEND`，打开
`common.c:391` 的 link-local IPv6 scope_id 处理；musl 的
`struct sockaddr_in6` 也有 `sin6_scope_id`，`IN6_IS_ADDR_LINKLOCAL` 同在，实测编译通过。

## 依赖版本
无 conan 依赖（`dependencies=[]`）。8 个程序只链 libc：
每个 ELF 的 `NEEDED` 只有 `libc.so`，解释器 `/lib/ld-linux-aarch64.so.1`。

## 验证结果

### 构建 + 消费者断言
```
conan create . -pr:h=ohos-aarch64-wsl-xbuild -pr:b=default --build=missing  → EXIT_RC=0
  lpr: compat object built for aarch64 (4144 bytes)
  lpr: all 8 programs built as aarch64 ELF64
  TPRESULT PASS (72 passed, 0 failed)
```

### ELF 静态核对（8/8）
- `ELF64` / `2's complement, little endian` / `Machine: AArch64` / `Type: DYN (PIE)`
- `NEEDED: libc.so`，`interpreter /lib/ld-linux-aarch64.so.1`
- `__*_chk`（FORTIFY）引用 0 个，**唯一例外**：`lpd` 引用 1 个 `__fd_chk`。
  这不是缺陷 —— `__fd_chk` 是 **OHOS SDK 自己**的钩子：`sysroot/usr/include/sys/select.h:33`
  把 `FD_SET/FD_CLR` 包了一层越界检查（lpd 用 select()）。真机 OHOS libc 导出该符号。

### compat 符号作用域（配方与 test_package 双重断言）
逐个 ELF 解析 `.symtab`，确认：
- 6 个消费者（lpc/lpd/lpq/lpr/lprm/pac）：`rresvport_af` 与 `innetgr` 都是
  **本地已定义函数**（`st_shndx != SHN_UNDEF`），且不在未定义集合里
  → 既没有链接失败，也没有悬空 libc 引用。
- 2 个非消费者（lpf/lptest）：两个符号**根本没出现** → 驱动包装脚本的注入范围精确。

### 执行验证（不是静态推断，是真的跑起来了）
本地 qemu-aarch64 + musl guest loader（`/opt/ohos-guest`）实际执行打包产物：

| 程序 | 实际输出 | rc |
|------|----------|----|
| `bin/lpr -Z` | `usage: lpr [-cdfghlmnpqrstv] …` | 1 |
| `bin/lpq -Z` | `lpq: unrecognized option: Z` + usage | 1 |
| `bin/lprm -Z` | `lprm: unrecognized option: Z` + usage | 2 |
| `sbin/lpc -Z` | `?Invalid command` | 1 |
| `sbin/pac -Z` | `pac: unrecognized option: Z` + usage | 1 |
| `sbin/lpf -Z` | `lpf: unrecognized option: Z` + usage | 1 |
| `bin/lptest -Z` | 读 stdin 直到 EOF（它本来就是过滤器），正常退出 | 0 |
| `sbin/lpd -v` | `usage: lpd [-dlrs] [-b bind-address] …` | 1 |
| `sbin/lpd`（无参） | 无输出，成功 fork 成守护进程（测完已清理） | 0 |

即 8/8 程序都被真实加载并执行了。日志：
`/root/ohpcd-work/logs/lpr-qemu-run.log`、`/root/ohpcd-work/logs/lpr-qemu-lpd.log`。

两个本地模拟环境的限制（如实记录，不是包缺陷）：
1. `lpd` 直接跑会 `Error relocating … __fd_chk: symbol not found`（rc=127）——
   guest 的 musl 没有 OHOS 的 `__fd_chk`。加上 `/opt/ohos-guest/lib/libfdchkshim.so`
   （`nm -D` 可见 `T __fd_chk`）后 `lpd` 正常运行、rc=0。真机 OHOS loader/libc.so
   自带该符号。同 archives/p/pd-iemlib/1.22.3 记录的成因一致。
2. 无参 `lpd` 会真的 daemonize（fork），本地跑完必须 `pkill` 清理，别在 CI 里无参调用。

### 五维账本
上游用例总数=0 执行=0 通过=0 失败=0 跳过=0。
上游 8 个子目录 Makefile + `common_source/Makefile.in` + 顶层 Makefile 一共只有
`all` / `clean` / `${PROG}` / `.o.c` 四个目标，**没有任何 check/test 目标**
（`make check` → "No rule to make target 'check'"），全树无 TESTS /
check_PROGRAMS / add_test，无 tests/ 目录 → L1 在
`ci/config/no_official_test.txt` 白名单豁免（理由已写入该文件）。
消费者断言 **不是**上游测试，不按上游测试口径上报。

## 交付物
conan 包 `lpr/2008.05.17.4`（application）：
`bin/` 4 程序 + `sbin/` 4 程序 + `etc/printcap` + `share/man/man1` 4 份 +
`share/man/man5` 5 份 + `licenses/copyright`。8 个程序合计约 380 KB。

## 注意事项
- **刻意不 strip** 打包产物：test_package 要读 `.symtab` 证明
  `rresvport_af`/`innetgr` 是已定义符号而非悬空引用，事后审计也依赖符号表。
  代价可忽略（8 个程序合计 ~380 KB）。同理 `.symtab` 的解析是手写 ELF64 解析，
  不依赖 nm/readelf —— OHOS worker 的 HMBS 只注入 cmake/make/ninja/python3。
- **本地产物未签名**：本地交叉编译机上没有 `binary-sign-tool`
  （`/data/service/hnp/bin/` 只有 clang/clang++/ld/llvm-{ar,nm,ranlib}/perl/bash），
  配方按 `archives/t/termdebug/2.2` 同策略**记 warning 继续**，不伪造"已签名"。
  真机拒绝执行未签名 ELF，所以真机 CI 需要
  `/data/service/hnp/bin/binary-sign-tool` 走签名路径（配方里已实现，
  会先 `llvm-objcopy --remove-section .codesign` 再 `-selfSign 1`）。
- 保留的两条上游告警（未压制）：`displayq.c:338/341` 的
  `-Wformat-security`（`fprintf(stderr, *fmt)` 式非字面量格式串）。
  Debian 侧同样只是 `-Wno-error=format-security`，不改变行为；这里也不动它，
  免得"为了让日志干净"去改上游语义。
- `patches: {}`：上游源码零改动，`patches_applied=[]`。新增的 `compat/` 是**新增
  文件**而不是补丁 diff —— 与 `archives/a/abiword-plugin-clarisworks/3.0.8` 同样处理
  （toybox patch 在 OHOS 上会把"新建文件"的补丁真的打进 orig 目录）。
- 可升知识库：musl `<dirent.h>` 不拉 `<sys/types.h>`；musl `<termios.h>` 不拉
  `<sys/ttydefaults.h>`（但 sysroot 里该头是有的）；`rresvport_af`/`innetgr` 是
  glibc-only 的 BSD 遗留接口；`$(CC) -o ${PROG} ${OBJ}` 型 Makefile 需要链接期
  注入时的驱动包装脚本模式。

---

**编译结束**: 2026-10-05
**最终状态**: built
## 2026-10-10 复审记录
- PR 标题与描述已按模板补全（【积分赛】前缀 + 5 字段 + 统计表 + 验证结果），
  本提交用于触发平台 Septest 对最新状态重新审查（此前裁决读到的仍是旧元数据）。
- CI 构建通过，test_package 72 条断言全过（TPRESULT PASS）。
