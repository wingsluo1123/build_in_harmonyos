# vector-blf 2.4.2 适配笔记

## 软件信息

| 项 | 值 |
|---|---|
| 软件 | vector-blf（Vector Binary Log File support library） |
| 版本 | 2.4.2（上游 tag `v2.4.2`，commit `ea219cc508fadbea7f867f8bdecd595d253e0f1f`） |
| 上游 | https://github.com/Technica-Engineering/vector_blf |
| 许可 | GPL-3.0-or-later |
| 类型 | 共享库（上游 `add_library(Vector_BLF SHARED)` 硬编码，无 static 选项） |
| 用途 | 读写 Vector Informatik 的 BLF 日志文件（CAN/CAN-FD/LIN/MOST/FlexRay/Ethernet 事件流） |

## 编译环境

- 构建系统：CMake（上游 `cmake_minimum_required(VERSION 3.9)`）
- 编译日期：2026-10-15
- 编译器：OHOS SDK clang 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- 平台：HarmonyOS PC aarch64（native 编译，非交叉）
- Conan profile：`ci/conan/profiles/ohos-aarch64`（`os=OHOS`、`arch=armv8`、`compiler=clang`、`libcxx=libc++`）
- 状态：**built**（本 PR 阶段：配方验证通过、未上传；合并后由 release 流水线 `conan upload` 转 published）

## 编译步骤

```bash
# 1) 依赖：zlib（LogContainer 的 zlib 压缩容器）
conan install --requires=zlib/1.3.2.1 -pr:h=ci/conan/profiles/ohos-aarch64 \
              -pr:b=ci/conan/profiles/ohos-aarch64 -g CMakeDeps -g CMakeToolchain -of <deps>

# 2) 配置 + 编译（参数最少化：只关掉纯文档目标）
cmake -S <src> -B build \
      -DCMAKE_TOOLCHAIN_FILE=<deps>/conan_toolchain.cmake \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DOPTION_RUN_DOXYGEN=OFF
make -j4                     # 0 warning / 0 error（377 个源文件）

# 3) staging 安装 + 消费者冒烟
make install DESTDIR=$TEST_PREFIX
```

> 探索阶段未生成任何 `.patch`：上游源码在 OHOS SDK clang 15.0.4 上零警告直接编译成功，
> 不需要 `#include <cstdint>` 之类的 GCC-13 头文件补丁（Arch 的 `fix-build.patch`
> 在本次环境中无必要，故未引入）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(Doxygen REQUIRED)` 失败（环境无 doxygen） | `OPTION_RUN_DOXYGEN` 上游默认 **ON**，还会连带 `find_package(Graphviz)` | 配方 `generate()` 里 `tc.variables["OPTION_RUN_DOXYGEN"] = False`（纯文档目标，关掉不影响库本体） |
| 2 | 链接期 `cannot open Scrt1.o` / 找不到 `-lc` | 手工编译时误用了 PATH 里的 conan clang 包（`~/usr/local/bin/clang` → clang **22.1.8**，host 版、无 sysroot；与正文使用的 OHOS SDK clang **15.0.4** 是两个不同工具链） | 改用 OHOS SDK clang（`/data/service/hnp/bin/clang{,++}` = clang 15.0.4，即 conan profile 的 `tools.build:compiler_executables`，与 profile `compiler.version=15` 一致） |
| 3 | `Vector/BLF/config.h not found` | `config.h` / `vector_blf_export.h` 是 CMake `configure_file` + `generate_export_header` 的**生成头**，只存在于 build 树/安装树 | 消费者只用安装树的 `include/`（test_package 通过 `find_package` 获得） |
| 4 | 产物没有 `libVector_BLF.so.2` / SONAME | CMake 把 clang 默认三元组 `aarch64-unknown-linux-ohos` 识别为系统 `HarmonyOS`（无 `Platform/HarmonyOS.cmake`），该平台无 soname 支持 ⇒ 上游 `SOVERSION 2`/`VERSION 2.4.2` 不生效 | 平台行为，无需处理；扁平 `libVector_BLF.so` 反而避开 HMDFS 软链接限制。已记入 `manifest.yaml` 的 `knowledge_gained` |
| 5 | 跑上游测试时 `pthread_setcancelstate` 未声明 | OHOS musl 无该符号，Boost 1.84 头文件默认调用它 | 测试侧加 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（与 OHOS `boost-1.85` 配方一致，E099 关联）；**库本体不需要** |
| 6 | ⚠️ **首版配方静默链上宿主 zlib-ng**：`conan create` 产出的 `libVector_BLF.so` 出现 `NEEDED libz.so.1`（指向 `~/.harmonybrew/lib/libz.so.1.3.1.zlib-ng`），而手工编译时链的是 Conan 的静态 `libz.a` | 配方 `generate()` 只调了 `CMakeToolchain(self).generate()`，**漏调 `CMakeDeps(self).generate()`** ⇒ build 目录里没有 `ZLIBConfig.cmake`；上游又用 `find_package(ZLIB)` + 旧式 `${ZLIB_LIBRARIES}`，于是退到 CMake 内置 `FindZLIB` 模块模式，命中了构建机上的同名库 | `generate()` 里显式 `CMakeDeps(self).generate()`。修复后实测 `NEEDED` 只剩 `libc++_shared.so`/`libc.so`，zlib 符号静态内嵌（R26 满足）。已沉淀为知识草稿 `knowledge/drafts/E550-draft-F7C2.kv` |

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| zlib | 1.3.2.1 | `find_package(ZLIB REQUIRED)`；Conan 提供**静态** `libz.a`，被静态链入 `libVector_BLF.so`（`NEEDED` 仅 `libc++_shared.so`/`libc.so`），消费者无需额外运行库 |
| Threads | 系统 libc | `find_package(Threads REQUIRED)`，OHOS libc 自带 |
| Boost | （仅测试期） | 跑上游用例用头文件版 Boost.Test；**不是**本包的构建依赖 |

## 源码修改

无。上游源码零改动，`patches/` 为空。

## 验证结果

```bash
# conan create（G2 干净构建）——见 reports/conan-verify-report.md
conan create archives/v/vector-blf/2.4.2 -pr:h=ci/conan/profiles/ohos-aarch64 \
             -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable

