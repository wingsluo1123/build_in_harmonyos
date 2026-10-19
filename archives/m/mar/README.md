# mar — HarmonyOS PC 适配说明

`mar`（meta archive）把键值元数据和用户数据放进同一个二进制文件：文件头 + 定长的键索引 + 用户数据 + 元数据块，所有多字节整数按大端编码，与主机字节序无关。适合“需要一点结构化元数据、又不值得上数据库”的场景。本包含 C 库 `libmar.a`、C++ 流/迭代器封装头文件和命令行工具 `mar`。

- 上游：Mark Aylett，2004 年发布 0.5（原站 www.emantic.co.uk 已下线）；本包源码取自 FreeBSD ports `archivers/mar` 使用的 distfiles
- 形态：两级手写 Makefile（无 configure）；C 库 + C 工具 + 头文件式 C++ 封装
- 产物：`bin/mar`（static-pie）、`lib/libmar.a`、`include/` 下 17 个头文件、`share/man/man1/mar.1`、`share/doc/mar/`、`licenses/copying.txt`
- 依赖：无第三方依赖，只用 libc / POSIX（文件 I/O、`mmap`/`msync`）；C++ 封装与上游测试只用 C++ 标准库
- 许可证：MIT

## 用法

```bash
mar -s product=OpenHarmony-PC -s arch=aarch64 -i payload.bin data.mar   # 创建，设置键值，插入用户数据
mar -t data.mar        # 列出全部 key=value
mar -k data.mar        # 只列出 key
mar -m arch data.mar   # 按键取值
mar -l data.mar        # 用户数据长度
mar -x out.bin data.mar  # 提取用户数据
mar -f -u arch data.mar  # 删除一个键（-f：不再确认）
```

使用库时必须定义 `MAR_STATIC`（Conan 包已通过 `cpp_info.defines` 导出），否则 `mar_storage_c.h` 会 `#error`。

## OHOS 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | OHOS aarch64 的 plain `char` 无符号。`mar_main_c.c` 把 `mar_getopt()` 的 `int` 返回值存进 `char ch`：选项扫描结束时的 `EOF`（-1）变成 255，`-1 != ch` 恒真，控制流落进 `switch` 的 `default`，每条真实命令都以 `Unknown option` 退出 1（`-h` 因提前返回而正常）。选项表被扫描两遍（`main` 和 `mar_run`），两处都要改；只改第一处，操作已执行但仍退出 1，只改第二处，什么都不执行 | 补丁 0003：两处 `char ch` → `int ch`。clang 默认就会报 `-Wtautological-constant-out-of-range-compare`，但只是告警、构建照常成功，配方把这一条单独提升为 `-Werror=` 作回归护栏 |
| 2 | C++ 流封装 `mar_stream_cpp.h`/`mar_streambuf_cpp.h` 无限定地调用依赖基类成员 `rdbuf`、`setg`、`sputc`，clang + libc++ 的两阶段名字查找拒绝编译，上游自己的 `make check` 也编不过 | 补丁 0001/0002：9 处加 `base_type::` |
| 3 | 上游 `make install` 的头文件清单漏了 `mar_string_c.h`，而 `mar_key_cpp.h` 包含它：12 个 C++ 头里 8 个（含 `mar_archive_cpp.h`、`mar_stream_cpp.h`、`mar_util_cpp.h` 三个入口头）装完无法包含；另外不创建 `$(MANDIR)/man1`、没有 `DESTDIR` | 不用上游 install，`package()` 自行安装 17 个头文件 |
| 4 | x86 运行器无法启动动态链接的 OHOS 产物（缺 `/lib/ld-musl-aarch64.so.1`） | `bin/mar` 用 `-static-pie -Wl,-z,relro,-z,now` 链接，同一产物在 AArch64 原生运行、x86 经 `qemu-aarch64` 运行。先例：tal/1.9、cutmp3/4、ctpv/1.1 |

## 测试

- 上游：无 `tests/` 目录、无 ctest/pytest；Makefile 的 `check` 目标构建并运行 `src/mar_test`（C++，8 个命名用例）→ 8 个，`build()` 中实跑 8/8 通过。
- test_package：2 个消费者用例（都执行包内 `bin/mar`，并在 test_package 里用 OHOS 工具链链接包内头文件和 `libmar.a` 编译消费者程序），共 98 条断言。
  1. `mar_consumer_c`：`bin/mar` 写归档 → C 消费者经 mmap API 读回并核对大端文件头 → 消费者写第二个归档（ABI 探针键、4 份 3000 字节负载，跨多页）→ `bin/mar` 列出、测长、提取。
  2. `mar_consumer_cpp`：C++ 消费者包含全部安装的 C++ 头，用 `mar::index` 遍历、`mar::istream` 读、`mar::copy` 复制，并经文件型 `mar::iostream` 写入 400 行（22400 字节，约 22 次 1024 字节缓冲区回填）→ `bin/mar` 列出、测长、提取。
