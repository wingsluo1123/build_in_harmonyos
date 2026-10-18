# libnetfilter_acct 1.0.3 编译笔记

> 本文件含两段：**一、前任探索记录（2026-05-29，正文原样保留，仅在其后就地标注更正）**；
> **二、本次适配实测（2026-10-18，一手读数）**。第二段是权威读数。

---

## 一、前任探索记录（2026-05-29，正文原样保留）

### 编译环境
- 日期: 2026-05-29
- 平台: OpenHarmony aarch64
- 编译器: clang

### 遇到的问题及解决

#### 1. 平台识别问题
**问题**: configure 脚本无法识别 aarch64-linux-ohos 平台
**解决**: 更新 build-aux/config.guess 和 build-aux/config.sub 文件

#### 2. LIBM 库依赖缺失
**问题**: configure 执行时提示 LIBM 库未找到
**解决**: 修改 configure 脚本，添加 LIBM 库依赖检查

#### 3. stdint.h 头文件缺失
**问题**: 编译 src/libnetfilter_acct.c 时提示 uint64_t 类型未定义
**解决**: 在源码文件中添加 `#include <stdint.h>` 头文件

### 补丁列表
- 0001-build-aux-config.guess.patch: 更新 config.guess 以支持 OpenHarmony
- 0002-build-aux-config.sub.patch: 更新 config.sub 以支持 OpenHarmony
- 0003-configure.patch: 添加 LIBM 库依赖
- 0004-src-libnetfilter_acct.c.patch: 添加 stdint.h 头文件

### 测试情况
- 测试状态: SKIPPED（纯库项目，无测试套件）
- 手动验证: pkg-config 验证通过

### 最终状态
- 状态: built
- 需要质量门禁通过后升级为 published

### 1.1 就地更正（2026-10-18，本次适配逐条复核补丁实物后写成）

| 前任原文 | 实物复核结论（一手） |
|---|---|
| 「1. 平台识别问题 → 更新 config.guess / config.sub」 | **正确**。0001 在 `config.guess` 的 `${UNAME_SYSTEM}` case 首插 `HarmonyOS)` 分支（置 `LIBC=musl`），并在 `${UNAME_MACHINE}:${UNAME_SYSTEM}:…` case 首插分支直接 `echo ${MACHINE}-unknown-linux-ohos`；0002 在 `config.sub` 的 `maybe_os` 白名单与 `-linux-*` 校验列表各加 `linux-ohos*`。对应知识条目 **E007**。 |
| 「2. LIBM 库依赖缺失 → 修改 configure 添加 LIBM 依赖检查」 | ⚠ **与补丁实物不符**。0003 的实际内容是 `configure` 里两处 `(umask 077 && mktemp/mkdir …)` → `(umask 022 && …)`（HMDFS 上 0700 临时目录不可写，**E011**）。`configure.ac` 里**没有**任何 `LIBM`/`libm` 检查，链接行也不需要 `-lm`；本包唯一外部依赖是 **libmnl**（`configure.ac` 第 19 行 `PKG_CHECK_MODULES([LIBMNL], [libmnl >= 1.0.0])`）。 |
| 「3. stdint.h 头文件缺失 → 源码加 `#include <stdint.h>`」 | ⚠ **与补丁实物不符**。0004 的实际内容是 `sockaddr_storage` 双定义守卫（`#include <sys/socket.h>` + `_UAPI_LINUX_SOCKET_H` + `__kernel_sa_family_t`，**E091/E119**）。源码本身经 `<inttypes.h>` 取 `uint64_t`，无 `stdint.h` 缺失问题。 |
| 「补丁列表 0003=添加 LIBM 依赖 / 0004=添加 stdint.h」 | 同上，两条描述均已按实物改写（见 §2.3）。 |
| 「测试状态: SKIPPED（纯库项目，无测试套件）」 | **方向正确但需精确化**：上游确无自动化测试套件（无 `tests/`、无 `TESTS`、无 `add_test`/`enable_testing`），但 `examples/Makefile.am` 声明 `check_PROGRAMS = nfacct-get nfacct-add nfacct-del`，`make check` 会**编译并链接**这 3 个程序（＝上游验证入口）。本次已接入配方 `build()`，并用真实消费者测试补足可执行断言。 |

