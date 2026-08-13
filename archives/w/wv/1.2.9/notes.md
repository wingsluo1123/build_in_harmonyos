# wv 1.2.9 适配笔记

## 编译环境
- 构建系统: Autotools
- 编译日期: 2026-08-13
- 编译器: clang/clang++ 15.0.4
- 目标平台: OHOS arm64
- 状态: built

## 编译步骤

使用 OHOS Conan profile 安装 libgsf、GLib、libxml2、zlib 和 gettext 依赖。配置时关闭 libwmf 和共享库，构建静态 libwv，并以串行 Make 避免 HMDFS 不支持 GNU Make FIFO jobserver。

```bash
conan create archives/w/wv/1.2.9 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=default \
  --build='wv/1.2.9' --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | config.status 无法写入临时目录 | HMDFS 对 umask 077 创建目录的权限映射异常 | 调整 Autoconf 临时目录 umask 为 022 |
| 2 | 新版 libgsf 元数据 API 无声明 | wvSummary.c 未包含公开 API 头 | 补充 gsf-doc-meta-data.h |
| 3 | 公共 wv.h 传播 libgsf 头路径 | GsfInput 仅以不透明指针使用 | 改为前置声明，并在 lfo.c 私有包含 glib.h |
| 4 | 依赖缓存中的 .la 路径失效 | 依赖包迁移后 libtool archive 仍记录旧路径 | 构建时复制真实库到无 .la 的临时链接目录 |
| 5 | GNU Make jobserver FIFO 失败 | HMDFS 不支持 mkfifo | 本体和 test_package 固定使用 -j1 |

## 源码修改

- `0001-configure.patch`: 使用 HMDFS 可写的临时目录权限。
- `0002-lfo.c.patch`: 显式包含 GLib 以使用 `G_MAXUINT`。
- `0003-wv.h.patch`: 前置声明 `GsfInput`，减少公共头耦合。
- `0004-wvSummary.c.patch`: 包含新版 libgsf 元数据 API 头。

## 依赖版本

- libgsf 1.14.53
- glib 2.84.0
- libxml2 2.15.3
- zlib 1.3.1
- gettext 0.22.5
- 传递依赖: libffi 3.4.4、pcre2 10.40

## 验证结果

- 上游正式入口: `make check`
- 上游实际测试用例: 0（上游未定义 `TESTS`，入口正常返回成功）
- Conan test_package: 1 个真实消费者 API/链接/运行测试，通过
- 运行输出: `wv version: wvWare version 1.2.9`

## 交付物

- `lib/libwv.a`
- `include/wv/wv.h`
- `lib/pkgconfig/wv-1.0.pc`
- wv 命令行工具及数据文件

## 注意事项

当前适配仅支持静态库；已发布 zlib 依赖不是 PIC，不能用于构建共享 libwv。
---

**编译结束**: 2026-08-13 19:10
**最终状态**: built
