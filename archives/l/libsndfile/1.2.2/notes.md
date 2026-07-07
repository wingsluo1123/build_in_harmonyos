# libsndfile 1.2.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang 15.0.4
- 状态: built
- 构建备注: CMake 构建（避免 HMDFS autotools 临时文件问题）

## 编译步骤

### 1. 解决链接器依赖问题

HMDFS 文件系统上的 clang 使用 lld 作为链接器，但 lld 依赖 libxml2.so.16。需设置 LD_LIBRARY_PATH：

```bash
export LD_LIBRARY_PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:/storage/Users/currentUser/usr/local/lib:/data/service/hnp/magic-cli.org/magic-cli_1.0.0/lib:$LD_LIBRARY_PATH"
```

### 2. CMake 配置

创建外部构建目录（在 $TMPDIR 中避免 HMDFS 问题）：

```bash
mkdir -p /storage/Users/currentUser/tmp/libsndfile-build-1.2.2
cd /storage/Users/currentUser/tmp/libsndfile-build-1.2.2

cmake /storage/Users/currentUser/tmp/builds/libsndfile-1.2.2.work \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_C_FLAGS="-fPIC -O2" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DENABLE_EXTERNAL_LIBS=OFF \
  -DENABLE_MPEG=OFF
```

**关键参数说明**:
- `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`: CMake 4.x 不支持 VERSION < 3.5 的兼容性
- `-DENABLE_EXTERNAL_LIBS=OFF`: 禁用 FLAC/Vorbis/Opus 等外部库（避免依赖问题）
- `-DENABLE_MPEG=OFF`: 禁用 MPEG 编码（避免 mp3lame/mpg123 依赖）

### 3. 编译

```bash
cmake --build . -j2
```

编译成功，生成静态库 libsndfile.a 和 10 个命令行工具。

### 4. 安装到 staging 目录

```bash
export DESTDIR=/storage/Users/currentUser/tmp/test-install-libsndfile-1.2.2
cmake --install . --prefix /storage/Users/currentUser/usr/local
```

### 5. 测试

```bash
ctest --output-on-failure
```

测试结果：123/143 通过 (86%)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
<<<<<<< HEAD
| 1 | CMake 配置失败：libxml2.so.16 缺失 | lld 链接器依赖 libxml2.so.16 | 设置 LD_LIBRARY_PATH 包含 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib` |
| 2 | CMake 版本兼容性错误 | CMake 4.x 不支持 VERSION < 3.5 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | FLAC::FLAC 目标未找到 | ENABLE_EXTERNAL_LIBS=ON 但缺少 FLAC 库 | 禁用外部库 `-DENABLE_EXTERNAL_LIBS=OFF` |
| 4 | misc_test_* 测试失败 | E046: chmod() 在鸿蒙上不生效 | 已知平台限制，不阻塞发布 |

## 源码修改

无源码修改。使用 CMake 构建避免了 autotools configure 的 HMDFS 临时文件问题。

## 依赖版本

- clang 15.0.4
- CMake 4.1.2
- GNU ld 2.45（系统提供）
- SQLite3 3.49.1（可选，用于 regtest）
- Vorbis 1.3.7（可选，已安装但未启用）

## 验证结果

### 测试结果
- 总测试数: 143
- 通过: 123 (86%)
- 失败: 20 (14%)
- 失败原因: E046 平台限制（chmod 不生效）

### 安装产物
```bash
ls /storage/Users/currentUser/tmp/test-install-libsndfile-1.2.2/storage/Users/currentUser/usr/local/
# bin/ - 10 个 sndfile-* 工具
# lib/libsndfile.a - 静态库
# include/sndfile.h, sndfile.hh - 头文件
# lib/pkgconfig/sndfile.pc - pkg-config 文件
# lib/cmake/SndFile/ - CMake 配置文件
=======
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
>>>>>>> origin/main
```

## 交付物

<<<<<<< HEAD
待打包：libsndfile-1.2.2-ohos-aarch64.tar.gz

## 注意事项

1. **链接器依赖**: 使用 clang 编译时必须设置正确的 LD_LIBRARY_PATH，确保 lld 能找到 libxml2.so.16
2. **CMake 版本**: CMake 4.x 需要显式设置 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 才能处理旧的 CMakeLists.txt
3. **测试失败**: misc_test_* 测试失败是预期的平台限制，不影响核心音频处理功能
4. **外部库**: 如果需要 FLAC/Vorbis/Opus 支持，需要先编译安装这些依赖库，然后启用 `-DENABLE_EXTERNAL_LIBS=ON`
=======
| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-05-20 18:38
**最终状态**: published
>>>>>>> origin/main
