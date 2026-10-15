# megactl 0.4.5 适配笔记（HarmonyOS PC / OHOS aarch64）

- 软件：megactl 0.4.5（LSI/Dell PERC、MegaRAID SAS 控制器诊断工具）
- 配方：`archives/m/megactl/0.4.5/conanfile.py`（version = 上游版本，R37 首次适配）
- 交付：`bin/megactl`、`bin/megasasctl`、两页 man、AppStream metainfo、GPL-2.0 COPYING
- 依赖：**零**（W0 依赖闸无需任何制品仓预编译包）

## 1. 上游与源码来源

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/namiltd/megactl （megactl 主页） |
| 上游 tag | `v0.4.5` = commit `8f86e0be53b273188bf2779d974fcf3f9c68b8f0`（2024-08-14） |
| 实际取包 | `https://github.com/namiltd/megactl/archive/refs/tags/v0.4.5.tar.gz` |
| sha256 | `3343edab107a33a70d2fa72e9fe0382bc4be2f428ccd1497609b5595e0871bbb` |

**来源交叉验证**：同一份字节可从两条独立途径取到，且逐字节相同 ——

| 途径 | 大小 | sha256 |
|---|---|---|
| GitHub tag 归档 `archive/refs/tags/v0.4.5.tar.gz` | 182212 B | `3343edab…1bbb` |
| Debian pool `megactl_0.4.5.orig.tar.gz` | 182212 B | `3343edab…1bbb` |

`cmp` 判定两者 byte-identical；Debian 公布的 md5 `585b2e1d63b256702a19edb6af79b892`
亦与之一致。归档共 103 个条目，并保留了构建**必需**的符号链接
`megaraid → kernel-2.6.9-55.0.2.EL/megaraid-2.20.4.6-rh2`（`#include "megaraid/…"`
靠它定位 ioctl 结构体；缺了它连编译都过不去）。

采用 GitHub 官方 tag 归档（R39 首选形态），CI 会自动追加镜像回退。

## 2. 上游构建系统与构建结果

- 语言：纯 C99（`SRCS` 共 8 个 .c），构建系统是**手写 Makefile**（非 autotools）。
- 外部依赖：**零**。SCSI/MTP 结构体来自上游自带的 `schily/` 头（`-I./schily`），
  megaraid ioctl 结构体来自 vendored 的 `kernel-2.6.9-55.0.2.EL/megaraid-2.20.4.6-rh2/`
  （源码根的 `megaraid` 符号链接）。因此 requirements 为空，不需要先发布任何依赖。
- `all` 目标产出 `megactl` + `megasasctl`（`PROGRAMS` 变量）；`megasasctl` 是同一份
  `megactl.c` 加 `-DMEGA_SAS_CTL` 编译出的 SAS 架构变体。

**结论：构建零补丁**，`patches/` 目录不存在。OHOS clang 15
（`--target=aarch64-linux-ohos`，`--sysroot=<OHOS musl sysroot>`）直接编译通过。
上游代码只 include POSIX 头（`sys/ioctl.h`、`sys/sysmacros.h`、`netinet/in.h`、
`malloc.h`、`memory.h`、`sys/ptrace.h`、`sys/uio.h`、`sys/wait.h`、`sys/syscall.h`），
这些在 OHOS musl sysroot 里全部存在。

## 3. 踩坑与处置（全部为实测结论）

### 3.1 上游把 `-g` 硬编码 → 二进制泄漏**构建机绝对路径**（本次最实质的坑）

上游 Makefile：`CFLAGS+= -g -Wall ...`、`LDFLAGS+= -g ...`。本机交叉工具链的
sysroot 不在 `/usr` 下（在构建机的用户目录里，路径形态为
`/mnt/<盘符>/Users/<用户名>/ohos-sysroot/`；示例中的用户名已按公开 PR 惯例隐去），
DWARF 于是把 sysroot 的绝对路径写进 `.debug_str`，实测形态为：

