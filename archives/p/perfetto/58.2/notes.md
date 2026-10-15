# perfetto 58.2 — HarmonyOS PC 适配笔记

上游：https://github.com/google/perfetto tag **v58.2**（commit `add693d8b338ba9599dbcbc3e300b1ab8c000897`）
源码 sha256：`ad566546d5c461135a41962e95b680f374e438cf2d9936867608b84132ec610a`
构建系统：**GN + Ninja**（上游 standalone），非 CMake/autotools。

---

## 1. 构建方式（gn args）

```
gn gen out/ohos --args='
  is_debug=false
  is_system_compiler=true        # 用 OHOS 系统 clang（非上游 hermetic clang）
  is_hermetic_clang=false        # 上游为系统编译器保留的配置（无 -Weverything/-Werror）
  target_triplet="" sysroot=""   # 上游默认把 linux/arm64 当 Debian sysroot 交叉，OHOS 需清空
  use_custom_libcxx=false        # 用 OHOS sysroot 自带 libc++
  skip_buildtools_check=true     # 依赖已由 source() 供给，跳过 install-build-deps 产物校验
  perfetto_use_system_zlib=true  # 用 OHOS sysroot 自带 zlib（上游 chromium zlib fork 不可得）
  strip=""                       # 保留 .codesign（OHOS 上 strip 会让 ELF 无法执行）
'
```

构建目标（零裁剪核心组件 + 可选测试二进制）：

```
# 默认（CI / 发包）：产品件全开
libperfetto.so libperfetto_client_experimental.a \
trace_processor_shell tracebox traceconv perfetto traced traced_probes protoc

# -o "&:with_tests=True" 时追加：上游测试二进制（宿主侧全量实测用）
perfetto_unittests perfetto_base_unittests perfetto_misc_unittests perfetto_profiling_unittests \
perfetto_trace_processor_unittests perfetto_tracing_unittests trace_processor_minimal_smoke_tests \
perfetto_benchmarks perfetto_integrationtests
```

> **为什么测试二进制默认不建**：CI 只跑 `conan create` + `test_package`，并不运行上游单测；而测试二进制
> 合计约 1.6 GB，其编译+链接占整条流水线的大头，会顶到 CI 默认 `DEFAULT_BUILD_TIMEOUT=3600 s`。
> 本地复现全量测试：`conan create . -o "&:with_tests=True"`。

## 2. GN 工具链自举（本任务最大障碍）

- 上游 `tools/gn` 是 Python 下载器（`run_buildtools_binary` → `buildtools/<os>/gn`），**不 vendor 二进制**，
  `buildtools/linux64/` 被 gitignore；tarball 内没有任何 gn 可执行文件。
- 上游确实提供 arm64 预编译（`gn-linux-arm64-1968-0725d782`），但它是 **glibc** 动态链接
  （interp `/lib/ld-linux-aarch64.so.1`），而 OHOS 是 **musl**；且**不带 `.codesign`** → 在 OHOS 上
  双重不可用（`Permission denied`，rc=126）。
- **解法：源码自举**。pin 上游 `install-build-deps` 指定的同一 revision
  `0725d7827575b239594fbc8fd5192873a1d62f44`（GitHub 镜像 `JiauZhang/gn` 含该 SHA）：

  ```sh
  export CC=clang CXX=clang++
  python3 build/gen.py --no-last-commit-position      # 源码 tarball 无 .git，需跳过 git describe
  # gen.py 因此不生成该头，需手工补 out/last_commit_position.h
  ninja -C out                                        # 产出 out/gn（musl + .codesign）
  ```
- 自举产物可正常执行（含 `gn_unittests` 654/654 通过），并成功驱动 perfetto 全树
  （`gn gen` → `Made 2495 targets from 380 files`）。
- **OHOS 平台 `sys.platform` 陷阱（补丁 0017）**：CI worker 构建期 `python3` 是 OHOS 系统 Python，
  其 `sys.platform == 'ohos'`（**并非 `'linux'`**）。GN 自举脚本 `build/gen.py` 的平台归一化只认
  `linux/darwin/win/...`，遇 `ohos` 时在 `WriteGenericNinja` 的模板查表处直接 `KeyError: 'ohos'`
  （CI 构建 #73450 / #73451 即秒级死在此处，与本地 `sys.platform=='linux'` 的 rc=0 形成差异）。
  补丁 `0017-gn-bootstrap-ohos-platform.patch` 把 `ohos`/`harmonyos` 归一为 `linux`（OHOS 内核与
  syscall 语义即 Linux）；对 `sys.platform=='linux'` 的上游路径**零影响**（Linux 分支行为逐字节不变）。

## 3. 第三方依赖供给（20 个包）

上游 `tools/install-build-deps` 从 `*.googlesource.com` 抓取，OHOS 侧该域**全系不可达**。
改为 GitHub 镜像，**逐条核对同一 commit SHA**：

