# tesseract 5.3.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-08
- 编译器: clang / clang++
- 状态: published

## 编译步骤

1. **源码下载**: 从GitHub下载 tesseract 5.3.3
   - URL: https://github.com/tesseract-ocr/tesseract/archive/refs/tags/5.3.3.tar.gz
   - SHA256: dc4329f85f41191b2d813b71b528ba6047745813474e583ccce8795ff2ff5681

2. **依赖准备**:
   - leptonica/1.87.0@ohpcd/stable（本地 conan 缓存可用）
   - 制品仓访问失败（system acceleration policy not enabled），使用本地缓存

3. **cmake配置**:
   ```bash
   cmake .. \
     -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
     -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_TRAINING_TOOLS=False \
     -DGRAPHICS_DISABLED=True \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   ```
   - 禁用训练工具（依赖 pango/cairo，鸿蒙平台不可用）
   - 禁用 ScrollView 图形界面（无头构建环境）
   - 允许旧版 cmake 策略（CMAKE_POLICY_VERSION_MINIMUM=3.5）

4. **编译**:
   ```bash
   make -j$(nproc)
   ```
   - 编译成功，生成 libtesseract.a 和 tesseract 可执行文件

5. **Staging安装**:
   ```bash
   make install DESTDIR=/storage/Users/currentUser/tmp/test-install-tesseract-5.3.3
   ```

6. **本地安装**:
   ```bash
   make install
   ```
   - 安装路径：/storage/Users/currentUser/usr/local
   - 库文件：libtesseract.a
   - 可执行文件：tesseract
   - 头文件：tesseract/*.h

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SIMD检测链接错误 | aarch64平台代码 `#if defined(__aarch64__)` 无条件启用NEON，但 HAVE_NEON 未定义导致 NEON 函数（如 DotProductNEON）链接失败 | 应用 0001-simddetect.patch，将条件改为 `#if defined(HAVE_NEON) && defined(__aarch64__)` |
| 2 | 训练工具编译失败 | 训练工具依赖 pango/cairo，鸿蒙平台无此依赖 | cmake 配置 `-DBUILD_TRAINING_TOOLS=False` 禁用 |
| 3 | ScrollView 图形界面编译失败 | 无头构建环境无图形库支持 | cmake 配置 `-DGRAPHICS_DISABLED=True` 禁用 |

## 源码修改

### 0001-simddetect.patch
修复 aarch64 平台 NEON SIMD 检测逻辑，修改 `src/arch/simddetect.cpp`：

- **修改1**: `#if defined(__aarch64__)` → `#if defined(HAVE_NEON) && defined(__aarch64__)`
  - 确保 NEON 代码路径只在 HAVE_NEON 宏定义时启用
  - 添加 fallback 分支：`__aarch64__` 但无 HAVE_NEON 时 `neon_available_ = false`

- **修改2**: `#if defined(HAVE_NEON) || defined(__aarch64__)` → `#if defined(HAVE_NEON) && defined(__aarch64__)`
  - DotProduct 和 SIMD 初始化中的 NEON 条件统一改为 AND 逻辑

- **修改3**: 在非 NEON 平台的 else 分支添加 `neon_available_ = false` 声明
  - 确保所有代码路径中 neon_available_ 都有定义

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| leptonica | 1.87.0 | Conan包 (@ohpcd/stable) |

## 验证结果

```bash
# tesseract 版本验证
tesseract --version
# 输出: tesseract 5.3.3

# TessVersion API 测试 (test_package)
# test.cpp 调用 TessVersion() 返回版本字符串
# 输出: tesseract version: 5.3.3
# 输出: test tesseract 5.3.3: OK

# 库文件验证
ls -lh /storage/Users/currentUser/usr/local/lib/libtesseract.a
```

## 注意事项

1. **构建系统**: 使用 cmake 构建，源码自带 CMakeLists.txt
2. **混合类型**: tesseract 既有库（libtesseract）又有可执行文件（tesseract binary），需创建 commands.json (R38)
3. **SIMD 补丁**: aarch64 平台必须应用 0001-simddetect.patch，否则链接失败
4. **依赖**: leptonica/1.87.0 是硬依赖，通过 Conan 管理
5. **可选依赖**: 训练工具依赖已禁用，不影响核心 OCR 功能
---

**编译结束**: 2026-07-08 12:07
**最终状态**: published
