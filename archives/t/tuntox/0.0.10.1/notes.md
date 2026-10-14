# tuntox 0.0.10.1 适配笔记

## 编译环境
- 构建系统: makefile（tuntox 主 Makefile）+ cmake（vendor 的 c-toxcore）
- 编译日期: 2026-10-12
- 编译器: clang/clang++（OHOS SDK，/data/service/hnp/bin）
- 状态: building（真机 rule4 预检待跑）

## 软件概述

tuntox 是基于 Tox 协议(Toxcore) 的 TCP 端口转发工具：在服务端把本地端口
开放给远端，客户端通过 Tox ID 安全地把本地 TCP 端口或 stdin/stdout
（SSH ProxyCommand 模式）转发到服务端。构建产物是 `tuntox` 应用（源码
仅 main.c 等直接链接 c-toxcore，不对外提供库）。

## 依赖链与 vendor 策略

```
tuntox ──(pkg-config toxcore + #include <tox/tox.h>)──> c-toxcore v0.2.19
    └──> libsodium 1.0.22（c-toxcore core 唯一硬依赖）
```

c-toxcore 未在 build_in_harmonyos 仓库单独适配（仓库仅提供其依赖
libsodium/1.0.22、libevent/2.1.13）。遵循"一个 PR 只含一个库"且规避
missing_dependency 门禁，配方在 `source()` 内联下载 c-toxcore v0.2.19
（2022-05 发布，与 tuntox 0.0.10.1 的 2022-06 同期稳定），`build()` 先用
`CMakeToolchain` 静态构建其核心并安装到私有 prefix，再把 tuntox 链接其上，
全程不污染全局/共享目录（R49）。

c-toxcore 的 toxav 需 opus/vpx、bootstrapd 需 libconfig：全部用 CMake 开关
（`-DBUILD_TOXAV=OFF -DBOOTSTRAP_DAEMON=OFF -DDHT_BOOTSTRAP=OFF -DAUTOTEST=OFF
-DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=OFF`）关闭。core 不需 libevent
（仅 esp32 docker 示例引用）。因此 toxcore 核心仅需 libsodium，由
`PkgConfigDeps` 生成的 `libsodium.pc` 经 PKG_CONFIG_PATH 供
`pkg_search_module(LIBSODIUM libsodium ...)` 检索。

## 编译步骤

1. `source()`：下载 tuntox 0.0.10.1 归档 + c-toxcore v0.2.19 归档
   （strip_root 到 `src/` 与 `src/third_party/toxcore/`）。
2. `generate()`：`PkgConfigDeps`（产 libsodium.pc）+ `CMakeToolchain`
   （产 conan_toolchain.cmake，OHOS 适配版 conan 自动映射 HarmonyOS）。
3. `build()`：
   a. `cmake -S third_party/toxcore -B toxcore-build`（静态核心，PKG_CONFIG_PATH
      指向 generators_folder 找 libsodium）；`make -j1`（E074: HMDFS jobserver
      fifo EPERM）；`cmake --install` 到私有 `toxprefix/`。
   b. 手写 `toxprefix/lib/pkgconfig/toxcore.pc`（`Libs: -L${libdir} -ltoxcore
      -lsodium -lm -lrt` 全量静态链接行）。
   c. `make tuntox_nostatic`，命令行覆盖 `CC=clang CFLAGS="-O2 -I<toxprefix>/include"`
      `DSO_LDFLAGS="-g -pthread -lm -lrt -L<toxprefix>/lib -ltoxcore -lsodium -lrt"`。