---

## 二、本次适配实测（2026-10-18，主理-8 链主 · B 机）

### 2.1 环境与源码

- 上游版本 / URL / 格式：`1.0.3` / `https://www.netfilter.org/projects/libnetfilter_acct/files/libnetfilter_acct-1.0.3.tar.bz2` / `tar.bz2`
- HTTP 实测：`200`，`Content-Length: 296999`，`Content-Type: application/x-bzip2`
- `sha256 = 4250ceef3efe2034f4ac05906c3ee427db31b9b0a2df41b2744f4bf79a959a1a`
- 构建系统：autotools；release tarball **自带 `configure`**（无需 `autoreconf`）
- 依赖：**libmnl/1.0.5**（`configure.ac:19` `PKG_CHECK_MODULES([LIBMNL], [libmnl >= 1.0.0])`，无关闭开关）；`configure.ac` 另要求 host 匹配 `*-*-linux*`，`aarch64-unknown-linux-ohos` 命中
- 交付形态：**静态**（`--enable-static --disable-shared`）——上游 `configure.ac` 调 `AC_DISABLE_STATIC`，`--enable-static` 必须显式给；libmnl 制品为 static-only，且 OHOS 上 CMake 不为导入的共享库注入 RPATH/RUNPATH ⇒ 共享交付会让 out-of-tree 消费者找不到 libmnl（与同族 libmnl/1.0.5、libnfnetlink/1.0.2 一致）。

### 2.2 五维测试账本（PR 正文 / 本文件 / `test_package/MANIFEST.yml` 三处同源）

> **⚠ 口径（防 rule4 少报/虚报误读）**：上游**没有任何 automake 用例**（`configure.ac` 与
> `examples/Makefile.am` 均**无 `TESTS` 变量**、无 `add_test`/`enable_testing`）⇒ 上游侧五维**全部为 0**。
> `make check` 在本包只做一件事：**编译并链接** 3 个 `check_PROGRAMS`（examples/ 下的交互式工具）。
> 它们**不是用例**，上游也不执行它们 ⇒ 下表**不得**把"编译了 3 个 exe"写成"跑了 3 个用例"。

| 维度 | 读数 | 依据 |
|---|---|---|
| `N_static`（上游静态声明的原子用例） | **0** | 无 `tests/` 目录；`TESTS`/`add_test`/`enable_testing` 在 `Makefile.am`/`configure.ac`/`Makefile.in` 中**无命中**（`Makefile.in` 只出现 `check_PROGRAMS`） |
| 可执行用例数 | **0** | 上游未注册任何 `TESTS`/runner ⇒ 无"可执行用例"这一维度 |
| 实测通过数 | **0** | 上游用例数为 0，无分母 |
| 跳过数 | **0** | 未执行任何用例，故无跳过项 |
| 失败数 | **0** | 同上 |
| `N_consumer`（新增消费者测试，独立项） | **1 个程序 / 24 断言** | `test_package/test.c`；`conan create` 的 `test()` 实跑 `libnetfilter_acct 1.0.3 consumer test OK: 24/24 assertions`，rc=0 |

**单列说明：`make check` 的 3 个 examples（编译+链接，非用例）**

- `examples/Makefile.am:3` `check_PROGRAMS = nfacct-get nfacct-add nfacct-del`；`make check` 实际日志为
  `make  nfacct-get nfacct-add nfacct-del` → `CC nfacct-get.o / nfacct-add.o / nfacct-del.o` +
  `CCLD nfacct-get / nfacct-del / nfacct-add`。
- **构建产物 3/3 成功**：`examples/nfacct-{get,add,del}` 各 **39360 B**。
- 这 3 个目标**不是 automake 用例、上游不执行**：它们是交互式示例，运行需要内核 nfnetlink ACCT 对象
  与 `CAP_NET_ADMIN`（本机/CI 均无该授权路径）。因此它们的**执行数 = 0**，本文件与 PR 正文**都不为它们申报任何通过率**。
- 把它们接入 `build()` 的意义只是**让上游自带的编译+链接验证路径真的跑一遍**（否则上游这条验证路径被静默跳过）。

