# unhide 20240510 适配笔记

## 编译环境
- 构建系统: custom（上游无 Makefile/configure；`build_all.sh` 直接调 gcc 产出 4 个静态二进制，配方按其清单复刻）
- 编译日期: 2026-10-12
- 编译器: OHOS NDK clang 15（本地 WSL 镜像 `/opt/lpk-fixed/clang` → `aarch64-unknown-linux-ohos-clang`；CI 用 `/data/service/hnp/bin/clang`，经 `tools.build:compiler_executables` 注入）
- 目标: aarch64-linux-ohos，profile `ohos-aarch64-lkyz`（`ci/conan/profiles/ohos-aarch64` 的本地镜像）
- 状态: built（本地 conan create + test_package 通过）

## 源码
- URL: https://github.com/YJesus/Unhide/releases/download/v20240510/unhide-20240510.tgz （上游 v20240510 官方 release 资产，HTTP 200，267603 字节）
- sha256: `7173ba2ec2732c943eca785fe01290b3cce09f60ded66df857caba3ec690877b`
- 解包顶层目录 `unhide-20241211`（上游 make_tarball.sh 于 2024-12-11 打包，tag 名 v20240510；二进制 banner 内嵌 "Unhide 20240509" 为上游自身字符串，未改动）
- 许可: GPL-3.0-or-later（COPYING 为 GPLv3 全文，各源文件头 "License GPLv3+"），`COPYING` 打包到 `licenses/`
- tarball 内含嵌套 `unhide-20241211.tgz`（上游自打包），配方不使用、不打包

## 产物（4 个命令行工具，均动态 PIE）
| 二进制 | 上游编译命令（build_all.sh） | 说明 |
|---|---|---|
| unhide-linux | gcc -Wall -O2 --static -pthread unhide-linux*.c unhide-output.c | 主工具：6 种隐藏进程检测技术（ps 对比/procfs/syscall/PID 爆破/复合/快速） |
| unhide_rb | gcc -Wall -O2 --static unhide_rb.c | unhide.rb 的 C 复刻（上游自述 P.O.F. 玩具，仅供对照） |
| unhide-tcp | gcc -Wall -O2 --static unhide-tcp.c unhide-tcp-fast.c unhide-output.c | 隐藏 TCP/UDP 端口检测 |
| unhide-posix | gcc -Wall -O2 --static unhide-posix.c | 旧版（Linux < 2.6 / 其他 UNIX）兼容版 |

4 个工具都是命令行程序（`package_type = "application"`、`cpp_info.bindirs = ["bin"]`），
因此按 CI 的 L0k / R38 闸必须提供**软件级** `commands.json`：

- `archives/u/unhide/commands.json`（`type: "tool"`，`versions."20240510".ref = "unhide/20240510"`，
  `binary: false` —— 尚未通过 release 流水线发布；`true` 才代表制品仓已有预编译二进制）
- CI #88314 的失败正是缺这个文件：`L0 quality gate failed: commands_json_r38`

## 编译步骤

```bash
# conanfile.py build() 的等价命令（CC 取自 tools.build:compiler_executables）
clang -Wall -O2 -Werror=implicit-function-declaration -pthread -I. -o unhide-linux \
  unhide-linux.c unhide-linux-bruteforce.c unhide-linux-compound.c \
  unhide-linux-procfs.c unhide-linux-syscall.c unhide-output.c
clang -Wall -O2 -Werror=implicit-function-declaration -I. -o unhide_rb unhide_rb.c
clang -Wall -O2 -Werror=implicit-function-declaration -I. -o unhide-tcp unhide-tcp.c unhide-tcp-fast.c unhide-output.c
clang -Wall -O2 -Werror=implicit-function-declaration -I. -o unhide-posix unhide-posix.c
```

- 与上游 `build_all.sh` 的对象清单/链接旗标一一对应，仅去掉 `--static`：OHOS
  sysroot 无静态 libc（`find -name '*.a'` 为空）且无 `rcrt1.o`，`-static-pie`
  链接直接失败（`ld.lld: cannot open rcrt1.o`；`sockstat/0.4.2` 同因同解）。
  驱动默认产出动态 PIE（ET_DYN + PT_INTERP），`NEEDED` 仅 `libc.so`：
  CI aarch64 真机原生执行（musl loader），x86 本地经 qemu-aarch64 执行
  （/lib/ld-*-aarch64.so.1 与 libc.so 由本地 ohos-guest 提供）。
