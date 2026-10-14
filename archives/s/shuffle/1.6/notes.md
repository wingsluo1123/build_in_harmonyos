# shuffle 1.6 适配笔记

## 编译环境
- 构建系统: custom（上游无构建系统；配方随包 CMakeLists.txt 经 Conan CMakeToolchain 编译）
- 编译日期: 2026-10-07
- 编译器: OHOS SDK clang（`/data/service/hnp/bin/clang`），profile `ohos-aarch64`
- 状态: built

## 语言预检（R47）
- 只读预判 `detect_language`: `detected_language=c`；evidence: build_system=none，manifest=未发现，source_stats=源文件 1 个（c:1），主体占比 100%
- `lang-preflight shuffle 1.6 --src <dir>` 默认口径放行（c ↔ cpp 兼容族）

## 依赖（W0）
- libc-only / POSIX，无 Conan 依赖，无需检查制品仓

## 历史核验（W0b）
- 仓库无 shuffle 历史归档；`recipe-search shuffle` 无相似配方。同形态先例：`archives/l/lockrun/1.1.3`（单个 `.c` 官方源）

## 编译步骤

1. `init-build` 按 tar.gz 解压会失败（上游是裸 `.c`），改用 `init-archive` 建骨架。
2. 下载 `https://www.w3.org/People/Bos/Shuffle/shuffle.c`，sha256 `4d4cbc5ebe4fe37a6e1c74861269b16dc5c36ac254d695457f8caa210ffd16fb`（文件头 `$Id: shuffle.c,v 1.6 2015/08/12`，服务器 Last-Modified 2015-08-12）。
3. 手工编译：`clang -O2 -Wall -Wextra -c shuffle.c` 无任何警告；配方里改由 CMakeLists.txt + CMakeToolchain 编译。
4. 交付物只有 `bin/shuffle`；`package()` 在 OHOS 上对其重新自签（E077/E077B）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 报「解压失败: not a gzip file」 | 上游是单个 `.c`，不是压缩包 | 用 `init-archive` 建骨架，配方用 `download()` + sha256 |
| 2 | 输出文件 `shuffle in out` 新建后权限位随机（qemu-aarch64 实测 `0155`/`0055`/`0000`，属主无读写权限） | `open(argv[2], O_WRONLY\|O_CREAT)` 没有 mode 参数；`open()` 是变参函数，musl 在 `O_CREAT` 时用 `va_arg` 读 mode，读到寄存器里的残留值 | 补丁 0001：传入显式 `0666`（由 umask 过滤） |

## 源码修改

- `patches/0001-open-o-creat-mode.patch`（1 行）：`open(argv[2], O_WRONLY|O_CREAT)` → `open(argv[2], O_WRONLY|O_CREAT, 0666)`。无平台宏。
- 没有顺手改上游的其它行为：不加 `O_TRUNC`（覆盖更长的已有文件会留尾部）、空文件仍因 `mmap(len=0)` 报 `Invalid argument`，都是上游原样行为。

## 依赖版本

- 无

## 上游测试清点（R51）

- 上游发布物就是单个文件 `shuffle.c`（同目录另有 `shuffle.1` 手册与无关的小工具）：无 `tests/` 目录，无 ctest/pytest/make check 注册，N=0，N′=0。
- 上游目录里唯一的测试脚本 `test-soundex.sh` 属于 `soundex.c`，与本包无关。
- 因此上游测试不适用；`test_package` 补全真实功能测试（见下）。

## test_package（rule12）

- `test_shuffle_consumer.c`：5 个用例 / 26 条断言。驱动包内 `bin/shuffle`：1000 行文件→文件（mmap 路径）、重定向 stdin→stdout、240 KB 管道（read/realloc 路径）、单行、错误契约（输入文件不存在 / 缺结尾换行 / 参数过多，退出码 1 + 诊断信息）；校验输出与输入是同一行集合且顺序不同。
- `test_shuffle_ohos.c`：2 个鸿蒙特有用例 / 16 条断言。覆盖补丁 0001 的改动点：新建输出文件的权限位必须等于测试自己用 `open(O_CREAT, 0666)` 在同目录、同 umask 下建的参考文件（umask 022 → `0644`，umask 077 → `0600`；这样对会归一化权限位的文件系统也成立），属主可读写并读回内容。
- 构建与运行：`test_package/conanfile.py` 经 OHOS profile 消费本包 → CMake 编译两个 C 消费者程序 → `self.run` 执行。

## 验证结果

x86 runner 上动态链接的 OHOS 产物跑不起来（E544，缺 `/lib/ld-musl-aarch64.so.1`），本地验证用同源 `.o` 静态重链副本（`clang -static`）+ `qemu-aarch64`；**这不等于交付的动态链接 `bin/shuffle` 已实跑，交付产物由 CI 执行**。

```
$ qemu-aarch64 ./test_shuffle_consumer ./shuffle_patched $W
shuffle consumer tests: 5/5 cases passed (26 assertions, 0 failed)     exit=0
$ qemu-aarch64 ./test_shuffle_ohos ./shuffle_patched $W
shuffle OHOS-specific tests: 2/2 cases passed (16 assertions, 0 failed)   exit=0
对照: 同一 test_shuffle_ohos 驱动未打补丁的 shuffle
umask 0022: output file mode is 0055, a file created with mode 0666 gets 0644 / umask 0077: output file mode is 0000, a file created with mode 0666 gets 0600
shuffle OHOS-specific tests: 0/2 cases passed (16 assertions, 4 failed)   exit=1
对照: 同一 test_shuffle_consumer 驱动未打补丁的 shuffle -> 5/5（通用路径不受该缺陷影响）
```

最小复现（`O_CREAT` 缺 mode 的 4 行程序，OHOS clang `-static` + `qemu-aarch64`）：缺 mode 时新建文件为 `0210`（umask 022 与 0 下相同），补 `0644` 后为 `0644`；编译无警告。以上权限位均为 qemu 用户态观测，未在真机上实测。

x86 runner 上 `conan create` 内的 `test()` 只做 ELF 头检查并给出 WARN，不执行这些用例；CI（aarch64 OHOS builder）上会真正编译并运行，需在 CI 日志确认出现 `shuffle consumer tests: 5/5 cases passed` 与 `shuffle OHOS-specific tests: 2/2 cases passed`，且没有 x86 WARN。

`conan-verify` G0–G3 通过；`finish` 的 W3 本地 CI：L0 / L1（test_package executed）/ L1e 破坏性反向验证 / L4 / L5 为 pass，L2 冒烟为 skip（x86 上无法执行 OHOS 动态链接的 `bin/shuffle`）。`conan-verify` 报告里 G4/L2/L4/L5 被跳过却记 PASS，不作为验证依据。

## 注意事项

- `shuffle` 用 `srandom(time(NULL))` 播种：同一秒内两次运行得到同一排列，属上游行为，测试不依赖两次运行结果不同。
- 许可证：文件头声明 W3C Open Source 许可（http://www.w3.org/Consortium/Legal/），SPDX 标记为 `W3C`；上游没有单独的 LICENSE 文件，包内不附带。
---

**编译结束**: 2026-10-07 20:08
**最终状态**: built
