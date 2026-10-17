# ebook-tools

## 简介
EPUB / Mobipocket 电子书容器解析库（libepub）与信息查看工具（einfo），
上游托管在 SourceForge：<https://sourceforge.net/projects/ebook-tools/>

## OHOS 适配
- 构建系统: CMake
- 详见各版本 notes.md 获取适配详情

## 依赖
- libxml2（OPF/OCF XML 解析）
- libzip（EPUB 容器即 zip）

## 功能验证
test_package 现场构造最小 EPUB 并走 libepub 解析链路（详见版本目录 notes.md 与 test_package/MANIFEST.yml）

## 参考
- https://sourceforge.net/projects/ebook-tools/