```
<交叉工具链 sysroot>/usr/include
<交叉工具链 sysroot>/usr/include/aarch64-linux-ohos/bits
```

实测 `strings -a megactl | grep -c '<sysroot 路径前缀>'` = **2**。
交付进制品仓的二进制带构建机路径既是分发卫生问题，也会把私人路径带进公开 PR。

**处置**：保留上游 `-g` 不动（不重述上游 CFLAGS，减少偏差面），只在链接期剥掉
debug 段：`make ... LDFLAGS='-g -Wl,--strip-debug'`。实测泄漏降为 **0**，
`.interp`、`.note.gnu.build-id`、`.note.ohos.ident`、符号表全部保留。
`test_package/test_layout.py` 的「包内文本无构建机绝对路径泄漏」断言把这条钉死。
（`.note.gnu.build-id` 后来改成**显式**索取，原因见 3.10 —— 真机驱动不会自动给。）

对照实验（都实测过）：`CFLAGS='-O2 -Wall -I./schily -Iincludes-hack' LDFLAGS='-O2'`
同样泄漏 0，但会重述上游标志集；选 `-Wl,--strip-debug` 改动面最小。

### 3.2 绝不能用 `make CFLAGS=...` 传编译选项

上游用 `CFLAGS+=`。GNU make 里**命令行赋值会覆盖 makefile 里的所有赋值（含 `+=`）**，
所以 `make CFLAGS='-O2'` 会把 `-g -Wall -I./schily -Iincludes-hack` 一起清空，
`-I./schily` 消失后 `#include <scg/scsireg.h>` / `<scsi/scsi.h>` 直接找不到。
需要追加选项时只能走 `CPPFLAGS`（上游 `CFLAGS+= ... $(CPPFLAGS)`）。

### 3.3 不用 `make install`（HMDFS 用户态无 `install`(1)）

上游 `install:` 目标依赖 `$(INSTALL)`（= `install`）。本平台用户态没有该命令
（lzip/1.24.1 已实证 Error 127），且 `megactl` 的 `install` 用法是
`$(INSTALL) -d` / `$(INSTALL) -m644`，无法像 lzip 那样用 `INSTALL="cp -f"`
在命令行等价覆盖（`cp` 没有 `-d`/`-m644` 语义）。
**处置**：`package()` 用 `conan.tools.files.copy()` 从 `source_folder` 直接落包。
这同时规避了 T105（install 落地的可执行文件在真机 worker 上带内核级
不可执行标记、打包后 EPERM）。`copy` 后再显式 `os.chmod(0o755)`。

### 3.4 `ARCH=` 必须显式置空

上游 `CFLAGS+= -g -Wall $(INC) $(ARCH) $(CPPFLAGS)` 会吸收环境里的 `ARCH`。
CI worker 的环境不保证没有它，显式 `ARCH=` 保证构建可复现。

### 3.5 上游 pattern rule 依赖一个不存在的 `Makefile.bak`（**无害，已证**）

上游 Makefile：`%.o: Makefile.bak %.c`。但发布 tarball 里**没有** `Makefile.bak`
（`tar tzf | grep -i makefile` 只有 `Makefile` 一个文件）。直觉上 GNU make 应该报
`No rule to make target 'Makefile.bak'`。

**实测不报错**：用最小复现件（同款 `%.o: Makefile.bak %.c` 规则、缺 `Makefile.bak`）
在本机 GNU Make 4.3 下 `make` 与 `make -j8` 均 rc=0 正常产出；megactl 真实构建
（从干净解包开始）也 rc=0。**因此不需要为它打补丁**。若未来 CI 换到会报错的 make
版本，再考虑在配方里 `touch Makefile.bak`。

### 3.6 `megatrace` 不构建（正确做法，不是漏构建）

`megatrace` 不在 `PROGRAMS` 里，不属于 `all` 目标。它 `#include <asm/user.h>`
—— x86 专用头，aarch64 的 `asm/` 指向 `asm-generic/`，没有 `user.h`。
**处置**：只构建上游默认目标 `all`（= `megactl` + `megasasctl`），与上游
`make` 行为完全一致，不擅自扩大交付范围。

