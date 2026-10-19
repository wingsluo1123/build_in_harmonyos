# mar 0.5 适配笔记

## 编译环境
- 构建系统: makefile（上游两级手写 Makefile，无 configure）
- 编译日期: 2026-10-04
- 编译器: OHOS NDK clang 15.0.4（aarch64-unknown-linux-ohos），x86_64 构建机交叉编译
- 状态: built（conan-verify 与 finish W3 本地 conan create 通过；未上传制品仓）

## 上游概况
- 作者 Mark Aylett，2004-12-15 发布 0.5（gzip 头时间戳 2004-12-15 07:08:11）；原站 `www.emantic.co.uk` 域名已不再解析。
- 源码包取自 FreeBSD ports `archivers/mar` 使用的 distfiles：`https://critical.ch/distfiles/mar-0.5-src.tar.gz` 返回 302，跳转到 `distcache.FreeBSD.org/local-distfiles/ehaupt/`。sha256 `8ee7612ab7bdb55dc43619ae50113dad7bf669939b454573fcac0941c45829ab`（74089 字节），经 4 个来源核对一致：init-build 下载一次、独立再下载一次、FreeBSD ports `archivers/mar/distinfo`（SHA256 与 SIZE 均一致）、Wayback Machine 2006-02-11 对原始上游 URL 的快照。
- 源码包 91 个文件：C 源文件 23 个（`src/` 19 个，`src/unix/`、`src/win/` 各 2 个）+ 1 个 C++ 测试，`include/` 30 个头文件（上游 install 清单列出 16 个，其余是内部头与 Windows 头），以及 `doc/html`、`man/man1/mar.1`、`msvc/`、`sample/`。主体语言判定 cpp（C 23、C++ 1、perl 1、sh 1，主体 92%），默认口径通过语言预检。
- 依赖: 无第三方依赖，只用 libc / POSIX（open/fstat/lseek、`mmap`/`msync`/`munmap`、`getpagesize`、`netinet/in.h` 的 htons/htonl）；C++ 封装与测试只用 C++ 标准库。
- 许可证: MIT（`copying.txt`，随包安装在 `licenses/`）。
- 文件格式（`include/mar_format_c.h`，另见 `src/mar_format.txt`）：版本 2 字节 + 索引项数 2 字节 + 索引（每项 38 字节 key + 2 字节元数据长度）+ 用户数据（4 字节长度 + 数据）+ 元数据块；整数经 htons/htonl 编码为大端，与主机字节序无关。

## 编译步骤

配方 `build()` 在源码目录执行（make 命令行变量覆盖 Makefile 里的 `CC`/`CXX`/`AR`/`RANLIB`/`CFLAGS`/`LDFLAGS`）：

```bash
make -j1 -C src all CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
     AR=<NDK>/llvm/bin/llvm-ar RANLIB=<NDK>/llvm/bin/llvm-ranlib \
     CFLAGS='-O2 -fPIC -Werror=tautological-constant-out-of-range-compare' CXXFLAGS=-std=gnu++17 \
     LDFLAGS='-static-pie -Wl,-z,relro,-z,now'
# 之后同样的变量构建上游 check 目标的测试程序并运行:
make -j1 -C src mar_test ...;  qemu-aarch64 src/mar_test
```

