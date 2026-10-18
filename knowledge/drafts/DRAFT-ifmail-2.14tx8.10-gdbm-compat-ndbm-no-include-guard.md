# DRAFT: OHOS 无系统 ndbm，只能用 gdbm compat 层——而它的 `<ndbm.h>` 没有 include guard，且制品仓 gdbm 1.23/1.24 的 compat 开关相反

- **Status**: DRAFT
- **出处**: ifmail 2.14tx8.10 适配（2026-10-16，【知识库扩展】PR，分支 `feat/ifmail-2.14tx8.10`）
- **领域**: 依赖选型 + 头文件包含纪律（compat 层替代系统 API）
- **agent_id**: 6E98

## 相关既有条目（撞车判定）

查重方式：`ohc-run.py engine "<真实报错>"` + `grep -in "ndbm\|gdbm" knowledge/graph/index.tsv`。

| 条目 | 它覆盖什么 | 本条增量 |
|---|---|---|
| E119 | OHOS SDK 里 `linux/socket.h` 与 `sys/socket.h` 同时包含导致 `sockaddr_storage` 重定义，用 `_UAPI_LINUX_SOCKET_H` 宏守卫跳过 | **同一类症状（同一 TU 里类型被定义两次）但完全不同的一对头**：E119 是内核 UAPI 头 vs 用户态头，可用宏守卫；本条是**依赖包提供的 compat 头自身缺 guard**，消费方无法用宏守卫解决（不能改依赖包），只能收敛包含点。engine 对本条报错串只命中 E119（Phase B: 1），说明没有覆盖 |
| E042 | Python 扩展模块的 RPATH/patchelf（关键词里带 gdbm 只是因为它 `_gdbm` 扩展） | 与 dbm API 无关，仅关键词偶然重叠 |
| nmh/1.8 配方 | 自带 `ndbmcompat/ndbm.h` shim，配 gdbm/1.24（compat 关闭）走自实现路线 | 那是 fallback 路线（本条 fallback_approach 即引它）；本条主张**优先选 compat 打开的 gdbm/1.23**，并把 1.23/1.24 开关相反这件事记成选型硬规则 |
| rgb/1.1.1 notes | 记录"实测 gdbm/1.23 compat 层可让 `checking for dbm_open in -lgdbm_compat... yes` 通过，头文件才是硬墙" | 与 1.23 可用性结论一致；本条补上 **1.24 是 --disable-libgdbm-compat**、以及 ndbm.h 无 guard 这个从未被记录过的编译期地雷 |

结论：无既有条目覆盖，独立申报；`similar_to: E119`。

## Scope（何时用）

源码里出现经典 dbm/ndbm API 的任何软件在 OHOS 上适配时：

```
dbm_open / dbm_store / dbm_fetch / dbm_delete / dbm_firstkey / dbm_nextkey / dbm_close
dbminit / fetch / store / nextkey / dbmclose            （更老的 dbm.h 一族）
#include <ndbm.h> / #include <dbm.h> / -DHAS_NDBM_H
configure: AC_CHECK_HEADERS(ndbm.h) / --with-ndbm / checking for dbm_open in -lgdbm_compat
```

实测命中：ifmail 2.14tx8.10（`iflib/ref.c`、`ifgate/{msgidbm,ifdbm,nlindex,nodecheck}.c`、
`ifcico/nlindex.c`，共 30 处 `dbm_*` 调用）。

**不适用**：只用 gdbm 原生 API（`gdbm_open`/`gdbm_fetch`）的软件；Berkeley DB（`db.h` +
`db_create`）路线。

## Symptom（真实日志，2026-10-16 本机 OHOS clang 15 交叉构建）

地雷一：同一 TU 二次包含 compat 头。

