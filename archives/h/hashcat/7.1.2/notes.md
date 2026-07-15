# hashcat 7.1.2 适配笔记

## 编译环境
- 构建系统: makefile（自定义构建系统）
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built（编译成功，CI验证通过）

## 编译步骤

1. 下载源码（从 GitHub）
   - URL: https://github.com/hashcat/hashcat/archive/refs/tags/v7.1.2.tar.gz
   - 官方 GitHub Release

2. 初始化编译环境
   - 使用 ohc-run.py init-build
   - 检测到构建系统为 makefile（自定义 Makefile）

3. 修改源码以支持 HarmonyOS
   - 修改 src/Makefile 添加 HarmonyOS 支持
   - 修改 deps/unrar/consio.cpp 处理 getpass 函数
   - 修改 src/affinity.c 禁用 CPU亲和性设置

4. 手动编译
   - make -j1 CC=clang CXX=clang++
   - 需要禁用并行构建（避免 FIFO 问题）

5. 手动安装
   - make install DESTDIR=...
   - 需要使用 ginstall（GNU coreutils）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 不支持 HarmonyOS | 源码硬编码了操作系统列表 | 在 filter 条件中添加 HarmonyOS（3 处） |
| 2 | 使用 gcc 但系统只有 clang | Makefile 默认 CC=gcc | 添加 HarmonyOS 编译器设置块 |
| 3 | CFLAGS_NATIVE 未设置 | 缺少 HarmonyOS 的编译标志定义 | 添加完整的 CFLAGS_NATIVE 设置 |
| 4 | getpass 函数不可用 | HarmonyOS 缺少 getpass 实现 | 修改 unrar/consio.cpp 使用 fgets（添加 __OHOS__ 条件） |
| 5 | pthread_setaffinity_np 未定义 | HarmonyOS 缺少此函数实现 | 在 affinity.c 中添加 __OHOS__ 条件，返回 0 |
| 6 | sse2neon.h 找不到 | 缺少 include 路径 | CFLAGS_NATIVE 添加 -Ideps/sse2neon/ |
| 7 | install 命令不可用 | 系统 install 不是 GNU 版本 | 使用 ginstall（GNU coreutils） |
| 8 | HMDFS 不支持 FIFO | make jobserver 需要 mkfifo | 使用 -j1 禁用并行构建 |
| 9 | Python.h 找不到 | python3-config 返回错误路径 | 通过 PYTHON_CFLAGS 传递正确的 include 路径 |

## 源码修改

### 补丁 1: deps/unrar/consio.cpp
- 类型: 平台适配
- 用途: 替换 getpass 为 fgets
- 守卫: #if defined(_EMX) || defined (__VMS) || defined(__OHOS__)

### 补丁 2: src/Makefile
- 类型: 平台适配
- 用途: 添加 HarmonyOS 操作系统支持
- 修改点:
  - 操作系统检测列表添加 HarmonyOS
  - 编译器设置（CC=clang, CXX=clang++）
  - CFLAGS_NATIVE 设置（-D__OHOS__, -Ideps/sse2neon/）
  - install 目标检测添加 HarmonyOS
  - INSTALL=ginstall 设置

### 补丁 3: src/affinity.c
- 类型: 平台适配
- 用途: 禁用 CPU亲和性设置
- 守卫: #if defined (__CYGWIN__) || defined(__OHOS__)

## 依赖版本

- GNU sed 4.9
- GNU coreutils 9.10（ginstall）
- Python 3.12.9（可选，用于 Python bridge 插件）

## 验证结果

- ✅ G2 conan create 通过（干净构建验证）
- ✅ L2 smoke test 通过（hashcat --version 返回 v7.1.2）
- ✅ L4 安全扫描通过（NX/PIE/RELRO）
- ✅ W3 本地 CI 模拟通过（setup.sh + build_and_test.sh）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hashcat | 1.4M | 主程序二进制 |
| patches/*.patch | 3 files | 平台适配补丁 |
| conanfile.py | Conan 配方 | CI 输入 |
| conandata.yml | 源码+补丁声明 | CI 输入 |
| test_package/ | 测试包 | CI 输入 |

## 注意事项

1. **HMDFS 限制**: 不支持 ln -s、FIFO（mkfifo）、chmod/chown 可能无效
2. **需要 GNU 工具**: 必须安装 GNU sed、GNU coreutils（ginstall）
3. **禁用功能**: CPU亲和性、Rust 插件（可选）
4. **构建系统**: hashcat 使用自定义 Makefile，不是标准 autotools/cmake
5. **Python 插件**: 可选，需要正确的 Python.h include 路径

---

**最终状态**: built
