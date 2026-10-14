# shuffle

## 简介

shuffle 是 W3C 的 Bert Bos 编写的小工具：把文件（或标准输入）的所有行读入内存，以随机顺序写出。
实现为单个 C 文件 `shuffle.c`（`$Id: shuffle.c,v 1.6`），先尝试 `mmap()`，输入不可寻址（管道）时回退到 `read()`；
随机数用 `random()`，并避免取模偏差（Fisher–Yates 洗牌）。

## 功能概述

- 用法：`shuffle [infile [outfile]]`；省略参数或参数为 `-` 时分别读标准输入、写标准输出
- 输入最后一行必须以换行结束，否则报 `Missing newline at eof` 并以退出码 1 结束
- 参数超过 2 个报 `Usage`，退出码 1

## OHOS 适配

### 1.6（feat/shuffle-1.6）

- 上游只提供一个 `.c` 文件，无压缩包、构建系统和测试；配方下载固定 sha256 的单文件，用随包 `CMakeLists.txt` 经 Conan 工具链编译
- 补丁 `0001-open-o-creat-mode.patch`：`open(outfile, O_WRONLY|O_CREAT)` 没有 mode 参数。`open()` 是变参函数，
  musl 在 `O_CREAT` 时用 `va_arg` 读取 mode，未传入则读到寄存器里的残留值，新建的输出文件权限位不确定
  （qemu-aarch64 实测 `0155`/`0055`/`0000`，属主无读写权限）。补丁传入显式 `0666`（由 umask 过滤）
- `package()` 对 OHOS 构建重新自签 `bin/shuffle`（SDK 链接器写入的 `.codesign` 不被加载器认可）
- 上游无测试；`test_package` 补全 7 个消费者用例（42 条断言），其中 2 个为鸿蒙特有用例
- 命令行工具，已按 R38 声明 `commands.json`

## 依赖关系

- 编译依赖：C 编译器、CMake
- 运行依赖：无（libc-only / POSIX）

## 参考资料

- 项目主页：<https://www.w3.org/People/Bos/Shuffle/>
- 源码：<https://www.w3.org/People/Bos/Shuffle/shuffle.c>
