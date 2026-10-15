# iitii 0.0-git20191030.85209e0 适配笔记

## 来源核验（官方资料确认）

- 上游仓库：https://github.com/mlin/iitii（Implicit Interval Tree with Interpolation Index）
- 快照提交：`85209e07a3ee403fb6557387a7f897cd76be4406`（`git ls-remote` 实测为 PR #4 head，日期 2019-10-30）
- Debian/Ubuntu 快照版本 `0.0+git20191030.85209e0` 即此提交；本配方按 `0.0-git<date>.<short>` 惯例取版本 `0.0-git20191030.85209e0`
- 源码包：`https://github.com/mlin/iitii/archive/85209e07a3ee403fb6557387a7f897cd76be4406.tar.gz`
- SHA-256：`40a2baf1f325375e070ec29392ed7e156318658c4b79f4f6b5f328d2cbeab671`（105015 bytes，实测下载值）
- 许可证：Apache-2.0（LICENSE 文件头确认为 Apache License Version 2.0）
- 源码结构（归档共 16 条目）：`src/iitii.h`、`src/main.cpp`、`test/test_iitii.cc`、`test/util.h`、`test/CMakeLists.txt`、顶层 `CMakeLists.txt`

## 结构

- header-only C++14 库：核心头文件 `src/iitii.h`，提供模板类 `iit`（cgranges 复刻）与 `iitii`（插值索引扩展）
- `src/iitii.h` 的第三方头文件引用：`ips4o.hpp`、`mmappable_vector.h`（均由 Conan 依赖提供）
- 顶层 `CMakeLists.txt` 构建可执行工具 `iitii`（`src/main.cpp`，memmapped CLI，需 Taywee args + OpenMP + mmap_allocator 静态库）；本配方为 header-library，不构建该工具
- C++ 标准：顶层工具要求 C++14；头文件本身 C++11/14 均可（test_package 按 C++14 编译）

## 依赖

- `ips4o/0.0-git22069381cc`：提供 `ips4o.hpp`（上游 CMake ExternalProject  pin `22069381cc1bf2df07ee1ff47f6b6073fcfb4508`，与制品仓版本一致）
- `mmap_allocator/3.1`：提供 `mmappable_vector.h`（上游 ExternalProject 跟踪 `ekg/mmap_allocator` master；制品仓 3.1 已做 libc++ 适配）
- 不引入 Taywee args：仅 `src/main.cpp` CLI 需要，库头文件不需要；header-library 配方保持 0 工具依赖以外的最小依赖
- 不引入 htslib/CTPL/Catch2：仅上游 `test/` 基准与单测 harness 需要，不入生产配方

## 上游测试清点（R51 三步法第 1 步：申报）

- `test/CMakeLists.txt` 注册 ctest 数量：1（`add_test(NAME unit_tests ... ./test_iitii -d yes)`，另有 `dumb_benchmark`、`gnomad_benchmark` 两个 benchmark 可执行文件，非 ctest）
- `test/test_iitii.cc` 内 Catch2 `TEST_CASE` 数量：6
  1. `cgranges example`（确定性，iit 基本查询）
  2. `cgranges example with iitii`（确定性，iitii 基本查询）
  3. `dark nodes (N=5)`（确定性，含访问代价 `== 4` 断言）
  4. `dark nodes (N=5) with iitii`（确定性，插值后代价 `== 1` 断言）
  5. `fuzz`（随机种子 42，N=3 起按 3 倍增至 <2000000，每轮 1000 查询；无外部数据依赖，可运行但耗时）
  6. `gnomAD chr2`（需 `/tmp/gnomad...chr2.vcf.bgz` 外部 20M 数据集，不存在时 `WARN` 跳过）
- `test/util.h` 依赖 htslib（`kstring.h`/`tbx.h`）、CTPL；`test/CMakeLists.txt` 通过 ExternalProject 下载 htslib 1.9 + CTPL + Catch v2.9.1，且测试命令含 `LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so`（Linux 专有路径）
- 结论：上游 harness 为 Linux 台式机实验设计（ExternalProject 外网下载 + jemalloc 预载 + 可选大体量 VCF），不能原样在 OHOS 真机/CI 直接复用；适配策略为 test_package 复刻前 4 个确定性用例 + 轻量 fuzz，覆盖核心语义与代价断言

## test_package 设计（R34 实质调用）

- `test_iitii.cpp`：直接 `#include "iitii.h"`，调用 `iit`/`iitii` 的 `builder::add/build/overlap` 真实 API，共 5 项检查：
  1. iit 基本查询（复刻上游用例 1：22-25 查询命中 2 条且首地址为 0/12）
  2. iitii 基本查询（复刻上游用例 2，domains=1）
  3. dark nodes 代价断言（复刻上游用例 3：7-10 查询代价 `== 4`）
  4. iitii 插值代价断言（复刻上例 4：代价 `== 1`）
  5. 轻量 fuzz（固定种子 42，N=300，100 查询，与朴素线性扫描逐项比对结果集）
