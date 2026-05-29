# sdl3-ttf 3.2.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **下载源码**: 从 GitHub 下载 SDL3_ttf-3.2.2.tar.gz
2. **解压源码**: 解压到 ~/tmp/builds/sdl3-ttf-3.2.2.work
3. **配置 CMake**: 
   ```bash
   cmake -B build -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DSDLTTF_SAMPLES=OFF \
     -DSDLTTF_VENDORED=OFF -DBUILD_SHARED_LIBS=OFF
   ```
4. **编译**: make -j4
5. **安装 staging**: make install DESTDIR=$TEST_PREFIX
6. **安装本地**: make install
7. **生成预编译包**: ohc-run.py package

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 平台识别问题 | HarmonyOS 平台不被识别 | 已通过 E092 解决 |
| 2 | freetype 依赖缺失 | 系统中没有 freetype 库 | freetype 已安装（26.6.20） |
| 3 | 链接错误（zlib/libpng） | 动态库编译时依赖未传递 | 使用静态库编译（BUILD_SHARED_LIBS=OFF） |
| 4 | lld 缺少 libxml2 | 链接器库路径问题 | 设置 LD_LIBRARY_PATH |

## 源码修改

无补丁，使用系统库编译。

## 依赖版本

- SDL3: 3.2.6+
- FreeType2: 26.6.20（内部版本号）
- HarfBuzz: 14.2.0
- zlib: 已安装
- libpng: 已安装

## 验证结果

```bash
# 静态库检查
ls -lh ~/usr/local/lib/libSDL3_ttf.a
-rw-rw---- 1 file_manager file_manager 149K 2026-05-29 16:10 libSDL3_ttf.a

# pkg-config 检查
pkg-config --modversion sdl3-ttf
3.2.2
```

## 交付物

| 文件 | 大小 | SHA256 | 说明 |
|------|------|--------|------|
| sdl3-ttf-3.2.2-ohos-aarch64.tar.gz | 290KB | e42343cfcc450ecabede78085b6cda2341e01f5306bca638a754d472cfe92db5 | 预编译包 |

## 注意事项

1. **静态库编译**: 使用 BUILD_SHARED_LIBS=OFF 避免 HarmonyOS 上的动态链接问题
2. **依赖链**: FreeType 依赖 zlib 和 libpng，需要确保这些库已安装
3. **库路径**: 需要设置 LD_LIBRARY_PATH 以解决 lld 的 libxml2 依赖问题
4. **无测试套件**: SDL3_ttf 没有内置测试，通过文件完整性验证

---
**编译结束**: 2026-05-29 16:13
**最终状态**: published
---

**编译结束**: 2026-05-29 16:14
**最终状态**: published
