# 能力宏同时罩住「类型」与「函数实现」→ 已发布 DSO 带悬空符号 → 可执行文件消费者链接必炸

- **Status**: DRAFT
- **出处**: pacredir 0.7.10 适配 HarmonyOS PC（本 PR，消费者侧）
- **缺陷源**: 已发布的 `systemd/261` 与 `systemd/261.1`（`libsystemd.so.0.44.0` 带 `U mallinfo2`）
- **严重度**: 3（blocking：链接直接失败，且失败方是完全无辜的下游）
- **阶段**: linking（`conan create` 的 G2 门禁）

## 相关既有条目（撞车判定）

写本条前实测查重：`mallinfo` 在 `knowledge/graph/index.tsv`（768 条）、`knowledge/doc/`、
`knowledge/drafts/`（5440 文件）里 **0 命中**；`allow-shlib` / `shlib-undefined` 在
index.tsv 里 0 命中，doc/ 里仅 E531 顺带提到过这个词。

另外用仓内工具做了机器相似度复核（`ohc-run.py draft-review <本草稿> --top 4`）：
质量预检 signature/root_cause/rec 三项全绿；最近邻是 **E213（score 0.43，
sig 0.67）**，其次 E485（0.23）、**E229（0.22）**、E093（0.19），工具给出
`review-similar → E213` 的灰区建议。sig 分量高主要来自 `undefined reference`
这个在库内极高频的短语，不是机制重合；下面把工具点到的 E213/E229 一并列入
逐条对比（连同手工查重的 E245/E531/E320/E302/E085）：

| 条目 | 它覆盖什么 | 本条增量 |
|---|---|---|
| **E213**（OHOS musl 无 `l64a()`，工具判为最近邻 score 0.43） | **本包源码直接调用** `l64a()`，musl 不提供该函数 → `undefined reference to 'l64a'`；修复是 `implement-locally`（本包内自实现） | 报错文本相近（都含 undefined reference），机制完全不同：E213 的未定义符号由**本包目标文件**引用、平台**真的没有**该函数、修复在**本包源码**里；本条的符号由**依赖 DSO** 引用、平台**其实有**（libc.a 里是 `T`）、修复在**消费者链接行**，在本包源码里加实现反而有害（forbid_2） |
| **E229**（libc 兼容 fallback 存在但测试目标没链上） | 上游把 fallback 实现编进主库并设为 hidden，独立测试可执行文件只链公共测试对象 → 链接器找不到符号；修复是 `link-exact-fallback-object`（精确链接那个 fallback 对象） | 主题最近（都是「libc 兼容 fallback 对消费者不可见」），但可见性的**成因**相反：E229 的 fallback **编出来了**、只是被 hidden/没进链接行，精确链上即可；本条的 fallback **根本没被编译**（被能力宏整块跳过），产物里不存在任何可链对象，只能在依赖包侧改宏作用域，或在消费者侧放行链接期检查 |
| **E245**（OHOS libc 未导出 `vhangup`） | **本包源码直接调用**了平台缺失的函数；三层诊断（无声明 / libc.so 无符号 / 内核 syscall 存在），修复是在**本包源码**里加 `syscall(SYS_vhangup)` shim | 三处不同：① 悬空符号来自**已发布的依赖 DSO**，消费者不能改它；② E245 认定「libc 完全没有这个符号」，本条实测 **libc.a 里有 `T mallinfo2`**，缺的只是链接桩 libc.so 的 `.dynsym` 条目——结论正好相反（设备能解析，构建期视图不全）；③ 修复位点在**链接行**，不在任何源码里 |
| **E531**（musl 缺 glibc 风格 `qsort_r`） | 本包源码调用 GNU 签名 `qsort_r`，musl 只有 BSD 签名 → `--no-allow-shlib-undefined` 报错；修复是源码内 `#ifndef __GLIBC__` shim | 本条同样以 `--no-allow-shlib-undefined` 为表现，但 E531 的未定义符号是**本包目标文件**引用的，本条是**依赖 DSO** 引用的；前者加源码 shim 是对的，后者加源码 shim 有害（见 forbid_2：会被反向绑定顶掉 libc 真实现） |
| **E320**（`fmemopen`：符号存在但语义不可用） | `AC_CHECK_FUNCS` 只做链接级检测 → 误置 `HAVE_FMEMOPEN=1` → 走坏路径 | 同属「能力探测的证据层级不够」家族，但方向相反：E320 是**证据太弱导致误判为有**（假阳性），本条是**证据层级错配导致把兜底实现关掉**（类型层证据被拿去支持符号层结论）；且 E320 的探测在**本包 configure 期**，本条的注入在**依赖包配方**里，受害者是第三方 |
| **E302**（`open_memstream` 空捕获输出） | 符号级探测放行了一条契约已破的能力，建议行为级探测或证据绑定的关闭 | 同一原则（探测要验到可观测契约层）。本条把它推到符号层：`grep` 头文件只能证明**类型**存在，证明不了**符号**被导出，必须 `nm` |
| **E085**（musl 缺 `pthread_cancel` 族） | 本包源码调用平台未实现的 POSIX 线程取消 API → 未定义符号；修复是 no-op stub + `system_libs` | 同为「musl 能力缺口 → 未定义符号」，但 E085 的缺口是平台**真的没有**、stub 是合理降级；本条平台**其实有**（libc.a 为证），缺口纯在链接桩的符号表，因此正确处置是放行链接期检查而不是伪造实现 |

