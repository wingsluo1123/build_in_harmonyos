# sdl2_ttf 2.24.0 编译笔记

## 编译环境
- 平台: HarmonyOS (HongMeng Kernel 1.12.0)
- 架构: aarch64
- 构建系统: cmake（autotools 受 HMDFS 限制）

## 关键问题

### 1. HMDFS 文件系统限制
- **问题**: autotools 的 config.status 脚本在当前目录创建临时子目录失败
- **错误**: `./config.status[1047]: can't create ./confXXX/subs1.awk: Permission denied`
- **解决方案**: 使用 cmake 作为替代构建系统

### 2. 链接依赖缺失
- **问题**: FreeType 静态库依赖 zlib 和 libpng，但 cmake 配置没有自动添加
- **错误**: `undefined symbol: inflateInit2_`, `undefined symbol: png_create_read_struct`
- **解决方案**: 手动修改 link.txt 添加 `-lpng16 -lz -lm`

### 3. config.guess 平台识别
- **问题**: 默认 config.guess 不支持 HarmonyOS
- **解决方案**: 手动添加 HarmonyOS 识别规则（参考 SDL2_image 补丁）

## 编译流程
1. 源码下载: 从 GitHub releases 下载（网络需要长超时）
2. cmake configure: 使用系统库（harfbuzz, freetype, SDL2）
3. 手动修复链接: 添加缺失的 zlib 和 libpng
4. make: 成功构建共享库
5. make install: 安装到 ~/usr/local

## 依赖关系
- SDL2 (>= 2.0.10)
- FreeType2 (26.6.20)
- Harfbuzz (14.2.0)
- libpng (16.39.0)
- zlib (1.3.1)

## 产物
- libSDL2_ttf.so (共享库)
- SDL_ttf.h (头文件)
- SDL2_ttf.pc (pkg-config)
- SDL2_ttfConfig.cmake (cmake config)

---

**编译开始**: 2026-05-27 18:33
**编译结束**: 2026-05-27 18:49
**最终状态**: published
