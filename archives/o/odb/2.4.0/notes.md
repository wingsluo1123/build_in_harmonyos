# ODB 2.4.0 — OHOS 适配记录

## 包结构
ODB 2.4.0（Code Synthesis，2015）官方以三个源码包发布（
https://codesynthesis.com/download/odb/2.4/ ，sha1/sha256 已按官方 .sha1 与
本地计算双校验）：

| 组件 | 内容 | 依赖 |
|---|---|---|
| odb-2.4.0 | ODB 编译器（代码生成器 + 驱动，bin/odb） | libcutl/1.11.0 |
| libodb-2.4.0 | 核心运行时库 | 无 |
| libodb-sqlite-2.4.0 | SQLite 后端运行时库 | libodb + sqlite3/3.49.1 |

三者合并打包为单个 conan 包 `odb/2.4.0`（bin/odb、lib/libodb.*、
lib/libodb-sqlite.*、include/odb/**、lib/pkgconfig/*.pc）。

## 范围决策
- 仅含 SQLite 后端：MySQL/PostgreSQL/Oracle/MSSQL 后端的客户端库
  （libpq、libmysqlclient 等）未在 ohpcd 发布，按「依赖未发布即放弃该部分」
  处理，不做。
- 编译器（bin/odb）为 aarch64 OHOS 目标产物：在目标设备上可驱动
  目标工具链完成代码生成；host 侧（开发机）代码生成需要另行提供
  开发机版 odb（上游本身也区分构建），超出本包范围，记录为已知限制。
- 2015 代码库使用 C++03/11 时代特性（std::auto_ptr、动态异常说明
  throw (type)），C++17 已移除。配方钉住 compiler.cppstd=14，
  **下游消费 ODB 头文件须使用 C++14 或更低**（test_package 同样钉 14）。
  上游 ODB 2.5+ 才完成 C++17 迁移，2.4.0 无官方修法。

## 补丁（均 portability，最小改动，.am 与随附 Makefile.in 成对修改）
0. 说明：tarball 附带预生成 Makefile.in；OHOS CI 构建环境无
   aclocal/automake/perl（juise 先例实证），无法重生成，故补丁同时覆盖
   源 .am 与随附 .in，保持一致。
1. `0001-config-guess-sub-ohos.patch`
   - config.sub（autoconf 2.69）不认 `aarch64-linux-ohos`
     （实测 `sh config.sub aarch64-linux-ohos` → "system `ohos' not
     recognized"）：在 maybe_os 列表与最终校验列表各加 ohos 项。
   - config.guess 增加 HarmonyOS 宿主猜测（对齐仓库 juise 先例补丁）。
2. `0002-drop-version-file.patch`
   - 源码根目录的 `version` 纯文本文件（内容 "2.4.0"）在
     `-I$(top_srcdir)` 下遮蔽 C++ 标准库 `<version>` 头
     （OHOS libc++ 的 `<cstddef>` 会 `#include <version>`），
     导致 "expected unqualified-id" 编译错误。
   - 该文件仅 `make dist`（dist_doc_DATA）使用，`make all/install` 不引用；
     删除文件并从 dist_doc_DATA 移除条目。
3. `0003-disable-gcc-plugin.patch`
   - 编译器组件无条件构建 GCC 插件（plugin_LTLIBRARIES = odb.la），
     其源码 include GCC 内部头（gcc-plugin.h、gmp.h、tree.h、real.h），
     OHOS clang 工具链无这些头，无法构建。
   - 移除插件构建目标与 uninstall 钩子；驱动（bin/odb）本体不依赖插件。
4. `0004-stdio-filebuf-libcxx.patch`
   - 驱动 odb.cxx 使用 libstdc++ 专属 `__gnu_cxx::stdio_filebuf`
     （4 处，单方向：写子进程 stdin / 读 stdout、stderr）。
   - 以最小 streambuf 兼容层 `odb/stdio_filebuf.hxx` 替代
     （underflow/overflow/sync over FILE*），行为等价。

## 构建要点
- 三组件各自在 build 目录独立 configure（in-source make），
  `--host=aarch64-linux-ohos`（OHOS）、`--disable-shared --enable-static`。
- libodb-sqlite 链接本配方内先构建的 libodb 组件：
  `--with-libodb=<build>/libodb-2.4.0` + 工具链 LDFLAGS 注入
  `-L<build>/libodb-2.4.0`（conan 依赖旗标不覆盖同配方组件）。
- libcutl 发布包把头文件放在 `include/libcutl/`，而 odb 编译器
  `#include <cutl/...>`：build 目录内建 cutl-include/cutl 符号链接
  桥接，经 `--with-libcutl` 传入（LIBCUTL 宏由此派生 -I）。
- configure 中 GCC 插件头探测（`#include <bversion.h>` +
  BUILDING_GCC_MAJOR）为无条件检查、无命令行开关，OHOS clang 工具链
  无 GCC 插件开发头：在 cutl-include 目录放 bversion.h 桩满足该残留
  探测（插件本体已由补丁 0003 移除，桩不安装、驱动不使用）。
  注意：GCC_PLUGIN 宏（configure.ac 第 29 行）早于 LIBCUTL 宏
  （第 141 行）执行，`--with-libcutl` 的 -I 在探测时点尚未生效，
  故 shim 目录在编译器组件的 configure 命令上以内联环境变量方式
  前置到 CPPFLAGS（`CPPFLAGS="-I<shim> $CPPFLAGS" ./configure ...`）。
- `--with-gxx-name=no`：不内嵌宿主 g++ 路径（OHOS 目标无 g++）；
  `--with-gcc-plugin-dir=no`：交叉构建不探测插件目录。

## 测试
- 上游测试套件（各组件 make check）需要可达的数据库服务器与
  完整 GCC 开发工具链，CI 环境不具备，未执行（MANIFEST 已声明）。
- test_package：消费者级 C++ 程序，构造 odb::sqlite::database(":memory:")
  打开内存库，在 odb::transaction 内经 odb::database::execute() 建表、
  插入，再经事务连接的 sqlite3 原生句柄
  （transaction.connection() → odb::sqlite::connection::handle()，
  sqlite3_prepare_v2/step/column_text）回读并断言往返值；
  链接链路覆盖 libodb-sqlite → libodb → sqlite3。
- 测试在目标侧执行：CI 工作机为真实 OHOS 设备（原生 aarch64 运行），
  本地 WSL 经 qemu-aarch64（binfmt 透明模拟）运行；不因交叉目标跳过
  ——跳过会使 L1e 负例（R34）把测试判为假测试。
- cppstd 钉 14（C++03/11 时代代码库）；MANIFEST.yml 断言数 6。
- 已知坑：下载型 registry 依赖（sqlite3/3.49.1、libcutl/1.11.0）的
  CMakeDeps 不导出 include 目录（生成目标 INTERFACE_INCLUDE_DIRECTORIES
  为空），而 <odb/sqlite/database.hxx> 直接 #include <sqlite3.h>。
  test_package 经 CMakeToolchain（变量 SQLITE3_INCLUDE_DIR）显式注入
  依赖包 include 目录（与 odb 配方自身访问依赖的 package_folder
  模式一致），CMakeLists 挂到测试目标上。

## 产物证据（本地 WSL 交叉编译，arm64 / OHOS 工具链）
- 构建命令：`conan create archives/o/odb/2.4.0 -pr:h=ohos-aarch64-wsl
  -pr:b=ohos-aarch64-wsl --build=missing`；完整门禁
  ci/conan/build_and_test.sh（tmux 会话 odb-gate，
  日志 /root/ohpcd-work/odb-gate-r2.log）。
- 门禁结果（2026-10-17 第 4 轮）：
  L0_RESULT=pass（L0k: commands.json valid (type=tool)）；
  L1_RESULT=pass: test_package executed（RUN: ./test_odb →
  "odb sqlite roundtrip OK (ODB_VERSION=2.4)"，qemu 下执行）；
  L1e: Negative test confirmed；L2_RESULT=pass: odb --version OK；
  L4_RESULT=warn: dangerous functions in patches（非阻断，可接受）；
  L5_RESULT=pass: bin/ has content；
  Build Summary: 1/1，100%，"All packages built and tested successfully ✅"。
- 手工三段式 L1e（T425 补充证据：本地门禁 L1e 用 profile 文件路径
  ci/conan/profiles/ohos-aarch64-wsl，该文件本地不存在、属空转；改用
  profile 名称 -pr ohos-aarch64-wsl 手工复现负例）：
  基线通过（roundtrip OK）→ 破坏包 lib/ 后 conan test 在 configure
  阶段硬失败（find_library 找不到 odb-sqlite，rc=1）→ 恢复后通过；
  S1=0 S2=1 S3=0，L1E_MANUAL=PASS
  （日志 /root/ohpcd-work/odb-l1e-manual.log）。

## CI 修复记录（build #97493 → feat/odb-2.4.0）
- 现象：CI #97493 conan-build-test 步骤唯一失败
  `[fail] L0k: CLI tool detected but commands.json missing (R38)`，
  L1–L5 blocked_by_L0。
- 根因：配方 cpp_info.bindirs=["bin"] 且产物含 bin/odb（detect_bindirs
  命中），触发 L0k 软件级 CLI 工具声明检查（R38），但 archives/o/odb/
  软件级目录缺 commands.json。
- 修复 1（71304e30fcb）：新增软件级 archives/o/odb/commands.json
  （type=tool，name odb，versions 含 2.4.0，binary=false 未做设备级验证）。
- 发现 2：原提交的 test_package 在目标 OS 非 Linux 时跳过 build/test；
  CI 工作机为真实 OHOS 设备、原生执行测试，跳过会被 L1e 判为
  假测试（R34）而 CI 红。
- 修复 2（9f2b646650e）：test.cpp 重写为真实 SQLite 往返测试（无跳过
  分支），conanfile 去掉 OS 条件跳过，MANIFEST 断言数对齐（1→6）。
- 发现 3：下载型依赖 CMakeDeps include 缺失（见「测试」节已知坑），
  test_odb 编译报 `fatal error: 'sqlite3.h' file not found`。
- 修复 3（7b8eebb3750）：SQLITE3_INCLUDE_DIR 注入（见「测试」节）。
- 本地全量门禁与手工三段式 L1e 证据见「产物证据」节；随后推送
  feat/odb-2.4.0 并触发 /rebuild。
