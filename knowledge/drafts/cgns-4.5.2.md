# cgns 4.5.2 适配知识

## 构建信息
- 构建系统: CMake
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 编译选项: 禁用 HDF5 (-DCGNS_ENABLE_HDF5=OFF)
- 构建类型: Release

## 关键适配点
1. CMake 构建系统，无 configure 脚本（注意: 非 autotools）
2. HDF5 可选依赖，当前版本禁用 HDF5 可正常编译
3. CMake 可能报 "System is unknown to cmake" 的警告，不影响编译

## 产物
- libcgns.so (shared library)
- libcgns.a (static library)
- 工具: cgnscheck, cgnsconvert, cgnsdiff, cgnslist, cgnsnames, cgnscompress, cgnsupdate

## 测试
- 上游无独立测试套件（需要 HDF5 + MPI）
- conan test_package 验证库链接和工具运行