- PT_INTERP 具体值不进断言：CI 设备驱动（/data/service/hnp/bin/clang）产出
  `/lib/ld-musl-aarch64.so.1`，本地 WSL shim 产出 `/lib/ld-linux-aarch64.so.1`
  （Ubuntu clang-15 不识别 ohos env 的回退），两者都能启动；测试只断言
  "有 PT_INTERP + NEEDED 恰为 libc.so"。
- `-pthread` 只加在 unhide-linux（上游如此）；musl 线程内建于 libc，无额外库。
- `-Werror=implicit-function-declaration`：防御性旗标（`sockstat/0.4.2` 同款），
  防止 musl 某天把 POSIX 声明藏进 feature macro 后 C89 隐式声明截断 64 位
  指针（tal/1.9 类回归：编译只有一条告警、运行即 SIGSEGV）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `use of undeclared identifier 'PATH_MAX'`（unhide-linux-compound.c:70/76/240/254、unhide-linux-procfs.c:104/112） | glibc 下 `sys/wait.h` 等传递包含 `limits.h` 兜底；musl 头不传递，需显式包含 | 补丁 0002 给两个 PATH_MAX 使用者加 `#include <limits.h>` |
| 2 | `wait.h: warning redirecting incorrect #include <wait.h>` / 非转发 sysroot 下直接 fatal error | `<wait.h>` 是 glibc/libc6-dev 的转发头（Ubuntu: `#include <sys/wait.h>`），musl/OHOS sysroot 无此文件 | 补丁 0001 将 6 个文件的 `<wait.h>` 改为标准 `<sys/wait.h>`（先例：nwipe/0.39 补丁 0002） |
| 3 | 上游无构建系统 | build_all.sh 仅是 4 行 gcc 命令 | build() 按上游清单逐二进制编译，不引入 configure/make |
| 4 | `-static-pie` 链接失败：`ld.lld: error: cannot open rcrt1.o: No such file or directory` | OHOS sysroot 无静态 libc（`find -name '*.a'` 为空）亦无 `rcrt1.o`，静态链接无法解析 | 放弃静态链接，产物动态链接仅依赖 `libc.so`；CI 为 aarch64 真机原生执行，x86 本地用 qemu-aarch64（先例：`sockstat/0.4.2` 同因同解） |

## 源码修改

- `patches/0001-fix-wait-include.patch`：6 个文件 `<wait.h>` → `<sys/wait.h>`（unhide-linux.c、unhide-linux-bruteforce.c、unhide-linux-compound.c、unhide-linux-procfs.c、unhide-linux-syscall.c、unhide_rb.c）
- `patches/0002-add-limits-include.patch`：unhide-linux-compound.c、unhide-linux-procfs.c 加 `#include <limits.h>`

全部是可移植 POSIX 替换，无 `__OHOS__` 等平台宏。

## 依赖版本

无第三方依赖（只用 libc 与 pthread，musl 内建；W0：`requirements()` 为空）。

## 上游测试清点（R51）

| 项 | 结果 |
|---|---|
| tests/ 目录数 | 0 |
| 上游测试脚本 | sanity.sh（7 个编号测试，伪造 ./ps 逐项验证检测逻辑）、sanity-tcp.sh（2 个编号测试，伪造 ./ss/netstat） |
| 可否用于 test_package | 否：两者均需 root 且在解包源码树内运行（PATH 注入伪造 ps/ss），CI 设备非 root（euid 20020084） |

test_package 改为驱动安装后的真实产物：ELF 加固检查（4 个二进制 × AArch64/OHOS note/动态 PIE+PT_INTERP/NEEDED 仅 libc.so/NX）、
root 模式下真实 CLI 语义 + checksysinfo/getpriority 实扫、非 root（CI 设备）模式下上游自带的
root 拒绝路径断言。详见 `test_package/MANIFEST.yml`。

## 运行时行为备注

- 4 个二进制的实际扫描均要求 root（`getuid() != 0` 时 die/exit 1）——这是上游取证语义，不是缺陷
- unhide-tcp 依赖 `/proc/net/{tcp,tcp6,udp,udp6}` 与 `ss`/`netstat`；unhide-linux 的 ps 对比依赖 `ps`（OHOS toybox 提供）
- 版本字符串 "20240509" 为上游内嵌 banner 原文（tag v20240510、打包目录 unhide-20241211），未改动以保持与上游一致
