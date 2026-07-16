# cmatrix 2.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-16
- 编译器: clang (OHOS toolchain, version 15)
- 状态: verified

## 编译步骤
1. 下载源码（abishekvashok/cmatrix v2.0，官方上游 bisqwit/cmatrix 无 release tag）
2. 应用补丁：更新 CMake 最低版本，并改为独立发现 ncurses 库
3. 创建可适配多种系统头布局的 ncurses.h 包装器；系统未安装头文件时使用随配方导出的 ncurses 6.4 生成头
4. cmake configure + cmake build
5. 手动打包 bin/cmatrix

## 源码来源
- 官方上游: bisqwit/cmatrix（无 v2.0 release tag）
- 实际使用: abishekvashok/cmatrix（v2.0 tag 唯一发布源）
- R39 例外: 已获主编批准，追溯记录见 PR #1953

## 依赖
- ncurses（CI/目标环境系统库，非 Conan 包；头文件缺失时使用随配方导出的兼容头）

## 验证结果
```bash
$ conan create archives/c/cmatrix/2.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 编译通过，test_package 通过
$ /var/conan/cmatrix-2.0/p/b/.../p/bin/cmatrix -V
CMatrix version 2.0 (compiled 17:12:38, Jul 15 2026)
Email: abishekvashok@gmail.com
Web: https://github.com/abishekvashok/cmatrix
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 不兼容 cmake_minimum_required(VERSION 2.8) | CMake 4.x 移除了 3.5 以下版本兼容 | 补丁修改为 3.5 |
| 2 | CI 编译找不到 curses.h | Worker 已安装 ncurses 静态库，但未安装对应开发头文件 | 导出 ncurses 6.4 生成头作为 fallback，并补丁分离库与头文件发现 |
| 3 | CMake install 找不到 CMakeRelink.dir | CMake 4.x 生成新式 install 路径 | 手动 copy 二进制到 package bin/ |

## 注意事项
- cmatrix 是终端 screensaver，需要 ncurses 库
- ncurses 未发布为 Conan 包，使用系统库
- conandata.yml 使用 abishekvashok/cmatrix 源（R39 例外）