4. `package()`：复制 `tuntox_nostatic` → `bin/tuntox`，LICENSE → `licenses/`，
   上游测试审计 JSON → `res/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 依赖 c-toxcore 不在仓库 | tuntox 为 toxcore 之上的应用 | 配方内联 vendor c-toxcore v0.2.19，先静态构建核心再链接 |
| 2 | toxcore 需 pkg-config 找 libsodium | CMake 依赖发现机制 | PkgConfigDeps 产 libsodium.pc + PKG_CONFIG_PATH 指向 generators_folder |
| 3 | tuntox Makefile 硬编码 gcc/-static/pkg-config | 上游 Makefile 不面向交叉编译 | `make tuntox_nostatic`（去掉 -static），make 命令行覆盖 CC/CFLAGS/DSO_LDFLAGS（command-line 变量使 makefile `+=` 失效，完全可控） |
| 4 | `-static` 不可用 | OHOS musl 无静态 libc，且静态破坏 DNS 解析 | 构建 tuntox_nostatic 目标 |
| 5 | tox_bootstrap.h 可能触发联网生成 | `make` 规则依赖 generate_tox_bootstrap.py（requests+jinja2+联网） | 发布包已自带 tox_bootstrap.h，仅当其不存在才重新生成，故不会触发 |
| 6 | Makefile `install` 用 `install -C` | 非标准、OHOS 上不可靠 | package() 直接 copy 构建产物，不走 make install |
| 7 | toxcore configure 报 `Cannot find source file: third_party/cmp/cmp.c` | c-toxcore 的 git 子模块 `third_party/cmp`（github.com/camgunz/cmp）未被 GitHub 源码 tarball 打包 | conandata.yml 新增 `cmp` 源（c-toxcore v0.2.19 锁定提交 643e6a62），source() 解包到 `third_party/toxcore/third_party/cmp` |
| 8 | toxcore 编译 LAN_discovery.c 报 `redefinition of 'sockaddr_storage'`（linux/socket.h vs sys/socket.h） | c-toxcore 在已含 `<sys/socket.h>` 的情况下再 include `<linux/if.h>`，后者经 `<linux/socket.h>` 重复定义 sockaddr_storage（musl/OHOS 的 `<sys/socket.h>` 已定义） | conandata.yml patches 新增补丁：LAN_discovery.c 把 `<linux/if.h>` 改为 POSIX 的 `<net/if.h>`（不再拉入内核 linux/socket.h）；对 glibc/musl 均正确，非 OHOS 专属宏 |
| 9 | 换 `<net/if.h>` 后 LAN_discovery.c 报 `array has incomplete element type 'struct ifreq' / variable has incomplete type 'struct ifconf'` | musl/OHOS 的 `<net/if.h>` 仅在定义 `_GNU_SOURCE`/`_BSD_SOURCE` 时暴露 `struct ifreq`/`struct ifconf`（`-std=gnu99` 不会自动定义 `_GNU_SOURCE`） | conanfile 在 toxcore 的 CMake 配置命令注入 `-DCMAKE_C_FLAGS="-D_GNU_SOURCE" -DCMAKE_CXX_FLAGS="-D_GNU_SOURCE"`，显式启用特性宏使 `struct ifreq/ifconf` 可用 |
| 10 | 真机 rule4 预检 `source()` 下载 github.com 源归档连接超时（ConnectTimeoutError，github.com 直连不可达） | worker 网络无法直连 github.com | conandata.yml 三个 GitHub 源码 url（sources/toxcore/cmp）改写为有序 URL 列表：`https://gh-proxy.com/<官方URL>` 镜像排前，官方 github.com 保留末尾作回退；镜像与官方归档一致，sha256 校验不变（复用仓库 build_and_test.sh 维护的 GitHub 镜像映射） |

## 依赖版本

- tuntox 0.0.10.1（官方源码）
- c-toxcore v0.2.19（vendor 内联，官方源码）
- cmp（c-toxcore 子模块，锁定提交 643e6a62，vendor 内联）
- libsodium 1.0.22（Conan 包）

## 上游测试清点（R51 / MANIFEST 审计）

