# GNU-EFI (gnu-efi)

GNU-EFI 是 UEFI 固件应用的开发工具包：把 UEFI Boot Services / Runtime Services
的调用面封装成可直接链接的静态库，并附带把 ELF 镜像转换成 PE32+ EFI 可执行文件
所需的一切构建资产。`efibootmgr` 一类工具即建立在它之上。

| 交付物 | 说明 |
|------|------|
| `libefi.a` | UEFI Boot/Runtime Services 封装（`libefi`） |
| `libgnuefi.a` | GNU-EFI 运行期辅助库（`libgnuefi`） |
| `crt0-efi-aarch64.o` / `crt0-efi-aarch64-local.o` | aarch64 EFI 入口桩（objcopy 路径 / 汇编合成路径各一） |
| `elf_aarch64_efi.lds`（+ `_local`） | EFI 链接脚本 |
| `include/efi/**` | EFI 头文件树（`efi.h`、`efilib.h`、`protocol/`、`aarch64/`、`legacy/`） |
| `lib/pkgconfig/gnu-efi.pc` | pkg-config 元数据（前缀已改写为可重定位形式） |
| `lib/gnuefi/apps/*.efi` | 上游示例 EFI 应用（上游 `APPSDIR` 约定，非宿主可执行文件） |

## 在 HarmonyOS PC 上使用

```sh
conan install --requires=gnu-efi/4.0.4

# 用包内工具链构建一个 UEFI 应用（消费者侧典型流程）
clang -c hello.c -o hello.o \
      -I<prefix>/include/efi -I<prefix>/include/efi/aarch64 -I<prefix>/include/efi/protocol \
      -ffreestanding -fno-stack-protector -fPIC -fno-jump-tables -std=c11 -O2
ld.lld -nostdlib -z common-page-size=4096 -z max-page-size=4096 \
      -L<prefix>/lib <prefix>/lib/crt0-efi-aarch64.o hello.o -o hello.so \
      -T <prefix>/lib/elf_aarch64_efi.lds -lefi -lgnuefi
objcopy -O efi-app-aarch64 hello.so hello.efi
```

源码里请使用 C11 `u"…"`（或自带 `-fshort-wchar`）来匹配 gnu-efi 的
2 字节 `CHAR16`；上游示例即为 `u"…"` 口径。

## 适配信息

- 版本：4.0.4（上游 tag `4.0.4` = commit `37cd8f069b`，官方 GitHub 归档）
- 构建系统：上游手写 Makefile（无 configure / CMake），`make` + `make install`
- 依赖：无 Conan 依赖；构建期需 clang / lld / llvm-ar / llvm-ranlib / GNU objcopy / GNU install（`ginstall`）
- 适配要点与测试证据见 `4.0.4/notes.md` 与 `4.0.4/reports/test-report.md`

## 上游

- 主页：https://github.com/ncroxon/gnu-efi
- 源码：https://github.com/ncroxon/gnu-efi/archive/refs/tags/4.0.4.tar.gz
- 许可：GPL-2.0-or-later OR BSD-3-Clause
