# E688 — OHOS sysroot 无 fts(3)：C 程序的 fts 目录遍历须改写为 POSIX dirent 递归

## 错误特征

```
./medialib.h:32:10: fatal error: 'fts.h' file not found
#include <fts.h>
         ^~~~~~~
1 warning and 1 error generated.
make: *** [Makefile.linux:33: commands.o] Error 1
```

同族表现（不同编译器/语言前端）：

- `call to undeclared function 'fts_open'` / `implicit declaration of function 'fts_read'`（clang，无头文件时会报未声明）
- 链接期 `undefined symbol: fts_open` / `cannot find -lfts`

## 触发条件

- 平台: OHOS / HarmonyOS PC（aarch64，musl 系 sysroot）
- 阶段: compilation（首次编译即失败；若头文件被条件包含，也可能推迟到 linking）
- 构建系统: 任意（手写 Makefile / autotools / cmake），只要源码直接 `#include <fts.h>`
- 典型代码: 用 fts(3)（`fts_open`/`fts_read`/`fts_close`，FTS_LOGICAL/FTS_NOCHDIR/FTS_PHYSICAL）做递归目录遍历、文件扫描、库索引的 C 程序

## 根因分析

OHOS musl 系 sysroot **既没有 fts.h 头文件，也没有 fts(3) 的实现符号**：

```bash
$ nm -D "$(clang -print-file-name=libc.so)" | grep -c fts_open
0
$ find "$(dirname "$(clang -print-file-name=libc.so)")/../include" -name fts.h
（空）
```

fts(3) 是 BSD 遗产（后被 glibc 收录），不属于 POSIX，musl 未实现。因此 C 程序不能靠
"加一个依赖" 解决——制品仓里也**没有**可用的 libbsd（libbsd 提供 fts 移植）：

```bash
$ conan download libbsd/0.12.2 -r=ohpcd --only-recipe
ERROR: Recipe not found
```

C++ 程序可以走 `std::filesystem::recursive_directory_iterator`（见关联条目里的 zeek 案例），
但 C 程序只能把遍历本身改写成 POSIX 接口。改写时必须注意 FTS_LOGICAL（跟随符号链接）语义：
朴素的 `opendir/readdir` 递归遇到指回祖先的符号链接会**无限递归**。

## 解决方案

### 推荐方案

把 fts 遍历重写为 POSIX `opendir/readdir/stat` 递归，逐项保留原语义：

1. 把原 `case FTS_F:`（普通文件）分支体抽成一个处理函数（如 `scan_file()`），保留原有
   输出与计数；
2. 主循环改写为递归函数 `scan_dir()`：`printf("Checking Directory: %s\n", path)` →
   `opendir()` 失败则报 "Unreadable" 并计 skipped_dir → 遍历 `readdir()`，跳过 `.`/`..`
   → `stat()` 失败按原语义处理（悬空符号链接静默跳过，其余计 error）→ 目录递归、普通文件
   交 `scan_file()`；`closedir()`；
3. 为 FTS_LOGICAL 语义维护 **dev/inode 祖先表**（`dev_t devs[N]; ino_t inos[N]`，深度上限
   128）：进入子目录前比对祖先链，命中即跳过（等价于 fts 的 FTS_DC 环检测）；
4. 头文件 `#include <fts.h>` 改为 `#include <dirent.h>`。

vitunes 2.3 实测补丁（可直接对照实现）：`archives/v/vitunes/2.3/patches/0002-medialib.c.patch`、
`0003-medialib.h.patch`。

> 若项目已有 `compat/` 这类平台垫片目录，也可以把 dirent 递归封装成内部 `fts_*` 兼容层
> （本文不推荐：多一层间接、且要自己复刻 FTSENT 结构，成本高于直接改写调用点）。

### 禁止做法

- ❌ 用空壳 `fts.h` 或 stub（`fts_open` 返回 NULL / 空实现）让编译通过——遍历功能会静默失效，
  属于 R8 明令禁止的空壳 stub；
- ❌ 在补丁里写 `#ifdef __OHOS__` 之类的平台宏绕开（默认禁止，见 R8/PF5）；
- ❌ 直接复制一份第三方 fts 实现进来（体积大、引入来源与许可问题；本平台 C++ 场景已有官方
  替代 API，C 场景用 dirent 只需几十行）；
