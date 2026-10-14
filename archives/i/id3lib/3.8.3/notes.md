# id3lib 3.8.3 适配笔记

## 编译环境
- 构建系统: autotools（configure + make；autoconf 2.13 时代生成的脚本）
- 编译日期: 2026-10-09
- 编译器: clang / clang++ 15.0.4（OHOS SDK，hnp 工具链）
- 平台: aarch64-unknown-linux-ohos（HarmonyOS PC，原生编译）
- 依赖: zlib/1.3.1（制品仓静态二进制，shared=False）
- 源码: id3lib-3.8.3.tar.gz（SourceForge 官方源）
  sha256 = 2749cc3c0cd7280b299518b1ddf5a5bcfe2d1100614519b68702230e26c7d079

## 编译步骤

1. `init-build id3lib 3.8.3 --url=https://downloads.sourceforge.net/project/id3lib/id3lib/3.8.3/id3lib-3.8.3.tar.gz`
   （双轨展开：`~/tmp/builds/id3lib-3.8.3.orig` / `.work`，256 文件基线指纹）
2. 探索期 configure（等价参数；conan 配方中由 AutotoolsToolchain 注入 CC/CXX/CPPFLAGS/LDFLAGS）：
   `CC=clang CXX=clang++ CPPFLAGS=-I<zlib include> LDFLAGS=-L<zlib lib> ./configure --prefix=<prefix>`
3. `make -j1` → `src/.libs/libid3.a` + `examples/{id3info,id3convert,id3tag,id3cp}`
4. `make install DESTDIR=<staging>` → lib/ + include/ + bin/ 完整
5. 安全弹窗（R7）：四个 CLI 逐一执行 `--version` 触发确认框后正常
6. `make check`：9 个 `check_PROGRAMS` 全部编译通过（上游无 `TESTS=`，不自动执行任何测试）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 补丁 |
|---|------|------|----------|------|
| 1 | config.guess 无法识别 HarmonyOS | 2003 版脚本无该分支（`uname -s` = HarmonyOS） | 追加 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`（E007） | 0001 |
| 2 | config.sub 不识别 `aarch64-unknown-linux-ohos` | 同上 | maybe_os 白名单 + OS 白名单 + `-ohos*` 映射 三处（E072） | 0002 |
| 3 | configure 因缺 `iomanip.h` 致命报错 | `AC_CHECK_HEADERS(string iomanip.h, , AC_MSG_ERROR)`；现代 libc++ 无此头 | 从致命检查列表移除 `iomanip.h`（代码实际只用标准 `<iomanip>`） | 0003 / 0004 |
| 4 | `include/id3/id3lib_bitset` 使用 `<iostream.h>` | C++98 前弃用头 | 改 `<iostream>` | 0012 |
| 5 | main 首参非 int：`unsigned int argc`（demo_* 4 个）、`unsigned argc`（findeng/findstr） | C++ 标准要求 main 第一个参数为 `int` | 统一改 `int argc` | 0005-0010 |
| 6 | test_io.cpp：`main(size_t argc)` + `cin`/`hex`/`dec` 未限定 | 缺少 using 声明 + 非标准 main 签名 | `int argc` + `using std::cin/hex/dec` | 0011 |
| 7 | config.status 建临时目录 `Permission denied`（`$TMPDIR/csXXXXXX`） | HMDFS + `umask 077` + `mktemp -d`（E011） | `configure`/`zlib/configure` 内 `umask 077`→`022`（a52dec 0.7.4 先例） | 0003 / 0013 |
| 8 | 无 libz 链接时回退编译内嵌 zlib（1998 年代码） | 系统仅有 `libz.so.1`，无开发软链；`AC_CHECK_LIB(z,uncompress)` 失败 | 声明制品仓 `zlib/1.3.1`（R18/R26 静态），`HAVE_ZLIB=1`、`ID3_NEEDZLIB=false` | 无（配方层） |
| 10 | conan create 中 configure 以 `C preprocessor "/lib/cpp" fails sanity check` 致命退出 | OHOS profile `[buildenv]` 导出 `SHELL/CONFIG_SHELL=<hnp bash>`；autoconf 2.13 的 configure 会用 `$CONFIG_SHELL` 重新 exec 自身，而 hnp bash 在本环境 getcwd 失败（`job-working-directory: error retrieving current directory`）→ configure 内 `cd ..` 与相对路径 conftest 全部损坏（`fatal error: 'confdefs.h' file not found`）→ CPP 探测连锁失败（E386 类） | build() 手工运行 configure，命令前缀 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh CPP="<clang> -E" CXXCPP="<clang++ -E"`（路径取自 `tools.build:compiler_executables`，R33）；configure 参数从 `conanbuild.conf` 读取（cdo 2.6.3 / idutils 4.6 / id3v2 0.1.12 先例） | 无（配方层 build()） |
| 11 | [审计 R26] 4 个 CLI 实测 `NEEDED [libz.so]`（命中 SDK sysroot 共享库），与『静态 zlib/1.3.1』申报不符 | AutotoolsToolchain 不注入依赖 -I/-L；最终链接 `clang++ ... libid3.a -lz` 无 `-L`，`-lz` 落到 SDK sysroot `.../aarch64-linux-ohos/libz.so` | generate() 从 `self.dependencies["zlib"]` 注入 `-I/-L`（extra_cflags/cxxflags/ldflags，私有 package prefix）；build() 的 configure 前缀补 `CPPFLAGS=-I<zlib>`；重建后 4 个 bin `llvm-readelf -d` 不再出现 libz.so（id3v2/0.1.12 先例） | 无（配方层 generate()/build()） |
| 9 | findeng.cpp/findstr.cpp 第 5 行为混合 CRLF，补丁干跑失败 | refresh-patch 文本模式 difflib 无法表达 CRLF 上下文 | build() 先 `sed 's/\r$//'` 归一化再 apply patches（mp3val/0.1.8 先例） | 0009 / 0010 |

