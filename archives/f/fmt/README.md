# fmt 10.2.0 for HarmonyOS

## 概述

{fmt} 是一个开源的 C++ 格式化库，提供快速、安全的字符串格式化功能，支持 C++11 及以上版本。

本文档记录 fmt 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试结果。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | fmt |
| 版本 | 10.2.0 |
| 下载地址 | https://github.com/fmtlib/fmt/releases/download/10.2.0/fmt-10.2.0.tar.gz |
| 官方文档 | https://fmt.dev/latest/index.html |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0+ |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 (aarch64-unknown-linux-ohos) |
| 构建系统 | cmake |

## 编译步骤

```bash
# 1. 下载源码（GitHub 可能超时，可使用 Gitee 镜像）
wget https://github.com/fmtlib/fmt/releases/download/10.2.0/fmt-10.2.0.tar.gz
# 或
curl -L https://gitee.com/mirrors/fmt/repository/archive/10.2.0.tar.gz -o fmt-10.2.0.tar.gz

tar -xzf fmt-10.2.0.tar.gz
cd fmt-10.2.0

# 2. 创建构建目录
mkdir build && cd build

# 3. 配置（关键：设置 CMAKE_SYSTEM_NAME=Linux）
cmake \
    -DCMAKE_SYSTEM_NAME=Linux \
    -DCMAKE_CXX_COMPILER=clang++ \
    -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
    -DBUILD_SHARED_LIBS=OFF \
    -DFMT_TEST=OFF \
    ..

# 4. 编译
make -j$(nproc)

# 5. 安装（staging）
make install DESTDIR=$HOME/tmp/test-install-fmt-10.2.0

# 6. 安装到本地
make install
```

## 补丁说明

无需补丁，源码无修改。

## 遇到的问题

### 问题1: CMake 无法识别 HarmonyOS 平台

**现象**: 
```
System is unknown to cmake, create:
Platform/HarmonyOS to use this system
The C++ compiler is not able to compile a simple test program
```

**原因**: CMake 缺少 HarmonyOS 平台文件，导致 ABI 检测失败

**解决**: 设置 `CMAKE_SYSTEM_NAME=Linux` 绕过平台检测。fmt 的代码与平台无关，使用 Linux 作为系统名称不影响功能。

### 问题2: GitHub 下载超时

**现象**: wget/curl 连接 GitHub 超时

**原因**: 网络限制

**解决**: 使用 Gitee 镜像下载源码

## 测试结果

详见 [notes.md](./10.2.0/notes.md)

| 测试项 | 结果 |
|--------|------|
| 编译 | ✅ 成功 |
| 链接 | ✅ 静态库链接正常 |
| 功能测试 | ✅ format() 函数正常 |

## 验证安装

```bash
# 检查安装
ls -la $HOME/usr/local/lib/libfmt.a
ls -la $HOME/usr/local/include/fmt/

# 功能测试
cat > test_fmt.cpp << 'EOF'
#include <fmt/format.h>
#include <iostream>
int main() {
    std::string s = fmt::format("Hello {}!", "fmt");
    std::cout << s << std::endl;
    return 0;
}
EOF

clang++ -I$HOME/usr/local/include test_fmt.cpp $HOME/usr/local/lib/libfmt.a -o test_fmt
./test_fmt
# 输出: Hello fmt!
```

## 注意事项

1. **必须设置 CMAKE_SYSTEM_NAME=Linux**：这是绕过 CMake 平台识别问题的关键
2. **建议编译为静态库**：设置 `BUILD_SHARED_LIBS=OFF` 以避免 ELF 签名问题
3. **fmt 是 header-only 可选**：如果只需要头文件，可以使用 `fmt-header-only`

## 经验总结

1. 对于纯 C++ 库（无平台依赖），设置 `CMAKE_SYSTEM_NAME=Linux` 是最简单的适配方法
2. 静态库编译避免了动态库的 ELF 签名和 RPATH 问题
3. Gitee 镜像可以作为 GitHub 的下载备选方案

## 参考资料

- [fmt 官方文档](https://fmt.dev/latest/index.html)
- [fmt GitHub](https://github.com/fmtlib/fmt)
- [CMake 平台支持](https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html#cross-compiling)