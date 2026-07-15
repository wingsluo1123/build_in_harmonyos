# nymphcast 0.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang / clang++
- 状态: built
- 平台: HarmonyOS PC (aarch64)
- 源码来源: https://github.com/MayaPosch/NymphCast/archive/refs/tags/v0.2.tar.gz

## 软件信息
- 名称: nymphcast
- 版本: 0.2
- 上游仓库: MayaPosch/NymphCast
- 许可证: BSD-3-Clause
- 描述: Audio/video casting and streaming receiver application
- 产物: nymphcast (可执行文件) + nymphcast_server (服务端)
- 依赖: SDL2, FreeType2, libcurl

## Conan 配方说明

本归档采用 Conan 2.x CMAKE 配方：

- `conanfile.py`: CMAKE 构建配方
  - settings = "os", "compiler", "build_type", "arch"
  - OHOS 平台删除 shared 选项（HarmonyOS 仅支持静态库）
  - exports_sources = "patches/*"
- `conandata.yml`: 源码 URL + sha256（留空，CI 校验）
- `test_package/`: 测试包，运行 `nymphcast --help`

## 编译步骤

1. Conan 下载源码：`get(self, **self.conan_data["sources"], strip_root=True)`
2. 生成工具链：`CMakeToolchain`
3. 配置：`cmake.configure()`
4. 构建：`cmake.build()`
5. 安装：`cmake.install()`

## 遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 平台不支持动态库 | HarmonyOS PC 当前仅支持静态链接 | config_options 中 OHOS 平台 rm_safe("shared") |
| 2 | sha256 暂未填入 | CI 环境校验 | conandata.yml 中 sha256 留空，由 CI 下载校验后回填 |

## 验证结果

test_package 验证 nymphcast 核心功能，运行 `nymphcast --help`。

## 注意事项

- nymphcast 为积分赛范畴
- 默认静态构建（shared=False），符合系统库规则
