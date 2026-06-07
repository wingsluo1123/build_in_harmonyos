# E105 — lld 链接器缺少 libxml2 运行时依赖

## 症状

```
Error loading shared library libxml2.so.16: (needed by /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld)
Error relocating /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld: xmlFreeDoc: symbol not found
Error relocating /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld: xmlReadMemory: symbol not found
...
clang-15: error: unable to execute command: No such file or directory
clang-15: error: linker command failed due to signal (use -v to see invocation)
```

## 根因分析

OHOS SDK 的 lld 链接器（ld.lld）在编译时链接了 libxml2.so.16 库。当 clang++ 调用 lld 进行链接时，lld 在运行时需要加载 libxml2 来解析 XML 格式的链接脚本或配置文件。

然而，libxml2.so.16 不在 lld 的默认搜索路径中，导致动态链接器找不到该库。即使设置了 `-L` 参数或 `LD_LIBRARY_PATH`，问题仍然存在，因为 lld 本身启动时就失败，而不是链接参数问题。

**关键点**：这不是编译时的库依赖问题，而是链接器工具本身的运行时依赖缺失。

## 解决方案

### 方案 1：使用 ld.bfd 代替 lld（推荐）

通过 `-fuse-ld=bfd` 参数强制 clang++ 使用 GNU ld.bfd 链接器，避免 lld 的 libxml2 依赖问题。

**CMake 配置**：
```cmake
cmake -B build \
  -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=bfd" \
  -DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=bfd" \
  -DCMAKE_MODULE_LINKER_FLAGS="-fuse-ld=bfd"
```

**Toolchain 文件示例**：
```cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)
set(CMAKE_EXE_LINKER_FLAGS "-fuse-ld=bfd")
set(CMAKE_SHARED_LINKER_FLAGS "-fuse-ld=bfd")
set(CMAKE_MODULE_LINKER_FLAGS "-fuse-ld=bfd")
```

**验证**：
```bash
ls /data/service/hnp/bin/ld.bfd  # 确认 ld.bfd 存在
/data/service/hnp/bin/ld.bfd --version  # GNU ld (GNU Binutils) 2.45
```

### 方案 2：设置库路径（不推荐）

将 libxml2.so.16 添加到库搜索路径，但这可能影响其他软件且不够稳健：

```bash
export LD_LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH"
```

## 禁止策略

- ❌ 不要使用 `-fuse-ld=lld` 或强制使用 lld
- ❌ 不要尝试手动修复 lld 的依赖问题（应该使用替代链接器）

## 相关条目

- **E012**: ar 命令缺失 → LLVM 工具链问题
- **E064**: conftest 无法执行 → 安全弹窗/编译器测试失败

## 元数据

- **来源事件**: abseil-cpp 20260107.1 编译
- **贡献者**: DFCF
- **创建日期**: 2026-05-29