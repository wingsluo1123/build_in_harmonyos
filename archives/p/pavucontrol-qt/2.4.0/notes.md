# pavucontrol-qt 2.4.0 编译笔记

## 基本信息
- 软件: pavucontrol-qt
- 版本: 2.4.0
- 状态: built (conan adaptation complete)
- 构建系统: CMake

## 依赖说明
pavucontrol-qt 的依赖链复杂，多个依赖不在 ohpcd conan 仓库中：
- **Qt6** (qtbase/6.11.1): 从 conan 仓库获取 ✅
- **PulseAudio 17.0**: 不在 ohpcd 仓库，从源码构建（client-only, meson）
- **GLib 2.84.0**: 不在 ohpcd 仓库（binary），从源码构建（meson + HarmonyOS patches）
- **libsndfile 1.2.2**: 不在 ohpcd 仓库，从源码构建（cmake, minimal）
- **lxqt-build-tools 2.4.0**: 不在 ohpcd 仓库，CMake 模块直接安装

## 适配要点
1. **Qt6 LinguistTools**: conan 的 qtbase 包不包含 LinguistTools 组件
   - 修改 CMakeLists.txt 使其可选，提供 fallback 函数
   - 翻译文件(.ts)仍包含在包中，只是不编译为 .qm

2. **GLib 编译**:
   - 使用 conan 仓库中的 glib 2.84.0 HarmonyOS 补丁
   - 额外添加 strtoull_l/strtoll_l 声明补丁（musl libc 有符号但无声明）
   - 使用系统 HNP 提供的 libffi、pcre2、gettext

3. **PulseAudio 编译**:
   - 仅构建客户端库（daemon=false, client=true）
   - 禁用所有可选依赖（alsa, dbus, x11, etc.）
   - 需要手动提供 .tarball-version 文件

4. **libsndfile 编译**:
   - 禁用外部编解码器（ENABLE_EXTERNAL_LIBS=OFF）
   - 仅提供 WAV/AIFF 等基本格式支持

5. **lxqt-build-tools**:
   - 直接下载 CMake 模块并安装
   - 需要从 .cmake.in 模板生成 LXQtTranslateTs.cmake

## 编译结果
- 二进制: /storage/Users/currentUser/usr/local/bin/pavucontrol-qt
- 架构: AArch64 (ARMv8), PIE
- 链接: 动态链接到 libQt6Core.so, libpulse.so, libglib-2.0.so 等

---
**编译结束**: 2026-08-07
**最终状态**: built (conan adaptation complete)