`package()` 安装 `bin/mar`、`lib/libmar.a`、17 个头文件、`share/man/man1/mar.1`、`share/doc/mar/{changelog.txt,mar_format.txt}`、`licenses/copying.txt`。`package_info()` 导出 `libs=["mar"]`、`defines=["MAR_STATIC"]`、`bindirs=["bin"]`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建成功，`mar -h` 正常，但 `mar -s name=hello a.mar` 报 ``Unknown option `-s': Try `mar -h' for more information`` 并退出 1，`a.mar` 没有创建；每条真实命令都如此 | OHOS aarch64 的 plain `char` 无符号（`CHAR_MIN` 0，`__CHAR_UNSIGNED__ 1`）。`mar_main_c.c` 的 `main()` 与 `mar_run()` 各有一个 `char ch` 接收 `mar_getopt()` 的 `int` 返回值，选项扫描结束的 EOF(-1) 变成 255，`-1 != ch` 恒真，控制流落进 `switch` 的 `default`。clang 默认其实报了 `-Wtautological-constant-out-of-range-compare`，但只是告警 | 补丁 0003：两处 `char ch` → `int ch`。只改一处是半修复：只改 `main()` → `mar_run()` 把操作做完才报 `Unexpected option '-s'` 并退出 1（a.mar 已写入）；只改 `mar_run()` → 预扫描就失败，什么都没写。配方 CFLAGS 加 `-Werror=tautological-constant-out-of-range-compare` 作回归护栏 |
| 2 | 上游 `make check`（C++ 测试 `mar_test`）与任何包含安装头文件的 C++ 消费者都编不过：`explicit qualification required to use member 'rdbuf'/'setg'/'sputc' from dependent base class` | 2004 年的 C++ 流封装在类模板里无限定地调用依赖基类（`std::basic_istream/ostream/iostream/streambuf`）的成员；clang+libc++ 按两阶段名字查找拒绝 | 补丁 0001（`mar_stream_cpp.h` 7 处 `rdbuf` → `base_type::rdbuf`）、0002（`mar_streambuf_cpp.h` 的 `setg`、`sputc` 各 1 处）。无平台宏 |
| 3 | 按上游 Makefile 的 `HEADERS` 清单安装后，12 个 C++ 头里 8 个无法单独包含：`fatal error: 'mar_string_c.h' file not found`（含入口头 `mar_archive_cpp.h`、`mar_stream_cpp.h`、`mar_util_cpp.h`） | `mar_key_cpp.h` 包含 `mar_string_c.h`，但上游 install 清单漏掉它；另外 `make install` 不创建 `$(MANDIR)/man1`（man 页安装必失败）、不支持 DESTDIR | 不用上游 install，`package()` 自行安装 17 个头文件（上游清单 16 个 + `mar_string_c.h`）；对每个已安装头文件只用包内 `include/` 做 C++ 语法检查，17/17 通过 |
| 4 | 消费者不定义 `MAR_STATIC` 时 `#error Please define either MAR_SHARED or MAR_STATIC` | `mar_storage_c.h` 强制要求链接方式宏 | `package_info()` 的 `cpp_info.defines = ["MAR_STATIC"]`，CMakeDeps 自动带给消费者 |
| 5 | x86_64 构建机无法启动动态链接的 OHOS 产物（缺 `/lib/ld-musl-aarch64.so.1`） | 本机没有 aarch64 musl 动态加载器 | `bin/mar` 用 `-static-pie -Wl,-z,relro,-z,now` 链接（仍是 PIE，带 GNU_RELRO + BIND_NOW，栈不可执行），同一交付产物在 AArch64 原生运行、x86 经 `qemu-aarch64` 运行；先例：tal/1.9、cutmp3/4、ctpv/1.1 |
| 6 | 未修补的 `mar -l` 用 `printf("%d\n", size)` 打印 `size_t`（`-Wformat` 告警） | 上游格式串与参数类型不符 | 未改动：aarch64 小端 LP64 上参数寄存器低 32 位即所需值，输出正确（`mar -l` 实测 3000、12000、22400 均正确）；补丁保持最小 |

## 源码修改

3 个补丁，全部由 `refresh-patch --auto` 生成，类型 portability，不含平台宏：

| 补丁 | 文件 | 改动 |
|---|---|---|
| 0001-include-mar_stream_cpp.h.patch | `include/mar_stream_cpp.h` | +7/-7：`rdbuf(&streambuf_);` → `base_type::rdbuf(&streambuf_);` |
| 0002-include-mar_streambuf_cpp.h.patch | `include/mar_streambuf_cpp.h` | +2/-2：`setg(...)`、`sputc(c)` 加 `base_type::` |
| 0003-src-mar_main_c.c.patch | `src/mar_main_c.c` | +2/-2：`char ch;` → `int ch;`（`main()` 与 `mar_run()`） |

补丁可干净应用到上游 `mar-0.5/`（`patch -p1 --dry-run` 三个都通过）。

## 依赖版本

无第三方依赖（`requirements()` 为空），W0 依赖发布检查无待查项。

## 上游测试清点（R51）

