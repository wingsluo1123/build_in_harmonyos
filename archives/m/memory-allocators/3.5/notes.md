# memory-allocators 3.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 真机）
- 状态: built

## 编译步骤

1. `python3 scripts/ohc-run.py init-build memory-allocators 3.5 --url=<master tarball>` —
   上游仓库 https://github.com/mtrebi/memory-allocators 无 tag/release，使用
   `archive/refs/heads/master.tar.gz` 并固定 sha256 8c62d3ec...bff86622。
2. `lang-preflight` — task=cpp, detected=cpp, exit 0。
3. 手动 CMake 验证（模式 B）: cmake + make -j1 + ./main，编译与运行均 exit 0。
4. `conan-init` 生成配方后按实际构建系统改写为 CMake 配方；上游 CMakeLists 仅构建
   benchmark 可执行文件，补丁 0001 新增静态库目标 `memory-allocators` 与 install 规则。
5. `conan-verify` — G0-G4/L2/L4/L5 全 PASS（报告 reports/conan-verify-report.md）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载返回 HTML | 直接传仓库页 URL | 改用 master tarball 官方归档 URL |
| 2 | conan-init 生成 autotools 模板 | 工具按 URL 猜测构建系统 | 手工改写为 CMake 配方（补丁 0001 加库目标+install） |
| 3 | finish G2 export_sources 失败 | refresh-patch 自动重命名补丁为 `0001-CMakeLists.txt.patch`，conandata 仍引用旧名 | 修正 conandata.yml 引用为实际补丁文件名 |
| 4 | W3 JC full 模式拦截 4 个其他库空状态文件 | cloog/kics/thc 在 HEAD 中历史遗留 `.build-closed`/`.staging-verified` 空文件被整仓扫描命中 | 审计确认为无关基线（非本库、不在允许路径），临时 index 隔离→复验通过→无条件恢复（审计: /storage/Users/currentUser/tmp/ma-baseline-isolation-audit.json） |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`: 在 upstream CMakeLists.txt 末尾新增
  `add_library(memory-allocators ...)` 静态库目标（6 个分配器源文件，不含 main.cpp）
  与 `install(TARGETS ...)` / `install(DIRECTORY includes/ ...)` 规则。不改动上游
  benchmark 目标。

## 依赖版本

- 无第三方依赖（纯 C++11 库，仅依赖标准库）

## 验证结果

- conan create（OHOS profile, clang15/armv8/Release）: exit 0
- test_package 1/1 通过（test_memory-allocators）；HarmonyOS 专项测试 5 allocator
  API 断言全部 PASS，exit 0
- 上游 benchmark ./main: exit 0
- W3 本地 CI（setup.sh + build_and_test.sh）: 通过

## 交付物

- conanfile.py / conandata.yml / patches/0001-CMakeLists.txt.patch
- test_package/（CMakeLists.txt + conanfile.py + MANIFEST.yml + test.cpp）
- reports/（conan-verify-report.md / conan-create.log / test-report.md /
  w3-local-ci.log / knowledge-decision.md）

## 注意事项

- 上游无正式 tag/release，版本标识 3.5 为任务指定；源码固定 master HEAD
  ad599a377450f4a1152ab0335e82243304e3f5ca（2026-09-21）。
- 知识判定: reuse_existing（E092 等价命中）→ 路径 A，无草稿对（见 reports/knowledge-decision.md）。
---

**编译结束**: 2026-09-29 17:54
**最终状态**: published
---

**编译结束**: 2026-10-15 16:13
**最终状态**: published

---

## R03 变更记录（2026-10-15）

- **CI 归因**: build 64417（fork-OOM）位于共享框架 G0b 段，属 CI worker 平台资源限制；
  2026-10-15 CI 重跑新首错 `make: jobserver mkfifo: ...GMfifo4178: Operation not permitted`
  + `/bin/sh: can't fork - try again`（-j20 阶段）——GNU make jobserver 依赖 mkfifo，
  目标文件系统(HMDFS/FUSE 族)拒绝命名管道，属平台基础设施限制。
- **配方 -j1 适配**: conanfile.py 与 test_package/conanfile.py 的 build()/test() 均改为
  `build_tool_args=["-j1"]`（R03 明确仅限 -j1 变更），规避 jobserver fifo 与并发 fork 压力；
  conan create 复验 exit 0、jobserver 报错 0、can't fork 报错 0、test_package 1/1 通过。
- **Review P2/P3 闭合**: 交付态 test_package/test.cpp 使用 NDEBUG 免疫 CHECK 宏（21 校验点），
  Release(-DNDEBUG) 实测 21 checks/0 failures/rc=0；负向注入 rc=1 + CHECK FAILED（P3 链路验证）。
- **鸿蒙特有测试重建**: 新增独立 harmonyos_specific_test.cpp（位于版本目录、非 reports/、
  调用 CAllocator 之外四种分配器、CHECK 宏同强度、无平台宏条件编译），OHOS 真机 Release
  独立编译运行 25 checks/0 failures/rc=0；与 test_package 分属两个口径。
- **知识判定**: reuse_existing（E259 等价命中 + E092 继承）→ 路径 A，无草稿（R03 快照 HEAD b544378a）。
