# pommed 1.39-dfsg 适配笔记

## 编译环境
- 构建系统: makefile（上游递归 Makefile）
- 编译日期: 2026-10-16
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，musl）
- 状态: published

## 编译步骤

上游没有 configure，直接进 `pommed/` 子目录构建：

```bash
PKG_CONFIG_PATH=<conan generators> \
make -j1 -C pommed \
  CC=clang \
  CPPFLAGS="-fcommon" LDFLAGS="-lc++" \
  INOTIFY_CFLAGS= TIMERFD_CFLAGS=
```

`generate()` 生成 pkg-config 描述文件并补齐 `dbus-1.pc` / `libpci.pc`
别名；`package()` 手工安装 bin/、share/pommed（蜂鸣采样 + 示例配置）、
man 手册与 COPYING（上游无 install 目标）。

### 为什么只构建 pommed 本体

tarball 顶层 Makefile 的 `all:` 目标是 `pommed gpomme wmpomme`：

- `gpomme` 需要 GTK+ 2.0、dbus-glib、gettext(msgfmt)
- `wmpomme` 需要 X11 / Xpm / Xext

这两者都是 GUI 客户端，且 Debian 源码包本身就把它们拆成
`gpomme` / `wmpomme` 独立二进制包（本仓库的适配对象是 `pommed`）。
x86 时代（2011 年）的 GTK2 + X11 OSD 客户端在 HarmonyOS PC 上
既无对应运行时也不属于本次适配目标，故本配方只构建 `pommed`
守护进程本体。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `unknown type name 'pthread_mutex_t'`（beep.h） | musl libc 不传递包含 pthread 类型 | 补丁 0001：beep.h 加 `#include <pthread.h>` |
| 2 | `use of undeclared identifier 'PATH_MAX'`（mactel/ambient.c） | musl libc 不传递包含 limits.h | 补丁 0002：ambient.c 加 `#include <limits.h>` |
| 3 | aarch64 上 `#error "inotify not supported on this architecture!"` / `#error Unsupported architecture` | Makefile 用 `test -e /usr/include/sys/{inotify,timerfd}.h` 探测**构建机**头文件；OHOS sysroot 里有这两个头文件，但 `/usr/include` 下没有，被误判缺失 → 回退到只支持 x86/ppc 的 syscall 编号 shim | 命令行覆盖 `INOTIFY_CFLAGS=` `TIMERFD_CFLAGS=`（命令行变量优先级高于 Makefile 赋值），强制使用 sysroot 真实头文件，无需改 Makefile |
| 4 | `binary operator '>>' ... <sys/io.h>` 缺失 / `outb`/`inb`/`iopl` 未声明 | mactel/nv8600mgt_backlight.c 走 x86 I/O 端口；aarch64 的 `<sys/io.h>` 存在但为空 | 补丁 0003：加架构守卫，非 x86 时 `probe()` 记日志并返回 -1（如实上报不支持，非空壳 stub） |
| 5 | `ld.lld: error: duplicate symbol: lcd_bck_info` | 2011 年 C 依赖 GCC<10 的暂定定义（`lcd_bck_info` 在 3 个编译单元中都定义）；clang 默认 `-fno-common` | 通过 `CPPFLAGS="-fcommon"` 编译 |
| 6 | `undefined symbol: operator new[]`, `std::__n1::...`（来自 libaudiofile.a） | audiofile 0.3.6 含 C++ 目标文件，纯 C 链接行未带 C++ 运行时 | 通过 `LDFLAGS="-lc++"` 链接 libc++ |
| 7 | `pkg-config dbus-1` / `pkg-config libpci` 无结果 → 误走 `/usr/lib/libpci.a` + `-lz` 分支 | PkgConfigDeps 按 Conan 包名生成 `dbus.pc` / `pciutils.pc`，与上游 Makefile 查询名不一致 | `generate()` 中补建 `dbus-1.pc` → `dbus.pc`、`libpci.pc` → `pciutils.pc` 别名 |

## 源码修改