- 源码包无 `tests/` 目录、无 ctest/pytest 注册；`src/Makefile` 有 `check` 目标：构建 `src/mar_test`（由 `src/mar_test_cpp.cpp` 编译，412 行，C++ 封装 + libmar.a）并运行 `./mar_test`。`mar_test` 的 `tests[]` 表有 **8 个命名用例**：meta functions、user functions、insert function、extract function、copy function、opencopy function、iterator class、stream class。N = 8。
- 未打补丁时 `mar_test_cpp.cpp` 编不过（上面问题 2）。打补丁后 `conanfile.py` 的 `build()` 用同一套 make 规则构建（`-static-pie`），在 `build_folder/mar_test_run` 里运行：8/8 `OK`，`All tests PASSED`，N′ = 8，通过率 100%。运行方式：AArch64 主机直接运行，x86 主机经 `qemu-aarch64`；两者都不具备时只打印 SKIPPED 警告，不写成通过。本次本地经 qemu-aarch64 实跑，无 skip。

## 适配后测试统计

| 类型 | 用例 | 断言 | 说明 |
|---|---|---|---|
| 上游测试 `mar_test` | 8 | 8 | build() 里实跑 8/8 |
| **鸿蒙特有测试** `mar_consumer_c` | **1** | 47 | 完整消费者流程，见下 |
| **鸿蒙特有测试** `mar_consumer_cpp` | **1** | 34 | 完整消费者流程，见下 |
| `test_package/conanfile.py` 对 `bin/mar` 输出的逐字节断言 | — | 17 | 贯穿上面两个流程 |

鸿蒙特有测试（N = 2）都在 `test_package` 的 `conan create` 必跑路径上；`build()` 用 OHOS 工具链经 CMake 把消费者链接到包内头文件和 `libmar.a`（`MAR_STATIC` 由 `cpp_info.defines` 带入），`test()` 实际执行：

1. **`mar_consumer_c`（C API + 包内 CLI 往返）**：包内 `bin/mar` 创建 `cli.mar`（4 个键值，其中 `title` 是 UTF-8 非 ASCII 字节，加 3000 字节覆盖全部字节值的二进制负载）→ C 消费者经 `mar_open()`/mmap 读回：按键与按序号取值、`MAR_NOMATCH` 分支、用户数据（映射读取和 `mar_seek`/`mar_read` 分块读取）、原始文件头大端字节 `00 01 00 04` → 消费者写第二个归档 `lib.mar`（ABI 探针键：指针宽度、plain char 符号性、页大小；4 份 3000 字节负载共 12000 字节，跨多页，经 `mar_write()`/`mar_sync()`）并重新读回 → `bin/mar` 列出键、按键取值、测长、提取，并仍拒绝未知选项、缺失的键、缺失的归档名。
2. **`mar_consumer_cpp`（C++ 封装 + 包内 CLI）**：C++17/libc++ 编译，包含全部安装的 C++ 头文件（`mar_string_c.h` 在内，缺一个就编不过）→ `mar::index` 正向、反向遍历与 `find` → `mar::istream` 读用户数据（`read()` 与 `istreambuf_iterator`）→ `mar::copy()` 复制到内存归档 → 文件型 `mar::iostream` 写入 400 行共 22400 字节（约 22 次 1024 字节缓冲区冲刷）、同一流 `seekg(0)` 读回、关闭 → `bin/mar` 读键值、测长、提取，逐字节比对。

平台相关性：OHOS aarch64 的 plain `char` 无符号。未修补的 `mar` 在流程第一步（`mar -s ... cli.mar`）就退出 1；未修补的 C++ 头文件让 `mar_consumer_cpp` 根本编译不过。

负向对照（本地按同一用例手工重放，x86_64 + qemu-aarch64）：

| 构建 | 结果 |
|---|---|
| 未打补丁的 `mar`（静态重链） | `mar -s product=OpenHarmony-PC -i payload.bin cli.mar` 退出 1，`Unknown option `-i'`，`cli.mar` 未创建 |
| 只修 `main()` 的 `char ch` | 退出 1，`Unexpected option '-s'`，但 a.mar 已写入 |
| 只修 `mar_run()` 的 `char ch` | 退出 1，`Unknown option `-s'`，什么都没写 |
| 未打补丁的 `mar` + `-fsigned-char` | 退出 0，键值写入（符号性是唯一变量） |
| `consumer_cpp.cpp` 对未打补丁的头文件 | 4 个编译错误（`rdbuf`×2、`setg`、`sputc`） |
| 同一文件对已打补丁的头文件 | 编译通过 |

## 验证结果

