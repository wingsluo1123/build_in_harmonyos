# sra-sdk 3.2.1 适配笔记

## 编译环境
- 构建系统: CMake（sra-tools 与 ncbi-vdb 两棵配套源码树）
- 编译日期: 2026-10-18
- 编译器: clang/clang++ 15.0.4（OHOS SDK，target aarch64-unknown-linux-ohos）
- 状态: built（conan create 通过，含 test_package）

## 上游构成

sra-sdk 是 NCBI 官方发行名（Debian 源码包 `sra-sdk`），实际由两棵配套源码树构建：

| 组件 | 仓库 | 作用 |
|------|------|------|
| sra-tools | https://github.com/ncbi/sra-tools | prefetch/fasterq-dump/vdb-dump 等工具与 NGS 绑定 |
| ncbi-vdb | https://github.com/ncbi/ncbi-vdb | VDB 存储引擎与 NGS/VDB 库 |

ncbi-vdb 未在制品仓发布，且 sra-tools 的 CMake 必须指向 ncbi-vdb 的头文件与库；
按 NCBI 官方发行方式，配方在 `source()` 同时下载两棵树并在 `build()` 中先建 VDB 再建工具。

## 编译步骤

```bash
# 1. ncbi-vdb（静态库 + 共享库）
cmake -G Ninja -S ncbi-vdb -B build/vdb \
  -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake> \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_BUILD_TYPE=Release -DLIBS_ONLY=ON
ninja -C build/vdb

# 2. sra-tools（工具 + 测试 + NGS 库）
cmake -G Ninja -S sra-tools -B build/sra \
  -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake> \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_BUILD_TYPE=Release -DTOOLS_ONLY=OFF \
  -DVDB_LIBDIR=build/vdb/lib -DVDB_INCDIR=<ncbi-vdb>/interfaces \
  -DLIBXML2_INCLUDE_DIR=<libxml2 头目录> -DLIBXML2_LIBRARIES=<libxml2.so>
ninja -C build/sra
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `unknown OS HarmonyOS` / `unknown architecture unknown` | CMake 4 依据 clang target 识别出 HarmonyOS，但无 Platform 模块；`CMAKE_HOST_SYSTEM_PROCESSOR` 为 unknown；sra-tools 用 `CMAKE_HOST_SYSTEM_*` 判平台 | 交叉编译语义：`-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64`；补丁 `0003` 让 sra-tools 在 `CMAKE_CROSSCOMPILING` 时改用 `CMAKE_SYSTEM_*` |
| 2 | `AST_error` 重定义为不同类型 / `yyerror` 不可调用 | Bison 3.8 把内建 `error` token 放入 `<prefix>error` 枚举，与上游同名错误回调冲突 | 补丁 `0001`：`#undef yyerror` 并重定向到 `*_error_handler` 回调（不改语义） |
| 3 | `undefined symbol: pthread_cancel` | OHOS musl 未实现 POSIX 线程取消 | 补丁 `0002`：kproc 构建期探测 `HAVE_PTHREAD_CANCEL`；有该能力时保留原 `pthread_cancel` 路径，无能力时 `KThreadCancel` 返回 `rcUnsupported`，BGZF 读线程改为协作式取消（cancel 标志 + 条件变量唤醒，退出时不再用局部 rc 覆盖 `rcCanceled`），Whack 先置位再 join |
| 4 | `libxml/xmlreader.h` not found / `ATTRIBUTE_UNUSED` 未定义 | 上游使用旧式 `LIBXML2_INCLUDE_DIR` 变量；libxml2 2.15 删除了 `ATTRIBUTE_UNUSED` | 配方显式传入旧式变量；补丁 `0004` 在函数体内 `(void)ctx` 替代属性宏 |
| 5 | 打包时批量建符号链接偶发 `EACCES` | HMDFS 在高并发创建大量符号链接时拒绝 | `package()` 采用“符号链接 → 硬链接 → 复制”降级策略，保持 `tool -> tool.3 -> tool.x.y.z` 链 |

## 源码修改

- `patches/vdb/0001-ncbi-vdb-bison38-error-handler.patch` — ncbi-vdb schema 两个 bison 语法文件（由配方手动应用到 `ncbi-vdb/` 源树）。
- `patches/vdb/0002-ncbi-vdb-thread-cancel-ohos.patch` — ncbi-vdb `kproc/unix/systhread.c`、`align/bam.c`（同样手动应用到 `ncbi-vdb/`）。
- `patches/0003-sra-tools-cross-compiling-system.patch` — sra-tools `build/env.cmake`（`apply_conandata_patches` 应用于源码根）。
- `patches/0004-kxml-libxml2-2.15.patch` — sra-tools `libs/kxml/xml.c`（同上）。

均为可移植性修复，无 stub；`pthread_cancel` 缺失通过构建期能力探测 `HAVE_PTHREAD_CANCEL` 处理，不引入平台条件编译宏。

## 依赖版本

- libxml2/2.15.3（制品仓已有）
- zlib/bzip2/zstd 由 ncbi-vdb 自带源码构建，无外部依赖

## 验证结果

```bash
conan create archives/s/sra-sdk/3.2.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default
# 构建、打包、test_package 全部通过
```

上游测试：见 `reports/test-report.md`。190 项 CTest 在适配期手动执行
（`ctest --output-on-failure --timeout 300 -j4`），不属于 `conan build` 步骤；
`test_package` 由 `conan create` 自动执行并通过。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/ | 90 个工具入口（prefetch/fasterq-dump/fastq-dump/vdb-dump/vdb-config/sra-stat/sam-dump 等，含版本别名链） |
| lib/ | ncbi-vdb/ncbi-wvdb 共享库 + ngs/ngs-c++/kxml 等静态库 |
| include/ | VDB interfaces 头文件 + NGS C++ 头文件（`ngs/`、`ncbi-vdb/NGS.hpp`） |
| ncbi/ | default.kfg / certs.kfg |

## 注意事项

- **线程取消的残余限制**：无 `pthread_cancel` 的平台无法打断已阻塞的 `read()`；BGZF 底层源为管道/FUSE/远端存储时，销毁路径可能等待当前读完成（需配合有界读/可打断 I/O，参见知识条目 E3700 与 E1603）。
- **共享库 dlopen 限制**：本机 OHOS 策略拒绝从应用数据目录 `dlopen` 任意 `.so`
  （`Permission denied`），导致上游 6 项 Python 绑定测试无法运行；工具与 C/C++ SDK
  使用静态链接不受影响。使用 Python 绑定时需将 `libncbi-ngs.so` 放入应用 bundle 的
  原生库目录。
- `CMAKE_SYSTEM_NAME=Linux` 仅用于让 CMake 选择 Linux 平台语义；编译器默认 triple
  仍为 `aarch64-unknown-linux-ohos`，产物为 OHOS ELF。
- 测试数据在源码树内（`test/` 约 172MB）；`SlowTest_*` 需要访问 NCBI SRA 网络数据。
---

**编译结束**: 2026-10-18 21:38
**最终状态**: built