3 个补丁，全部为可移植性（`patch_type: portability`），无功能变更：

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-pommed-beep.h.patch | pommed/beep.h | 补 `#include <pthread.h>` |
| 0002-pommed-mactel-ambient.c.patch | pommed/mactel/ambient.c | 补 `#include <limits.h>`（PATH_MAX） |
| 0003-pommed-mactel-nv8600mgt_backlight.c.patch | pommed/mactel/nv8600mgt_backlight.c | x86 I/O 端口驱动加架构守卫：非 x86 时 `get()` 返回 0、`set()` 空操作、`probe()` 记日志返回 -1 |

> 关于补丁 0003 的平台宏：该补丁新增行使用 `__i386__` / `__x86_64__`
> 架构宏而非 `__OHOS__`。理由：这里的判断依据是**架构能力**（outb/inb/iopl
> 只在 x86 上可用），与操作系统无关；用架构宏才能在任意非 x86 平台上
> 如实表达"该硬件驱动不可用"，而不是给 OHOS 打一个无意义的功能洞。
> 守卫分支含有实质逻辑（`probe()` 返回 -1 并记录日志），不是空壳 stub（R40）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| dbus | 1.14.10 | D-Bus 事件广播 |
| alsa-lib | 1.2.16.1 | 蜂鸣器音频输出 |
| audiofile | 0.3.6 | WAV 采样解码 |
| libconfuse | 3.3 | 配置文件解析 |
| pciutils | 3.13.0 | 显卡（背光）PCI 识别 |

## 验证结果

`conan create`（ohos-aarch64 profile）编译 + test_package 全绿：

```
PASS: pommed is on PATH
PASS: pommed -v exit status
PASS: pommed -v version banner
PASS: pommed -v copyright line
PASS: pommed -Z exit status
PASS: pommed -Z prints usage
PASS: pommed -Z usage lists -f
PASS: pommed -Z usage lists -d
PASS: pommed -f aborts at a startup gate
PASS: pommed -f reports the failing startup gate
PASS: pommed is a native AArch64 ELF
PASS: x86-only backlight driver carries the non-x86 guard
RESULT: 12 passed, 0 failed
```

产物为原生 aarch64 ELF（`lib/ld-musl-aarch64.so.1`）：

```
$ readelf -h bin/pommed | grep Machine
  Machine:                           AArch64
$ bin/pommed -v
pommed v1.39 Apple laptops hotkeys handler
Copyright (C) 2006-2011 Julien BLACHE <jb@jblache.org>
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/pommed | 守护进程本体（原生 aarch64） |
| share/pommed/{click,goutte}.wav | 蜂鸣器采样（`BEEP_DEFAULT_FILE` 编译期指向 /usr/share/pommed/goutte.wav） |
| share/pommed/pommed.conf.{mactel,pmac} | 示例配置 |
| share/man/man1/pommed.1 | man 手册 |
| licenses/COPYING | GPL-2.0 |

## 上游测试用例

上游**没有任何测试**：递归 Makefile 只有 `all` / 逐目标规则 / `clean`，
没有 `check` / `test` 目标，tarball 里也没有任何测试程序。

因此 test_package/test.sh 覆盖的是守护进程可观察的运行时行为
（版本输出、getopt 用法诊断、非 root 权限门禁），外加两条
HarmonyOS/aarch64 专属断言（原生 AArch64 ELF、x86-only 背光驱动
的架构守卫已进入二进制）。详见 test_package/MANIFEST.yml。

## 注意事项

- pommed 是 Apple 硬件专用守护进程：非 Apple 机器上 `check_machine()`
  会输出 `Unknown non-Apple machine` 并正常退出。本次适配保证其在
  HarmonyOS PC (aarch64) 上正确构建 / 加载 / 运行，不承诺驱动 Mac 硬件。
- 运行时依赖（libexpat.so、libasound.so、libc++_shared.so）由 Conan 的
  `VirtualRunEnv`（`conanrun`）提供；包内未注入 RPATH。
---

**编译结束**: 2026-10-16 01:30
**最终状态**: published