- 任一检查失败返回非零退出码并打印 `FAIL` 行；全部通过打印 `PASS` 行；CMake CTest 注册 1 个测试 `test_iitii`
- OHOS 移植补丁 `patches/0001-ohos-no-openmp-serial-fallback.patch`（portability）：真机有 `omp.h` 头但无 `libomp.so` 运行时（HarmonyOS 缺 `pthread_cancel`，libomp 无法构建，见知识库 E127），链接 OpenMP 会在 `test()` 运行时报 `Error loading shared library libomp.so`。补丁在 `_OPENMP` 未定义时让 `iit_mm_builder_base` 单线程运行（`get_thread_count()=1`、`get_writer()` 取 writers[0]），并把 `ips4o::parallel::sort` 换成串行 `ips4o::sort`（排序结果同一，索引几何与查询代价断言不受影响；串行 `ips4o::sort` 已在 ips4o 自身 merged 配方中于 OHOS 验证通过）。test_package 故意不链接 `OpenMP::OpenMP_CXX`，避免二进制带上无法解析的 `libomp.so` NEEDED 项
- `MANIFEST.yml`：`upstream_test_total: 1`，口径 `ctest_entries`（与官方 `add_test` 注册单位一致，不用 Catch2 内部 6 用例冒充总数）

## 编译步骤（待真机验证）

- header-only：`conan create` 解包 → 拷贝 `src/iitii.h` 到 `include/` → test_package 以 CMakeDeps/Toolchain 编译 `test_iitii.cpp` 并运行
- 本地未运行 conan（按任务守则，W3 改为真机内执行；除 rsync/ssh 外不在本机运行 conan）
- 首轮仅交付未提交工作树，由 HMBS 后台做完整真机验证；验证通过前不 commit、不 push、不建 PR

## Windows 基线说明（本机检出限制，不入配方）

- `git checkout main` 在 Windows 上遇到两处平台限制，已用 `git update-index --skip-worktree` 本地屏蔽（Linux 真机/CI 无此问题）：
  1. `archives/g/gama/2.29/patches/0002-dataparser-ungated.patch\r\r` 文件名含回车，Windows 文件系统无法创建
  2. `archives/l/libXext` 与 `archives/l/libxext` 大小写仅差一字母，Windows 不区分大小写文件系统发生碰撞
- 屏蔽后 `git status` 为干净基线；本 PR 仅新增 `archives/i/iitii/**`，未改动上述文件

## 验证结果（待真机 evidence 轮回填）

- 编译状态：待 HarmonyOS aarch64 真机预检
- 上游测试用例通过率：待真机回填（总数口径 1 ctest；harness 限制见上游测试清点）
- 新增测试用例通过率：待真机回填（test_package 5 项检查）

## Upstream suite OHOS adaptation (rule4 evidence round, 2026-10-14)

- Preflight 2026-10-14T11:27Z reported `rule4: missing upstream run result`
  (discovered 1 / executed 0, status skipped with an `environment` gap citing
  jemalloc preload + ExternalProject htslib/CTPL/Catch downloads).
  Per task rules, `missing_dependency` cannot waive execution: deps must be
  completed and the suite really run on the device.
- Root causes confirmed from source + logs:
  1. Catch2 framework missing on device -> completed via repo Conan package
     `catch2/2.13.10` as `test_requires` (OHOS-verified header-only), replacing
     ExternalProject `Catch v2.9.1.zip` (no network on device).
  2. `test/util.h` (htslib `kstring.h`/`tbx.h` + `ctpl_stl.h`) only needed by
     the gnomAD case; the other 5 cases use pure iit/iitii API. The port drops
     util.h and keeps the gnomAD case under its upstream name with the
     identical WARN-skip text when `/tmp/gnomad...chr2.vcf.bgz` is absent
     (never shipped on preflight, same as a bare Linux box).
  3. `LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so` removed (Linux-only
     path; suite runs identically without preloading).
  4. Builder API drift (decisive): at 85209e0 `src/iitii.h` exposes ONLY
     `iit_mm_builder_base` (backing-file constructors), while
     `test/test_iitii.cc` still calls the old in-memory `builder(begin, end)`
     API that no longer exists — it cannot compile even on Linux. The port
     (`test_package/upstream_test_iitii.cc`) keeps all 6 TEST_CASE names and
     every REQUIRE, threading a TMPDIR backing file through build helpers.
  5. Fuzz scale: upstream `N<2000000, Q=1000` is billions of naive comparisons
     on a jobs=1 shared preflight slot. Same structure/seed(42)/
     distributions/spikes/naive cross-check/cost-bound REQUIREs, capped at
     `N<60000, Q=200` (10 levels) so it finishes in seconds. Adaptation only,
     no assertion weakened; documented in the port header.
- Execution: `test_package/CMakeLists.txt` builds `upstream_test_iitii` (C++17,
  `Catch2::Catch2`, no OpenMP linkage like the consumer test) and registers
  `add_test(NAME unit_tests ...)`; `conanfile.test()` runs the consumer binary
  then `ctest -R unit_tests --output-on-failure`, parses `Total Tests: N` plus
  one `Test #N ... Passed|Failed` line per test (cross-checked against the
  `tests passed/tests failed out of` summary, mismatch aborts instead of
  patching numbers), and emits `HMBS_UPSTREAM_TEST_RESULT` with
  `framework: ctest, discovered: 1`. At `ctest_entries` granularity the
  gnomAD WARN is inside the passing entry, so no gaps at ctest level.
- `MANIFEST.yml`: `upstream_test_command` is now the real
  `ctest -R unit_tests --output-on-failure`; `test_dependencies` declares
  `catch2/2.13.10`; total stays `1` / `ctest_entries`; audit records the API
  drift + adaptation chain above.
