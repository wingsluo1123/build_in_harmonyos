# libuecc 7 适配笔记

## 编译环境

| 项目 | 值 |
|------|-----|
| 构建系统 | CMake |
| 编译日期 | 2026-06-26 |
| 编译器 | clang 15.0.4 / clang++ |
| 平台 | OpenHarmony aarch64 |
| CMake 版本 | 4.1.2 |
| 状态 | published |

## 编译步骤

1. **下载源码**: `https://git.universe-factory.net/fastd/libuecc/archive/v7.tar.gz`
2. **CMake 配置**:
   ```bash
   cd $BUILD_SRC_DIR
   mkdir build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   ```
3. **编译**: `make -j1` — 构建出 `libuecc.so`（共享库）和 `libuecc.a`（静态库）
4. **Staging 安装**: `make install DESTDIR=$TEST_PREFIX` — 安装 4 个文件
5. **测试**: 上游未提供测试套件，`make test` 无目标；Conan test_package 通过
6. **Conan 配方**: 使用 CMake 构建系统，生成 conanfile.py + conandata.yml + test_package/
7. **Conan 验证**: 8 道门禁全部通过，标记为 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 报错 "Compatibility with CMake < 3.5 has been removed" | libuecc 的 CMakeLists.txt 使用 `cmake_minimum_required(VERSION 2.6)`，CMake 4.x 移除了 < 3.5 的兼容 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数 |
| 2 | Conan 报 "Invalid package version '7'" | Conan 2.12.0 版本正则 `^[a-z0-9_][a-z0-9_+.-]{1,100}\Z` 要求至少 2 个字符，单字符 "7" 不匹配 | conanfile.py 中 version 设为 `"7.0"`，归档目录名保持 "7" |
| 3 | conanfile.py 中 `tc.variables` 设置的 CMAKE_POLICY_VERSION_MINIMUM 未传递到 cmake 命令行 | `variables` 写入 toolchain 文件，但 `cmake_minimum_required` 在 toolchain 加载前执行 | 改用 `tc.cache_variables`（作为 -D 参数传递到命令行） |
| 4 | test_package 编译报 `fatal error: 'libuecc/ecc.h' file not found` | 头文件安装在 `include/libuecc-7/libuecc/ecc.h`，默认 includedirs=["include"] 不够 | 设置 `cpp_info.includedirs = ["include/libuecc-7"]` |
| 5 | conan-init 自动生成的 conanfile.py 使用 Autotools 模板 | 自动检测误判构建系统为 autotools | 手动重写 conanfile.py 使用 CMake (CMake/CMakeToolchain/cmake_layout) |
| 6 | finish 首次降级为 built | 缺少 `.knowledge-done` 标记，DRAFT-003.kv 草稿内容为 TODO 占位符 | 填写 DRAFT-003.kv 实际内容，创建 `.knowledge-done` 标记，重新运行 finish |

## 源码修改

无源码修改。所有适配通过 conanfile.py 的 CMake 参数完成，未修改 libuecc 上游源码。

## 依赖版本

无外部依赖。libuecc 是纯 C 库，仅需标准 C 编译器。

## 验证结果

```bash
# 静态库符号检查
$ llvm-nm libuecc.a | grep -c " T "
16  # 16 个导出符号

# Conan test_package 测试
$ conan create ... --user=ohpcd --channel=stable
100% tests passed, 0 tests failed out of 1

# Conan verify 8 道门禁
✅ G0-G4 + L2/L4/L5 全部 PASS
```

## 注意事项

1. **CMake 兼容性**: libuecc 使用 `cmake_minimum_required(VERSION 2.6)`，在 CMake 4.x 环境下必须添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
2. **版本号格式**: Conan 2 要求版本号至少 2 个字符，单数字版本需加 `.0` 后缀
3. **include 路径**: libuecc 头文件安装在 `include/libuecc-7/` 子目录下，conanfile.py 中需设置 `includedirs = ["include/libuecc-7"]`
4. **无测试套件**: libuecc 上游未提供测试，`make test` 无目标，不阻塞编译流程

---

**编译结束**: 2026-06-26 02:47
**最终状态**: published
