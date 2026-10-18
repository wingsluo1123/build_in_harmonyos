# rezound 0.13.1beta 适配笔记

ReZound —— X Window 系统上的图形化音频编辑器（FOX 工具包 GUI），上游
0.13.1beta（SourceForge）。本仓库首个归档版本。

## 编译环境

| 项 | 值 |
|----|----|
| 构建系统 | autotools（configure + make） |
| 编译日期 | 2026-10-14 |
| 编译器 | clang / clang++ 15（OHOS SDK，target aarch64-linux-ohos） |
| libc | libc++，C++17 |
| 构建类型 | Release |
| 状态 | built（conan create 全绿） |
| 制品 | `bin/rezound`（GUI 程序，无库/头文件） |

## 依赖

| 依赖 | 版本 | 必需性判定依据 |
|------|------|----------------|
| fox | 1.6.57 | **硬依赖**。`configure.ac:731-741` 用 `AX_PATH_GENERIC([fox],[1.1.0])`，失败分支为 `AC_MSG_ERROR`(:739)；且 `AC_OUTPUT` 无条件包含 `src/frontend_fox/Makefile`，无 `--without-fox` 之类的关断开关 |
| reswrap | （随 fox 提供） | **硬依赖**。`AC_PATH_PROG(RESWRAP, reswrap)`(:746) 失败即 `AC_MSG_ERROR`；make 阶段用它把图片/图标编成 C++ 资源 |
| boost | 1.91.0.1.3 | **硬依赖（仅头文件）**。`configure.ac:136-138` 探测 `boost/detail/atomic_count.hpp`，失败即 `AC_MSG_ERROR`；全树仅 `src/backend/CAtomicCounter.h` 使用 |
| libx11 / libxext / libxau / libxdmcp / libxcb / xtrans / xorgproto / libpng / libjpeg-turbo / libtiff / libwebp / zlib / bzip2 / xz / zstd | 见 manifest | 传递依赖，均由 fox/1.6.57 带入，制品仓已发布 |

**可选能力依赖**（报错均落在各自 `AC_ARG_ENABLE` 分支内，本次显式 `--disable-*`）：
OSS / PortAudio / JACK / PulseAudio / FFTW3 / LADSPA。另有 `soundtouch`
（`configure.ac:717`）失败仅 `AC_MSG_WARN`。这些都不构成依赖缺口。

> 依赖链 `rezound → fox → libx11/libxext → ...` 的上层 fox/1.6.57 已先行以
> 【依赖项】PR 单独导入（R36：依赖必须先发布再构建下游）。

## 编译步骤

探索阶段（真实报错驱动，直接改源码并 track-edit）：

```bash
./configure --prefix=$DEFAULT_PREFIX \
    --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
    --with-fox-prefix=$REZ_PREFIX/fox \
    --disable-oss --disable-portaudio --disable-jack --disable-pulse \
    --disable-fftw3 --disable-ladspa \
    CPPFLAGS="-I$REZ_PREFIX/include" LDFLAGS="-L$REZ_PREFIX/lib"
make -j1 && make install DESTDIR=$TEST_PREFIX
```

聚合前缀 `$REZ_PREFIX` 由脚本把图内 16 个包的
`include/`、`lib/`、`bin/` 汇到一棵树（HMDFS 上符号链接须先删后建）。

固化阶段（复现路径，`conan create` 一条命令）：