- **上游无任何自动化测试**：`Makefile` 无 `check`/`test` 目标
  （目标仅 all/FORCE/tuntox/tuntox_nostatic/clean/install）；源码树无
  `tests/`、`test/` 目录；`.travis.yml` 的 `make check` 指 libsodium 而非
  tuntox。发布包 `tox_bootstrap.h`/`gitversion.h` 为生成数据非测试。
- 因此 `upstream_tests_exist: false`，`upstream_test_total: 0`，由
  test_package 做消费者视角真实功能验证（`tuntox -h` → print_version →
  tox_version_major/minor/patch 真实 toxcore API 调用）。

## 验证结果

- 真机 rule4 预检待 HMBS 执行（本轮仅完成工作树，不本地跑 conan）。
- test_package 预期：`tuntox -h` 打印 help（stderr）并 exit 1，证明二进制可
  运行、toxcore 正确链接。

## 注意事项

- c-toxcore 构建与 tuntox 链接均在 `build()` 内完成，所用工具
  （cmake/make/clang）经 profile [buildenv] 与 HMBS_CMAKE/HMBS_MAKE 注入，
  未裸用 shell 环境变量（R33）。
- `-j1` 贯穿（E074）。
- `toxprefix` 为 build_folder 下的私有 prefix（R49），编译/链接标志全文
  指向它，不注入共享目录。

## 真机预检失败 #11：链接 tuntox_nostatic 报 `unable to find library -lsodium`（rule4）
- **现象**：`make tuntox_nostatic` 链接阶段 `ld.lld: error: unable to find library -lsodium`，
  make 退出码 1 → conan create 失败。上游测试 0/0/0。
- **根因**：tuntox 的链接行 `DSO_LDFLAGS` 中给出了 `-ltoxcore -lsodium -lrt`，
  但 `-L` 只有 `toxprefix/lib`（toxcore 私有安装目录）；libsodium 的真实静态归档
  位于其 Conan 包目录，不在 `-L` 搜索路径内，故 ld 找不到 `-lsodium`。
- **修复**：build() 中从 `self.dependencies["libsodium"].cpp_info.libdirs` 收集
  libsodium 的真实包 libdir（相对路径拼接 package_folder），生成 `-L<sodium_libdir>`
  追加进 `dso_ldflags` 与手写 `toxcore.pc` 的 Libs 行。

## 真机预检失败 #13：test_package 前两个 `-h` 断言仍 FAIL（改用 `/bin/sh` 后未解决，rule4 evidence）
- **现象（真机 preflight）**：#12 把 shell 从 HNP bash 换成 `/bin/sh` 并改用绝对路径、cd 到
  TMPDIR 后，conan create 在 test() 阶段仍失败：
  - `[test] tuntox -h runs and prints usage` → `FAIL: help banner missing`；
    `[test] tuntox -h help lists Options` → `FAIL: options missing`；
  - 仅 `[test] tuntox ELF is aarch64 (armv8)` PASS（od 读文件字节，不经 shell exec）；
  - HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,...,"discovered":3,"passedCount":1}。
- **根因（OHOS 打包 ELF 调用方式，同 wwwoffle/2.9j）**：#12 误判为 [shell_getcwd]，
  把 shell 从 bash 换成了 `/bin/sh`（mksh/toybox）。但 OHOS 上打包后的 ELF 经 `sh` 无法
  直接运行——与 wwwoffle 完全一致（"wwwoffle: inaccessible or not found"，
  问题出在调用方式而非文件本身：copy() 已用 os.replace 保留可执行位，ELF aarch64 校验通过）。
  于是 `"$TUNTOX" -h 2>&1` 捕获到的 content 为空/非预期，前两条 grep 断言失败。
