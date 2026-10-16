# rpcgen 2.6.4 适配笔记

## 目标身份

- 上游：**nfs-utils 2.6.4** 源码树中的 `tools/rpcgen/`（Sun TIRPC `rpcgen.new` 的
  清理版；维护副本随 nfs-utils 发布，无独立 release）
- 源码：`https://cdn.kernel.org/pub/linux/utils/nfs-utils/2.6.4/nfs-utils-2.6.4.tar.xz`
  sha256 `01b3b0fb9c7d0bbabf5114c736542030748c788ec2fd9734744201e9b0a1119d`
  （核对于 kernel.org 官方签名清单 `sha256sums.asc`）
- 包版本 2.6.4 = nfs-utils 版本；发行版 `rpcgen` 包（如 Alpine）同样由该目录构建
- 许可证：`tools/rpcgen/*.c` 均为 Oracle America 的 3-clause BSD 风格声明
  （"Redistribution and use in source and binary forms …"），故声明 `BSD-3-Clause`；
  源码树顶层 COPYING 为 GPL-2.0（覆盖树内其他组件）。构建另经
  `support/include/nls.h` 处理 `ENABLE_NLS`（本包 `--disable-gss` 路径下未定义，
  走无 NLS 分支，不引入 libintl 依赖）
- 语言预检（R47）：`detected_language=c`，构建系统 autotools，任务类别 cpp（c↔cpp 兼容族）

## 任务身份

- 分支：`feat/rpcgen-2.6.4`，worktree `/storage/Users/currentUser/build_in_harmonyos-rpcgen`
- 基线：`b5e60d0ad3`（= upstream/main 顶端 `!16028 merge feat/tqftpserv-1.2 into main`）
- 认领/绑定：任务平台未在本工作区提供元数据（无 OHC_TASK_* 环境变量、无任务描述文件），
  任务身份由分支名与包版本一致推得；**尚未核实平台认领状态**
- 结果回执位置：`$HOME/ohpcd-ai-worker-result.rpcgen-2.6.4.json`
  （`$HOME/ohpcd-ai-worker-result.json` 属上一条 trimadap 任务，未覆盖）

## 编译环境