结论：无既有条目覆盖「依赖 DSO 的悬空符号 + 能力宏作用域跨类型与函数 + 链接桩
`.dynsym` 是 `.a` 的真子集 + 共享库/可执行文件的 lld 检查不对称」这一组合，
可独立申报。上述 7 条（E085、E213、E229、E245、E302、E320、E531）已填入
`.kv` 的 `similar_to`。是否纳入正式库由主编人工审核决定；本 PR 不做 promote。

## Scope（何时用本条）

### 作为消费者（本 PR 的处境）

链接**可执行文件**时报：

```text
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: <symbol>
>>> referenced by <某个 conan 依赖包>/lib/lib<dep>.so
```

三个特征一起出现即命中本条：

1. 报错里 `referenced by` 指向的是**依赖包的 .so**，不是你自己的 .o；
2. 你自己的源码从未调用过 `<symbol>`；
3. 把同一份依赖链成**共享库**时不报错（见下面的不对称实测）。

### 作为依赖包维护者（缺陷源）

配方里存在 `-DHAVE_<X>=1` 这类**能力宏注入**，而对应补丁用 `#ifndef HAVE_<X>`
守卫的块里**同时**含有类型定义和函数定义/声明。预扫描规则见 `.kv` 的 `prescan_pattern`。

## Symptom（真实日志与实测证据）

### 1. 消费者的链接失败

```console
$ clang ... pacredir.c ... -lsystemd ... -o pacredir
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: mallinfo2
>>> referenced by /Users/<user>/.conan2/p/syste851b5d32e819a/p/lib/libsystemd.so
clang: error: linker command failed with exit code 1 (use -v to see invocation)
```

### 2. 悬空符号确实在已发布的 DSO 上

```console
$ llvm-nm -D -u <pkg>/lib/libsystemd.so.0.44.0 | grep -w mallinfo2
                 U mallinfo2
$ llvm-nm -D -u <pkg>/lib/libsystemd.so.0.44.0 | wc -l
     320
$ llvm-readelf -d <pkg>/lib/libsystemd.so.0.44.0 | grep -E 'NEEDED|FLAGS'
  (NEEDED)    Shared library: [libc.so]
  (SONAME)    Library soname: [libsystemd.so.0]
  (FLAGS)     BIND_NOW
  (FLAGS_1)   NOW NODELETE
```

`DT_NEEDED` 只有 `libc.so`，所以 lld 只会去 `libc.so` 里找 `mallinfo2`。

### 3. 类型层与符号层的结论**相反**（本条的核心判据）