- `chromium.googlesource.com/external/github.com/<owner>/<repo>` 系（protobuf/abseil/re2/zstd/libexpat/sqlite/googletest/benchmark）
  → GitHub 同名仓库（SHA 一致）。
- AOSP 专有仓库（system/core、system/unwinding、system/logging、system/libbase、system/libprocinfo、
  bionic、external/lzma、external/OpenCSD）→ **`msft-mirror-aosp`**（`aosp-mirror` 无这些仓库；msft 镜像同名 SHA 全部 200）。
- `storage.googleapis.com/perfetto` 自建桶可达（sqlite amalgamation / llvm-project / libbacktrace）。
- **唯一例外**：zlib。上游用 chromium 专有 fork（`chromeconf.h`、`cpu_features.*`、
  `contrib/optimizations/insert_string.h`），GitHub 无对应仓库 → libunwindstack 改用
  **OHOS sysroot 自带系统 zlib**（见补丁 0001）。

## 4. 移植补丁（6 个，均为硬错误）

| 补丁 | 根因 |
|---|---|
| 0001 buildtools-use-system-zlib | libunwindstack 直接依赖 `//buildtools:zlib` 源（chromium fork，不可得）→ 改用系统 zlib |
| 0002 zstd-ohos-qsort-r-fallback | **musl 无 `qsort_r`**（无声明亦无符号）；zstd 在 linux 分支自行 `#define _GNU_SOURCE`（其 guard 只排除 `__ANDROID__`）→ OHOS 下 `#undef` 走自带 C90 `qsort` fallback |
| 0003 libbase-ohos-getprogname | **musl 无 glibc 的 `program_invocation_short_name`** → 由可执行路径派生程序名 |
| 0004 liblog-ohos-getprogname | 同上（用 `/proc/self/exe`） |
| 0005 symbolizer-filesystem-ohos-nftw | **musl 不提供 `<fts.h>`** → 用 `nftw()` 重写目录遍历（保持功能，非裁剪） |
| 0006 vm-sockets-ohos-sockaddr-storage | OHOS sysroot 的 `<linux/socket.h>` **无条件重定义 `sockaddr_storage`**，与 musl `<sys/socket.h>` 冲突 → 改用 perfetto 自带 UAPI 兜底结构 |

所有补丁均为 per-file `diff -u`，并做过**黄金验证**：干净树按序 `patch -p1` 应用后与开发树**逐字节一致（diff=0）**。

## 5. 关键环境事实（跨库通用）

- **OHOS 用户存储（hmdfs）执行 ELF 需 `.codesign` 段**：缺失则 `execve` 返回 `EACCES`
  （表现为 `Permission denied`，rc=126）——**不是 noexec 挂载问题**。本机 OHOS clang 在链接期自动添加；
  `binary-sign-tool -selfSign 1` 可给外部 ELF 补签。因此**禁止**直接复用外部下载的未签名预编译二进制。
- **strip 破坏签名**：任何 strip/objcopy 都会让 `.codesign` 失效 → 构建必须 `strip=""`。
- OHOS 头把 **`NULL` 定义为 `0L`**（glibc 为 `__`）；perfetto 的 `-Weverything` 是按
  hermetic clang 19 校准的，系统 clang 15 下会因告警集不同大量失败 → 用上游为系统编译器保留的
  `is_hermetic_clang=false`。
- OHOS `/tmp` 只读（erofs）；`/data/local/tmp` 对普通用户不可写。
- `googlesource.com` 全系不可达；`github.com` / `codeload.github.com` / `storage.googleapis.com` 可达。
- **OHOS 的 Python 报 `sys.platform == 'ohos'`（并非 `'linux'`）**：任何以 `sys.platform`/`platform.system()`
  做平台分支的构建脚本（GN 自举、autotools 生成器、各类 codegen）都必须把 `ohos`/`harmonyos` 归一为 `linux`，
  否则报错或走错分支。CI worker 的 `python3` 为 OHOS 系统 Python（`/data/app/bin/python3`），
  与本地 DevBox 的 HNP Python（`sys.platform=='linux'`）行为不同——**"本地绿、CI 红"的经典根因之一**。

## 6. 运行实测

- `trace_processor_shell --version` → `Perfetto v58.2 (N/A)`（rc=0）
- 空 trace + `--query-string "select 1 as x"` → 输出 `1`（rc=0）
- 运行期观测：`d_trace_internal.cc:590 Cannot use mmap on this system. Falling back on read()`
  （OHOS 上 mmap 不可用 → 自动回退 read()，功能不受影响）
- `gn_unittests`（自举的 gn 自带单测）：**654/654 PASSED**

（perfetto 自带 unittests / trace_processor 套件的逐套件实测与逐条归因见
learninglog/20260930perfetto-58.2/reports/失败逐项归因表.md 与 证据七环.md）

## 7. 上游测试实测（宿主侧）

| 套件 | 规模 | 通过 | 失败 |
|---|---|---|---|
| `perfetto_unittests`（聚合） | 3832 | 3745 | 22（+3 skipped） |
| `perfetto_trace_processor_unittests` | 2019 | 2019 | 0 |
| `perfetto_misc_unittests` | 61 | 61 | 0 |
| `perfetto_profiling_unittests` | 164 | 156 | 8 |
| `gn_unittests`（工具链自测） | 654 | 654 | 0 |

