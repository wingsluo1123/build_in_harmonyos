# expat 2.6.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

使用 cmake 构建系统编译 expat：

```bash
# 设置环境变量（关键：lld 链接器依赖 libxml2）
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib

# 创建构建目录
mkdir -p build-cmake && cd build-cmake

# cmake 配置
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
         -DCMAKE_C_COMPILER=clang \
         -DCMAKE_CXX_COMPILER=clang++ \
         -DCMAKE_BUILD_TYPE=Release

# 编译
make -j2

# 测试
make test

# 安装到 staging
make install DESTDIR=$HOME/tmp/test-install-expat-2.6.0

# 安装到本地
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure failed: C compiler cannot create executables | lld 链接器依赖 libxml2.so.16，找不到库 | 设置 LD_LIBRARY_PATH 包含 SDK 的 llvm/lib 目录 |
| 2 | autotools configure 临时目录权限问题 | 当前环境的临时目录权限限制 | 使用 cmake 构建系统代替 autotools |

## 源码修改

无补丁，使用 cmake 构建系统直接编译。

## 依赖版本

无外部依赖，expat 是独立的 XML 解析库。

## 验证结果

```bash
$ xmlwf --version
xmlwf using expat_2.6.0

$ pkg-config --modversion expat
2.6.0

$ pkg-config --libs expat
-L/storage/Users/currentUser/usr/local/lib -lexpat
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| expat-2.6.0-ohos-aarch64.tar.gz | 245K | 预编译包 |

## 注意事项

1. **必须设置 LD_LIBRARY_PATH**：编译前需要将 SDK 的 llvm/lib 目录添加到 LD_LIBRARY_PATH，否则 lld 链接器无法找到 libxml2.so.16
2. **推荐使用 cmake**：autotools 在当前环境可能有临时目录权限问题，cmake 更稳定
---

**编译结束**: 2026-05-29 17:17
**最终状态**: built
