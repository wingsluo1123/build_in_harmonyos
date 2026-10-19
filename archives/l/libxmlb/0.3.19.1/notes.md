# libxmlb 0.3.19.1 编译笔记

## 版本定位

- 上游源码版本：0.3.19
- Conan 修复版本：0.3.19.1（R37 后缀版本）
- 构建系统：Meson
- 产物：共享库 `libxmlb.so.2.0.0`、`xb-tool`

## 修复目的

已发布的 `libxmlb/0.3.19` 直接依赖 `glib/2.88.3`，无法与目标
GTK4/libadwaita/libpanel 依赖图统一到 `glib/2.84.0.1.1`。本修复版本保持
上游源码与功能不变，将 GLib 依赖切换为共享 `glib/2.84.0.1.1`，并按该
制品的实际 Conan 组件名引用 `glib-2.0`、`gobject-2.0`、`gio-2.0`。

## 构建配置

- `introspection=false`、`gtkdoc=false`：目标构建环境不提供对应生成工具，
  二者不是 C API 运行时功能。
- `tests=true`：构建并原生执行上游测试。
- `lzma=enabled`、`zstd=enabled`：保留并覆盖压缩数据路径。
- `cli=true`：保留 `xb-tool`。
- 安装后物化共享库别名并重新签名安装阶段被改写的 ELF。

## 测试基线

- 上游 `xb-self-test`：49 个默认测试；另有 2 个仅 `--perf` 注册的性能测试，
  不计入默认上游基线。
- 通用消费者测试：11 项断言/硬失败检查。
- HarmonyOS 专项测试：7 项，覆盖系统与 AArch64 ABI、GObject 实例创建、
  `libxmlb.so.2` 的 `dlopen`/`dlsym`。

## HarmonyOS PC 实测结果

- 上游 `xb-self-test`：49/49 通过。
- 通用消费者测试：11/11 通过。
- HarmonyOS 专项测试：7/7 通过。
- `xb-tool compile` 与 `xb-tool query` 端到端通过，查询结果为
  `<id>xb.tool.check</id>`。
- `PACKAGE_CODESIGN=PASS signed_elfs=4`。

编译状态: built

## 编译结束

2026-10-17：目标机完整构建与测试通过，档案关闭。
