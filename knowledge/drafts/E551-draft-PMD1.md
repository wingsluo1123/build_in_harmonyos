# E551 — x86 I/O 端口访问驱动在 aarch64 上无法编译

## 错误特征

```
mactel/nv8600mgt_backlight.c:66:3: error: call to undeclared function 'outb'; ISO C99 and later do not support implicit function declarations
mactel/nv8600mgt_backlight.c:69:11: error: call to undeclared function 'inb'
mactel/nv8600mgt_backlight.c:207:8: error: call to undeclared function 'iopl'
```

## 触发条件

- 构建系统: 任意
- 阶段: compilation
- 代码: 直接读写 I/O 端口（`outb`/`inb`/`outw`/`iotl`/`iopl`/`ioperm`）的低级驱动

## 根因分析

这些原语来自 x86 平台。aarch64 的 OHOS sysroot **有** `<sys/io.h>`，
但它是**空文件**——既没有函数声明，也没有对应指令（x86 的 `in`/`out`
指令在 aarch64 指令集里根本不存在）。因此 `#include <sys/io.h>` 会成功，
但编译随即报 "call to undeclared function 'outb'"。

典型场景：x86 笔记本的固件背光/风扇/EC 驱动（通过 SMI 走 I/O 端口）。

## 解决方案

### 推荐方案

用**架构能力**宏（而非 `__OHOS__`）加守卫，让非 x86 平台把端口调用编译掉，
并使驱动的 `probe()` 如实上报"硬件不支持"：

```c
#if !defined(__i386__) && !defined(__x86_64__)
# define XXX_NO_PORT_IO 1
#endif

int xxx_probe(void)
{
#ifdef XXX_NO_PORT_IO
  logmsg(LOG_ERR, "xxx requires x86 I/O port access, unavailable on this architecture");
  return -1;
#else
  /* 原有探测逻辑 */
#endif
}
```

守卫分支必须含**实质逻辑**（返回 -1 + 日志），不能是 `return 0;` 的空壳 stub
（R40 禁止空壳）。用架构宏而非 `__OHOS__` 的理由：判断依据是架构能力，
与操作系统无关，架构宏能在任意非 x86 平台上正确表达。

### 备选方案

从构建中剔除该驱动源文件；但必须同步在**调用点**加守卫，否则链接报未定义符号。

### 禁止做法

- ❌ `probe()` 直接 `return 0;` 假装成功——上层会以为硬件可用，运行期得到无意义数据（空壳 stub）。
- ❌ 用内联汇编手写 `outb`——aarch64 无法编码 x86 I/O 指令，编译期即失败。

## 验证

```bash
cat <sysroot>/usr/include/sys/io.h        # 确认为空
readelf -h <built-binary> | grep Machine  # AArch64
strings <built-binary> | grep "requires x86 I/O port access"   # 守卫已编入产物
```

## 关联条目

- 相关: E550（同属平台能力误判）