```bash
# conan-verify: conan create -pr:h/-pr:b ci/conan/profiles/ohos-aarch64（本机 x86_64 + qemu-aarch64）
RUN: qemu-aarch64 .../src/mar_test       # build() 里的上游测试
Testing meta functions... OK  ...  Testing stream class... OK
All tests PASSED                          # 8/8
mar consumer (C): 47 checks, 0 failed     # 鸿蒙特有消费者用例 1
mar consumer (C++): 34 checks, 0 failed   # 鸿蒙特有消费者用例 2
PASS ... x 17                             # conanfile.py 对 bin/mar 输出的断言

# 交付产物属性
bin/mar: ELF 64-bit LSB pie executable, ARM aarch64, static-pie linked
FLAGS BIND_NOW, FLAGS_1 NOW PIE, GNU_RELRO, GNU_STACK RW（不可执行栈）
include/: 17 个头文件，逐个只用包内 include/ 做 C++ 语法检查，17/17 通过
```

## 注意事项

- test_package 在非 AArch64 运行器上依赖 `qemu-aarch64`；缺失时测试失败，不会静默跳过。build() 里的上游测试在既非 AArch64 又无 qemu 时只告警跳过，并如实写 SKIPPED。
- 本地验证在 x86_64 + qemu-aarch64 上完成，未在 HarmonyOS 真机实跑；`mmap`/`msync` 在真机文件系统（含 HMDFS）上的表现未验证，真机结果以 PR CI 为准。
- `bin/mar` 是静态 PIE，不依赖运行时加载器；未剥离符号（与已合入的 tal 相同）。
- 本地 W3（`finish` 的 `ci/conan/build_and_test.sh`）结果：L0j/L0k/L0m、KC、JC1–JC6 通过；conan create 通过；L1a、L1b、L1c（build() 里的上游测试）通过；L1e 破坏性反向验证确认测试真实依赖包（bin/、lib/、include/ 全部移走后 `conan test` 失败）；L4、L5 通过；L2 烟测只试 `--version`/`--help`，`mar` 只有短选项（`-h`），记为 skip（脚本标注非阻塞）。
- 未在 Windows/macOS 验证（`validate()` 限定 Linux/OHOS）；上游的 `msvc/`、`win/` 目录不参与构建。
- 知识草稿 `knowledge/drafts/E14735-draft-1370`：随包交付的 CLI 里 getopt 返回值存进 plain char 的症状、两遍扫描的两处接收变量与半修复状态、对测试设计的后果。与 `E6401-draft-1687`、cyrus-sasl-digestmd5 草稿同根因（它们是上游测试台形态），与 E419、DRAFT-8543 等同属 plain-char/EOF 家族；定位为 E6401 的补充条目，建议主编 merge-into，差异见草稿「关联条目与查重」。clang+libc++ 的依赖基类查找、安装清单漏装被引用头两个问题已有草稿覆盖（DRAFT-maq-0.7.1-stdhash-dependent-base-this-qualifier、DRAFT-delaunay-triangulation-2.1-install-headers-missing-referenced-header），未重复立条。

## 对话记录

### 对话 #1 — 2026-10-04

- W0：无第三方依赖；仓库无 mar 历史归档（`archives/m/` 里只有无关的 marcli、marco、mariadb 等）；lang-preflight 判定 cpp 族，默认口径通过。
- 手工交叉编译：库与 CLI 一次编过；用 `-static` 重链后经 qemu 实跑发现 `mar -s ...` 报 Unknown option；用 `-Wall` 与默认选项分别编译，确认 clang 默认就会报 `-Wtautological-constant-out-of-range-compare`；构造 A–E 五种构建（上游原样、`-fsigned-char`、两处都改、只改 main、只改 mar_run）实测，定位为选项表两遍扫描的两个 `char ch`。
- C++ 测试对象编不过，定位为依赖基类成员未限定；对安装头文件做逐个闭包检查，发现上游 install 清单漏装 `mar_string_c.h`。
- 参照已合入的 tal 用 `-static-pie` 交付 CLI，使 test_package 执行交付二进制本身；上游 `mar_test` 经同一 make 规则构建后在 build() 里实跑 8/8。
- 源码 sha256 经 FreeBSD distinfo 与 Wayback 快照交叉核对。
---

**编译结束**: 2026-10-04
**最终状态**: built