## 源码修改（13 个补丁，全部由 `refresh-patch --auto` 生成且 dry-run 通过）

| 补丁 | 文件 | 修改 |
|------|------|------|
| 0001-config.guess.patch | config.guess | 增加 HarmonyOS 分支（echo aarch64-unknown-linux-ohos; exit 0） |
| 0002-config.sub.patch | config.sub | linux-ohos 三元组支持（3 处） |
| 0003-configure.patch | configure | 移除 iomanip.h 致命检查；umask 077→022 |
| 0004-configure.in.patch | configure.in | 移除 iomanip.h 检查 |
| 0005-0008 | examples/demo_convert,copy,info,tag.cpp | `unsigned int argc` → `int argc` |
| 0009-0010 | examples/findeng,findstr.cpp | `unsigned argc` → `int argc` |
| 0011-examples-test_io.cpp.patch | examples/test_io.cpp | `size_t argc` → `int argc`；补 `using std::cin/hex/dec` |
| 0012-include-id3-id3lib_bitset.patch | include/id3/id3lib_bitset | `<iostream.h>` → `<iostream>` |
| 0013-zlib-configure.patch | zlib/configure | umask 077→022（内嵌 zlib 配置目录） |

## 依赖版本
- zlib/1.3.1（静态；显式 -I/-L 注入后 configure 走 HAVE_ZLIB，4 个 CLI 静态集成 libz.a，
  `llvm-readelf -d` NEEDED 无 libz.so）

## 配方层修复（无补丁，固化在 conanfile.py）

- **CONFIG_SHELL/CPP 显式覆盖**（问题 10）：build() 不再直接调用 `Autotools.configure()`，
  而是以 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh CPP="<clang> -E" CXXCPP="<clang++ -E"`
  命令前缀运行 configure；参数沿用 conan 生成的 `conanbuild.conf`（与 Autotools helper 同源）。
- **CRLF 归一化**（问题 9）：`apply_conandata_patches` 之前 `sed 's/\r$//'` 两个文件。
- **zlib 预编译依赖 + 显式注入**（问题 8/11）：`requirements()` 声明 `zlib/1.3.1`；
  generate()/build() 从 `self.dependencies["zlib"]` 注入 `-I<zlib>/include`、`-L<zlib>/lib`
  （私有 package prefix，R33/R49），使 configure 探测与 4 个 CLI 链接命中制品仓 `libz.a`（R26）。
- `make`/`make check`/`install` 仍走 Autotools helper（make 使用 /bin/sh，不受 hnp bash 影响）。

## 验证结果

```text
make -j1            rc=0（libid3.a + 4 个 CLI）
make check          rc=0（9/9 check_PROGRAMS 编译通过；无 TESTS= 不执行）
make install        rc=0（DESTDIR staging：lib/libid3.a + include/ + bin/ 4 个）
CLI --version       id3info 3.8.3 / id3cp 3.8.3 / id3tag rc=0 / id3convert rc=0
llvm-readelf -d     4 个 bin NEEDED 无 libz.so（libz.a 静态集成；仅 libc++_shared/libc）
```

实跑证据（scratch 目录，避免污染源码树）见 `reports/test-report.md`：
testunicode / testcompression / testpic / testio / id3simple / findeng / findstr
rc=0；`id3tag --artist=... --song=...` 后 `id3info` 读回 TPE1/TIT2 断言通过。

## 上游测试清点（R51）

- **无正式测试套件**：`examples/Makefile.am` 中无 `TESTS=`（证据：`grep -n "TESTS" examples/Makefile.am` 输出为空）；
  `make check` 仅编译 `check_PROGRAMS`，不运行任何测试程序。
- `check_PROGRAMS` 共 9 个：id3simple / testpic / testunicode / testcompression /
  testremove / testio / get_pic / findstr / findeng —— **9/9 编译通过**。
- `bin_PROGRAMS` 4 个（安装）：id3info / id3convert / id3tag / id3cp。
- 结论：examples/ 为演示与临时程序，**不能视为测试套件**；本包实质功能验证由
  `test_package/`（R34/R53）承担。

## 注意事项
- **build() 必须先做 CRLF 归一化**（examples/findeng.cpp、examples/findstr.cpp）再
  `apply_conandata_patches`，否则 0009/0010 补丁无法命中第 5 行上下文。
- 内嵌 zlib（1998）不构建；依赖制品仓 zlib/1.3.1（R26 静态）。
- 2003 年代码，编译保留 `-Wall` 警告（无害）。
- 鸿蒙 `uname -s` = `HarmonyOS`，是指纹三元组的来源。
- `libid3.a` 的 sha256 随 `ar` 成员 mtime 变化：复核请对照 **packaging tarball 成员**
  （当前 `28dc0942…254080`，与同次 W3 重建件一致）；跨构建哈希不同属 `ar` 可复现性特性，非产物差异。
- 4 个 CLI 的 zlib 为**静态**（R26）：`llvm-readelf -d` NEEDED 仅 libc++_shared.so/libc.so。
---

**编译结束**: 2026-10-09 10:42
**最终状态**: built
