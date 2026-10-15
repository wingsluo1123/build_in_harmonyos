# E-DRAFT: OHOS musl 硬编码 32-bit wchar_t 撞上 clang -fshort-wchar 的 16-bit 定义

- **触发实例**：u-boot 2026.07 适配（2026-09-29，任务 11418，分支 feat/uboot-2026.07，
  patch 0008-sandbox-syshdrs-wchar-musl.patch）
- **错误签名**：
  `typedef redefinition with different types ('unsigned int' vs 'unsigned short')`
  → 错误链 `arch/sandbox/cpu/initjmp.c:24` → sysroot `stdlib.h:19` →
  `bits/alltypes.h:15`，对端为 clang 资源目录 `stddef.h:74`
- **类别**：musl-clang-incompat
- **严重度**：2（混合头 TU 确定性编译失败，修复模式固定且上游有先例）

## 症状

```text
In file included from arch/sandbox/cpu/initjmp.c:24:
In file included from /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/stdlib.h:19:
/data/service/hnp/.../sysroot/usr/include/aarch64-linux-ohos/bits/alltypes.h:15:16:
error: typedef redefinition with different types ('unsigned int' vs 'unsigned short')
   15 | typedef unsigned wchar_t;
      |                ^
.../lib/clang/15.0.4/include/stddef.h:74:28: note: previous definition is here
   74 | typedef __WCHAR_TYPE__ wchar_t;
```

## 根因

两份互不知情的 `wchar_t` 定义在同一个 TU 里碰头：

| 定义方 | 内容 | 守卫宏 |
|---|---|---|
| musl `<bits/alltypes.h>` | `typedef unsigned wchar_t;`（aarch64 上 32-bit，**硬编码**，无编译器内省） | `__NEED_wchar_t` / `__DEFINED_wchar_t` |
| clang 资源目录 `<stddef.h>` | `typedef __WCHAR_TYPE__ wchar_t;`（-fshort-wchar 下 `__WCHAR_TYPE__` = `unsigned short`，16-bit） | `__need_wchar_t` / `_WCHAR_T` |

两份守卫宏互不相识 → 两个 typedef 都生效 → 重定义冲突。**glibc 从不触发**：
它的 wchar_t 由 `__WCHAR_TYPE__` 派生（无硬编码），所以上游 Linux CI 对这个坑完全无感。

u-boot 2026.07 是教科书级实例：

1. 顶层 `Makefile:546` 无条件给 KBUILD_CFLAGS 加 `-fshort-wchar`（u-boot 自用
   宽字符串的刻意设计，固件侧 ABI 依赖它）；
2. `arch/sandbox/cpu/Makefile:17` 的 `CFLAGS_USE_SYSHDRS := eth-raw-os.o
   initjmp.o os.o sdl.o` 机制给这四个宿主风格文件生成专用规则：**去掉
   -nostdinc、把 -I 转 -idirafter**（libc 头优先于 u-boot 自带头），**但保留
   -fshort-wchar**；
3. `initjmp.c` 是裸宿主文件（pthread/stdio/stdlib/setjmp/signal），`<stdlib.h>`
   直落 musl sysroot → alltypes.h 与资源目录 stddef.h 在一个 TU 内同台 → 炸。

**上游早就知道这个坑**——同一文件里 sdl.o 的覆盖注释明言
"sdl.c also needs -fshort-wchar removed (musl)"：

```make
cmd_cc_sdl.o = $(CC) $(filter-out -nostdinc -fshort-wchar, \
	$(patsubst -I%,-idirafter%,$(c_flags))) -fno-lto -c -o $@ $<
```

但只覆盖了 sdl.o，其余三个文件（initjmp.o/os.o/eth-raw-os.o）仍用生成规则。

## 最小修复（旗标级，沿上游先例）

在 `arch/sandbox/cpu/Makefile` 的 sdl.o 覆盖之后，把同一 filter-out 扩展到
其余三个文件：

```make
$(foreach f,initjmp.o os.o eth-raw-os.o, \
	$(eval cmd_cc_$(f) = $(CC) $(filter-out -nostdinc -fshort-wchar, \
		$(patsubst -I%,-idirafter%,$(c_flags))) -c -o $$@ $$<))
```

四个文件零宽字符 API 使用（全目录 grep 实证），去掉旗标后 wchar_t 交由 C 库
定义、无任何 ABI 影响；glibc 平台行为不变（该旗标去掉的 16-bit typedef 在
glibc 里本来就不存在）。

## 为什么垫片方案是死路（真机实证否决）

曾试在 include/ 放自定义 `stddef.h` 垫片压住冲突——两套旗标下都不可达：

- 普通目标 TU 旗标：`-nostdinc -isystem <资源目录> -Iinclude`——**资源目录排在
  include/ 之前**，`<stddef.h>` 永远先命中编译器自带头，垫片根本轮不到；
- syshdrs 四文件的 -idirafter 更是把 include/ 排在 sysroot **之后**。

`-D` 覆盖编译器保留宏（`__WCHAR_TYPE__` 等）随编译器版本漂移、且可能静默改掉
无关 TU 的宽字符布局——比原报错更糟。旗标级修复是唯一可靠解。

已验证：patch 0008 后 u-boot 2026.07 在 OHOS aarch64 真机 `conan create`
干净构建（initjmp.o → os.o 全部编译通过，见 notes.md 决策表 12 行）。

## 禁忌

- 禁止 shim 头垫片（两套旗标下均不可达，已验证）；
- 禁止 `-D__WCHAR_TYPE__`/`_WCHAR_T` 等宏覆盖（对抗工具链、跨版本脆弱）；
- 禁止全局删 `-fshort-wchar`（动固件侧宽字符 ABI，仅在万不得已时按目录回加）。

## 适用范围与查重

- **适用**：所有「TU 同时吃系统头 + -fshort-wchar」的混合头编译——内核/沙箱/
  固件项目的宿主侧构建打开 sysroot 时都可能命中（u-boot sandbox、类 Kbuild
  syshdrs 机制的项目）。
- **查重**：grep 现有 drafts，`-fshort-wchar`/`alltypes.h` 无同机制条目；
  E 系列 musl 条目多为「函数纯缺失」（如 E093 getpass）或「空壳头探测误判」
  （如 13410 libintl），本条是「硬编码 typedef 与编译器派生 typedef 的守卫互不
  相识」类型冲突，修复对象是编译旗标而非守卫逻辑。draft-review 相似度预期
  0.30 以下，建议 create。