### 3.7 上游版本号 quirk：`0.4.5` 的 tarball 里 `-V` 打印 `0.4.3-hmage`

`megactl.c:91`：`static char *version = "0.4.3-hmage";` —— 上游发布 0.4.5 时
漏改了这个变量（与 rtl-sdr 2.0.2 的 `VERSION_INFO_PATCH_VERSION` 同类 quirk）。
**处置**：不改上游源码（如实保留），`test_megactl.py` 按**实测值** `0.4.3-hmage`
断言，并在 conanfile docstring / MANIFEST / PR 正文里注明，避免评审误判为适配错误。

### 3.8 `-j1`

HMDFS 上 GNU make jobserver 创建 command FIFO 失败（仓库既有先例，见
lzip/1.24.1）。megactl 只有 8 个 .c，`-j1` 成本可忽略。

### 3.9 CI 的 Pre-download 步骤会被「注释里的裸 URL」改坏 conandata.yml（本轮实测踩到）

**现象**：换成 GitHub tag 归档后，本地门禁 `ci/conan/build_and_test.sh` 的
conan create 直接失败：

```
WARN: Could not download from the URL https://gh-proxy.com/file:///…/predl_cache/1f893089_megactl/archive/refs/tags/v0.4.5.tar.gz
ERROR: Error in source() method, line 87
NotADirectoryError: [Errno 20] Not a directory: '…/predl_cache/1f893089_megactl/archive/refs/tags/v0.4.5.tar.gz'
```

**根因**（已用最小复现件逐字验证，非推测）：门禁的 Pre-download 块用正则
`(?:^|\s)(?:url:?\s*)?["']?-?\s*(https?://[^\s"']+)` 扫描**整个 conandata.yml
（含注释）**抽取 URL，逐个 `curl` 预下载，然后用 `content.replace(url, 'file://…')`
做**朴素子串替换**。而我最初的 conandata.yml 注释里写了裸仓库主页 URL
`https://github.com/namiltd/megactl` —— 它是 `sources.url`
`https://github.com/namiltd/megactl/archive/refs/tags/v0.4.5.tar.gz` 的**严格前缀**，
于是：① 主页被当成源码包预下载成文件 `1f893089_megactl`（58 KB 的 HTML）；
② 因为它在文件中出现得更早，`replace` 先命中，把真正的 sources.url 一并改坏成
`<hash>_megactl/archive/refs/tags/v0.4.5.tar.gz` —— 前半段是**文件**不是目录，
于是 `NotADirectoryError`；③ 同样的替换还把 gh-proxy 镜像项里的内联 URL 也污染成
`https://gh-proxy.com/file://…`。

复现件输出（同一段脚本逻辑）：

```
BAD2  抽取到 3 个 URL（含注释里的裸仓库 URL）
  → "- "https://gh-proxy.com/file:///…/1f893089_megactl/archive/refs/tags/v0.4.5.tar.gz"
  → "- "file:///…/1f893089_megactl/archive/refs/tags/v0.4.5.tar.gz"
GOOD  注释只用 host-less 文本
  → "- "file:///…/predl_cache/e36e91a3_v0.4.5.tar.gz"
  → "- "file:///…/predl_cache/9dd78758_v0.4.5.tar.gz"
```

**处置**：conandata.yml 的注释里**不写任何裸 `https://` URL**，只写 host-less 文本
（如 `github.com/namiltd/megactl`）。这样抽取到的 URL 只有镜像项与官方项两条，
且容器项先被整体替换，互不污染。