**通过率 98.33%（全量分母）/ 99.31%（排除环境限制项）**

未被执行的项均为 OHOS 环境硬限制，已逐条归因：**拒绝创建文件路径型 unix socket**（hmdfs EPERM /
`/data/local/tmp` EACCES / `/tmp` EROFS / `/dev/shm` EACCES，仅抽象 socket 可用）、**ptrace 被禁**
（本机 gdb 亦不可用）、**memfd sealing 不支持**、HMDFS 目录遍历语义差异、musl `strtod` 边界差异。

## 8. 消费者验证（conan test_package，`conan create` 内自动执行）

- `test_package/consumer.cc`：编译并链接 `libperfetto` 的最小消费者程序 → 运行 rc=0
- `test_package/test.sh`（消费者用例）：**14/14 PASS**
- `test_package/test_ohos.sh`（鸿蒙平台特有）：**11/11 PASS**（AArch64 ELF + `.codesign` 段 + 只读 `/tmp` 下的 TMPDIR 约定）

## 9. 打包要点（conan）

- `package_type = "shared-library"`：**不能用 `application`**——application 会让 conan 清空
  `cpp_info.libs`/`includedirs`，CMakeDeps 因而不导出头文件路径，消费者 `find_package(perfetto)` 后编译缺头。
- perfetto 可执行文件以 rpath `$ORIGIN/.` 链接 `libperfetto.so`（上游 standalone 为扁平输出目录），
  故除 `lib/` 外**在 `bin/` 也放一份** `libperfetto.so`。
- 公共头 `perfetto/base/build_config.h` 会 include **生成头** `perfetto_build_flags.h`（上游由 `-Igen/build_config`
  提供）→ 打包时把 `gen/build_config/*.h` 一并放入 `include/`。
- `libperfetto.so` 以 `-fvisibility=hidden` 构建，对外导出面为 entrypoint
  （`perfetto::ServiceMain` / `perfetto::ProbesMain`）。

## 10. 审查整改（AI review P1/P3，2026-10-12）

针对 AI 检视意见做的整改（**不引入任何平台条件编译宏**）：

- **P1 / R8（平台宏）**：`0002/0003/0004/0005/0006/0007/0008/0009/0010/0012` 十个补丁原先用
  `#if/#elif defined(__OHOS__)`，现**全部改为能力探测**：
  - zstd(0002)、libbase(0003)、liblog(0004)、vm_sockets(0006)、relay statx(0010)、gtest(0012)：
    以 **libc 族**判定 → `#if !defined(__GLIBC__)`（glibc 族行为逐字节不变；非 glibc 走可移植分支）；
  - symbolizer(0005)：`#if !__has_include(<fts.h>)`（OHOS sysroot 无 `fts.h`，自动走 `nftw()`）；
  - heapprofd/java-hprof/proc-descriptors(0007/0008/0009)：`#if !defined(__SIGRTMIN)`。
  - 整改后 **`grep -rn '__OHOS__' patches/` 为空**；`__GLIBC__` 判定不改变 glibc 平台的既有行为。
- **P3**：
  - `test.sh`：`set -u` → `set -euo pipefail`；去掉 `eval` 断言（改 `"$@"` 直接执行 + `grep -E` 匹配经
    stdin 传入），消除 `PKG_BIN` 命令注入面。
  - `consumer.cc`：删除恒真的 `entry != nullptr`，改为**运行期真实断言**——用 `dladdr()` 确认
    `perfetto::ServiceMain` / `perfetto::ProbesMain` 确由 `libperfetto.so` 提供（并校验构建宏为 `PERFETTO_OS_LINUX`）。
  - `patches/0014`/`0015`：经核查**上游 `api_test_support.cc` / `bundle_integrationtest.cc` 本就已 include
    `perfetto/ext/base/temp_file.h`** ⇒ 该条为误报，无需改动（已在 PR 回复中附证据）。
- **复验**：合并后 `conan create` **rc=0**（2942/2942 步；consumer 输出
  `ServiceMain/ProbesMain resolved from libperfetto.so`；test.sh 14/14、test_ohos 11/11 PASS）。
- **P2 / R39（`JiauZhang/gn`）**：不改代码；该 revision 无任何可达官方/权威镜像（见 PR 正文豁免说明）。

### 10b. 追加整改（AI review 第二轮，2026-10-14）

- `test_package/test_ohos.sh`：`set -u` → `set -euo pipefail`；去 `eval`（断言改 `"$@"` 直接执行 / 固定子串 `case` 匹配，
  `readelf` 输出经变量捕获后比对），消除 `PKG_BIN` 命令注入面。与 `test.sh` 手法一致。
- 其余首轮项保持不变；gn 源（R39）按 PR 正文「审查整改与豁免说明」申请人工豁免。
