# manifold 3.5.2 适配笔记

## 编译环境
- 构建系统: cmake (上游 >= 3.18, 实际 4.1.2)
- 编译日期: 2026-09-29
- 编译器: clang/clang++ (OHOS SDK, -target aarch64-linux-ohos, libc++)
- 状态: built

## 编译步骤

设备上原生构建 (非交叉), Conan 2.x recipe 驱动:

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c:h='tools.build:compiler_executables={"c":".../clang","cpp":".../clang++"}' \
  -c:b='tools.build:compiler_executables={"c":".../clang","cpp":".../clang++"}' \
  [--build=missing]            # 默认静态; -o:h='&:shared=True' 构建共享
```

上游选项映射 (全部走上游 find_package 快路径, 零补丁):
- `MANIFOLD_TEST=ON` → gtest/1.17.0 (CMakeDeps 生成 GTestConfig.cmake 命中)
- `MANIFOLD_CROSS_SECTION=ON` → clipper2/2.0.1 (同上, 避开 FetchContent 从 GitHub 拉源)
- `MANIFOLD_PAR=OFF` (TBB 不引入), `MANIFOLD_CBIND=ON` (C 绑定),
  `MANIFOLD_DOWNLOADS=OFF`, PYBIND/JSBIND/FUZZ/TRACY/ASSIMP 全 OFF
- 附加 `manifold-deps-alias.cmake` (CMAKE_PROJECT_INCLUDE): 把 CMakeDeps
  生成的 `GTest::gtest_main`/`clipper2::clipper2` 别名到上游硬编码的
  全局目标名 `gtest_main`/`Clipper2::Clipper2`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 共享库 install 后 test_package 报 `Error loading ... Permission denied` | OHOS hmdfs `hmmac=use_task` 完整性保护: .so 落盘后任何字节级改写 (cmake 4.1 install 的 `file(RPATH_CHANGE)` 重写 RUNPATH) 都被动态链接器拒载; 实验证明改 1 字节 padding 也不行, cp 原字节副本却可加载 | `CMAKE_SKIP_RPATH=ON`: 本包运行期依赖全静态, RUNPATH 无存在价值; 链接输出即最终字节, install 为纯复制 |
| 2 | SKIP_RPATH 后 `gtest_discover_tests` 的 POST_BUILD 探测失败 | cmake 4.1 中 `CMAKE_BUILD_RPATH`/`BUILD_RPATH` 不再自动注入链接命令, rpath 仅由 install 事后写入; build 树 exe 无 rpath 找不到 `libmanifold.so.3` | 构建期通过 `LD_LIBRARY_PATH` 提供 build 树 .so 目录 (src/ bindings/c/ samples/) |
| 3 | LD_LIBRARY_PATH 注入传导不到 cmake 子进程 | conan 2 的 `run()` 仅 source generators/ 下 env 文件; build() 里改 `os.environ`、generate() 里 append `buildenv_info` 都无效 | generate() 里写自定义 `ohos_buildpath_env.sh`, build()/test() 以 `env=["conanbuild","ohos_buildpath_env"]` 传给 `CMake._build()`/`CMake.test()` |
| 4 | 初版 ABI 检查误报 SONAME 不匹配 | 检查器把 dev symlink `libmanifold.so` (指向 .so.3) 当 ELF 实体, 与 SONAME `libmanifold.so.3` 比对失败 | 检查器只扫真实实体 (`.so.3.5.2`), SONAME 链完整性 (so→so.3→so.3.5.2) 由独立 M10 检查 |

## 源码修改

无 (零补丁)。上游 `find_package(... QUIET)` + FetchContent 回退的设计
使 Conan 依赖可直接接管。

## 依赖版本

- clipper2/2.0.1 (静态)
- gtest/1.17.0 (静态, 仅测试)

## 验证结果

```bash
# 上游 CTest (ctest -N 统计):
Total Tests: 427
# 共享库变体 (分组运行覆盖全部 427): 427 passed, 0 failed
# 静态库变体 (一次完整运行): 100% tests passed, 0 tests failed out of 427
# 上游总执行量: 854/854 — 同一套 427 个上游测试在 static/shared
#   两种构建形态下分别完整执行 (427 × 2), 上游唯一测试定义仍为 427
# test_package (真实链接 + 运行): PASS × 17 (cube volume/surface/NumVert,
#   boolean add/subtract/intersect, genus, scale, translate, extrude,
#   cross-section ×3, sphere volume, GetMeshGL, simplify, version macros)
#   口径: test_manifold.cpp 预处理后实际输出的 PASS 行; static 与
#   shared 各执行一次, 均为 17/17
# OHOS ABI 专项检查: ALL OHOS ABI CHECKS PASSED (M0-M10, 见下)
```

OHOS ABI 专项 (test_package/ohos_abi_check.py, 纯 Python 解析 ELF):
- M0 静态归档格式 `!<arch>\n` (静态变体)
- M1 ELF64 little-endian, e_machine=EM_AARCH64(183)
- M2 SONAME 实体名匹配 (libmanifold.so.3 / libmanifoldc.so.3)
- M3 PT_INTERP 为 OHOS musl loader (仅可执行文件)
- M4 DT_NEEDED ⊆ {libc.so, libc++_shared.so, libmanifold.so.3(包内)}
- M5 无 .gnu.version_r (glibc symbol versioning)
- M6 RUNPATH 无 build-host 路径 (SKIP_RPATH 后为 none)
- M7 clipper2 未出现在 DT_NEEDED (静态链入)
- M8 .dynsym 存在
- M9 .note.ohos.ident 存在 (OHOS 工具链标识)
- M10 SONAME 链完整 (so / so.3 / so.3.5.2, symlink 全部可解析)

M0-M10 是 11 个检查类别; 实际断言数按 libdir 下发现的每个真实 ELF
实体展开 (不允许把类别数当断言数):

| 变体 | 检查对象 (真实 ELF 实体) | 实际断言数 | 结果 |
|------|--------------------------|-----------|------|
| static | libmanifold.a + libmanifoldc.a | M0 × 2 = 2 | 2/2 PASS |
| shared | libmanifold.so.3.5.2 + libmanifoldc.so.3.5.2 | (M1,M2,M4-M9) × 2 库 + M10 × 4 链接 = 20 | 20/20 PASS |

说明: M3 (PT_INTERP) 仅对含解释器的可执行文件执行, 库文件无 PT_INTERP,
不产生断言; ABI 检查由 test_package 的 test() 内嵌执行, 与上游 ctest
是不同执行入口, 统计不重复计算。

执行入口汇总 (PR 最终统计口径):

| 测试层 | 入口 | static | shared | 合计执行 |
|--------|------|--------|--------|---------|
| upstream CTest | 主配方 test() → cmake.test() | 427/427 | 427/427 | 854 |
| functional test_package | test_package test() → test_manifold | 17/17 | 17/17 | 34 |
| OHOS ABI 专项 | test_package test() → ohos_abi_check.py | 2/2 | 20/20 | 22 |
| 总执行断言/条目 | | 446 | 464 | 910 |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2.x 配方 (CI 唯一构建输入) |
| conandata.yml | 上游 tarball URL + SHA256 |
| manifest.yaml | 版本编译元数据 (交叉校验) |
| test_package/ | L1 官方测试 + OHOS ABI 专项检查 |

## 注意事项

- `CMAKE_SKIP_RPATH=ON` 仅在 OHOS+shared 时启用; 其它平台保持上游默认
- 若未来引入非静态的运行期依赖 (如共享 clipper2), 需重新评估 SKIP_RPATH
  策略 (届时应改用 `$ORIGIN` 相对 RUNPATH 且由链接器直接生成)
- cmake 4.1 的 rpath 行为变化 (BUILD_RPATH 不再注入链接命令) 是上游
  构建 (非 install) 场景需要注意的通用差异
