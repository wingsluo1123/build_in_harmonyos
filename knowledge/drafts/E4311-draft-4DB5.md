# E4311 — conan Release 的 `-DNDEBUG` 断掉 `<assert.h>` 传递链 ⇒ 共享库 UND `assert` ⇒ OHOS 运行期 relocation 失败

> 状态：**草稿**（`knowledge/drafts/E4311-draft-4DB5.kv`）
> 首次命中：lttng-ust 2.12.10 适配（`feat/lttng-ust-2.12.10`）· 2026-10-18
> 严重度：🟡 2（链接期全绿、加载期才死，排查方向极易被带偏）

## 错误特征

构建与链接**全部成功**，进入消费者执行阶段立刻失败：

```
Error relocating /storage/.../p/lib/liblttng-ust.so.0: assert: symbol not found
ERROR: lttng-ust/2.12.10 (test package): Error in test() method, line 60
	ConanException: Error 127 while executing
```

构建日志里只有**警告**、没有任何错误（可 grep）：

```
liblttng-ust/lttng-events.c:188:2: warning: call to undeclared function 'assert';
        ISO C99 and later do not support implicit function declarations
liblttng-ust/lttng-events.c:204:2: warning: ...
liblttng-ust/lttng-events.c:624:2: warning: ...
liblttng-ust/lttng-events.c:647:2: warning: ...
liblttng-ust/lttng-ust-statedump.c:389:4: warning: call to undeclared function 'assert';
liblttng-ust/ust-core.c:78:3: warning: call to undeclared function 'assert';
```

产物侧的直接判据：

```sh
$ readelf --dyn-syms <pkg>/lib/liblttng-ust.so.0.0.0 | grep -w assert
   104: 0000000000000000     0 NOTYPE  GLOBAL DEFAULT  UND assert     # ← 命中
# 正常应为：  UND __assert_fail
```

因为是**加载期**失败，消费者 `main()` 里的任何日志都打不出来，容易误判为
RPATH/签名/动态链接器问题。

## 触发条件

- 构建系统：autotools（conan `AutotoolsToolchain`）
- `build_type` ∈ {Release, RelWithDebInfo, MinSizeRel} ⇒ conan 把
  `self.ndebug = "NDEBUG"` 注入 `CPPFLAGS`
- 依赖某个「NDEBUG 条件包含 `<assert.h>`」的头（本次是 liburcu 的
  `urcu/assert.h`），而本包又有 TU **自己漏写 `#include <assert.h>`**
- 换到不导出 `assert` 兼容符号的 libc（OHOS/musl）

## 根因分析

liburcu 的 `include/urcu/assert.h`：

```c
#ifdef NDEBUG
# define urcu_posix_assert(_cond) _urcu_use_expression(_cond)
#else
# include <assert.h>
# define urcu_posix_assert(_cond) assert(_cond)
#endif
```

lttng-ust 2.12.10 的 3 个 TU（`liblttng-ust/lttng-events.c`、
`liblttng-ust/lttng-ust-statedump.c`、`liblttng-ust/ust-core.c`）**自己不包含**
`<assert.h>`，只靠 `<urcu/uatomic.h>` → `urcu/uatomic/uassert.h` →
`urcu/assert.h` 这条链把它带进来。定义 `NDEBUG` 后链路走 `#ifdef` 分支，
`<assert.h>` 不再被包含，`assert(...)` 就成了**未声明的函数调用**（C99 起只是
warning），于是共享库留下 UND `assert`。

链路之所以在链接期完全静默：libtool 默认不给共享库加 `--no-undefined`，而本仓库
配方又普遍加 `-Wl,--allow-shlib-undefined`（为 musl 的 pthread 符号而加），两者
叠加使未定义符号检查彻底失效。glibc 恰好导出兼容符号 `assert`，所以在 glibc
环境里连运行期都看不到问题——**这是一个换 libc 才暴露的坑**。

## 解决方案

### 推荐方案

在配方 `generate()` 里清掉 conan 注入的 NDEBUG：

```python
tc = AutotoolsToolchain(self)
tc.ndebug = None          # AutotoolsToolchain.__init__ 在 Release 下设为 "NDEBUG"
```

`<urcu/assert.h>` 随即走 `#else` 分支正常 `#include <assert.h>`；实测 UND
由 `assert` 变为可解析的 `__assert_fail`，消费者运行 rc=0。

该做法同时**回到上游 autotools 的默认语义**：上游自身 CFLAGS 默认是 `-g -O2`，
并不定义 NDEBUG（`-DNDEBUG` 是 CMake/发行版打包惯例，不是 autotools 默认）。
本次对照实验：同一份源码手工构建（无 `-DNDEBUG`）→ `UND __assert_fail`、运行
rc=0；conan Release 构建 → `UND assert`、运行 rc=127。

### 回退方案

若要保留 NDEBUG（Release 语义），就给漏 include 的 TU 补 `#include <assert.h>`
（上游补丁形态，更根治，但要逐文件确认）。

### 禁止做法

- ❌ 用 `-Wl,--allow-shlib-undefined`「解决」本坑——它正是链接期无输出的原因，
  等于把加载期崩溃留到运行期。
- ❌ 在共享库里补一个 `assert` 符号糊过去（掩盖真实缺陷且语义可疑）。
- ❌ 见到 `Error relocating …: assert: symbol not found` 就按 RPATH / 签名 /
  动态链接器方向排查（`main()` 日志打不出来是加载期失败的固有形态）。

## 验证

```bash
# 1) 产物判据：应为 0 命中 assert，正常是 UND __assert_fail
readelf --dyn-syms <pkg>/lib/liblttng-ust.so.0.0.0 | grep -w assert

# 2) 构建日志判据：应为 0 命中
grep -c "undeclared function 'assert'" <build-log>

# 3) 运行期 oracle：只 return 0 的消费者也必须能加载
printf 'int main(void){return 0;}\n' > /tmp/ldprobe.c
clang /tmp/ldprobe.c -o /tmp/ldprobe -L<pkg>/lib -llttng-ust -Wl,-rpath,<pkg>/lib \
      -Wl,--allow-shlib-undefined && /tmp/ldprobe; echo "rc=$?"   # 期望 rc=0
```

## 关联条目

- 相关：[E013](E013.md)（`dlclose` 语义）、[E1940](E1940.md)（OHOS/musl 平台原语差异）
- 本条目由 lttng-ust 2.12.10 的 test_package 加载失败触发
