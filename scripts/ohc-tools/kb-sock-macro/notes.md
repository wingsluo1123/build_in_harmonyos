# KB-SOCK-MACRO 取证与踩坑笔记

## 1. 取证环境（全部实测，非推断）

| 项 | 值 |
|---|---|
| 编译器 | clang 15.0.4 |
| Target | `aarch64-unknown-linux-ohos` |
| sysroot 头 | `.../ohos-sdk_26.0.0.18/ohos/native/.../sysroot/usr/include/sys/socket.h` |
| 平台宏真值 | `SOCK_CLOEXEC=02000000`(524288) `SOCK_NONBLOCK=04000`(2048) `SOCK_SEQPACKET=5` `MSG_NOSIGNAL=0x4000` `MSG_CMSG_CLOEXEC=0x40000000` `SO_REUSEPORT=15` |
| 上游实证 | sndio 1.10.0 `bsd-compat/bsd-compat.h:58`（原始形态保留 TAB：`#define SOCK_CLOEXEC<TAB>0`） |

## 2. 证据链

### 2.1 编译期（宽松 / 严格）

```
$ clang -Wall -O2 src/demo_sock.c test/check_cloexec.c -o check_loose
./bsd-compat/bsd-compat.h:19:9: warning: 'SOCK_CLOEXEC' macro redefined [-Wmacro-redefined]
sys/socket.h:99:9: note: previous definition is here
        #define SOCK_CLOEXEC   02000000
2 warnings generated.                      # rc=0

$ clang -Walletc -Werror=macro-redefined ...   # 同一份代码
error: 'SOCK_CLOEXEC' macro redefined [-Werror,-Wmacro-redefined]
2 errors generated.                        # rc=1
```

真实 sndio 头同样验证：

```
$ cd sndio-1.10.0 && printf '#include <sys/socket.h>\n#include "bsd-compat/bsd-compat.h"\n...' | clang -I. -Werror=macro-redefined -x c - -c -o /dev/null
error: 'SOCK_CLOEXEC' macro redefined [-Werror,-Wmacro-redefined]     # pristine rc=1
（fix.sh 加守卫后）                                                    # fixed rc=0
```

### 2.2 运行期（宽松编译通过之后）

```
ok 1 - demo_open_cloexec_socket() succeeded
not ok 2 - FD_CLOEXEC set by SOCK_CLOEXEC
not ok 3 - O_NONBLOCK set by SOCK_NONBLOCK
# SOCK_CLOEXEC=524288 SOCK_NONBLOCK=2048
1..3                                       # rc=1
```

注：`ok 1` + 后两条 `not ok` 是本条目的关键形态——**`socket()` 不报错**，缺陷只体现在 fd 属性上。
诊断行里的 `524288/2048` 来自测试 TU（未 include 兼容层头），正是平台真值，与库 TU 里的 `0` 形成对照。

### 2.3 修复后

```
FIX-A: guarded .../bsd-compat/bsd-compat.h:19 SOCK_CLOEXEC (platform 02000000, fallback 0)
FIX-A: guarded .../bsd-compat/bsd-compat.h:23 SOCK_NONBLOCK (platform 04000, fallback 0)
KB-SOCK-MACRO fix done: 2 site(s) guarded
→ 严格编译 rc=0；运行 ok 1/2/3 全绿，rc=0
```

真实 sndio 修复后的 diff（`fix.sh` 输出，保留上游 TAB）：

```diff
 #ifndef HAVE_SOCK_CLOEXEC
+#ifndef SOCK_CLOEXEC
 #define SOCK_CLOEXEC	0
 #endif
+#endif
```

detect 复扫修复后源码：`no hit`，rc=0（幂等且不误报）。

## 3. 与已交付人工补丁的差异（如实披露）

`archives/s/sndio/1.10.0/patches/0001-bsd-compat-bsd-compat.h.patch` 交付时除加守卫外，
还把 `#define SOCK_CLOEXEC<TAB>0` 的 TAB 归一化成空格；`fix.sh` **保留原始字节**（`out.append(raw)`），
只插入守卫行。两者语义完全等价，`fix.sh` 的 diff 更小；混合空白差异不进入判据。

## 4. 踩坑

1. **样例库首测即暴露自身错误**：`check_cloexec.c` 最初没有 `#include <sys/socket.h>`，
   `SOCK_CLOEXEC` 在测试 TU 未声明 → 报 `use of undeclared identifier`，看起来像"编译失败"，
   实际是样例自身 bug，掩盖了 `macro redefined` 这条真现象。修法是补系统头，让测试 TU 用平台真值、
   库 TU 用被覆盖的兜底值——两侧对照才有意义。
2. **`-Wall` 不会让构建红**：宽松编译 rc=0，必须靠 `-Werror=macro-redefined` 或运行期断言才能暴露；
   只跑 `make` 就宣布"编过了"是这类问题的典型漏检。
3. **覆盖方向取决于 include 顺序**：`bsd-compat.h` 在系统头之后 include 时宏被改成 0；
   若在系统头之前 include，系统头会再覆盖回 `02000000`，此时只剩告警、运行期反而正确。
   不要因为"运行没问题"就认为告警可以忽略——顺序是偶然的，重构/头文件整理会翻转结果。
4. **平台缺宏 ≠ 缺陷**：判据必须带"平台已定义"这一前提，否则会把合法的老系统兜底误报成缺陷
   （detect 输出里 `INFO ... #platform-undefined` 即此类，不计入命中）。

## 5. 与图谱现有条目的边界（防重复）

| 已有条目 | 覆盖内容 | 与本条目区别 |
|---|---|---|
| E086 `ohos-guard-ucred` | `struct ucred` / `SO_PEERCRED` / `SCM_CREDENTIALS` 缺失与本地 shim | 讲 peer credential **结构体缺失**；本条目讲 socket 扩展位**宏值被覆盖** |
| E510 / E254 / E484 / E431 / E475 / E526 | toybox patch 的 HUNK 失败、dry-run、postimage 保真、strip | 讲补丁**工具链**；本条目在集成建议里只引用其"补丁生效必须断言"的做法 |
| E274 / E316 / E330 / E383 / E537 | soname / DT_NEEDED / 运行时库解析 | 链接期问题，与本条目无关 |
| E532 | CMake 不识别 HarmonyOS 的三分支判定 | 构建系统条件分支；本条目是预处理器宏值覆盖 |

查重取证（`knowledge/graph/index.tsv`，本次立项前）：
`SOCK_CLOEXEC|SOCK_NONBLOCK|ancillary|cmsg|CMSG` → **0 命中**；
`bsd-compat|HAVE_SOCK|compat layer|portability shim` → **0 命中**。

## 6. 复现日志位置

`reproduce.sh --keep` 会保留工作目录（默认 `$TMPDIR` 或 `$HOME/tmp` 下的 `kb-sock-macro-repro.<pid>/`），
其中 `repro.log` 为全量汇总，另有 `p1-loose-build.log`、`p1-loose-run.log`、`p1-strict-build.log`、
`p2-detect.log`、`p2-fix.log`、`p2-strict-build.log`、`p2-run.log`。
所有输出均重定向落盘，脚本内不使用 `| head`（避免 SIGPIPE 掩盖退出码）。
