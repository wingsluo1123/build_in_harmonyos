# E081: lld 链接器找不到 libxml2.so.16

## 错误现象

编译过程中出现以下错误：

```
Error loading shared library libxml2.so.16: (needed by /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld)
Error relocating /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld: xmlFreeDoc: symbol not found
...
clang-15: error: unable to execute command: No such file or directory
clang-15: error: linker command failed due to signal (use -v to see invocation)
```

configure 检测阶段显示：

```
checking whether the C compiler works... no
configure: error: C compiler cannot create executables
```

## 根因分析

鸿蒙 SDK 的 clang 编译器默认使用 lld 链接器（位于 `llvm/bin/lld`）。lld 是一个动态链接的可执行文件，其 RUNPATH 设置为 `$ORIGIN/../lib`，依赖 `libxml2.so.16`。

虽然 SDK 的 `llvm/lib` 目录中存在 `libxml2.so.16`，但由于环境变量 `LD_LIBRARY_PATH` 未包含该路径，lld 在运行时无法找到依赖库，导致链接器崩溃。

## 解决方案

**方案一（推荐）：设置 LD_LIBRARY_PATH**

在编译前将 SDK 的 llvm/lib 目录添加到 LD_LIBRARY_PATH：

```bash
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
```

然后重新运行 configure 或 cmake。

**方案二：使用 GNU ld 链接器**

如果仍有问题，尝试强制使用 GNU ld：

```bash
clang -B/data/service/hnp/bin/ -fuse-ld=ld ...
```

## 验证方法

```bash
# 测试编译器是否正常
echo '#include <stdio.h>' > $TMPDIR/test.c
echo 'int main() { printf("test"); return 0; }' >> $TMPDIR/test.c
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:$LD_LIBRARY_PATH
clang $TMPDIR/test.c -o $TMPDIR/test
file $TMPDIR/test
# 应输出: ELF 64-bit LSB pie executable, ARM aarch64...
```

## 影响范围

所有使用 clang 编译器的软件编译，包括：
- autotools 项目（configure + make）
- cmake 项目
- 手动编译

## 相关知识条目

- E053: cc1plus 不可用，必须使用 clang++

## 注意事项

1. 此问题在每次新编译会话中都会出现，需要确保 LD_LIBRARY_PATH 正确设置
2. 可以将此设置添加到 shell 配置文件（如 `.zshrc`）中自动生效
3. SDK 版本可能变化，路径中的版本号需要根据实际情况调整