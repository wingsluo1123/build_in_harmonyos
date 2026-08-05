# apitrace 14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: published (Conan 配方已生成并验证)

## 源码获取

apitrace 使用 git submodules 管理第三方依赖。GitHub tarball 不包含 submodules，
需要在 conanfile.py 的 source() 方法中单独下载每个 submodule：

| Submodule | 来源 | Commit |
|-----------|------|--------|
| thirdparty/brotli | google/brotli | ed738e842d2fbdf2d6459e39267a633c4a9b2f5d |
| thirdparty/gtest | google/googletest | 52eb8108c5bdec04579160ae17225d66034bd723 |
| thirdparty/libbacktrace | ianlancetaylor/libbacktrace | 793921876c981ce49759114d7bb89bb89b2d3a2d |
| thirdparty/libpng | apitrace/libpng | 2b978915d82377df13fcbb1fb56660195ded868a |
| thirdparty/snappy | google/snappy | 6af9287fbdb913f0794d0148c6aa43b58e63c8e3 |
| thirdparty/zlib | madler/zlib | 51b7f2abdade71cd9bb0e7a373ef2610ec6f9daf |
| thirdparty/zstd | facebook/zstd | f8745da6ff1ad1e7bab384bd1f9d742439278e99 |
| thirdparty/directxmath | microsoft/DirectXMath | 56206b1916646b29b37e1eac56e96e2008d6c71f |
| frametrim/tests | apitrace/gltrim-tests | 12ceee777636bfca4a35390697e8e702254a82b2 |

## 编译步骤

1. 从 GitHub 下载 apitrace 14.0 源码 tarball
2. 下载所有 git submodules 到 thirdparty/ 和 frametrim/tests/
3. 使用 CMake 构建：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_SYSTEM_NAME=Linux \
         -DENABLE_GUI=OFF \
         -DENABLE_X11=OFF \
         -DENABLE_EGL=ON \
         -DENABLE_WAFFLE=OFF \
         -DENABLE_TESTS=OFF \
         -DBUILD_TESTING=OFF \
         -DENABLE_STATIC_SNAPPY=ON
   make -j2
   make install DESTDIR=$TEST_PREFIX
   ```

## 关键配置说明

- **ENABLE_EGL=ON**: 构建 egltrace.so wrapper，这是 apitrace 的核心功能——
  通过 LD_PRELOAD 拦截 EGL/OpenGL ES 调用进行追踪
- **ENABLE_X11=OFF**: HarmonyOS 无 X11 环境，EGL 不依赖 X11
  (apitrace 使用 dlsym 在运行时动态加载 EGL 符号)
- **ENABLE_GUI=OFF**: 不构建 Qt GUI（需要 Qt5/Qt6 依赖）
- **BUILD_TESTING=OFF**: 禁用单元测试（交叉编译环境无法运行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub tarball 缺少 submodules | tarball 不包含 git submodule 内容 | 在 conanfile.py source() 中逐一下载各 submodule tarball |
| 2 | 首次构建无 egltrace.so | 未启用 ENABLE_EGL | 设置 ENABLE_EGL=ON，apitrace 使用自带 Khronos 头文件 |

## 交付物

| 文件 | 说明 |
|------|------|
| bin/apitrace | 主命令行工具 |
| bin/gltrim | 帧裁剪工具 |
| lib/apitrace/wrappers/egltrace.so | EGL/OpenGL ES 追踪 wrapper |
| lib/apitrace/scripts/*.py | 辅助分析脚本 |
| share/doc/apitrace/ | 文档和许可证 |

## 最终状态

COMPLETED — Conan 配方已生成并通过 conan-verify 验证。
