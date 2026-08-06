# ffmpeg2theora 0.30 适配笔记

## 编译环境
- 构建系统: SCons (Python-based)
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built (conan adaptation in progress)

## 编译步骤

1. 源码获取: git clone from gitlab.xiph.org/xiph/ffmpeg2theora tag 0.30
2. 应用补丁: 4个补丁 (SConstruct, ffmpeg2theora.c, ffmpeg2theora.h, version.sh)
3. 安装依赖: ffmpeg/4.4.8, libvorbis/1.3.7, libogg/1.3.6 (via conan)
4. 构建 libtheora: 从源码编译 (CMake)，因为libtheora尚未在制品仓发布
5. 构建 ffmpeg2theora: scons prefix=... (使用SCons构建系统)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python 2 print语法 | SConstruct使用Python 2 | 补丁迁移到Python 3 |
| 2 | scons找不到sh | HarmonyOS PATH无sh | SConstruct设置SHELL='/system/bin/sh' |
| 3 | libavcodec版本检查失败 | conan .pc使用包版本非库版本 | 移除>= 52.30.0版本要求 |
| 4 | libpostproc缺失 | ffmpeg conan包未含libpostproc | 添加#ifdef HAVE_POSTPROC守卫使其可选 |
| 5 | libtheora不在制品仓 | 历史适配未做conan适配 | 从源码编译libtheora，conan配方声明依赖 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| SConstruct | Python 3迁移, CC/CXX env支持, 可选libpostproc, SHELL设置, 版本检查修复 |
| src/ffmpeg2theora.c | postproc代码加#ifdef HAVE_POSTPROC守卫 |
| src/ffmpeg2theora.h | pp_mode字段加#ifdef HAVE_POSTPROC守卫 |
| version.sh | 使用/bin/sh, 硬编码版本0.30 |

## 依赖版本

- ffmpeg/4.4.8 (conan artifact repo)
- libtheora/1.1.1 (从源码编译, 尚未发布到制品仓)
- libvorbis/1.3.7 (conan artifact repo)
- libogg/1.3.6 (conan artifact repo)
- scons 4.10.1 (pip install)

## 验证结果

```bash
$ file ffmpeg2theora
ffmpeg2theora: ELF shared object, 64-bit LSB arm64
$ scons prefix=... && echo "BUILD OK"
scons: done building targets.
BUILD OK
```

## 注意事项

- libtheora/1.1.1 尚未发布到conan制品仓，conan-verify将失败
- 需要先适配并发布libtheora才能完成conan验证
- libtheora CMakeLists.txt需要包含mcenc.c源文件