- 设备：HarmonyOS PC（`uname -s` = HarmonyOS，HongMeng Kernel 1.12.0，aarch64）
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`），libc 为 OHOS musl
- Conan 2.29.1（OHOS 适配版），profile `ohos-aarch64`（os=OHOS 6.0 / arch=armv8 /
  compiler=clang 15），**原生构建**（build = host = 目标机），非交叉编译
- 构建系统：autotools（tarball 自带预生成 `configure` / `Makefile.in`；
  **本机与 CI 均无 automake**，因此不重生成 autotools 文件）

## 依赖版本

| 依赖 | 版本 | 性质 | W0 证据 |
|---|---|---|---|
| libtirpc | 1.3.7 | 顶层 configure：`PKG_CHECK_MODULES([TIRPC])` + `rpc/rpc.h` | `conan install --requires=libtirpc/1.3.7 … --build=never` exit 0 |
| uuid | 2.40.1 | 顶层 configure：`AC_CHECK_HEADER(uuid/uuid.h)` 无条件门禁 | 同上 exit 0 |
| libevent | 2.1.13 | 顶层 configure：`AC_LIBEVENT` 无条件门禁 | 同上 exit 0 |
| sqlite3 | 3.49.1 | 顶层 configure：`AC_SQLITE3_VERS` 无条件门禁 | 同上 exit 0 |

四个依赖**均不参与链接**：`tools/rpcgen/Makefile.am` 中 `rpcgen_LDADD = $(LIBINTL)`，
产物为单文件可执行程序，`--disable-gss` 又去掉了默认开启的 GSS 路径（该路径会额外
要求 krb5）。W0 检查命令与输出见 `reports/test-report.md`。

## 问题与解决方案（按首次出现顺序）

| # | 首个真实错误 | 根因 | 最小修改 |
|---|---|---|---|
| 1 | `configure: error: cannot guess build type; you must specify one`（config.guess 提示下载新版） | tarball 的 `config.guess`/`config.sub`（2023 版）不含 HarmonyOS/ohos 三元组 | 补丁 0001/0002：`config.guess` 增加 `*:HarmonyOS:*:*` 分支（`uname -s` = HarmonyOS），`config.sub` 增加 `ohos-linux` 组合、OS 列表 `ohos*`、内核/OS 校验 `linux-ohos*`；**不使用 `--build/--host`**（E007：会被当作交叉编译，`AC_RUN_IFELSE` 全部跳过）。写法与同一 tarball 的姊妹包 `libnfsidmap-ldap/2.6.4` 一致，**不含平台宏**（PF5/R8） |
| 2 | `configure: error: Neither getrpcbynumber_r nor getrpcbynumber are available` | 顶层 `configure.ac:581-587` 是无条件整树硬门禁；OHOS libc 与 conan libtirpc/1.3.7 均未实现该函数 | 补丁 0003（第 1 段）：门禁降级为警告；`HAVE_GETRPCBYNUMBER*` 保持未定义，不谎报能力。唯一使用点 `support/nfs/svc_socket.c`（属 `libnfs.la`）不在本包构建范围（`grep -rn getrpcbynumber --include=*.c` 仅此一处） |
| 3 | `config.status: error: could not setup config files machinery` / `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 下 `mktemp -d` 恒建 0700 目录且 chmod 无效（E110/E112/E118） | 补丁 0003（第 2 段）：按 cln/1.3.7（CI 实证）改为 `tmp=./conf$$-$RANDOM; (umask 000 && mkdir "$tmp")`，失败分支再加 `-2` 后缀 |
| 4 | `rpc_main.c:970: error: call to undeclared library function 'rindex' … [-Werror,-Wimplicit-function-declaration]` | `rindex()` 是 BSD 遗留名；glibc 经 `<string.h>` 声明它，OHOS libc 则**从不声明**（`strings.h` 只声明 `index()`，`<strings.h>` 也补不上） | 补丁 0004：改用 POSIX 等价函数 `strrchr()`（语义相同、单调用点；BSD/glibc 上同样正确） |
| 5 | （预判并规避）`struct stat64` / `stat64()` 未定义 | rpc_main.c 无条件使用 LFS64 API；OHOS libc 仅在 `_LARGEFILE64_SOURCE`（或 `_GNU_SOURCE`）下把 `stat64` 定义为 `stat`（`sysroot/usr/include/sys/stat.h:100-103`），glibc 默认提供故上游无守卫 | 不补丁源码：`generate()` 中 `tc.extra_cflags` 加 `-D_LARGEFILE64_SOURCE`（标准 POSIX 特性宏，非平台宏；`CFLAGS` 中可见） |
| 6 | 运行 `rpcgen calc.x` → `cannot find C preprocessor: cpp` | rpcgen 运行期恒需外部预处理器，查找顺序为 `/lib/cpp` → `PATH` 中 `cpp` → `-Y <dir>`；OHOS 把预处理器提供为工具链下的 `clang-cpp`，**没有 `cpp` 命令** | 平台运行前置条件，已在 README/notes 说明并由 test_package 落地：自建含 `cpp` 的目录并加入 PATH（或 `-Y`）；注意 clang 对 `.x` 扩展名必须加 `-x c` 才进入预处理模式（否则按链接输入处理） |
| 7 | （测试期发现，非本包缺陷）消费者用旧式 `clnttcp_create()` → `RPC: Unknown protocol` | `clnttcp_create()` 经 netconfig 解析 `tcp` netid；OHOS 无 `/etc/netconfig`，且该路径是 libtirpc 的编译期常量（`netconfig.h:#define NETCONFIG "/etc/netconfig"`，实测 `NETCONFIG` 环境变量不生效） | 消费者改走传输层构造 `clnt_vc_create()`（自带 fd + 地址），服务端 `svc_vc_create()` 同样不经 netconfig；两者在 OHOS 上均正常。属 **TI-RPC 消费者侧的通用平台知识**，已提出知识草稿 |

## 补丁清单