- **修复（复用仓库已验证范式 templates/test_package-executable / keychain / wwwoffle）**：
  1. `test_package/conanfile.py test()`：shell 改用
     `os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/data/service/hnp/bin/bash"`
     （CONFIG_SHELL 默认即 HNP bash；HMBS 只注入 SHELL=/bin/sh，故必须优先 CONFIG_SHELL），
     以 bash 执行 test.sh 并以绝对路径传入打包二进制；cwd 仍用 HMBS TMPDIR 规避 getcwd。
  2. `test_package/test.sh`：shebang 改 `#!/data/service/hnp/bin/bash`（POSIX `set -u` 保留、
     `echo|grep` 改 `printf|grep` 更稳）；开头 `cd "$TMPDIR"` 规避 HMFS/HMDFS cwd；
     以绝对路径直接执行 `"$TUNTOX" -h`；新增 `printf '[debug] help_out=%s'` 供下次预检取证。
  3. 断言逻辑、3 条用例数、HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT 标记口径不变。
- **经验承接**：[经验 1] OHOS 上 test_package 用 sh 无法运行打包 ELF，改用 bash + 绝对路径
  （wwwoffle/2.9j 成功 1 次）。#12 的 `/bin/sh` 改动方向相反，本轮纠正为 bash + 绝对路径。
- **恒等式自检**：discovered=3；期望 passed=3、failed=0；passed+failed==executed==3、
  executed+skipped=3<=discovered=3。若成功则缺口 0，无需 gaps。

## 真机预检失败 #14：tuntox 运行时动态依赖 libtoxcore.so 导致全部 tox_* 符号无（rule4 evidence / [stale_runtime_library]）
- **现象（真机 preflight，#13 改 bash 后 debug 输出暴露真相）**：改用 bash+绝对路径后 `tuntox -h`
  仍无 help 输出，test.sh 新增的 `[debug] help_out=` 打印：
  ```
  Error loading shared library libtoxcore.so: (needed by .../p/bin/tuntox)
  Error relocating .../p/bin/tuntox: tox_callback_friend_lossless_packet: symbol not found
  ...（tox_friend_* / tox_version_* / tox_new / tox_kill 等全部 tox_* 符号 symbol not found）
  ```
  即二进制对 `libtoxcore.so` 有运行时动态依赖，OHOS loader 加载系统旧版 `libtoxcore.so`，
  符号集不对 → reloc 全失败 → 进程启动即报错、无 help 输出。这正是 HMBS 平台诊断
  `[stale_runtime_library]`：测试进程加载了系统旧动态库而不是当前构建产物。
- **根因**：c-toxcore 用自己一套 CMake 选项控制共享/静态库：
  `cmake/ModulePackage.cmake` 里 `option(ENABLE_SHARED ... ON)`、`option(ENABLE_STATIC ... ON)`，
  **默认同时开启**；`-DBUILD_SHARED_LIBS=OFF`（CMake 通用变量）对 c-toxcore 无效。
  于是 c-toxcore 同时产出 `libtoxcore.so`（toxcore_shared，OUTPUT_NAME toxcore）与
  `libtoxcore.a`（toxcore_static，OUTPUT_NAME toxcore）。tuntox 链接 `-ltoxcore` 时
  链接器挑中共享库 file → 生成对 `libtoxcore.so` 的动态依赖。设计本意是静态链接
  toxcore/libsodium（notes 开头"静态核心仅需 libsodium"），实际却变成动态链接。
- **修复（conanfile.py build()）**：
  1. toxcore CMake 配置新增 `-DENABLE_SHARED=OFF -DENABLE_STATIC=ON`，只构建并安装
     `libtoxcore.a`（静态归档，仍以 OUTPUT_NAME=toxcore 命名），消除 `libtoxcore.so`，
     使 tuntox 的 `-ltoxcore` 解析到静态归档。保留原 `-DBUILD_SHARED_LIBS=OFF`（无害）。
  2. 安装后防御性校验：toxprefix/lib 不得存在 `libtoxcore.so`，必须存在 `libtoxcore.a`，
     否则直接抛错 fail-fast。
  3. libsodium 无需改动：仓库 libsodium 1.0.22 配方以 `--disable-shared --enable-static`
     构建，只产 `libsodium.a`，`-lsodium` 已是静态。