- 上游测试用例通过率：**0/0（上游无 `TESTS` 用例，无分母可报；清点证据见上表依据列）**
- 新增测试用例通过率：**24/24**（100%）
- 消费者测试 API 面：`nfacct_alloc` / `nfacct_free` / `nfacct_attr_set` / `nfacct_attr_set_str` / `nfacct_attr_set_u64` / `nfacct_attr_unset` / `nfacct_attr_get` / `nfacct_attr_get_str` / `nfacct_attr_get_u64` / `nfacct_nlmsg_build_hdr` / `nfacct_nlmsg_build_payload` / `nfacct_nlmsg_parse_payload` / `nfacct_snprintf`（PLAIN + JSON）。其中 `build_payload → parse_payload` 是**纯用户态**完整编解码往返（经 libmnl 属性编码 + 大端字段），是本包无需特权即可取得的最强回归手段；`test.c` 内置 `N_ASSERT=24` 计数自校验，账本无法静默漂移。
- **未修改上游测试用例**（examples/ 3 个文件只加了可移植性头守卫，见 §2.3 尾注；无删改、无跳过）。

### 2.3 补丁清单（5 个，逐条在纯净 1.0.3 树上实跑 `patch -p1` rc=0，零 `.orig`/`.rej`）

| 补丁 | 目标 | 内容 | 对应知识 |
|---|---|---|---|
| `0001-build-aux-config.guess.patch` | `build-aux/config.guess` | 加 `HarmonyOS)` 分支（`LIBC=musl`）与直接 `echo aarch64-unknown-linux-ohos` 的系统识别分支 | E007 |
| `0002-build-aux-config.sub.patch` | `build-aux/config.sub` | `maybe_os` 白名单与 `-linux-*` 校验列表各加 `linux-ohos*` | E007 |
| `0003-configure.patch` | `configure` | 两处 `(umask 077 && …)` → `umask 022`（HMDFS 上 077 产出的临时目录不可写） | E011 |
| `0004-src-libnetfilter_acct.c.patch` | `src/libnetfilter_acct.c` | `<libmnl/libmnl.h>` 前 `#include <sys/socket.h>`，并 `#define _UAPI_LINUX_SOCKET_H` + `typedef unsigned short __kernel_sa_family_t;` | E091 / E119 |
| `0005-examples-sockaddr-guard.patch` | `examples/nfacct-{get,add,del}.c` | 同样三行守卫（这 3 个 check_PROGRAMS 直接 `#include <libmnl/libmnl.h>`，同一条头链） | E091 / E119 |

**0004/0005 的因果链（本次一手实测）**：sysroot 的 bionic 式 uapi `<linux/socket.h>` **无条件**定义 `struct sockaddr_storage`，musl `<sys/socket.h>` 另有一份，两者**不共用守卫宏**（musl 侧没有 `_UAPI_LINUX_SOCKET_H`）⇒ **任何 include 顺序都各自展开一次**。`<libmnl/libmnl.h>` 第 9/10 行先 `<sys/socket.h>` 再 `<linux/netlink.h>`，后者第 22 行拉进 `<linux/socket.h>`，于是该 TU 必然重定义。

- ⚠ **前人 0004 的形态不足以修复**：原 0004 只加了 `#include <sys/socket.h>`（调序半步）。实测两臂 `clang -c` **首错逐字相同**（`linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` + `sys/socket.h:377:8: note: previous definition is here`），预处理产物亦非逐字节相同（5 个 hunk 块重排、净 +1 空行）。补齐 `_UAPI_LINUX_SOCKET_H` 预定义与 `__kernel_sa_family_t` typedef 后消失（sysroot `linux/socket.h` 第 19–20 行确有该守卫，实测）。
- ⚠ **只给 `-D_UAPI_LINUX_SOCKET_H` 也不够**：实测报 `linux/netlink.h:49:3: error: unknown type name '__kernel_sa_family_t'`（`struct sockaddr_nl` 需要它）⇒ 必须**同时**补 typedef，故本包把两步写在同一个补丁里。
- 0005 触及 `check_PROGRAMS`（上游验证目标）的源文件，但**只加头守卫**（+14 行/文件，零删改、零跳过）；这些文件**不安装**（`include/linux/netfilter/Makefile.am` 为 `noinst_HEADERS`，examples 无 `bin_PROGRAMS`），不影响制品内容面。

