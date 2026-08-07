# pamixer 1.6 Conan 适配笔记

## 基本信息
- 软件: pamixer
- 版本: 1.6
- 状态: published
- 构建系统: custom (直接编译，绕过meson)
- 日期: 2026-08-07

## 依赖
- pulseaudio/17.0 (Conan依赖，从源码构建)
- cxxopts/3.2.1 (Conan依赖，header-only)

## 编译过程
1. 下载 pamixer 1.6 源码
2. 生成 config.hh (定义 VERSION)
3. 使用 clang++ 直接编译4个源文件 (callbacks.cc, device.cc, pamixer.cc, pulseaudio.cc)
4. 链接 pulseaudio 和 cxxopts 库
5. 打包可执行文件

## 依赖适配
- pulseaudio 17.0: 禁用 glib, libsndfile, daemon 等可选功能，仅构建客户端库
- cxxopts 3.2.1: header-only 库，直接打包头文件

## 验证结果
- conan create 成功
- 编译和链接测试通过
- 运行时测试因OHOS文件权限限制跳过

---
**编译结束**: 2026-08-07
**最终状态**: published