- **效果预期**：tuntox 变成除 libc 外完全静态（toxcore+sodium 静态嵌入），运行期不再依赖
  `libtoxcore.so`，`tuntox -h` 应能正常 exec 并打印 help。这同时从根上消除
  `[stale_runtime_library]`（无共享库可加载），无需 LD_LIBRARY_PATH/LD_PRELOAD hack。
- **恒等式自检**：discovered=3；期望 passed=3、failed=0；passed+failed==executed==3、
  executed+skipped=3<=discovered=3。若成功则缺口 0，无需 gaps。

## CI 失败 #88334：配置期 try-compile 递归 make EAGAIN → "Check for working C compiler broken"（E346）
- **现象（CI build #88334，worker CI-030，logid 527593）**：conan create 在 build() 第一步
  （toxcore cmake 配置）即失败：
  ```
  -- Check for working C compiler: /data/service/hnp/bin/clang
  -- Check for working C compiler: /data/service/hnp/bin/clang - broken
  CMake Error at .../CMakeTestCCompiler.cmake:67 (message):
    The C compiler "/data/service/hnp/bin/clang" is not able to compile a simple test program.
      Run Build Command(s): .../cmake -E env VERBOSE=1 /data/service/hnp/bin/make -f Makefile cmTC_3a85c/fast
      /data/service/hnp/bin/make  -f CMakeFiles/cmTC_3a85c.dir/build.make CMakeFiles/cmTC_3a85c.dir/build
      make: /data/service/hnp/bin/make: Resource temporarily unavailable
      make: *** [Makefile:134: cmTC_3a85c/fast] Error 127
  -- Configuring incomplete, errors occurred!
  ```
  注意日志里 clang 命令**零输出**，失败发生在 make 递归启动阶段（不是 clang 前端报错）。
- **根因（知识图谱 E346 同型）**：CMake 默认 Unix Makefiles generator 的配置期
  try-compile 需要**递归调 make**（顶层 `make -f Makefile` → 子 `make -f
  CMakeFiles/cmTC_xxx.dir/build.make`）。该 worker 当时进程/fd 资源受限，子 make 的
  fork/exec 返回 EAGAIN（`Resource temporarily unavailable`）→ Error 127 → CMake 判定
  编译器不可用（"broken"），干净构建在配置阶段中止。这不是 clang 或源码问题，也不是
  配方依赖缺失；`-j1` 对递归 make 的 fork 压力无效（E074 只治 jobserver FIFO）。
- **修复（复用 E346 推荐方案 + 仓库已合入范式 gdal/3.9.2.3、ccmake/4.3.4、libogg/1.3.5.1、
  aws-lc-tools/5.2.0）**：
  1. `generate()`：CMakeToolchain 改为探测 ninja 后 `tc.generator = "Ninja"` 并
     `tc.variables["CMAKE_MAKE_PROGRAM"] = <ninja 绝对路径>`。
  2. `build()`：toxcore 配置命令追加 `-G Ninja -DCMAKE_MAKE_PROGRAM=<ninja>`；编译阶段
     由 `make -C ... -j1` 改为 `ninja -C ... -j1`（ninja 直接 exec 编译器，不经递归
     make/`/bin/sh`，配置期 try-compile 与编译阶段均规避）。
  3. `_resolve_ninja()`：HMBS_NINJA → `/data/service/hnp/bin/ninja` → `shutil.which("ninja")`
     显式探测（R33 合规，不用未定义 shell 变量）；探测不到则回退默认 generator，保持
     本地/非 OHOS 环境可构建。
- **恒等式自检**：discovered=3；期望 passed=3、failed=0；passed+failed==executed==3、
  executed+skipped=3<=discovered=3。若成功则缺口 0，无需 gaps。
