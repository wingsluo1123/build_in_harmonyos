# DRAFT-pnmixer-0.7.2-ohos-libm-missing-gnu-math-exp10: OHOS 的 `<math.h>`/共享 libm 都不提供 GNU 扩展 `exp10()`，旧 C 代码链接期 `undefined symbol: exp10`

- **来源**：pnmixer 0.7.2 适配（2026-10-18）
- **领域**：libc 差异（glibc → musl/OHOS）× 数学库符号可见性 × 链接期失败
- **触发工具**：clang 15 / ld.lld（conan create 链接阶段）
- **邻近但不同**：E419（plain char signedness，同属 aarch64/musl 语义差异，机制不同）；E660（OHOS `libintl.h` 空壳 + gettext 制品，同属"头在实现不在"家族，但本条是**连声明都没有**、实现只在静态 `libc.a` 里）

## 现象

`conan create` 编译全部通过，**链接**时报：

```
ld.lld: error: undefined symbol: exp10
>>> referenced by alsa.c
>>>               CMakeFiles/pnmixer.dir/alsa.c.obj:(alsa_card_get_volume)
>>>               CMakeFiles/pnmixer.dir/alsa.c.obj:(alsa_card_set_volume)
clang-15: error: linker command failed with exit code 1
```

Linux 开发机（glibc）上同一份源码编译链接全绿 —— 典型的「本地绿、目标红」。

## 根因（两处同时不满足，实测）

`exp10()` 是 glibc 的 GNU 扩展，不是 C 标准函数。OHOS/musl 这一侧：

| 检查 | 命令 | 实测读数 |
|---|---|---|
| `<math.h>` 是否声明 `exp10` | `grep -n exp10 $SYSROOT/usr/include/math.h` | **0 命中**（因此写 `#define _GNU_SOURCE` 也没用，clang 只给隐式声明警告） |
| 共享 libm 是否导出 | `llvm-nm -D --defined-only libm.so \| grep -c ' exp10$'` | **0** |
| 静态 libc.a 是否有该成员 | `llvm-nm --defined-only libc.a \| grep -c ' T exp10$'` | **1** |

即：符号"存在但不可动态取用"——只在静态归档里，所以问题只在**链接期**暴露，
编译期没有任何错误提示。

pnmixer 的用法（upstream `src/alsa.c`，ALSA dB 增益→线性幅度换算）：

```c
normalized = exp10((value - max) / 6000.0);
if (min != SND_CTL_TLV_DB_GAIN_MUTE) {
        min_norm = exp10((min - max) / 6000.0);
        normalized = (normalized - min_norm) / (1 - min_norm);
}
```

## 解法（数学等价、必然可用、无平台宏）

在调用点之前给一个受保护的宏回退：

```c
#define _GNU_SOURCE /* exp10() */
#include <math.h>

/* exp10() is a GNU/libc extension.  On this platform <math.h> does not
 * declare it and the shared libm does not export it (only a static libc.a
 * member exists), so the calls below fail to link with "undefined symbol:
 * exp10".  pow(10, x) is the same value and always available; no code takes
 * the address of exp10, so the macro is a safe drop-in. */
#ifndef exp10
#define exp10(x) pow(10.0, (x))
#endif
```

四条要点：

1. `#ifndef exp10` 守卫：在不缺该函数的 libc 上不覆盖既有定义；
2. 只在**不取 `exp10` 地址**的代码里可用（`&exp10`、函数指针赋值会因宏编译失败
   —— 先 `grep -n exp10 src/*.c` 确认用法）；
3. **不引入 `__OHOS__` 等平台宏**（R8/PF5 合规），回退在所有 POSIX 平台语义相同；
4. 别顺手把 `pow` 换成 `expl`/`powl` 之类 —— 那是另一族 libc 差异点。

## 判据（很便宜，不用猜）

链接期报 `undefined symbol: <数学函数名>` ⇒ 先 `grep <函数名> $SYSROOT/usr/include/math.h`：
grep 不到就是本条家族（GNU 扩展缺失），直接上等价回退，不要往「依赖没链接」方向排查。

## 证据

- `archives/p/pnmixer/0.7.2/patches/0001-src-alsa.c.patch`（+10 行）
- `archives/p/pnmixer/0.7.2/notes.md` 问题表 #8（含 `llvm-nm` 实测读数）
- 修复后：`conan-verify` G2 PASS，消费者测试 24/24 通过