```bash
PATH=$HOME/tmp/bin:$PATH conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方内 `_stage_dependency_prefix()` 把依赖镜像成 `build_folder/deps-prefix`
（只建符号链接，不写共享前缀，R49/E524），并据此给 configure 传
`--with-fox-prefix`、给环境传 `CPPFLAGS`/`LDFLAGS`/`LD_LIBRARY_PATH`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.sub` 拒绝 `aarch64-linux-ohos` | 2008 年老版 config.sub 无该三元组 | `0001` 补丁在两个 case 分支加入 `linux-ohos*` |
| 2 | configure 造出的 `confXXXXXX` 目录不可读，后续探测莫名失败 | configure 内 `(umask 077 && mktemp -d)`，HMDFS 上 chmod 被忽略导致权限不可用（E011） | `0002` 补丁改 `umask 022` |
| 3 | `make` 报 `map<const string,...>` 用法错误 | 新版 libc++ 要求 map 键类型非 const（`like_type`/比较器不匹配） | `0003`/`0004` 补丁去掉 `const`（cpp 3 处 + h 1 处） |
| 4 | `TMemoryPipe.h`、`CTrigger.h` 报 `string` 未声明 | 新版 libc++ 不再经由其它头文件间接包含 `<string>` | `0005`/`0008` 补丁显式 `#include <string>` |
| 5 | 链接期 `anytype_to_string(vector<bool>)` 未定义 | `vector<bool>` 是特化，`operator[]` 返回代理引用而非 `bool&`，模板重载无法推导元素类型，回落到未定义的 primary template | `0007` 补丁补一个普通重载（精确匹配优先于模板） |
| 6 | `convert_images.sh` 报 ENOENT | shebang `#!/bin/bash` 在 OHOS 上不存在（bash 在 `/data/service/hnp/bin`），且脚本用 bash 专有 `function` 关键字 | `0006` 补丁改 `#!/usr/bin/env bash`。该步非构建必需（图片数据随源码发布），失败不影响产物 |
| 7 | `configure` 找不到 fox | `AX_PATH_GENERIC` 按 PATH 跑 `fox-config --version/--cflags/--libs`；而 fox 包安装的 `fox-config` 中 `prefix` 已硬固化为 `/`，`--prefix=` 只改脚本内部变量、`includedir`/`libdir` 早按 `/` 定型 | 配方建私有聚合前缀并把 `include/`、`lib/`、`bin/` 都汇进去；`--with-fox-prefix=<prefix>` 让宏在该前缀下找 `bin/fox-config`，同时直接用 `CPPFLAGS`/`LDFLAGS` 注入真实 `-I/-L` |
| 8 | `conan create` 报 `BadZipFile: File is not a zip file` | conan `get()` 用 `os.path.basename(url)` 推断落盘文件名并据此选解压器；SourceForge 项目页 URL 以 `/download` 结尾 → 文件名 `download` → 被当 zip | conandata 源改用 `https://downloads.sourceforge.net/project/rezound/ReZound/0.13.1beta/rezound-0.13.1beta.tar.gz`（官方下载端点，URL 以真实文件名结尾） |
| 9 | 本机 `patch` 是 toybox 0.8.12，对补丁静默 no-op 却返回 0 | 平台工具链缺陷 | 构建时 `PATH=$HOME/tmp/bin:$PATH` 前置 busybox patch shim；并由日志中 8 条 `Apply patch` 逐条核实补丁确实落地 |

## 源码修改

8 个补丁，全部为可移植性修复，**不含任何平台宏**（无 `__OHOS__` 守卫，
R8 口径）：

| 补丁 | 改动 | 平台专属 |
|------|------|----------|
| `0001-config-config.sub.patch` | 增加 `linux-ohos*` 三元组识别 | 是 |
| `0002-configure.patch` | `umask 077` → `022`（E011） | 是 |
| `0003-src-PoolFile-TPoolFile.cpp.patch` | `map<const string,...>` → `map<string,...>`（3 处） | 否 |
| `0004-src-PoolFile-TPoolFile.h.patch` | 同上（声明 1 处） | 否 |
| `0005-src-backend-CTrigger.h.patch` | 补 `#include <string>` | 否 |
| `0006-src-frontend_fox-convert_images.sh.patch` | shebang → `#!/usr/bin/env bash` | 是 |
| `0007-src-misc-CNestedDataFile-anytype.h.patch` | 补 `anytype_to_string(const vector<bool>&)` 普通重载 | 否 |
| `0008-src-misc-TMemoryPipe.h.patch` | 补 `#include <string>` | 否 |

补丁由 `refresh-patch --auto` 生成（per-file 差分），生成时已排除构建期
产生的 `src/frontend_fox/CFOXIcons.cpp` 与 `src/misc/CNestedDataFile/cfg.tab.cc`
两个生成文件（R6：只改源文件）。

## 上游测试清点（R51 三步法）

**结论：ReZound 0.13.1beta 上游不含任何测试。** 证据：

1. 源码树无 `tests/` 目录；`configure.ac` 与各 `Makefile.am` 无 `TESTS`、
   `check_PROGRAMS`、`check-local` 声明。
2. 实际执行 `make check` → `make: Nothing to be done for 'check'`（rc=0），
   零个测试被编译或运行。
3. 全树唯一的 check 目标是 `Makefile.am:74` 的 `distcleancheck:`，属 automake
   自动生成的清理目标，非测试。

因此无力可借上游测试，消费者验证由 `test_package/` 的鸿蒙特有用例承担。

## 验证结果