```console
$ grep -n 'struct mallinfo2' $SYSROOT/usr/include/malloc.h
51:struct mallinfo2 {
$ grep -nE 'mallinfo2 *\(' $SYSROOT/usr/include/malloc.h
（无命中 —— 头里没有函数声明）

$ llvm-nm -D --defined-only $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep -w mallinfo2
（无命中）
$ llvm-nm    --defined-only $SYSROOT/usr/lib/aarch64-linux-ohos/libc.a  | grep -w mallinfo2
0000000000000000 T mallinfo2          ← 真实实现存在
0000000000000000 T mallinfo            ← v1 也一样
```

即：**头里有 struct、`.a` 里有函数、`.so` 的 `.dynsym` 里没有**。

### 4. SDK 的 libc.so 是链接桩，不是完整实现

```console
$ ls -l $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so $SYSROOT/usr/lib/aarch64-linux-ohos/libc.a
-rwxr-xr-x  1 ... staff     71128 ... libc.so
-rw-r--r--  1 ... staff  10965028 ... libc.a
$ llvm-readelf -S $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep -E '\.text|\.dynsym'
  [ 3] .dynsym    DYNSYM    ... Size 009558 ...      ← 1589 个符号条目
  [13] .text     PROGBITS   ... Size 000150 ...      ← 336 字节，装不下任何实现
```

`.text` 只有 336 字节 ⇒ 这个 `.so` 只提供符号表供链接期解析，而它的符号表是
`libc.a` 的**真子集**：收了 `malloc` / `free` / `malloc_usable_size` / `mallopt`，
漏了 `mallinfo` / `mallinfo2` 家族。

### 5. 「共享库过、可执行文件炸」的不对称（最小复现）

同一份 `libsystemd.so`，两条命令：

```console
$ printf '#include <systemd/sd-bus.h>\nint f(void){sd_bus*b=0;return sd_bus_open_system(&b);}\n' > u.c
$ printf '#include <systemd/sd-bus.h>\nint main(void){sd_bus*b=0;return sd_bus_open_system(&b)<0;}\n' > m.c

$ clang -shared -fPIC -I<pkg>/include u.c -L<pkg>/lib -lsystemd -o libu.so ; echo "shared_rc=$?"
shared_rc=0                                    ← 链成共享库：一声不响地过

$ clang -I<pkg>/include m.c -L<pkg>/lib -lsystemd -o m ; echo "exe_rc=$?"
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: mallinfo2
>>> referenced by <pkg>/lib/libsystemd.so
exe_rc=1                                       ← 链成可执行文件：硬失败

$ clang -I<pkg>/include m.c -L<pkg>/lib -lsystemd -Wl,--allow-shlib-undefined -o m ; echo "rc=$?"
rc=0                                           ← 加上开关即通过
```

原因是 lld 的 `--no-allow-shlib-undefined` 只对**可执行文件**输出默认生效，
共享库输出默认放行。

**这条不对称正是缺陷能发布出来的通道**：`systemd/261.x` 的配方只
`ninja libsystemd.so.0.44.0`、只打包这个 DSO；它的 `test_package` 里那个
「编译并运行真实消费者」的用例被 `can_run(self)` 挡在交叉编译之外
（本地 profile 显式设 `tools.build.cross_building:can_run=False`）。
于是从构建到发布，**没有任何一环把 libsystemd 链进过可执行文件**。

## Root Cause

三层叠加，缺一层都不会暴露：

### ① 一个能力宏，守卫了两类语义完全不同的实体

`archives/s/systemd/261.1/patches/0005-musl-mallinfo2-guard.patch`：

```diff
--- a/src/include/musl/malloc.h
+++ b/src/include/musl/malloc.h
@@ -6,6 +6,10 @@
 #include <errno.h>
 #include <stdio.h>

+#ifndef HAVE_MALLINFO2
 struct mallinfo2 {
         size_t arena;
         ...
@@ -23,6 +27,7 @@
         return (struct mallinfo2) {};
 }

+#endif /* !HAVE_MALLINFO2 */
 static inline int malloc_info(int options, FILE *stream) {
```

