# ParMETIS 4.0.3 适配笔记

## 基本信息

- **上游仓库**：https://github.com/KarypisLab/ParMETIS
- **下载源**：https://karypis.github.io/glaros/files/sw/parmetis/parmetis-4.0.3.tar.gz
- **构建系统**：CMake 2.8+（顶层有 Makefile 包装器）
- **许可证**：University of Minnesota（研究/教育免费，商业需授权）

## 依赖关系

```
parmetis/4.0.3
├── open-mpi/5.0.10  (外部 conan 依赖)
├── metis/           (源码内 bundle)
└── metis/GKlib/     (源码内 bundle)
```

## 适配要点

### 1. CMake 构建策略
上游 CMakeLists.txt 中 FindMPI 被注释掉，设计意图是通过 `cc=mpicc` 让 MPI 编译器包装器
自动注入 MPI 头文件/库路径。本配方遵循此设计：设置 `CMAKE_C_COMPILER` 为 open-mpi 的 mpicc。

### 2. GKLIB_PATH 和 METIS_PATH
ParMETIS 在源码中 bundle 了 METIS 和 GKlib，不需要外部 METIS 依赖。
cmake 需设置：
- `GKLIB_PATH=<source_folder>/metis/GKlib`
- `METIS_PATH=<source_folder>/metis`

### 3. 上游测试缺失
ParMETIS 4.0.3 不发布测试套件（`add_subdirectory(test)` 被注释掉且代码未包含在 tarball 中）。
test_package 使用自编测试用例，调用 ParMETIS_V3_PartKway API 进行功能验证。

### 4. 平台兼容性
- CMakeLists.txt 使用 `execute_process(... create_symlink ...)`，OHOS HMDFS 可能不支持
- 默认静态库编译（`SHARED=OFF`）
- 需要 OHOS 上验证 conan create 通过

## 待验证（鸿蒙 PC）

- [ ] conan create 编译通过
- [ ] test_package 在 MPI singleton 模式下运行通过
- [ ] 产物完整性（libparmetis.a + libmetis.a + 头文件 + 命令行工具）
