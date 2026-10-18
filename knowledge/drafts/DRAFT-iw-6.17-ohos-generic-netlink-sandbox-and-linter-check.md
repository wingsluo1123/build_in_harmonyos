# DRAFT: OHOS app 沙箱的 netlink 协议号白名单 × 「check 目标 ≠ 测试套件」

> 来源：`feat/iw-6.17` 适配（平台任务 15547），2026-10-17。
> 配对文件：`DRAFT-iw-6.17-ohos-generic-netlink-sandbox-and-linter-check.kv`

## 一、两个被混淆的问题

iw 6.17 在 OHOS 上出现两个**必须分开记账**的"不可用"：

| # | 面 | 现象 | 性质 | 可修? |
|---|---|------|------|-------|
| 1 | 编译期 | `redefinition of 'sockaddr_storage'`（每个 TU） | sysroot 头不一致 | **可修**（E119/E1604） |
| 2 | 运行期 | `Failed to connect to generic netlink.` rc=1 | 沙箱权限策略 | **不可修** |

把两者混为一谈，就会"修好编译就以为修好了运行"。

## 二、机制一：netlink 协议号白名单（**修正 E237 的框架**）

### 实测（本机 python3，6 行探针）

```
NETLINK_ROUTE(0):    socket OK, bind OK
NETLINK_GENERIC(16): socket FAILED errno=13 (EACCES) Permission denied
NETLINK_NETFILTER(12): errno=13 (EACCES)
NETLINK_SELINUX(7):    errno=13 (EACCES)
未分配 proto=30:        errno=13 (EACCES)
未分配 proto=31:        errno=13 (EACCES)
```

### 判别要点（本条的核心）

**未分配协议号也返回 `EACCES`，而不是 `EAFNOSUPPORT`（97）。**

- 若真是「内核缺 NETLINK_GENERIC 协议族」（E237 的框架）⇒ 应为 `EAFNOSUPPORT`。
- 实测是 `EACCES`（权限），且**连内核根本没注册的 proto=30/31 也一样** ⇒
  裁决发生在**沙箱策略层、按协议号做白名单**，**先于**内核解析协议族是否存在。
- 结论：这不是"内核被裁剪"，而是"沙箱只放行 `NETLINK_ROUTE(0)`"。

> ⚠ 写 notes / 正文时若照抄 E237 的措辞（"内核缺 NETLINK_GENERIC"）会**误诊**，
> 进而误导后续包去"补内核设施"。带上未分配协议号这一探针即可自证。

### 后果与正确断言姿势

一切经 generic netlink 访问 nl80211 的工具（iw、ethtool 的 netlink 后端、
libnl 的 genl API 使用者）运行期必然失败：

```
$ iw --version   → iw version 6.17        rc=0     ← CLI 契约面可用
$ iw             → Usage: / Commands:     rc=0
$ iw help        → Usage: / Commands:     rc=0
$ iw dev         → Failed to connect to generic netlink.  rc=1   ← 能力墙
$ iw phy         → Failed to connect to generic netlink.  rc=1
```

**断言姿势**：把 rc **和**文案**逐字固定**，不要放宽成"rc 非 0 即可"、更不要跳过。
平台一旦放开，断言立刻翻红暴露——这才是诚实的能力墙记账。
（iw 6.17 的 `test_package/test_iw.py` A8/A9 即此形态。）

## 三、机制二：「check 目标存在」≠「有测试套件」

### iw 6.17 的清点事实（R51 六探针，全 0）

```
P1 test/tests 目录                    : 0
P2 TESTS= / check_PROGRAMS=           : 0     ← 无 Makefile.am，仅裸 Makefile
P3 test*.c / *_test.c 测试源           : 0
P4 add_test( / ctest / enable_testing  : 0
P5 *RUNTEST* / runtest 驱动            : 0
P6 demo / demos / examples 目录        : 0
```

全树 52 文件（40 `*.c` + 4 `*.h` + Makefile + Android.mk + version.sh + iw.8 +
COPYING + README + CONTRIBUTING + .gitignore）；全树 `grep -i test` 唯一命中是
`NL80211_CMD_TESTMODE`（nl80211 驱动透传命令，**不是测试**）。