> **这不是新坑**：仓库 `knowledge/drafts/` 下已有多份同源草稿
> （`DRAFT-8543-conandata-comment-url-predl-rewrite`、
> `DRAFT-8960-raqm-0.11.0-conandata-comment-url-predl-pollution`、
> `DRAFT-libexecinfo-20180201-…`、`DRAFT-libnbd-1.9.6-local-predl-url-pollution`、
> `DRAFT-ring-span-lite-0.7.0-…`、`DRAFT-status-value-lite-1.1.0-…`、
> `DRAFT-jwt-cpp-0.7.1-…` 等），属框架级已知陷阱。本包**不再另建草稿**避免重复沉淀，
> 只在此处留下 megactl 的具体触发条件（GitHub `archive/refs/tags/` 多级路径 + 注释里
> 写了仓库主页 URL）与复现证据，供主编合并进既有条目时取用。

HMDFS 上 GNU make jobserver 创建 command FIFO 失败（仓库既有先例，见
lzip/1.24.1）。megactl 只有 8 个 .c，`-j1` 成本可忽略。

### 3.10 交付二进制在 CI 上没有 `.note.gnu.build-id` → 本地绿、CI 红（CI #79116 实证）

**现象**：本地门禁 `ci/conan/build_and_test.sh` 31 项自检全过、conan create 退出 0；
同一个 SHA 推到 CI 后 `conan-build-test` 失败，报错落在 test_package 的两条自检上：

```
[4] 两个 CLI 是两个不同二进制（不是硬链接/副本）
  [FAIL] 两个 CLI 都带 BuildID（可区分构建产物）  megactl=(none) megasasctl=(none)
  [FAIL] 两个 CLI 的 BuildID 不同（确为分别编译的两个目标）  megactl=(none) megasasctl=(none)
  [ok] [鸿蒙] bin/megactl 带 OHOS 工具链的 .note.ohos.ident 段  note=['.note.ohos.ident']
适配自检 31 项：通过 29，失败 2
ERROR: megactl/0.4.5 (test package): Error in test() method, line 48
```

**根因**（实测，非推测）：配方原有的链接参数是 `LDFLAGS='-g -Wl,--strip-debug'`，
**没有**显式要求 build-id，于是「是否产生 `.note.gnu.build-id`」取决于驱动默认值，
而两边不一致：

| 环境 | 驱动 | 是否自动传 `--build-id` 给 ld | 交付二进制 |
|---|---|---|---|
| 本机 WSL（本地门禁） | `/opt/lpk-fixed/clang`（自建 shim；`-###` 可见驱动会传 `--build-id`） | **会** | `.note.ohos.ident` + `.note.gnu.build-id`（lld 默认 fast/xxHash，8 字节） |
| CI worker | `/data/service/hnp/bin/clang`（真机 OHOS 工具链） | **不会** | 只有 `.note.ohos.ident` |

于是本地那两条 BuildID 检查过、CI 上双双 FAIL，`test_layout.py` 返回 1，
conan create 以 `ConanException: Error 1 while executing` 结束。
**这是「本地 shim 与真机驱动不一致」造成的假绿**，不是 test_package 写错 ——
那两条检查的用意（证明两个 CLI 是**分别编译的两个目标**，不是硬链接/副本）是成立的。

**处置**：链接参数显式加 `-Wl,--build-id=sha1`，不再依赖驱动默认值：

```
LDFLAGS='-g -Wl,--strip-debug -Wl,--build-id=sha1'
```

选 `sha1` 而不是裸 `--build-id`：lld 的默认风格是 fast/xxHash（8 字节），
GNU ld 才是 sha1 —— 显式写死风格，跨链接器一致、便于人眼与脚本复核；
build-id 由链接产物内容算出，两个不同程序必然不同。零源码补丁。

**验证证据**（同一份上游源码、同一 `make` 命令行，只改 LDFLAGS）：

```
A) 模拟 CI 驱动默认值（-Wl,--build-id=none，等价于 worker 上不生成）
   bin/megactl      note 段: ['.note.ohos.ident']   build_id: (none)
   bin/megasasctl   note 段: ['.note.ohos.ident']   build_id: (none)
   ← 与 CI #79116 的 [4] 输出逐字一致（megactl=(none) megasasctl=(none)）

B) 本轮修复（-Wl,--build-id=sha1）
   bin/megactl      note 段: ['.note.ohos.ident', '.note.gnu.build-id']
                    build_id: ce2cc065c019651ffe45b69fb327aa51f525ffea（20 字节 sha1）
   bin/megasasctl   note 段: ['.note.ohos.ident', '.note.gnu.build-id']
                    build_id: 0d996a2a3f702ea666aa5ae66b2411fd15d543d8（20 字节 sha1）
```