```bash
$ PATH=$HOME/tmp/bin:$PATH conan create . -pr:h=...ohos-aarch64 -pr:b=...ohos-aarch64 --build=missing
...
rezound/0.13.1beta: Apply patch (portability): 0001 config config.sub      # 8/8 全部落地
...
rezound/0.13.1beta: checking for fox-config... /.../deps-prefix/bin/fox-config
rezound/0.13.1beta: checking for reswrap... /.../deps-prefix/bin/reswrap
...
======== Testing the package: Running test() ========
✅ installed binary: .../bin/rezound
✅ installation prefix: ...
✅ ELF header OK: 64-bit AArch64
✅ packaged data files present: share/rezound/ (5 files)
✅ executed and initialised FOX; display probe failed as expected (rc=1)
🎉 rezound consumer test passed
CREATE_EXIT=0
```

- 补丁应用：8/8（日志逐条 `Apply patch` 核对）
- 产物清单（14 文件）：`bin/rezound`；`share/rezound/{presets.dat,menu.dat,
  key_bindings.dat,impulse_hall1.wav,icon_logo_32.gif}`；`doc/rezound/*` 6 个
- `test_package`（消费者用例，非 `--version` 空壳）：定位已安装二进制 →
  校验 ELF 头为 64 位 AArch64 → 校验 5 个数据文件 → 实跑二进制直到 FOX
  显示初始化失败，以此证明 `libFOX-1.6 → libX11/libXext → Xft/freetype/
  fontconfig` 整条动态依赖链在鸿蒙侧可解析（漏打包依赖时只会在这一步暴露）

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 配方（application 型；私有聚合前缀注入，无共享前缀写入） |
| `conandata.yml` | 官方源 URL + sha256 + 8 补丁声明 |
| `patches/*.patch` | 8 个可移植性补丁（无平台宏） |
| `test_package/` | 消费者测试（conanfile.py + test.sh + MANIFEST.yml） |
| `archives/r/rezound/commands.json` | 软件级命令声明（R38/PF8，`type: tool`） |

## 注意事项

- ReZound 是纯 GUI 程序，`main.cpp:77` 直接开显示，**无无头模式**；无 DISPLAY
  时以 `FXApp::openDisplay: unable to open display :0.0` 退出（rc=1）。测试
  以此作为"已成功走到 GUI 初始化"的正向判据，并在同一断言里排除动态加载器
  报错，避免把「缺库」误判为「预期失败」。
- `make -j1`：并行 make 会踩 HMDFS 的 jobserver fifo（R9）。
- 本机 `patch` 为 toybox no-op 版本，本地复现须 `PATH=$HOME/tmp/bin:$PATH`
  前置 busybox shim；CI 上无此问题（R6/工具链章节）。
---

**编译结束**: 2026-10-15 18:03
**最终状态**: built

---

## CI 失败归因与本地复验（2026-10-16）

PR 的 CI 连续 8 轮校验失败、0 通过，且跨 7 个不同 worker
（CI-011 / CI-013 / CI-020 / CI-026 / CI-030 / CI-031 / CI-034）。各轮真实报错一致指向
**worker 侧进程（fork）资源耗尽**，而非本包构建错误：

```
/data/service/hnp/bin/bash: fork: Resource temporarily unavailable
as_echo: can't fork - try again
```

`fork: Resource temporarily unavailable`（EAGAIN）表示 worker 已无法派生新进程，
configure 的自检（C preprocessor）随之被误判为失败。属环境资源类故障，与包内容无关。

**同窗口集群对照**（同时段其他 PR 的 CI 评论，含同期通过构建的日志）：
- #16163（积分赛）10:43 FAIL — 日志含同类 fork 报错
- #16080（积分赛）10:46 / 11:29 两次 FAIL — 同样含 fork 报错

→ 属集群级窗口，非本包特有、非单机瞬时。

**本地同命令全量复跑**（本机非 CI worker，2026-10-16 11:40→11:46）：

```bash
conan create archives/r/rezound/0.13.1beta \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=rezound/*
# RC=0
# rezound/0.13.1beta: Package '124a42ec4bc00edd85d1399d1b8f67ffbdfc7a14' created
```

构建 + test_package 全绿，日志中 **0 行 fork 噪声** → 配方自包含、可复现，
本机无进程资源压力。

**处置**：先排除配方因素（本地复跑全绿）→ 配方零改动 → 评论 `/rebuild` 换 worker 重跑。

**过程备注**：曾试验「fork 耗尽感知的有界重试」（包装 Autotools.run 捕获输出、仅命中
EAGAIN 特征时重试；故障注入测试 5/5 通过），但该变体在本机复跑时于
`frontend_fox/CMainWindow.cpp:29: #include <CPath.h>` 失败（回退后同机同命令不复现，
具体变量未隔离到）。该改动未采用，补丁仅留在任务工作区，未进入本归档。
