# mm_file 1.0.0 — 适配笔记

## 概述

- 上游: https://github.com/jermp/mm_file
- 官方标签: v1.0.0（commit 41ca01bd11f2f84e485d823231d7740794bd0ef5，2021-05-06 Release "Version 1.0.0"）
- 类型: C++11 header-only 库（单头文件 include/mm_file/mm_file.hpp，176 行）
- 功能: 内存映射文件读写（mm::file_source / mm::file_sink / mm::advice），
  等价 boost::mapped_file 能力但无 boost 依赖
- 依赖: 无第三方依赖，仅 POSIX 系统调用（mmap/munmap/open/fstat/close/posix_madvise/ftruncate）
- 适配路径: archives/m/mm_file/1.0.0

## Bootstrap

- 官方源校验: tarball SHA-256 = 1bb1b057ea1f1b06366513a198c39277740f743b59a0e5669f2694698f52018b
  （github.com/jermp/mm_file/archive/refs/tags/v1.0.0.tar.gz 与 codeload 下载逐字节一致）
- 结构: include/mm_file/mm_file.hpp + test/test.cpp + test/CMakeLists.txt + LICENSE(BSD? MIT?) + README
  - LICENSE 为 MIT
- init-build 嵌套检测误把 test/ 提升为源码根，已修正为上游真实布局
  （include/ 与 test/ 平级）；归档 conan 配方使用 strip_root=True 从官方 tarball 解压，不受影响

## 配方要点

- conanfile.py: header-only（package_type=header-library, no_copy_source, 无 build()）
  - package(): 安装 include/mm_file/mm_file.hpp 与 LICENSE
  - package_info(): cpp_info 仅头文件（bindirs/libdirs 置空，cmake 目标 mm_file::mm_file）
  - R32: 无 settings.os 分支（无编译，头文件在 Linux/OHOS 下均使用 POSIX mmap API）
- conandata.yml: 官方 GitHub tag 源 URL + SHA-256
- test_package/: CMake 消费者测试，真实调用 file_sink 写 / file_source 读回校验 / iterator，
  非空壳（R34/PF3）

## 上游测试（R51 三步法）

- 上游测试清点: test/test.cpp（单文件单可执行 test），由 test/CMakeLists.txt 构建
- 注意: 上游 CMakeLists 带 -march=native / -stdlib=libc++（Clang）/ -ggdb，
  本机适配验证时需剥离 -march=native（OHOS 交叉工具链不支持 native 探测）
- 适配验证: 以等价 C++11 编译参数直接编译 test.cpp 并实际运行（见 reports/）

## L0i 依赖解析

- mm_file 无 requires/tool_requires → L0i 检查对象为当前库（自身），无第三方依赖待解析
- 无未发布依赖，无依赖/基础设施阻塞
---

**编译结束**: 2026-09-29 11:43
**最终状态**: built