修复后本地门禁重跑：`适配自检 31 项：通过 31，失败 0`、`conan create passed`、
`L0_RESULT=pass`、`L1_RESULT=pass`、退出码 0；两个 build-id 与实验 B 逐字相同
（说明结果与用哪个 clang 无关，可复现）。
`-Wl,--strip-debug` 的剥路径效果不受影响：`.debug_str` 里 sysroot 路径计数仍为 0，
[6]「包内文本无构建机绝对路径泄漏」通过。

> 教训（值得沉淀）：**用本地 shim 模拟真机驱动时，要覆盖「驱动传给链接器的默认 flag」这一层**。
> 编译/头文件层面模拟得像，不代表链接期默认参数也一样 —— 这个包的 build-id 差异
> 就是这么漏过本地门禁的。

## 4. 上游测试清点（R51 口径，**上游确无测试**）

清点方法与结果：

| 检查项 | 命令 / 依据 | 结果 |
|---|---|---|
| Makefile 目标 | `grep -E '^[a-zA-Z_.-]+:' Makefile` | `all` `megactl` `megasasctl` `megatrace` `install` `clean` `depend` —— **无 check/test** |
| 自动化测试目标 | 同上 | 无 `make check`、无 `ctest`、无 `pytest` |
| 测试目录 | `tar tzf` 全量 103 项 | 无 `test/` `tests/` `testing/` 目录 |
| CI 配置 | `.github/workflows/` | 只有 `codeql-analysis.yml`（静态扫描，非测试） |
| 测试框架依赖 | `Makefile` 无 `check_PROGRAMS` / `TESTS` | automake 测试变量一个都没有（T009 口径：`make -n check` 也不存在目标） |

**megactl 的真实验收前提是硬件**：需要 MegaRAID 控制器与 `/dev/megadev0`
（PERC）或 `/dev/megaraid_sas_ioctl_node`（SAS）设备节点，CI 与开发机都没有。
因此验证由消费者测试承担（见下）。

## 5. 测试证据（本地实测）

| 脚本 | 断言数 | 鸿蒙特有 | 结果 |
|---|---|---|---|
| `test_package/test_megactl.py` | 38 | 1 | 38/38 通过 |
| `test_package/test_layout.py` | 31 | 8 | 31/31 通过 |
| **合计** | **69** | **9** | **69/69 通过** |

`test_megactl.py` 覆盖 megactl **全部与硬件无关**的代码路径（38 项，分节计数
6 + 8 + 14 + 5 + 2 + 3）：

1. 版本/verbosity（**6**）：`-V`、`-v -V`，两个 CLI 各一组共 4 项，加退出码断言
   与「交付二进制在鸿蒙目标上真能执行」1 项
2. usage/帮助（**8**）：`-?` / `-h` 的 rc 与 usage 首行各 1；usage 正文含 `-V`
   选项、PERC 的 `/dev/megadev0` 与 `channels`、SAS 的
   `/dev/megaraid_sas_ioctl_node` 与 `enclosures`（后者证明 `-DMEGA_SAS_CTL`
   分支真的生效）
3. 选项校验错误分支（**14**）：`-Z` / `-T bogus` / `-l` / `-l 0xZZ` / `-l 9999` /
   `-D` / `-H a0c0`，每项 2 个断言（rc=2 + 精确首行文案，以及错误行后附 usage 正文）
4. target specifier 解析（**5**）：`zz` / `a0x0` / `a99`（越 MAX_CONTROLLERS=32）/
   `a0c99` / `a0c0t99`
