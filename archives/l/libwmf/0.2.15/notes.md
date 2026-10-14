# libwmf 0.2.15 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-04
- 状态: built

## 遇到的问题与解决方案
- 旧记录仅覆盖轻量版 libwmflite；本轮配方同时交付完整 libwmf API 和 libwmflite。
- 使用官方 0.2.15 release tarball；其预生成 configure/Makefile.in 避免目标机缺少 libtoolize 时重新自举。
- libpng 1.6 的不透明结构使用公开 png_jmpbuf() 访问器。
- 消费者通过 wmf_api_create、SVG 设备层和 wmf_api_destroy 验证完整 API；上游 Automake check-examples.sh 1/1 通过（内部执行 3 个转换器 × 17 个素材）。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml / patches/ | Conan 配方与兼容性补丁 |
| test_package/ | 完整 API 消费者验证 |
