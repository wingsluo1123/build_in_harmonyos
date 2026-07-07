# libsndfile

## 简介

libsndfile 是一个 C 语言库，用于读取和写入采样音频文件，支持 WAV、AIFF、AU、FLAC、OGG 等多种格式。

## OHOS 适配

### 适配要点

1. **构建系统选择**: 推荐使用 CMake 构建，避免 HMDFS 文件系统上 autotools configure 的临时文件问题
2. **链接器依赖**: clang 使用 lld 链接器，依赖 libxml2.so.16，需设置 LD_LIBRARY_PATH：
   ```bash
   export LD_LIBRARY_PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:$LD_LIBRARY_PATH"
   ```
3. **CMake 版本兼容**: CMake 4.x 需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
4. **外部库支持**: 默认禁用 FLAC/Vorbis/Opus 等外部库（`-DENABLE_EXTERNAL_LIBS=OFF -DENABLE_MPEG=OFF`）

### 已知问题

- misc_test_* 测试失败是 E046 平台限制（chmod 不生效），不影响核心音频处理功能

### 与 Linux 的差异

- 鸿蒙平台的 chmod() 系统调用受限，部分测试用例无法通过
- 使用静态库构建（`-DBUILD_SHARED_LIBS=OFF`）以避免动态库签名问题

## 排除与替代

无

## 依赖

### 编译依赖
- clang 15.0.4+
- CMake 4.x（或 CMake 3.x）

### 运行依赖
无（可选：SQLite3 用于 regtest）

### 可选依赖
- FLAC 1.3.x（`-DENABLE_EXTERNAL_LIBS=ON` 时需要）
- Vorbis 1.3.x（`-DENABLE_EXTERNAL_LIBS=ON` 时需要）
- Opus 1.3.x（`-DENABLE_EXTERNAL_LIBS=ON` 时需要）

## 功能验证

安装后可通过以下命令验证：

```bash
# 检查静态库
ls ~/usr/local/lib/libsndfile.a

# 检查头文件
ls ~/usr/local/include/sndfile.h

# 使用 sndfile-info 工具
~/usr/local/bin/sndfile-info --version

# 编译测试程序
cat > test_sndfile.c << 'EOF'
#include <sndfile.h>
#include <stdio.h>
int main() {
    printf("libsndfile version: %s\n", sf_version_string());
    return 0;
}
EOF
clang test_sndfile.c -I~/usr/local/include -L~/usr/local/lib -lsndfile -o test_sndfile
./test_sndfile
```

## 参考

- 官网: https://libsndfile.github.io/libsndfile/
- GitHub: https://github.com/libsndfile/libsndfile
- API 文档: https://libsndfile.github.io/libsndfile/api.html