# ① 消费者视角 L1（test_package，真实调用 API）
./test_vector_blf
# → vector-blf L1 test: 28007 checks, 0 failures

# ② 鸿蒙特有端到端消费者用例 + ③ 独立实现交叉校验（见下节）
./test_ohos_e2e <report> $TMPDIR/vector_blf_ohos_e2e.blf
./ref_blf_parser  $TMPDIR/vector_blf_ohos_e2e.blf <ref-report>
./test_compare    <report> <ref-report>
./ohos_dlopen_probe <pkg>/lib/libVector_BLF.so      # 不链接本库的加载探针
```

`conan create` 实测输出（三段全部通过）：

```
vector-blf L1 test: 28007 checks, 0 failures
OHOS e2e consumer: 6000 messages, 6000 objects, file=49714 B, uncompressed=288272 B,
                   digest=4964f8fbec9dd913, checks=14, failures=0
independent reference parser: 6000 objects, 4 containers, stream=288000 B,
                   trailing=0 B, digest=4964f8fbec9dd913
independent cross-check: 23 shared fields compared, 6 invariants enforced,
                   0 mismatches (digest=4964f8fbec9dd913)
ohos dlopen probe: loaded .../libVector_BLF.so, symbol=_ZN6Vector3BLF4File4readEv
```

L1 覆盖内容：写入 4000 条 CAN 报文（未压缩流 192240 B > 128 KiB 默认容器 ⇒ 多个
`LOG_CONTAINER`），关闭时走 zlib `compress2` 压缩；再读回逐字段校验
`channel/flags/dlc/id/data` 与 `objectSize == calculateObjectSize()`，并校验不存在的
文件通过 `is_open()` 报告。

压缩路径实证（探针程序，写盘后对比）：

```
uncompressedFileSize=192240   # 4000 条报文的未压缩流
on_disk_bytes=16024           # 落盘 BLF（zlib 压缩后）
```

## 鸿蒙特有测试（端到端消费者用例）

> 对应 PR 审查 rule12「鸿蒙特有测试」：不能为 0，且必须是**完整消费者用例**
> （端到端跑通功能/流程），纯断言集合不算。

`test_package/test_ohos_e2e.cpp` 是独立的可执行消费者用例（不是往断言文件里堆断言），
按四段式组织：

| 阶段 | 实现 |
|------|------|
| **构造输入** | 6000 条确定性 CAN 报文（`id=0x100+i`、`channel=1+i%4`、`flags=i%2`、`dlc=8`、`data[b]=(i*7+b)&0xFF`、`objectTimeStamp=i*1000`，无随机数）；写入 `$TMPDIR`（**OHOS 上 `/tmp` 只读，E002**，必须用 `$TMPDIR`/HMDFS） |
| **真实执行** | 经安装后的库写盘 → 关闭触发压缩（6000×48 B = 288000 B ⇒ **3 个数据容器 131072+131072+25856 + 关闭时 1 个空容器 = 4 个 `LOG_CONTAINER`，实测 compressionMethod 全为 2=zlib**）→ 重开并全量流式读回 → **第二遍读回** |
| **产出结果** | 确定性 `key=value` 报告（字段与取值均可复现；`lib:` 前缀为库侧私有项） |
| **校验内容** | 每条报文与构造公式逐项比对 + `objectSize==calculateObjectSize()` + 第二遍摘要一致；随后由 **独立实现** `ref_blf_parser`（**不链接 vector-blf**、不包含其头文件，自行解析 144 B 文件头 / LOG_CONTAINER 框架 + `objectSize%4` 填充 / zlib 载荷 / CAN_MESSAGE 字段）重新解码同一文件，`test_compare` 逐字段比对两侧报告并**强制 6 条不变量** |
| **平台可加载性** | 独立探针 `ohos_dlopen_probe`（**不链接 vector-blf**）在新进程里 `dlopen()` 产物并 `dlsym` 导出符号 —— 若在已链接本库的二进制里 dlopen，动态链接早在 `main()` 前就完成了映射，该检查将失去意义 |

实测：`23 shared fields compared, 6 invariants enforced, 0 mismatches`，两侧 `fields_digest`
完全一致（`4964f8fbec9dd913`）。强制的 6 条不变量（任一条不满足即 FAIL）：

1. 容器数 ≥ 2（确实跨多个日志容器）
2. 每个容器的 `compressionMethod == 2`（zlib 压缩路径真的被走到；方法 0 会被判失败）
3. 对象流无尾随字节（`ref:trailing_bytes == 0`）
4. 独立推算的未压缩大小（`144 + Σ(32+容器未压缩大小)`）== 库写出的文件头 `uncompressedFileSize`
5. 独立读出的文件大小 == 库侧 `file_size`
6. 库读回的报文数 == 写入数（`expected_messages`）

不变量已做**可伪证验证**：把参考报告的 `ref:compression_methods` 改成 `0,0,0,0`
或把 `ref:trailing_bytes` 改成 7，`test_compare` 立即以 1 退出并打印 `INVARIANT FAILED`。

> 独立实现的**参考值不是程序自输出回填**：它由另一套字节级解析器对同一份语料重新计算，
> 若库偷偷改了落盘格式、字段编码或统计口径，两侧报告会立即不一致。

## 上游测试三步法（R51）

### 1) 清点（申报表）

| 项 | 数值 | 依据 |
|---|---|---|
| 上游测试目录 | `src/Vector/BLF/tests/unittests/` | 上游源码树 |
| ctest 注册数 | **126** | `add_boost_test()` 调用数 = `add_test()` 注册数 = `test_*.cpp` 文件数 = 126 |
| 测试数据 | `events_from_binlog/test_*.blf`、`events_from_converter/*.blf`、`errors/*.blf`、`lobj/*` | 随源码 tarball 提供 |
| 其他测试目标 | `tests/cccc`、`tests/cppcheck`（静态分析，需 `OPTION_RUN_CCCC`/`OPTION_RUN_CPPCHECK`，默认 OFF） | 非功能测试 |

### 2) 运行方式（真机 HarmonyOS PC aarch64）

上游方式在 OHOS 上**不可用**的具体技术原因：上游 `add_boost_test()` 链接
`${Boost_UNIT_TEST_FRAMEWORK_LIBRARY}`/`${Boost_SYSTEM_LIBRARY}`/`${Boost_FILESYSTEM_LIBRARY}`
（并在非 Windows 下 `#define BOOST_TEST_DYN_LINK`），而制品仓的 OHOS Boost 包
（`boost/1.84.0`，见 `archives/b/boost/1.84.0`）只提供头文件与
filesystem/regex/program_options/iostreams 四个静态库，**没有
`libboost_unit_test_framework`**，干净环境无法 `find_package(Boost COMPONENTS unit_test_framework)`。

替代运行方式（**不改被测库**）：逐文件直接编译上游 126 个 `test_*.cpp`，仅做两处
测试脚手架改动 + 一个平台宏：

- `#include <boost/test/unit_test.hpp>` → `#include <boost/test/included/unit_test.hpp>`（头文件版 Boost.Test 入口，无需框架库）
- 删除 `#define BOOST_TEST_DYN_LINK`
- 追加 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（OHOS musl 无 `pthread_setcancelstate`）
- 链接 OHOS Boost 包提供的 `libboost_filesystem.a` 与被测 `libVector_BLF.so`

### 3) 实测结果

```
100% tests passed, 0 tests failed out of 126
Total Test time (real) =   6.57 sec
```

| 指标 | 数值 |
|---|---|
| 注册 | 126 |
| 执行 | 126 |
| 通过 | **126** |
| 失败 | 0 |
| 跳过 | 0 |

**通过率 126/126（100%）**，逐项结果与 ctest 原始输出见
[`reports/upstream-tests.md`](reports/upstream-tests.md)。

覆盖范围（上游用例本身即覆盖）：BLF 文件读写（`File::open/create/read/write/close`）、
LogContainer zlib 压缩/解压（`compress2`/`uncompress`）、CAN/CAN-FD/LIN/MOST/FlexRay/
Ethernet/A429/AFDX 全部事件类型序列化与反序列化、`objectSize == calculateObjectSize()`、
文件统计、损坏/截断文件的异常路径（`tests/unittests/errors/*.blf`）。

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libVector_BLF.so` | 共享库（无 SONAME，CMake 在 HarmonyOS 平台的产物形态） |
| `include/Vector/BLF.h` + `include/Vector/BLF/*.h` | 公开头文件（含生成的 `config.h`、`vector_blf_export.h`） |
| `lib/pkgconfig/Vector_BLF.pc` | pkg-config 元数据 |
| `share/doc/Vector_BLF/` | README/CHANGELOG/LICENSE + examples 源码 |

## 注意事项

- 本包是**共享库**且无 SONAME：运行期解析依赖 RPATH/`LD_LIBRARY_PATH`；消费方
  （含 test_package）由 Conan 自动注入 RPATH，不要手工 `-L` 后裸跑。
  **为什么不在配方里补 `-Wl,-soname`**：上游 `SOVERSION 2` 之所以不生效，是 CMake 在
  `HarmonyOS` 平台没有 soname 支持、因而**也没有生成 `libVector_BLF.so.2` 软链接链**
  （HMDFS 软链接受限）。若强行只注入 `-Wl,-soname,libVector_BLF.so.2`，产物的 `NEEDED`
  会变成 `libVector_BLF.so.2` 而磁盘上没有该文件 → 消费者运行期直接找不到库。
  保持"扁平 `.so` + 无 SONAME"是与平台行为自洽的形态（L5a 的 `DT_SONAME` 缺失属存量遥测，非阻断）。
- `OPTION_RUN_DOXYGEN=OFF` 是**必需**项而非可选优化：留 ON 会在无 doxygen 的环境
  直接 configure 失败。
- zlib 以静态库形式内嵌；`conanfile.py` 仍声明 `requires("zlib/1.3.2.1")` 以表达
  构建期依赖，消费方无需再链接 `-lz`。
- `generate()` 必须保留 `CMakeDeps(self).generate()`：删掉它会让 `find_package(ZLIB)`
  退回 CMake 内置 Find 模块，静默链上构建机的同名库（详见问题 #6 与知识草稿 E550）。
- 上游 `src/Vector/BLF/tests/` 下的 `/unittests` 由 `OPTION_BUILD_TESTS` 控制，
  本包保持默认 OFF，CI 只跑 `test_package/`。
---

**编译结束**: 2026-10-15 08:27
**最终状态**: built