### 2.4 构建与验证读数

```
$ bash ci/scripts/preflight_check.sh libnetfilter_acct/1.0.3
[OK] 已发布: libmnl/1.0.5      [OK] 版本号未被占用: libnetfilter_acct/1.0.3      rc=0

$ python3 scripts/ohc-run.py conan-verify libnetfilter_acct 1.0.3   # 槽位包裹 --mem 2000 --jobs 8
Verdict: PASS
  G0 ✅  G1 ✅  G2 ✅ (conan create 干净构建)  G3 ✅  G4 ✅  L2 ✅  L4 ✅  L5 ✅
  test package: RUN: …/test_libnetfilter_acct
  libnetfilter_acct 1.0.3 consumer test OK: 24/24 assertions

制品：lib/libnetfilter_acct.a（9098 B，静态）；include/libnetfilter_acct/libnetfilter_acct.h；
      lib/pkgconfig/libnetfilter_acct.pc；package() 已删 lib/*.la
make check：CC/CCLD 三个 check_PROGRAMS（见 §2.2）
```

### 2.5 构建期踩到并已定位的环境陷阱（**非本包缺陷、不影响 CI**，本地记档）

`conan-verify` G2 首红为 `configure: error: could not make ./config.status`（**所有编译探测都通过之后**才挂）。根因**不在本包**：`CONAN_HOME` 名含中文（`home-主理-8-libnfacct`）⇒ conan 生成的 `libmnl.pc` 的 `prefix=` 带非 ASCII 字节 ⇒ `LIBMNL_CFLAGS`/`LIBMNL_LIBS` 两个变量值携带高位字节 ⇒ autoconf `AC_OUTPUT` 的 `ac_delim` 自增循环计数永远差 2（本次 `ac_delim_num=124` vs `ac_delim_n=122`，124 个变量里**恰好** `LIBMNL_LIBS`/`LIBMNL_CFLAGS` 两行不匹配）⇒ 六轮分隔符升级耗尽后 `as_fn_error "could not make $CONFIG_STATUS"`。

- 对照（决定性）：同一棵树、同一 shell、同一 CC，只把 `libmnl.pc` 的 `prefix=` 换成 ASCII 副本 ⇒ `configure` **rc=0**，`config.status` 63973 B 落盘；另四臂（ASCII/非 ASCII 构建目录 × hnp bash `/bin/sh`）**全部仍失败** ⇒ 与 CWD、与 shell 无关，因子就在 `.pc` 派生变量。
- 处置：`CONAN_HOME` 换纯 ASCII（`home-zhuli8-libnfacct`）后**同配方零改动一次通过**。
- ⚠ 该机制**在 CI 不复现**（worker 的 CONAN_HOME 为 ASCII），已在 `经验文档/B草稿库/DRAFT-PKG-VER-non-ascii-conan-home-pc-prefix-toybox-sed.{kv,md}` 追加为本机制第 3 例独立复现（含变量级定位与 A/B 对照）。

### 2.6 已知限制

- 3 个 `check_PROGRAMS` 只做编译+链接校验，未运行（需内核 ACCT 对象与 `CAP_NET_ADMIN`）；这是上游 `make check` 的固有边界，非本次适配削减。
- 本包为静态交付，消费者需一并链接 libmnl（Conan 依赖链已自动传播）。
- 未做真机 netlink 往返（ACCT 对象增删查）；消费者测试覆盖到用户态编解码边界为止。

## 注意事项

- 交付形态与同族一致（libmnl/1.0.5、libnfnetlink/1.0.2、libnetfilter_queue/1.0.5）：**静态**、`make check` 接入 `build()`、`package()` 删 `.la`。
- 0004/0005 的守卫是**幂等**的（`#ifndef`）：若未来上游或工具链自带该修复，补丁仍可安全应用。

**编译结束**: 2026-10-18
**最终状态**: built
- 交付状态: built
---

**编译结束**: 2026-10-18 02:46
**最终状态**: built
