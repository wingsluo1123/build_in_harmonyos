# HiGHS 1.13.1 适配笔记

## 编译环境
- 系统：Windows 10 (Git Bash) / MSYS2 Clang64
- 编译器：clang 22.1.7
- CMake：4.4.0
- Conan：2.29.1

## 编译步骤
1. `conan create archives/h/highs/1.13.1/ --build=missing --user=ohpcd --channel=stable`

## 遇到的问题与解决方案
1. **CMakeLists.txt 禁止在源码目录构建**
   - 问题：CMakeLists.txt 第 36 行检查 `if(EXISTS "${LOC_PATH}")` 强制要求 out-of-source 构建
   - 解决：在 conanfile.py 的 build() 方法中通过字符串替换将 `if(EXISTS "${LOC_PATH}")` 改为 `if(FALSE)`

## 验证结果
- conan create 编译通过
- test_package 单测 1/1 通过