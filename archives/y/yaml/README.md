# yaml (libyaml)

YAML 1.1 解析器和发射器，用 C 语言编写。

## 软件信息

| 属性 | 值 |
|------|-----|
| 名称 | yaml (libyaml) |
| 描述 | YAML 1.1 parser and emitter written in C |
| 主页 | https://github.com/yaml/libyaml |
| 许可证 | MIT |
| 构建系统 | cmake |

## 可用版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.2.5 | built | 2026-06-25 |

## 版本 0.2.5

### 构建配置
- 构建系统: cmake
- 编译器: clang 15.0.4
- 配置选项: `-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- 依赖: 无

### 产物
- `lib/libyaml.a` — 静态库 (156KB)
- `include/yaml.h` — 头文件
- `cmake/yaml*.cmake` — CMake 包配置文件

### 补丁
1. `0001-cmake-config.h.in.patch` — 补充缺失的 cmake 配置模板
2. `0002-tests-CMakeLists.txt.patch` — 补充缺失的测试 CMakeLists.txt
3. `0003-yamlConfig.cmake.in.patch` — 补充缺失的 CMake 包配置模板

> 注: yaml-0.2.5 release tarball 未包含 cmake 构建所需的模板文件，这些文件从上游 git tag 0.2.5 获取。

### 注意事项
- libyaml 默认构建为静态库 (libyaml.a)，无共享库
- 无独立二进制文件（纯库）
- CMake 4.x 需要 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