`patch_type` 统一为规范固定值 `portability`（.gitcode/code-style.md §12；补丁的具体
平台/R8 说明写在 `patch_description` 与本文档上表中）。全部补丁**不含平台宏**
（无 `__OHOS__`，符合 R8 / preflight PF5）。

| 补丁 | 文件 | 说明 |
|---|---|---|
| `0001-config.guess.patch` | `config.guess` | 增加 HarmonyOS 三元组识别（E007） |
| `0002-config.sub.patch` | `config.sub` | 接受 `aarch64-unknown-linux-ohos`（E122） |
| `0003-configure.patch` | `configure` | getrpcbynumber 门禁降级为警告；config.status 临时目录 `$$` + `umask 000`（HMDFS） |
| `0004-tools-rpcgen-rpc_main.c.patch` | `tools/rpcgen/rpc_main.c` | `rindex()` → POSIX `strrchr()` |

关于修改生成的 `configure`：该 tarball 自带预生成的 `configure`/`Makefile.in`，而本机
与 CI 均**没有 automake**（`automake: 未找到`），重生成既不可行也不可复现；同一
tarball 的姊妹包 `libnfsidmap-ldap/2.6.4`（已合入 main）采用同一做法（`0003-configure.patch`）。
补丁只改错误分支与临时目录创建两处，不改变任何成功路径的语义。

关于临时目录用 `umask 000`：W4 独立审计提出可考虑收紧为 `022/027`（P3 非阻断）。
本包**刻意保持与 cln/1.3.7（CI 实证）及姊妹包同形**：HMDFS 会忽略 `chmod`，目录权限
只在创建时刻由 umask 决定，而该目录仅供 config.status 生成 `subs*.awk` 等中间产物、
构建结束即删除（`trap` 内 `rm -fr`）；收紧 umask 一旦在某类 HMDFS 挂载点上导致
`Permission denied` 复现，就是又一次不可复现的 CI 失败。若后续有 CI 实证表明 `022`
同样稳定，可再收紧——当前以"已实证可用"为准。

## 上游测试

- **`tools/rpcgen` 无任何自动化测试**。清点证据（nfs-utils-2.6.4 源码树）：
  - `grep -n -E "TESTS|check_PROGRAMS" tools/rpcgen/Makefile.am` → 无命中
  - `ls tools/rpcgen/ | grep -i -E "test|check"` → 无命中
  - `grep -rn -E "^\s*(TESTS|check_PROGRAMS)\s*=" --include=Makefile.am .` → 仅命中
    `tests/Makefile.am`（`check_PROGRAMS = statdb_dump`、`TESTS = t0001-statd-basic-mon-unmon.sh`）
    与 `tests/nsm_client/Makefile.am`（`check_PROGRAMS = nsm_client`），二者针对
    rpc.statd / NSM 客户端，**不覆盖 rpcgen**
  - 实测 `make -C tools/rpcgen check` → `make: Nothing to be done for 'check'.`（exit 0），
    配方 `build()` 仍执行该步骤，使"上游无测试"这一事实留在构建日志中
- 因此上游自动化用例数 = **0**（不提供通过/失败/跳过数），测试覆盖由 test_package 承担

## 注意事项

- 运行前置条件（**必须**）：rpcgen 需要外部 C 预处理器；OHOS 只提供 `clang-cpp`，
  没有 `cpp` 命令，需自建含 `cpp` 的目录（PATH 或 `-Y <dir>`），并且 clang 需 `-x c`
  才会以预处理模式读取 `.x`。详见软件级 `README.md` 的「运行说明」。
- TI-RPC 消费者注意：libtirpc 的 `clnt_create()`/`clnttcp_create()` 需要
  `/etc/netconfig`（OHOS 无此文件，且路径为编译期常量）；请改用
  `clnt_vc_create()`/`svc_vc_create()`。
- 本包产物只有 `bin/rpcgen` 与 man page，不含库；因此 `package_info()` 只声明
  `bindirs`。按 R38，软件级 `commands.json` 已声明 `type: tool`。
- 依赖关系上，四个依赖均为 configure 门禁（不链接）；已在下游可获得性（W0）中逐个实测。
---

**编译结束**: 2026-10-16 03:05
**最终状态**: built
