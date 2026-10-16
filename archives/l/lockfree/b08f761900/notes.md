# lockfree b08f761900 适配笔记

## 编译环境
- 构建系统: makefile（C99 与 C++11 两套 Makefile，各自构建 ffbench 基准程序）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 上游来源与版本核验
- 上游仓库: https://github.com/huangfcn/lockfree
- 版本标识: b08f761900（上游 commit b08f76190043f638a52f464eeeab1bcc8345d26d，"Update Next2Curr Index for linux"，2020-06-09；上游无 tags/release，提交即唯一版本标识，经 GitHub API 核验为真实提交）
- 源码 SHA-256: c5419a8c198bca6381a477da9044e5f77e1531ff3c13c1599d5f8c7ffbbce010

## 上游测试申报表（R51）
上游仓库为纯算法演示/良性竞争数据结构库，不含 tests/ 目录、无 ctest/pytest 注册。可运行测试为两个变体各自的基准程序（ffbench），其余为库头文件（API 由 test_package 实证）。

| 测试/可运行物 | 变体 | 位置 | 实测结果 |
|---|---|---|---|
| ffbench（SPSC/MPMC/stack/queue 基准） | C99 | C99/main.c | 构建通过（5 条 unused-function 警告），运行实测输出正常，threads 1-3 正常出数 |
| ffbench（同基准） | C++11 | C++11/main.cpp | 本机 clang++ 构建通过（无 -latomic，环境无 libatomic；-pthread 即可），运行实测正常 |

- 本机 C99: `make -C C99 CC=clang CFLAGS="-Wall -O2"` → ffbench 生成并运行
- 本机 C++11: `clang++ -Wall -O2 -std=c++17 -pthread main.cpp -o ffbench` → 生成并运行（上游 Makefile 的 -latomic 在本环境无 libatomic 库，属环境差异，非源码缺陷；link 时去掉即可）

## 编译步骤

本库为纯头文件 + 1 个 C 源文件（mirrorbuf.c）结构：
- C99 变体: magicq.h/rbq.h/lffifo.h（宏模板头）+ mirrorbuf.c/h（双映射环形缓冲实现）
- C++11 变体: magicq.hpp/rbq.hpp/lffifo.hpp（模板头，纯 header-only，基于 std::atomic）

conan 配方将两变体全部头文件与 mirrorbuf.c 打包为静态库（liblockfree.a），
test_package 编译调用库 API 的消费者程序实证。

依赖：仅 POSIX 系统能力（pthread + mmap 双映射），无第三方 conan 依赖。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时，init-build 下载失败 | 本机到 github.com:443 网络不可达 | 通过 gh-proxy.com 镜像下载官方 commit tarball（SHA-256 与官方一致），预置到 $TMPDIR/builds/ 后重跑 init-build |
| 2 | C++11 变体 Makefile 链接失败 | 上游 Makefile 使用 -latomic，本环境无 libatomic 库 | 本机验证时去掉 -latomic（-pthread 即可链接运行）；OHOS 交叉编译时确认 libatomic 可用性 |

## 源码修改

无源码修改（无 patches）。

## 依赖版本

无 conan 第三方依赖；仅系统 pthread/mman。

## 验证结果

```bash
# C99 变体构建+运行
make -C C99 CC=clang CFLAGS="-Wall -O2"   # → ffbench
./C99/ffbench  # → MPMC ring buffer benchmark, threads 1-3 正常
# C++11 变体构建+运行
clang++ -Wall -O2 -std=c++17 -pthread C++11/main.cpp -o /tmp/ffbench-cpp11
/tmp/ffbench-cpp11  # → 正常
# 语言预检
ohc-run.py lang-preflight lockfree b08f761900 --src ...work  # detected=cpp ✅
```

## 遗留事项

- test_package 与 conan 配方在 conan-init 阶段生成并验证（G1-G4/L2/L4/L5 门禁）
- HarmonyOS 专项测试在 conan-verify（OHOS profile）阶段执行
---

**编译结束**: 2026-09-27 19:51
**最终状态**: built
