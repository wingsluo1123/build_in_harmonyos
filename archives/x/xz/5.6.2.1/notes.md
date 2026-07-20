# xz 5.6.2.1 适配笔记

## 目标

`xz/5.6.2` 同时交付 `liblzma.so` 和 `liblzma.a`，其消费者测试通过设置 `LD_LIBRARY_PATH` 运行。HarmonyOS musl namespace 不保证解析第三方动态库的 RUNPATH 或 `LD_LIBRARY_PATH`，因此该模式不能作为稳定的 liblzma 依赖。

`xz/5.6.2.1` 改为只构建和交付静态 `liblzma.a`，供下游直接静态链接。

## 适配内容

- `--enable-static --disable-shared`：不生成 `liblzma.so`，避免动态加载路径问题。
- `--disable-scripts`：不安装依赖 `/bin/sh` 的脚本工具。
- `build-aux/config.guess` 和 `build-aux/config.sub`：加入 `aarch64-unknown-linux-ohos` 平台识别。
- 通过 `mktemp` wrapper 使 Autoconf 使用 mkdir 回退逻辑，避开 HMDFS 上的临时目录权限异常。

## 验证

- `conan create`：通过。
- 上游 `make check`：18/18 通过。
- `test_package`：CMake 消费者程序静态链接 `xz::xz`，调用 `lzma_easy_buffer_encode` 和 `lzma_stream_buffer_decode` 完成编解码往返验证；未设置 `LD_LIBRARY_PATH`。
- 本地 CI：L0、L1、L2、L5 通过；L4 仅对 config.guess 补丁中的 `case` 关键字给出非阻塞告警。

## 下游用法

Meson/CMake 等消费者应依赖 `xz/5.6.2.1`，并链接 Conan 暴露的 `lzma` 库；不要依赖 `liblzma.so.5` 的运行时路径解析。
---

**编译结束**: 2026-07-21 02:17
**最终状态**: built
