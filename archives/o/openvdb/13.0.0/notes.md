# openvdb 13.0.0 — 适配交付笔记（平台任务 #6637）

> 档案创建时间: 2026-09-21
> 认领人: Zmaomao　　分支: `feat/openvdb-13.0.0`　　平台任务 id: 6637
> 构建系统: CMake（上游要求 cmake ≥ 3.24、C++17）　　SDK: OHOS SDK v7.0 / clang 15.0.4
> 上游: https://codeload.github.com/AcademySoftwareFoundation/openvdb/tar.gz/refs/tags/v13.0.0
> sha256: `4d6a91df5f347017496fe8d22c3dbb7c4b5d7289499d4eb4d53dd2c75bb454e1`

## 一、任务背景

平台任务 #6637 要求适配 openvdb 13.0.0。制品仓已有 10.0.1 / 12.1.1，
**没有 13.0.0**（`conan list 'openvdb/*' -r=ohpcd` 复核，L0j/R37 通过）。
本目录以 `archives/o/openvdb/12.1.1` 的配方为基底演进。

上游分支 `feat/openvdb-13.0.0` 领取前**不存在**（领取时确认为 open/无 claimer）。

## 二、源码与校验

| 项 | 值 |
|---|---|
| 官方 URL | `https://codeload.github.com/AcademySoftwareFoundation/openvdb/tar.gz/refs/tags/v13.0.0` |
| 大小 | 4,891,966 字节 |
| sha256 | `4d6a91df5f347017496fe8d22c3dbb7c4b5d7289499d4eb4d53dd2c75bb454e1` |
| 确认方式 | **两次独立下载逐字节一致**（不同时间、经代理分别取），且该值在两次请求间稳定（GitHub tag 归档非动态重打包） |

`conandata.yml` 只写官方源（R39/PF7：不手写镜像前缀）。

## 三、OHOS 适配点

| # | 问题 | 处置 |
|---|---|---|
| 1 | 制品仓无 `blosc`（压缩后端） | `-DUSE_BLOSC=OFF`（注意变量名是 `USE_BLOSC`，不是 `OPENVDB_USE_BLOSC`） |
| 2 | OHOS 禁 mkfifo jobserver，`CMake.build()` 的并行封装会卡死 | 绕开封装，直接 `make -j1` |
| 3 | `OPENVDB_USE_DELAYED_LOADING` 默认 ON 会 `find_package(Boost)` 找 CMake config（conan 的 boost 包不提供） | `-DOPENVDB_USE_DELAYED_LOADING=OFF` |
| 4 | oneTBB 兼容：`openvdb/openvdb/thread/Threading.h` 依赖 `tbb/blocked_range.h` 间接带入 `tbb/version.h`（该文件注释明言），但 oneTBB 的 `blocked_range.h` 不再包含它 → `TBB_INTERFACE_VERSION` 未定义 → 走 `#else` 分支调用已被移除的 `tbb::task::self()` | 构建期在该 include 前插入 `#include <tbb/version.h>`（**上游 13.0.0 该注释与 include 行仍在**，与 12.1.1 同款处理） |
| 5 | 只需核心库 | 关 Python/Docs/Houdini/Maya/AX/Binaries/UnitTests；`OPENVDB_CORE_SHARED=OFF` 只建静态库 |

## 四、上游测试口径（不编造，方法可复现）

```
grep -rhoE '^\s*TEST(_F|_P)?\s*\(' openvdb/openvdb/unittest/*.cc | wc -l   →  738
```
上游 `openvdb/openvdb/unittest` 为 **gtest 套件：119 个 .cc / 738 个用例**，
链接为单一巨型二进制 `openvdb_test`（需 GTest）。

**归档构建保持 `OPENVDB_BUILD_UNITTESTS=OFF`**，理由（如实声明，非"跳过即通过"）：
- 该套件是单一巨型二进制，OHOS 上必须 `make -j1`，构建+运行成本超出 CI 单包预算；
- 既有归档 `openvdb/12.1.1` 亦为同一口径（其 MANIFEST 明确写"归档构建本身仍 UNITTESTS=OFF"）；
- 本适配**未修改上游任何测试源码**。

## 五、本地实测结果（★ 真实执行到哪一步就说到哪一步）

`conan create` 交叉编译（x86-64 → OHOS aarch64）：

```
conan create exit=0（库本体构建 + 打包成功）
test_package：
  PASS: libopenvdb 库文件存在（libopenvdb.a）
  PASS: include/openvdb/openvdb.h 存在
  PASS: libopenvdb 为 AArch64 ELF（纯 Python 解析 ELF 头 e_machine=183；有 readelf/llvm-readelf 时另打印附加证据）
  PASS: libopenvdb 导出关键 API 符号（4 个：GridBase / Grid< / tree::Tree< / math::Transform）
  PASS: 消费者编译+链接成功（libopenvdb 可用）
  ALL PASS (5 checks)
```