**但** Makefile 里**有**一个 `check:` 目标：

```make
check:
	$(Q)$(MAKE) all CC="REAL_CC=$(CC) CHECK=\"sparse -Wall\" cgcc"
```

这是 **sparse/cgcc 静态分析 lint**，本机 `sparse`/`cgcc` 均不存在。

### 陷阱的两个方向

| 判据错法 | 后果 |
|---|---|
| 「有 check 目标 ⇒ 有测试套件 ⇒ 报 N>0」 | 与 rule4 实测口径不符；且若照抄 ethtool 的 `autotools.make(target="check")` + `upstream_test_in_build: true`，会**失败或空跑假绿** |
| 「没跑起来 ⇒ 少报 N=0」 | 也可能错——见对偶条目 |

### 与既有条目的对偶关系

- `DRAFT-ydpdict-1.0.4.1-autotools-empty-tests-check-programs-audit`：
  **假阴性**陷阱——`TESTS` 为空但 `check_PROGRAMS` 非空（ydpdict 1.0.4 曾误报 N=0，
  实际 4 条）⇒ **清点必须下探 check_PROGRAMS**。
- 本条：**假阳性**陷阱——check 目标存在但其语义是 lint/格式/打包
  （sparse、cgcc、cppcheck、clang-tidy、shellcheck、check-format）
  ⇒ **不能据此报 N>0，也不能把它当测试跑**。

⇒ 正确做法是**三态分类**，而非二态"有没有 check 目标"：

1. **真测试套件**（`TESTS=`/ctest/`add_test` 有注册项）→ 真跑，回填 N/N′/通过率；
2. **无任何测试资产** → `N_static = 0`，逐条给清点命令；
3. **有 check 目标但语义是 lint/格式/打包** → `N_static` **仍为 0**，
   并在正文明确写"该 check 目标不是测试套件、不执行、不计入 N"。

### rule4 口径（判定优先的结论）

rule4 的 FAIL 谓词原文是「上游**有用例 N 个**但一个也没测（0/N）」——**要求 N>0**。
iw 的 N=0（而非"有 N 条没跑"）⇒ 不触发 rule4。
同日平台 approved 的同口径先例：fuse #16210（`upstream_tests present:false`）、
fstobdf #16251（`upstream_tests_static: 0`）、esmtp #16097（上游零测试资产）、
edid-decode #16167（Makefile 只有 all/clean/install，无 check）。

## 四、处置清单

- [x] 编译期走 E119/E1604：预锁 `_UAPI_LINUX_SOCKET_H` + 补 `__kernel_sa_family_t`；
      **用 libc 鉴别探针**（`#if defined(__linux__) && !defined(__GLIBC__)`）而非
      `__OHOS__`（E119 原处方用了平台宏，E1604 明确 forbid，PF5 会拦）。
- [x] 运行期：能力墙逐字断言（rc + 文案），不放宽、不跳过。
- [x] 测试清点：六探针 + 三态分类，`N_static = 0` 并给可复现命令。
- [x] **不**设 `upstream_test_in_build: true`、**不**把 lint 当测试跑。

## 五、复现命令

```bash
# 协议号白名单判别（关键：未分配协议号也应为 EACCES 而非 EAFNOSUPPORT）
python3 -c "import socket,errno
for p in (0,16,30):
    try: socket.socket(16,3,p).close(); print(p,'OK')
    except OSError as e: print(p,errno.errorcode.get(e.errno))"

# 六探针清点（官方 tarball）
tar xf iw-6.17.tar.xz && cd iw-6.17
find . -type d \( -name test -o -name tests -o -name testing \) | wc -l
grep -rE '^[[:space:]]*(TESTS|check_PROGRAMS)[[:space:]]*[:+]?=' . | wc -l
find . -name 'test*.c' -o -name '*_test.c' | wc -l
grep -rE 'add_test\(|ctest|enable_testing\(' . | wc -l
find . -iname '*RUNTEST*' | wc -l
find . -type d \( -name demo -o -name demos -o -name examples \) | wc -l

# check 目标语义鉴别
grep -n '^check:' -A2 Makefile
command -v sparse cgcc || echo 'sparse/cgcc absent: check 目标不可执行'
```
