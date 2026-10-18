# E4301 — musl/OHOS 的 pthread 两个错位：sysroot 头缺 `pthread_cancel` 声明、`pthread_t` 是指针

## 错误特征

```
plugins/atwf83.c:162:3: warning: call to undeclared function 'pthread_cancel';
      ISO C99 and later do not support implicit function declarations
      [-Wimplicit-function-declaration]
        pthread_cancel(repeat_thread);
        ^
plugins/zotac.c:314:3: warning: call to undeclared function 'pthread_cancel'; ...
plugins/mplay.c:786:7: warning: call to undeclared function 'pthread_cancel'; ...
```

同一批线程代码里通常还有第二个错位（硬错误，不是 warning）：

```
plugins/mplay.c:200:12: error: incompatible integer to pointer conversion
      initializing 'pthread_t' (aka 'struct __pthread *') with an expression
      of type 'int' [-Wint-conversion]
        .tid                            = -1
                                          ^~
plugins/mplay.c:785:33: warning: comparison between pointer and integer
      ('pthread_t' (aka 'struct __pthread *') and 'int')
```

形态要点：`pthread_cancel` 那条**编译只有 warning、链接通过、程序运行也正常** —— 因此
容易被当成噪声忽略，直到某天开了 `-Werror` 或 `-Wl,--no-undefined` 才突然变成硬失败；
而 `pthread_t` 那条是**编译期硬错误**，会直接中断构建。

## 触发条件

- 源码直接调用 `pthread_cancel()` / `pthread_setcancelstate()` / `pthread_testcancel()`
- 用 OHOS SDK 的 sysroot 头与 stub `libc.so` 链接（设备 HNP 默认如此）

## 根因分析

OHOS SDK 的 **sysroot 面**与**运行时而**不是同一份东西：

| 面 | `pthread_cancel` |
|---|---|
| `sysroot/usr/include/pthread.h`（148 个 `pthread_*` 符号） | **没有声明** |
| `sysroot/usr/lib/aarch64-linux-ohos/libc.so`（链接期 stub） | **不导出** |
| `/system/lib64/libc.so`（设备运行时真实 libc） | **导出**（`nm -D` → `T pthread_cancel`） |

所以：

- 编译期：clang 找不到原型 ⇒ `-Wimplicit-function-declaration`（C99+ 默认 warning）；
- 链接期：共享库默认允许未定义符号 ⇒ 不报错（可执行文件带 `--no-allow-shlib-undefined`
  时才会像 `rindex` 那样变成 `undefined reference`）；
- 运行期：动态加载器从真实 libc 解析到符号 ⇒ 功能正常。

**第二个错位**：musl 的 `pthread_t` 是**指针**（`struct __pthread *`），glibc 的
`pthread_t` 是 `unsigned long`。老代码普遍把 `-1` 当"线程未创建"哨兵
（`pthread_t tid = -1;` / `if (tid != -1)`），在 musl 上就是整数↔指针转换错误。
换成 `0` 哨兵即可：glibc 下 `pthread_t` 为 0 同样不是合法线程 id，语义等价；
切忌用强制类型转换 `(pthread_t)-1` 掩盖（那会把比较也一起带错）。

**关键区分**：这不是"musl 没有这个函数"（E093 的 getpass 那种），而是"头文件/stub
缺口、符号真实存在"+"类型定义不同"。判据必须先做符号核验与类型核验，再决定是补声明、
换哨兵，还是改架构。

## 解决方案

### 推荐方案

在调用点所在源文件补一行显式原型：

```c
#include <pthread.h>
/* OHOS/musl sysroot 的 <pthread.h> 省了 pthread_cancel 原型，但运行时 libc 导出该符号 */
extern int pthread_cancel(pthread_t thread);

/* pthread_t 在 musl 上是指针：用 0 而不是 -1 作"未创建"哨兵 */
static pthread_t repeat_thread;          /* 静态存储期 ⇒ 初值即 0 */
if (repeat_thread != 0) { pthread_join(repeat_thread, NULL); repeat_thread = 0; }
```

在 glibc 下与系统头的声明逐字相同，重复声明合法；不需要平台宏、不需要桩实现、
不需要改链接参数。

### 禁止做法

- ❌ 用 `#ifdef __OHOS__` 包住（补声明对所有平台都合法，且补丁新增 `__OHOS__`
  行会撞平台宏门禁 PF5）。
- ❌ 把 `pthread_cancel(...)` 整段删成空壳，或用 `-Wl,--allow-shlib-undefined`
  掩盖 —— 会静默改变线程回收语义。

## 验证

```bash
nm -D /system/lib64/libc.so | grep pthread_cancel          # T pthread_cancel
nm -D "$SYSROOT/usr/lib/aarch64-linux-ohos/libc.so" | grep -c pthread_cancel   # 0
grep -c pthread_cancel "$SYSROOT/usr/include/pthread.h"                        # 0
```

符号核验通过后再按"仅补原型"处理；三条读数全为 0 才考虑协作式退出方案。

## 关联条目

- 相似但不同：**E093**（musl 真的没有 `getpass()`，只能自己实现或禁用功能）
  —— 本条符号存在，只是头文件没声明。
- 同族 musl 缺口：`rindex()` 在 musl 里**确实**不存在（改 `strrchr()`）。
- 误配提示：引擎对 `pthread_t` 那条会匹配到 **E420**（"legacy C 源缺 API 属主头文件"）
  与 **E093**（`getpass` 缺失），两者根因都不同——本条是类型定义差异与 sysroot 头缺口。