**本地无法执行消费者二进制的原因（实测，不是推断）**：
1. OHOS SDK **不随附**设备端 musl 动态加载器 `ld-musl-aarch64.so.1`；
2. 本机 QEMU（8.2.2）执行**动态** aarch64 OHOS 产物**必然段错误** —— 实测连
   `hello world`（`ohos-cc hello.c`）在 `QEMU_LD_PREFIX` / `qemu-aarch64-static -L`
   三种方式下都 `uncaught target signal 11`，而同一程序 `-static` 编译后正常输出；
3. 依赖 **tbb 的制品仓包只提供共享库**（`libtbb.so` / `libtbbmalloc*.so`，无 `libtbb.a`），
   因此消费者无法做成全静态二进制（`-static` 下 `ld.lld: unable to find library -ltbb` 实测）。
   → 消费者在**设备端原生构建（官方 CI aarch64 worker）**下动态链接并真实执行
   （`cross_building` 为 False 时 test_package 走原生分支，要求 exit 0 且输出含 `ALL PASS`）。

产物核对：

| 产物 | 结果 |
|---|---|
| `lib/libopenvdb.a` | `ELF64 / AArch64` ✅（纯 Python 读 e_machine），导出 422,365 个符号（`llvm-nm`/`nm -C --defined-only`；无该工具时回退为纯 Python 解析 `.symtab`） |
| `include/openvdb/openvdb.h` | 存在 ✅ |
| `lib/` 下无 `.so` | 与 `OPENVDB_CORE_SHARED=OFF` 一致（同 12.1.1 归档） |

### 五之二、CI 修复记录（2026-09-28）

首次 CI（PR !11763，构建 #62116）**库本体构建到 100% 成功**，但 `conan create` 在
test_package 阶段失败：

```
FileNotFoundError: [Errno 2] No such file or directory: 'readelf'
  File ".../test_package/test_openvdb.py", line 41, in run
ERROR: openvdb/13.0.0 (test package): Error in test() method
L1_RESULT=fail: conan create failed
```

根因：消费者驱动直接用 `readelf`/`nm` 做架构与符号判定，而 **CI worker（OHOS 环境）的 PATH
里没有这两个工具**（本机有，属环境差异漏检）。修复（本文件对应提交）：

1. **架构判定**改为**纯 Python 解析 ELF 头** `e_machine`（0xB7 = AArch64），.a 归档会自动
   跳过 ar 符号表成员并取首个 ELF 成员；`readelf` 仅作附加证据；
2. **INTERP 判定**改为**纯 Python 解析程序头**（`PT_INTERP`）；
3. **符号判定**优先用 `nm` 家族，工具按 **PATH → 编译器同目录（`shutil.which(clang++)`）
   → OHOS SDK/HNP 目录**自动定位（CI 上可命中 SDK 的 `llvm-nm`/`llvm-readelf`）；
   找不到时回退为**纯 Python 解析 `.symtab`** 并按 mangled 片段匹配
   （`7openvdb5v13_08GridBase` 等，实测 0.2s 命中全部 4 项）；
4. `run()` 捕获 `FileNotFoundError`/`OSError`/超时 → 降级为 rc=127 并打印 NOTE，**任何工具缺失
   都不会再让测试脚本异常退出**。

验证：本机正常环境 5/5 PASS；模拟「PATH 无 readelf/nm」时架构/符号判定已不再崩溃
（纯 Python 路径全命中）；同一驱动在 CI 原生构建下继续执行消费者二进制。

## 六、局限（如实说明）

1. **上游 738 个 gtest 用例本次未执行**（原因见第四节）；本地层给出的证据是
   真实编译 + 真实链接 + 符号/架构校验，不是"跑过全部单测"。
2. 本机是交叉编译，与官方 CI 的设备端原生编译不等价；**本地层不替代 CI**。
3. 消费者二进制的真实执行只在设备端 CI 触发（本地受 3 条硬限制，见第五节）。
4. `lib/` 只产出静态库（`OPENVDB_CORE_SHARED=OFF`），与既有 12.1.1 归档一致。

## 七、复用知识

- **oneTBB 与 openvdb 的 `Threading.h` 版本宏陷阱**：`tbb/blocked_range.h` 在 oneTBB
  中不再间接包含 `tbb/version.h`，导致 `TBB_INTERFACE_VERSION` 未定义并走已被移除的
  `tbb::task::self()` 分支。处置：在 include 前显式 `#include <tbb/version.h>`。
  （该结论沿用自 12.1.1 归档，本轮验证 13.0.0 仍适用。）
- **OHOS 上 `CMake.build()` 并行封装会卡死**（禁 mkfifo jobserver）→ 一律
  `self.run("make -j1", env="conanbuild")`。
- **本机不能跑动态 aarch64 产物**：判定方法 = 用 `ohos-cc` 编一个 hello world
  直接执行，段错误即证实；不要再把时间花在 `QEMU_LD_PREFIX`/`-L` 的尝试上
  （本机已实测三种方式全部失败）。