`#endif` 落在 inline 函数的右花括号**之后**，所以这一个 `#ifndef` 同时罩住了：

- `struct mallinfo2 { ... }` —— **类型**，只需要头里有声明就够用；
- `static inline struct mallinfo2 mallinfo2(void) { return (struct mallinfo2){}; }`
  —— **函数实现**，需要平台真的导出该符号才能省掉。

两者的成立条件不同，却被同一个开关一起打开或一起关掉。

### ② 注入依据只到类型层

`archives/s/systemd/261.1/conanfile.py`（261 同款）：

```python
# OHOS 定制 musl 的 sysroot malloc.h 已自带 mallinfo2（0005 补丁用
# `#ifndef HAVE_MALLINFO2` 能力探测宏，R8 合规不含平台宏）——这里注入
# -DHAVE_MALLINFO2=1 让 OHOS 下跳过 systemd 的 mallinfo2 定义，
# 避免 redefinition；标准 musl/glibc 下不注入则补上。
if self.settings.os == "OHOS":
    tc.c_args.append("-DHAVE_MALLINFO2=1")
```

注释里的依据是「malloc.h 已自带 mallinfo2」——但实测那个头**只自带 struct**
（`grep -nE 'mallinfo2 *\(' malloc.h` 无命中）。避免 `redefinition` 这个目的对
struct 是成立的，对函数不成立：跳过之后**没人再提供 `mallinfo2()`**，
而 libsystemd 的其它目标文件仍然引用它 ⇒ `U mallinfo2` 进了发布产物。

### ③ 链接桩的 `.dynsym` 不完整，把问题从运行期提前到了链接期

设备上的真实 libc（与 `libc.a` 同源）是有 `mallinfo2` 的，所以这在**运行期根本
不是问题**。问题在于交叉编译时 lld 只看 sysroot 的 `libc.so`，而那是个 `.text`
仅 336 字节的链接桩，`.dynsym` 是 `.a` 的真子集，恰好漏了 `mallinfo`/`mallinfo2`
家族。于是「构建期视图」比「运行期事实」更窄，lld 据以更窄的视图判了死刑。

## Workaround / 修复

### 消费者侧（本 PR 采用）

在链接可执行文件的命令上加范围最小的那个开关：

```text
-Wl,--allow-shlib-undefined
```

**放行范围**：只放行**共享库自身**的未定义符号。本包目标文件的未定义符号仍照常
报错——所以它不会掩盖 pacredir 自己的缺符号问题（对照 forbid_1：
`--unresolved-symbols=ignore-all` 才会把两者一起放过）。

**安全性论证**（三条，缺一就不要用这个开关）：

1. 该符号在设备真实 libc 里存在 —— `libc.a` 里是 `T mallinfo2`，与 `libc.so` 桩同源构建；
2. 依赖 DSO 的 `DT_NEEDED` 已含 `libc.so`，运行期由加载器正常解析；
3. 失败只发生在**链接期视图**（桩的 `.dynsym` 不全），不是运行期缺失。

pacredir 配方里的落点（上游 Makefile 预留的 `CFLAGS_EXTRA` 注入点）：

```python
script = (
    'set -e; '
    'EXTRA="$CPPFLAGS $CFLAGS -Wl,--as-needed $LDFLAGS $LIBS '
    '-Wl,--exclude-libs,ALL -Wl,--allow-shlib-undefined"; '
    ...
)
```

其它构建系统的等价落点：

| 构建系统 | 落点 |
|---|---|
| CMake（Conan） | `tc.extra_exelinkflags = ["-Wl,--allow-shlib-undefined"]` |
| Autotools | `LDFLAGS="$LDFLAGS -Wl,--allow-shlib-undefined"` |
| Meson | `c_link_args` / `link_args` 追加同一项 |
| 裸 Makefile | 上游预留的 extra-flags 变量，或直接给 `LDFLAGS` 追加 |

按 P006 记为技术债务：配方注释、`notes.md`、PR 补充说明三处都要写清「为什么需要、
放行范围有多大、什么条件下应移除」。**移除条件**：`systemd` 修好能力宏作用域并发布
新版本后，用 `llvm-nm -D -u <新版 libsystemd.so> | grep -w mallinfo2` 复核为空即可移除。

### 依赖包侧（根治，需另开 PR）

把一个宏拆成两个，各自按自己那层的证据注入：

```c
/* 类型层：sysroot 头里有 struct 就该跳过，避免 redefinition */
#ifndef HAVE_STRUCT_MALLINFO2
struct mallinfo2 { ... };
#endif

