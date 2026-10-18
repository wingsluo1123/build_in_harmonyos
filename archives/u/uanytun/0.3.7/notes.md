# uanytun 0.3.7 适配笔记

## 软件信息
- 上游：uAnytun — SATP（Secure Anycast Tunneling Protocol）的精简单线程实现
- 官网：https://www.anytun.org/
- 源码：https://anytun.org/download/uanytun-0.3.7.tar.gz
  sha256 `076318c771c908386c4408dda0769171542da701785302903641ce23fd33a295`
- 产物：命令行工具 `uanytun`（安装到 `sbin/`；另有 `etc/uanytun`、`etc/init.d/uanytun` 示例）
- 语言/构建：C，随包自带手写 `src/configure` + `src/Makefile`（非 autotools）

## 编译环境
- WSL 上使用仓库既定交叉工具链（`ci/conan/profiles/ohos-aarch64`：
  `tools.build:compiler_executables` 指向 `/data/service/hnp/bin/clang`，
  该 wrapper 默认 target = `aarch64-unknown-linux-ohos`）
- 依赖：`libgcrypt/1.11.0`（→ `libgpg-error/1.55`），OHOS arm64 预编译包已在 ohpcd 制品仓

## 编译步骤

```bash
# conan create 内部（build()）：
./configure --target=Linux --prefix=<package_folder> --use-clang --no-manpage --no-examples
make -jN CC=<clang 绝对路径>
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'gcrypt.h' file not found` | 环境变量 CFLAGS 为空时 configure 正常，但一旦非空，`CFLAGS=$CFLAGS'-g -O2'` 无空格拼接，`-I<dir>` 与 `-g` 粘成 `-I<dir>-g` | 传给 configure 的 CFLAGS/LDFLAGS 以空格结尾；配方里显式 `" ".join(...) + " "` |
| 2 | 补上 libgcrypt 头目录后仍报 `'gpg-error.h' file not found` | `gcrypt.h` 内部 `#include <gpg-error.h>`，libgpg-error 是传递依赖 | 遍历 `self.dependencies.values()` 收集**全部**依赖的 includedirs/libdirs，而不是只取直接依赖 |
| 3 | configure 把 CC 写死成 `clang`/`gcc`，无法注入交叉编译器 | 手写 configure 无 `--host/--build` 支持 | 配方从 `tools.build:compiler_executables` 读 c 编译器绝对路径，用 `make CC=<path>` 命令行覆盖 include.mk 的 `CC :=`（R33，不依赖 shell 变量） |
| 4 | 手册页/示例安装需要 asciidoc 等额外工具 | 上游 `install-man` 依赖 asciidoc 重新生成 manpage | `--no-manpage --no-examples`，只装二进制与 etc 配置 |

## 未改动上游源码
本适配**无需任何 patch**：交叉编译在 Linux 目标分支（`--target=Linux`，
自动把 `src/linux/tun.c` 链接为 `src/tun.c`）下一次通过，
`uanytun -v` / `uanytun -h` 的正常退出路径不触碰 TUN 设备。

## 验证
- `conan create` 通过，产物为 `sbin/uanytun`（ELF 64-bit LSB pie executable, ARM aarch64）
- `test_package`：`uanytun -v` 输出版本串 + `uanytun -h` 输出用法（原生环境执行；
  WSL 为 x86_64 交叉构建时按 `can_run()` 只编译不执行）