```
In file included from nlindex.c:19:
In file included from ./nlindex.h:9:
/Users/.../gdbmaa77d3992c61d/p/include/ndbm.h:42:3: error: typedef redefinition with different types ('struct DBM' vs 'struct DBM')
} DBM;
  ^
nlindex.c:10:10: note: '/Users/.../include/ndbm.h' included multiple times, additional include site here
#include <ndbm.h>
         ^
./nlindex.h:9:10: note: '/Users/.../include/ndbm.h' included multiple times, additional include site here
#include <ndbm.h>
         ^
/Users/.../include/ndbm.h:42:3: note: unguarded header; consider using #ifdef guards or #pragma once
} DBM;
  ^
2 errors generated.
make: *** [nlindex.o] Error 1
```

地雷二：选了 compat 被关闭的那个 gdbm 版本（本例是**预先**实测避开的，症状为）：

```
fatal error: 'ndbm.h' file not found        # 包内只有 gdbm.h
ld.lld: error: cannot find -lgdbm_compat    # 包内只有 libgdbm.a
```

## Root Cause

**(1) OHOS/musl 没有 ndbm。** 既没有 `<ndbm.h>`/`<dbm.h>`，libc 里也没有 `dbm_open`
一族符号。经典 dbm API 只能由 gdbm 的 compat 层（`libgdbm_compat`）代打。

**(2) 制品仓两个 gdbm 版本的 compat 开关相反**（读配方实测）：

| 包 | generate() 里的 configure_args | 包内实测内容 |
|---|---|---|
| `gdbm/1.23`（shared=False） | `--enable-libgdbm-compat` | `include/{ndbm.h,dbm.h,gdbm.h}` + `lib/{libgdbm.a,libgdbm_compat.a}` |
| `gdbm/1.24`（shared=True） | `--disable-libgdbm-compat` | 只有 `gdbm.h` + `libgdbm` |

`conan list "gdbm/*" -r=ohpcd` 只会告诉你"gdbm 存在"，看不出 compat 开关，
必须 `conan download gdbm/<ver> -r=ohpcd --only-recipe` 读配方、或下载包体
`ls include lib` 实测（R35 也是这个口径：不用 `conan list` 下结论）。

**(3) gdbm compat 的 `ndbm.h` 完全没有 include guard。**
实测 `grep -c "ifndef\|pragma once" <gdbm1.23>/include/ndbm.h` == **0**，
而它内部是 `typedef struct { GDBM_FILE file; int dirfd; datum _dbm_memory;
char *_dbm_fetch_val; gdbm_error _dbm_errno; } DBM;`。第二次包含就是
typedef 重定义 → clang 硬错误（不是 warning，`-w` 也压不掉）。

为什么老项目特别容易踩：K&R 时代的习惯是".c 里把自己用到的系统头都包含一遍"，
项目自己的头（ifmail 的 `ifgate/nlindex.h`）也包含 `<ndbm.h>`，于是同一 TU
出现两次。在 glibc 上从来不出事——glibc 侧的 ndbm.h（无论来自 glibc 还是发行版
打包的 libgdbm-compat）带 guard；换到 OHOS 就炸。

## Workaround / 修复

**(1) 依赖选型**（配方里写清理由，防止后人"升级到 1.24"）：

```python
def requirements(self):
    # gdbm/1.23 是制品仓里 --enable-libgdbm-compat 的那个版本（静态），
    # 提供 <ndbm.h> 与 libgdbm_compat.a；gdbm/1.24 是 --disable-libgdbm-compat，
    # 连 ndbm.h 都没有，无法承载本包。
    self.requires("gdbm/1.23")
```

链接顺序 compat 在前：`LIBS="-L<gdbm>/lib -lgdbm_compat -lgdbm"`。

**(2) 收敛包含点**：让项目自己的头成为 `<ndbm.h>` 的唯一包含点，删掉 .c 里重复的
直接包含；同块里其它必要的头要留下（ifmail 的 `nodecheck.c` 的 `<fcntl.h>`
就嵌在被删的 `#ifdef HAS_NDBM_H` 块里，删块时必须保留，否则 `O_RDWR`/`O_CREAT`
未声明）。顺手把 `#else` 的 `<dbm.h>` 回退分支补齐，与同项目另一份头保持一致：

