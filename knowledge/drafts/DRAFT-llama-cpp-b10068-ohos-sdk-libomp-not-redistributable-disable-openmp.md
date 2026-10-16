# OHOS SDK 自带的 libomp.so 仅随工具链分发、不可随包再分发——CMake 项目开启 -fopenmp 后构建链接全通过，真机运行时才报 Error loading shared library libomp.so

- **草稿 ID**: DRAFT-llama-cpp-b10068-ohos-sdk-libomp-not-redistributable-disable-openmp
- **来源**: llama/cpp-b10068 HarmonyOS PC 适配（MateBook 真机 conan test 首跑暴露 → GGML_OPENMP=False 改上游内置线程池 → 消费者测试通过、W4 审计 PASS，MR !15476）
- **分类**: toolchain / runtime / packaging / redistribution
- **状态**: 草稿（knowledge/drafts，kv+md 一一对应）

## 问题 / 错误签名

- 真机 `conan test_package` 运行消费者：

```
Error loading shared library libomp.so
（needed by .../lib/libggml-cpu.so）
```

- `patchelf --print-needed libggml-cpu.so` 可见 `libomp.so` 条目；
- **欺骗性特征**：`conan create` 构建链接全绿（构建机 SDK 环境能解析
  `__kmpc_*` 符号），失败只在产物脱离 SDK 环境运行时出现——
  构建机上直接跑一切正常。

## 根因

1. **SDK 的 clang 自带 libomp.so**（LLVM OpenMP runtime），构建机环境
   链接期可解析 `__kmpc_*` 全部符号 → CMake 的 `find_package(OpenMP)`
   检测成功 → 自动开启 `-fopenmp` → 产物 DT_NEEDED 带上 `libomp.so`；
2. 该库**只存在于 SDK 目录**、不在系统默认搜索路径，且属 SDK 组件
   **不可随三方包再分发**——制品部署到真机后加载器找不到它；
3. 与 E127 划界：E127 是 libomp **头文件/宏层**的编译期问题
   （`pthread_cancel undeclared`，KMP 宏 undef 守卫）；本条是**运行期
   库分发**问题，链接完全成功，两者可在同一构建里各自独立出现。

## 影响面

- 一切被 CMake **自动检测**开启 OpenMP 的项目（开发者常常没有显式
  请求 OpenMP——ggml 系的 `GGML_OPENMP` 检测即此类，libggml-cpu.so
  实证中招）；
- 症状共性签名：**构建机可跑、脱机加载失败**——与"打包了不该打包的
  绝对路径"（cvsgraph 条目）同属"构建环境泄漏进产物"家族，但本条
  泄漏的是 DT_NEEDED 里的 SDK 依赖库名。

## 最小处置方案

用上游自有开关关闭 OpenMP，依赖上游内置并行实现：

```python
# conanfile.py generate() —— ggml 系实例
tc.variables["GGML_OPENMP"] = False   # 上游内置线程池，无功能损失（真机消费者测试实证）
```

```python
# 上游无开关的通用阻断
tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = True
```

- **不要**把 SDK 的 libomp.so 拷进包里再分发（许可 + 签名链双重问题）；
- **不要**用 `LD_LIBRARY_PATH` 垫 SDK 路径——本机假绿，CI/消费者
  环境没有该路径（真机绿≠CI 过，ivar stdin 教训同族）；
- PR/notes.md 披露关闭原因（可再分发性 + 运行时加载双重依据）。

## 查重声明

撰写前对知识库 doc/graph/drafts 全量扫描比对（2026-10-12）：
**无同类条目**。相邻主题已逐一核实并划界——E127（libomp 头文件层
pthread_cancel 编译期宏问题，同库不同病：宏层 vs 分发层）、
DRAFT-flang-minimal-runtime-link-contract（flang SDK 运行集**不含**
libomp 的工具链构成问题，不是三方包运行期再分发问题）、
DRAFT-lfortran-runtime-ohos-adaptation（Fortran runtime 移植，主题
不同）。
