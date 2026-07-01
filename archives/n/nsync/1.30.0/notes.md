# nsync 1.30.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-01
- 编译器: clang/clang++ 15.0.4
- 状态: built (conan-verify 8门禁通过)

## 编译步骤

```bash
# Step 1: init-build
python3 scripts/ohc-run.py init-build nsync 1.30.0

# Step 2: AI 手动编译
source .build-context-nsync-1.30.0 && cd $BUILD_SRC_DIR
cmake -S . -B _build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DNSYNC_ENABLE_TESTS=ON
cmake --build _build -j$(nproc)
cmake --install _build --prefix $TEST_PREFIX
ctest --test-dir _build  # 26/26 测试全部通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-data.yml SHA256 不匹配 | 使用 master 分支动态 URL，每次下载内容不同 | 固定到特定 commit SHA：`5b420ef6b16532a4fad4be1fde8e483b6b7bd8f4` |
| 2 | CMake NotADirectoryError: build/Release | nsync 源码有 Bazel BUILD 文件，OHOS 不区分大小写，BUILD 与 build 冲突 | `source()` 中重命名 BUILD → BUILD.bazel |
| 3 | CMake 不认识 HarmonyOS 平台 | CMakeLists.txt 仅识别 "Linux"、"Darwin"、"Windows" 等 | `generate()` 中设置 `CMAKE_SYSTEM_NAME=Linux` |
| 4 | conan-verify 知识图谱 E001 误命中 | 图谱将 CMake 项目误匹配为 autotools 编译器缺失 | 非真实错误，可通过知识图谱草稿区分标记 |
| 5 | test_package 编译失败 | test.c 中 nsync API 用法错误（nsync_once 是类型非函数） | 查阅头文件修正为 `nsync_run_once` |

## 源码修改

- `BUILD` → `BUILD.bazel`：重命名 Bazel 构建文件，避免与 CMake `build/` 目录冲突（OHOS 不区分大小写）
- `conanfile.py` `generate()`：添加 `CMAKE_SYSTEM_NAME=Linux` 使 OHOS 被识别为 Linux 平台
- `conanfile.py` `source()`：添加 BUILD 文件重命名逻辑

## 依赖版本

- 无外部依赖（仅需 gcc-libs + cmake）
- 编译器: clang 15.0.4

## 验证结果

```bash
# 上游测试: 26/26 全部通过
ctest --output-on-failure  # 26 tests passed, 0 failed, total 158.85s

# Conan 配方验证:
conan create ... nsync/1.30.0@ohpcd/stable  # G0-G4 + L2/L4/L5 全部通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/n/nsync/1.30.0/conanfile.py` | Conan 配方 |
| `archives/n/nsync/1.30.0/conandata.yml` | 源码声明（固定 commit SHA） |
| `archives/n/nsync/1.30.0/test_package/` | L1 测试（使用 nsync C API） |

## 注意事项

- nsync 在 GitHub 上无正式 release tag，需固定到具体 commit SHA 确保可复现构建
- 当前固定在 commit `5b420ef6b16532a4fad4be1fde8e483b6b7bd8f4`
- nsync 使用静态库（libnsync.a + libnsync_cpp.a），非系统同名库，无需特殊隔离
- 未来更新时需重新获取最新 commit SHA 并更新 conandata.yml
---

**编译结束**: 2026-07-01 17:44
**最终状态**: built