5. 组合语义（**2**）：`-est -V`、`-V a0c0`（证明 `-V` 在打开设备前短路）
6. 设备打开 / ioctl 失败路径（**3**）：`-D <不存在>` → rc=1，首行为 open()
   失败分支的上游诊断（megactl.c:601-630 的 /proc/devices 自愈逻辑）——
   /proc/devices 可读的宿主（Linux/WSL 本地）自愈未命中，落到
   `unable to open device`（两个 CLI）；OHOS 真机 worker 的 /proc/devices
   不可读（CI #73496/#70145 两台车跨天实证），fopen 失败分支报
   `file /proc/devices access error`，两条断言按宿主实际分支接受两种首行；
   `-D <普通文件>` → open 成功、真进 `ioctl()`、rc=1
   `unable to determine megaraid driver version`

`test_layout.py` 是**纯 Python 解析 ELF 字节**（不依赖 readelf / qemu / 执行权限），
因此任何宿主都能给确定结论（31 项，分节计数 10 + 4 + 6 + 4 + 4 + 3）：两个 CLI 各
5 项（存在 / 可执行位 / ELF64 / e_machine=AArch64 / ET_DYN）共 10；`DT_NEEDED`
白名单与「未混入宿主 glibc」各 2 项共 4；`.interp` 是 OHOS hnp loader、非 x86_64
loader、无 RPATH 各 2 项共 6；两个 CLI 各带 BuildID 且互不相同 + 各带 OHOS 工具链
独有的 `.note.ohos.ident` 段共 4；man 页 `.TH` 宏分别指向 megactl / megasasctl、
AppStream metainfo、`licenses/COPYING` 正文为 GPL-2.0 共 4；无构建中间产物、无隐藏
文件残留（JC5）、包内文本无构建机路径泄漏共 3。

> L1e（R34）反证：两个脚本都真读 `bin/` 下交付物并在包缺失时硬失败 ——
> CI 把 `bin/` 移走后必然失败，不可能通过空壳。

## 6. 执行方式说明（为什么不加 `can_run` 门）

`test_megactl.py` **不用** `can_run()` 直接跳过，而是尝试 exec 并捕获 `OSError`：
本机 `/proc/sys/fs/binfmt_misc` 已注册 `qemu-aarch64`，所以 x86_64 宿主上
直接 exec 交付的 aarch64 ELF 就能跑通（本地 38/38 实测）；OHOS aarch64 worker
上则是原生执行。若宿主既非 aarch64 又无 qemu/binfmt（`ENOEXEC`），CLI 断言会
**如实标记 SKIP 并以非零退出**，绝不把「没跑」伪装成「通过」。

## 7. 已知限制（如实声明）

- `megactl` / `megasasctl` 需要 MegaRAID 硬件才能完成真实枚举与报告；本环境
  无该硬件，测试只覆盖到设备打开/IOCTL 失败边界为止。这不是可以靠适配消除的
  限制，属上游设计前提。
- 上游 `megaioctl.c` 把指针强转成 `uint32_t`（`xferaddr` 等字段是 32 位），
  在 64 位 aarch64 上会截断地址（x86_64 上同样如此）。属上游内核结构体 ABI
  的既有设计，**未改动**：本次只做平台适配，不改上游行为。编译期有 11 条
  `-Wvoid-pointer-to-int-cast` / `-Wpointer-to-int-cast` 警告，非错误。
- `megatrace` 与 `modepage.c` 不参与构建（见 3.6）；| `modepage.c` 还 include 了
  上游 tarball 里根本不存在的 `megactl.h`，进一步说明它是未纳入构建的残留文件。
- CI 的 L2 冒烟会对两个 CLI 各报一条 `[warn] L2: … --version/--help failed`：
  megactl 只有短选项（`-V` / `-h`），`megactl --version` 会被上游选项解析当成
  `invalid flag "-version"` 并以 rc=2 退出（已实测）。该 warn 非阻塞
  （`build_and_test.sh` 的 L2 失败分支只 echo warn，不置 `L2_FAILED`），
  要消除它就得改上游行为，故如实保留；本包的测试用的是上游真实的 `-V` / `-h`。
