# fbset

`fbset` 用于**查询与调整 Linux 帧缓冲（frame buffer）设备的显示模式**：通过 FB ioctl 族
（`FBIOGET_VSCREENINFO` / `FBIOPUT_VSCREENINFO` / `FBIOGET_FSCREENINFO` …）读出或设置分辨率、
色深、时序（pixclock/边距/同步长度）与屏幕标志，也可从模式数据库（`fb.modes`）按名字套用显示模式。

- 上游：Geert Uytterhoeven（linux-fbdev 项目），最新版本 **fbset-2.1.tar.gz（1999/06/23）**
- 上游页面：`http://g33rt.be/migrated/Linux/fbdev/`（作者迁移后的现站；Debian 2.1-35 的 `Homepage`
  与 `debian/watch` 均指向该址）
- 许可证：GPL-2.0-only
- 构建系统：裸 Makefile（无 configure、无 check/test 目标、`make install` 写绝对路径并 `mknod /dev/fb*`）
- 类型：命令行工具（产物 `bin/fbset`，无库、无头文件）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.1 | built | 首次适配 HarmonyOS PC (aarch64) |

## 适配要点

1. **无编译墙**：`fb.h` 随源码内置，不需要内核头文件；唯一阻塞是 `fbset.h` 把
   `#include <asm/types.h>` 放在 `#ifdef __GLIBC__` 里（musl/OHOS 不定义 `__GLIBC__` ⇒ `__u32` 未定义），
   补丁 0001 改为无条件包含（与 Yocto meta-oe 同名补丁同一结论）。
2. **工具链**：上游 Makefile 写死 `CC = gcc -Wall -O2 -I.`，本平台只有 clang ⇒ 配方按 R33 从 Conan conf
   取编译器并在命令行覆盖 `CC/CFLAGS/LDFLAGS`；`modes.l`/`modes.y` 未预生成 ⇒ `tool_requires`
   `flex/2.6.4` + `bison/3.8.2`。
3. **安装**：不使用上游 `make install`（写 `/sbin`、`/usr/man` 并 `mknod /dev/fb0..fb7`），
   由 `package()` 手工安装 `bin/fbset` 与模式库 `share/fbset/fb.modes.*`，并按 OHOS 要求自签 ELF。
4. **运行期能力**：OHOS PC 上不存在可访问的帧缓冲设备，`fbset -s` 得到
   `open /dev/fb0: No such file or directory`（对非帧缓冲字符设备则为 `ioctl FBIOGET_VSCREENINFO: ...`）；
   属**运行期墙**，可披露，不影响工具自身的编译、安装与消费者验证。