/* 符号层：只有 libc.so 真导出了 mallinfo2 才能跳过兜底实现 */
#ifndef HAVE_MALLINFO2
static inline struct mallinfo2 mallinfo2(void) { return (struct mallinfo2){}; }
#endif
```

配方侧的注入依据也要跟着分层：

```python
# 类型层证据（grep 头文件即可）
#   grep -q 'struct mallinfo2' $SYSROOT/usr/include/malloc.h
# 符号层证据（必须 nm，grep 头文件证明不了）
#   llvm-nm -D --defined-only $SYSROOT/usr/lib/*/libc.so | grep -qw mallinfo2
```

代价与边界：这是**别人归档目录**里的改动，本仓铁律禁止夹带在单库 PR 里，必须给
`systemd` 开新版本（R37：`261.2`）走完整发布流程，且它改的是 DSO 自身，需要重新
发布二进制。所以对当前消费者不是即时路径，应作为 Issue 提给维护者。

## Prevention

1. **能力宏的注入证据必须与被守卫物的层级一致**：守卫**类型** → `grep` 头文件足够；
   守卫**函数实现** → 必须 `nm -D --defined-only` 查符号，或做链接级/行为级探测
   （E302、E320 的同一原则）。
2. **一个宏不要跨类型与函数**。补丁里如果一个 `#ifndef` 块同时含 `struct`/`typedef`
   和函数定义，拆成两个宏。预扫描可按 `.kv` 的 `prescan_pattern`
   （`-DHAVE_[A-Z0-9_]+=1`）配合补丁内容审查。
3. **发布 DSO 前查一次自己的悬空符号**：`llvm-nm -D -u lib<dep>.so` 的输出应当能被
   `DT_NEEDED` 链完整解析。这一步成本几秒，能避免把缺陷带进制品仓。
4. **`test_package` 的消费者用例要覆盖「链成可执行文件」**：只链共享库永远暴露不了
   这一类问题（见 Symptom §5 的不对称实测）。`can_run()` 为假时至少应保留一次
   **不运行、只链接**的可执行文件链接检查——链接期检查不需要目标平台。
5. **交叉工具链的 sysroot `libc.so` 可能是链接桩**，其 `.dynsym` 未必覆盖 `libc.a`
   的全部符号。判桩的快捷办法：`llvm-readelf -S libc.so | grep '\.text'` 看 Size
   是否小到不可能装下实现。

## References

- lld 文档：`--allow-shlib-undefined` / `--no-allow-shlib-undefined`（后者是可执行文件输出的默认值）
- 本 PR：`archives/p/pacredir/0.7.10/conanfile.py`（模块 docstring「依赖图处置 5」与
  `build()` 的 `EXTRA`）、`archives/p/pacredir/0.7.10/notes.md`（问题 #8）
- 缺陷源：`archives/s/systemd/261.1/conanfile.py`（`-DHAVE_MALLINFO2=1` 注入）、
  `archives/s/systemd/261.1/patches/0005-musl-mallinfo2-guard.patch`（`#endif` 位置）、
  `archives/s/systemd/261.1/test_package/conanfile.py`（`can_run()` 守卫下的消费者用例）
- 相关条目：E085、E245、E302、E320、E531
- 相关原则：P006（CFLAGS/链接 hack 必须记为技术债务）、P012（静态库优先）、
  P013（平台限制必须降级而非绕过）