- ❌ 用 `nftw()` 硬套：行为差异（排序/环检测/属性获取时机）需要重新对齐，不如递归直写可控。

## 验证

```bash
# 1) 确认平台缺口（命中本条目）
nm -D "$(clang -print-file-name=libc.so)" | grep -c fts_open          # 0
find "$(dirname "$(clang -print-file-name=libc.so)")/../include" -name fts.h   # 空
conan download libbsd/0.12.2 -r=ohpcd --only-recipe                   # Recipe not found

# 2) 改写后：编译通过
make -f Makefile.linux CC=clang CFLAGS=... LDFLAGS=... -j1            # rc=0

# 3) 功能验证：构造含「指回祖先的符号链接」的目录树，扫描须有限时间返回
#    且每个目录只被访问一次（vitunes 实测：4 个目录各访问一次，环被静默跳过）
mkdir -p /tmp/t/music/artist1/album1/sub
: > /tmp/t/music/note.txt
ln -s /tmp/t/music /tmp/t/music/artist1/album1/sub/loop
./<prog> -e add /tmp/t/music | grep -c '^Checking Directory:'        # 4（不多不少）
```

## 适用边界

- 适用：任何直接调用 fts(3) 的 **C** 代码（C99/C11 均可），以及移植到 aarch64/OHOS 后发现
  `fts.h` 缺失的同类工具；
- 适用：需要保留 FTS_LOGICAL（跟随符号链接）语义的目录树扫描（祖先表提供等价环检测）；
- 不适用：C++ 代码（应优先 `std::filesystem`，语义更完整、无需自己写环检测）；
- 不适用：依赖 FTS 独有特性且行为敏感的代码——`FTS_NOSTAT` 延迟 stat、`fts_compar` 自定义
  排序、`FTS_XDEV` 跨设备限制、`fts_children` 批量读取等在本方案中没有对应实现，需按需补齐；
- 深度上限：祖先表固定 128 层（栈友好），超深目录树会记一次 error 并跳过。

## 查重结论（六维对照）

最相近条目：**knowledge/drafts/E432-draft-B3BA**（OHOS sysroot 缺 fts.h / libfts，触发于
zeek 8.2.1 的 zeekygen）。

| 维度 | E432（zeek，C++） | 本条目（vitunes，C） | 是否重复 |
|------|------------------|--------------------|---------|
| 错误特征 | `fatal error: 'fts.h' file not found` | 同 | 重合 |
| 触发条件 | OHOS musl sysroot 缺 fts | 同 | 重合 |
| 根因 | sysroot 无 fts(3)/libfts | 同，并补充"制品仓无 libbsd 可依赖"的实测证据 | 部分重合 |
| 解决方案 | C++17 `std::filesystem::recursive_directory_iterator` | C：POSIX `dirent` 递归 + dev/inode 祖先表环检测 | **不同**（C 无 filesystem） |
| 语言/适用面 | 仅 C++ | 仅 C（C++ 场景仍用 E432 路线） | 互补 |
| 验证方式 | 编译 zeekygen 通过 | 缺符号/缺头的三条探针 + 含符号链接环目录树的访问计数 | **新增** |

其他查重动作：

- `grep -rln "fts\.h\|fts_open" knowledge/graph/ knowledge/doc/ knowledge/drafts/` → 仅命中 E432 草稿；
- `grep -rln "readdir\|符号链接环" knowledge/` → 无 fts→dirent 重写类条目；
- E032（musl 需 `_GNU_SOURCE` 暴露 dirent API）是不同问题（宏可见性，不是 API 缺失），不重合。

结论：**部分重复后保留**。重合点是根因（sysroot 无 fts），差异与新增价值是 C 语言的等效实现、
符号链接环守卫的具体做法，以及"制品仓无 libbsd"这一让"补依赖"路线被排除的实测依据。

## 关联条目

- 部分重复: knowledge/drafts/E432-draft-B3BA（C++ 场景：`std::filesystem` 重写）
- 同族平台缺口: 其它"OHOS sysroot 缺头/缺符号"条目（本条目与 E432 均属该族）
- 具体复现: archives/v/vitunes/2.3（补丁 0002/0003 + notes.md）
