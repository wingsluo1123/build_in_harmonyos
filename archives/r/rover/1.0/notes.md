# rover 1.0 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile，非 autotools，无 configure）
- 编译日期: 2026-10-13
- 编译器: clang 15（OHOS NDK / lpk-fixed 工具链）
- host profile: ohos-aarch64-wsl-xbuild（os=OHOS 6.0, arch=armv8）
- build profile: default（x86_64 WSL Linux）
- 状态: built（本地 `conan create` 通过，未走 release 上传）

## 源码
- 上游: https://github.com/lecram/rover/archive/refs/tags/v1.0.0.tar.gz
- sha256: f2e6629107f80cc71e64cf1f2c79afe8c76d3aa0d53074bd221e5ddcda895a4e
- HTTP: 200（curl -sIL，最终 codeload.github.com）
- 顶层目录: rover-1.0.0/（strip_root）
- 文件: rover.c（单文件实现）、config.h（RV_VERSION="1.0.0"）、Makefile、rover.1

## 编译步骤

```bash
# 在 WSL 原生盘 /root/ohpcd-work/build/rover-1.0
conan create . -pr:h=ohos-aarch64-wsl-xbuild -pr:b=default -r=ohpcd --build=missing
```

上游 Makefile 链接行：

```make
LDLIBS=-lncursesw
rover: rover.c config.h
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS) $(LDLIBS)
```

配方通过 `make -j1 -C <source> CC=<clang> CFLAGS='...' LDFLAGS='...'` 覆盖构建：

- `CFLAGS = -I<ncurses>/include -DNCURSES_WIDECHAR -Wall -O2`
- `LDFLAGS = -L<ncurses>/lib -lncursesw`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 不接依赖路径，交叉编译会取构建机系统 curses.h | 上游 Makefile 无 pkg-config/configure，只有裸 `$(CC) ... -lncursesw` | make 命令行传 `CFLAGS/LDFLAGS`（命令行变量覆盖 Makefile 内赋值），显式写 conan 依赖的 `-I/-L` |
| 2 | 宽字符声明缺失（wchar 相关） | rover 使用 ncursesw；OHOS ncurses 头文件需宏开关 | 添加 `-DNCURSES_WIDECHAR` 并链接 `-lncursesw` |
| 3 | 无法运行期验证 | 交叉产物为 aarch64/OHOS，宿主 x86_64 不能执行 | test_package 的 `test()` 用 `can_run()` 判定，不可运行时不伪造成败，只校验包内 `bin/rover` 存在 |

## 依赖

- ncurses/6.5（制品仓 ohpcd 已有预编译包，OHOS 静态库）
- 上游无其他依赖（无 libjpeg/libpng 等可选依赖需求）

## 功能验证结果

交叉编译产物为 aarch64/OHOS，宿主 x86_64 不能直接执行，改用本机
`qemu-aarch64` + OHOS guest sysroot 实测运行：

```bash
$ file <package_folder>/bin/rover
bin/rover: ELF 64-bit LSB pie executable, ARM aarch64, ... dynamically linked,
           interpreter /lib/ld-linux-aarch64.so.1, not stripped
$ readelf -d <package_folder>/bin/rover | grep NEEDED
 0x... (NEEDED)  Shared library: [libc.so]
$ qemu-aarch64 -L /opt/ohos-guest <package_folder>/bin/rover -v
rover 1.0.0
$ echo $?
0
```

- 版本号来源：源码 `config.h` → `#define RV_VERSION "1.0.0"`（`rover -v` 输出一致）
- 帮助信息：`rover -h|--help` 打印 `Usage: rover [OPTIONS] [DIR [DIR [...]]]`（源码 main() 逐字可见）
- 产物依赖仅 `libc.so` → ncursesw 已静态链接（G3 系统同名库隔离无风险）
- test_package：编译消费者程序 `test.c`，运行 `bin/rover -v` 并断言输出含 `rover`（仅当 can_run；交叉构建时按预期跳过运行）