```c
#ifdef HAS_NDBM_H
#include <ndbm.h>
extern DBM *nldb;
#else
#include <dbm.h>
#endif
```

对应补丁：`archives/i/ifmail/2.14tx8.10/patches/0005-ifgate-nlindex.c.patch`、
`0006-ifgate-nodecheck.c.patch`、`0012-ifgate-nlindex.h.patch`。

**(3) 不能改依赖包里的头。** 给 `<gdbm>/include/ndbm.h` 加 guard 看似最省事，
但包是共享制品：改动不进 git，下次 `conan install`/换机器就消失，本地与 CI
行为分叉。

## 验证（可复算）

```sh
G=$(conan cache path gdbm/1.23)/p
printf '#include <ndbm.h>\nint main(void){DBM *d=dbm_open("x",0,0600);(void)d;return 0;}\n' > /tmp/ndbm1.c
printf '#include <ndbm.h>\n#include <ndbm.h>\nint main(void){DBM *d=dbm_open("x",0,0600);(void)d;return 0;}\n' > /tmp/ndbm2.c
clang --target=aarch64-linux-ohos --sysroot=$SYSROOT -c /tmp/ndbm1.c -I$G/include -o /dev/null   # rc=0
clang --target=aarch64-linux-ohos --sysroot=$SYSROOT -c /tmp/ndbm2.c -I$G/include -o /dev/null   # typedef redefinition
grep -c 'ifndef\|pragma once' $G/include/ndbm.h                                                  # 0
grep -n 'libgdbm-compat' $(conan cache path gdbm/1.23)/e/conanfile.py \
                         $(conan cache path gdbm/1.24)/e/conanfile.py                            # enable / disable
```

实测结论（2026-10-16）：单次包含 rc=0；二次包含报 `typedef redefinition with
different types ('struct DBM' vs 'struct DBM')`；**OHOS clang 15 与宿主 Apple
clang 17 同样报错**，说明这是 gdbm compat 头自身的缺陷，与 OHOS 工具链无关
（也意味着任何消费方、任何构建机都会踩）。

修复后端到端验证：`ifindex -I <fixture>` 建 ndbm 索引 → `nlookup -I <fixture> -v
2:5020/230` 读回，输出与预期 8 行逐字节一致（`archives/i/ifmail/2.14tx8.10/
test_package/test_ifmail_ohos.sh` 的 OHOS-1，5 项；参考构建 11/12，唯一未过项
OHOS-1b 断言 `index.pag` 非空——gdbm compat 的两文件布局，macOS 的 BSD db 落在
`index.db`，属本地不可验证项，只在真机成立）。

## Prevention

1. 需要 ndbm/dbm 的包，**选型时就读依赖配方**的 configure_args，别只看
   `conan list` 有没有这个包名。
2. 遇到 `typedef redefinition with different types ('struct X' vs 'struct X')`
   且 clang 附 `unguarded header`，第一反应是"谁包含了两次"，不是"类型定义冲突"。
   `clang` 的 note 已经直接把两个 include site 的行号打出来了。
3. 老代码的 `.c` 直接包含系统头 + 项目头也包含同一系统头，是 1990s 项目的通病；
   适配时顺手把包含点收敛到项目头，能一次消掉整类问题。
4. 不要给依赖包内的头打补丁。

## References

- `archives/i/ifmail/2.14tx8.10/{conanfile.py,conandata.yml,notes.md}`
- `archives/i/ifmail/2.14tx8.10/patches/{0005,0006,0012}-*.patch`
- `archives/i/ifmail/2.14tx8.10/test_package/test_ifmail_ohos.sh`（OHOS-1）
- `archives/n/nmh/1.8/{conanfile.py,ndbmcompat/ndbm.h}`（fallback shim 先例）
- `archives/r/rgb/1.1.1/conanfile.py`（gdbm/1.23 compat 可用性的既有实测记录）
- gdbm 上游 `compat/ndbm.c`、`compat/dbminit.c`（compat 层实现）
