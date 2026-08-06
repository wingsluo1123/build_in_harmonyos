# fish 3.7.1 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码 (GitCode镜像)
2. 应用补丁: 0001-cmake4-compatibility.patch
3. CMake 配置:
   ```bash
   cmake $FISH_SRC \
     -DCMAKE_C_COMPILER=clang \
     -DCMAKE_CXX_COMPILER=clang++ \
     -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
     -DWITH_GETTEXT=OFF \
     -DFISH_USE_SYSTEM_PCRE2=OFF \
     -DFETCHCONTENT_SOURCE_DIR_PCRE2=$PCRE2_SRC
   ```
4. 修复 config.h: TPUTS_USES_INT_ARG (CMake check fails without curses lib linked)
5. make -j2 && make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake error: 'test' target is reserved | CMake 4.x 不允许 reserved target name | 注释掉 add_custom_target(test ...) 和 cmake_policy(PUSH/POP) |
| 2 | TPUTS_USES_INT_ARG check fails | CMake check_cxx_source_compiles 不链接 curses 库 | 手动修复 config.h: #define TPUTS_USES_INT_ARG 1 |
| 3 | PCRE2 FetchContent fails | GitHub 不可达 | 提供 PCRE2 10.36 本地源码 + FETCHCONTENT_SOURCE_DIR_PCRE2 |
| 4 | ncurses 不可用 | 系统有 libncurses.so.6 但无头文件 | 从 ncurses 6.4 源码编译静态库 |

## 依赖版本

- ncurses 6.4 (静态编译, 从源码构建)
- PCRE2 10.36 (fish 内嵌, FetchContent 本地源码)
- gettext: 禁用 (不可用)
