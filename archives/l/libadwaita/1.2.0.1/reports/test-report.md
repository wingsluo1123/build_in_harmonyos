# libadwaita 1.2.0.1 HarmonyOS PC 测试报告

## 测试环境

- 日期：2026-10-16
- 目标：HarmonyOS PC 6.0，aarch64
- 编译器：clang 15.0.4
- Conan：2.29.1
- 构建系统：Meson
- 支持配置：HarmonyOS PC、`shared=True`
- 图形后端：GTK Broadway（目标端签名后执行）
- 源码：GNOME libadwaita 1.2.0
- 源码 SHA-256：`ab0030434af58ae0a01e6979acc56f7e88cc43ca5a2bbd53da9a3b7707403687`

## 构建结果

目标配方通过 `conan create` 从官方源码完成构建、安装、制品检查和
`test_package` 消费测试。

- recipe revision：`401dbe0d744f16aab731d333224d4b64`
- package ID：`17236ecb15ac8a71fa79681290a38c8521e1bd72`
- package revision：`b56f3abe5ca29730e761af3e93ea01d5`
- 结果：通过

## 上游测试

上游 `tests/meson.build` 注册 37 个测试程序。本配方保留 `tests=true`，在
HarmonyOS PC 上启动签名后的 `gtk4-broadwayd`，再执行：

```text
meson test -C build-release --print-errorlogs
```

结果：

| 统计口径 | 通过 | 失败 | 跳过 | 通过率 |
|---|---:|---:|---:|---:|
| 上游测试程序 | 37 | 0 | 0 | 100% |
| GLib TAP 子测试 | 208 | 0 | 0 | 100% |

上游测试文件和断言均未修改。

## HarmonyOS 特有消费者测试

`test_package/test.c` 仅通过安装包公开头文件和生成的消费元数据编译链接，随后
在目标端 Broadway 后端运行。它验证版本 API、初始化状态以及真实 `AdwBin`
对象创建，覆盖旧制品双 GObject 类型注册表问题。

| 统计口径 | 通过 | 失败 | 通过率 |
|---|---:|---:|---:|
| 消费者程序 | 1 | 0 | 100% |
| 程序内断言 | 8 | 0 | 100% |

目标端最终输出包含 `HARMONY_LIBADWAITA_TEST_PASS`。

## 实际下游验证

使用 `libpanel-detach` 的 Zrythm `1.6.0-1-for-zrythm` 源码作为实际消费者，
直接依赖 `libadwaita/1.2.0.1`，并统一选择 `graphene/1.10.8.1` 与共享
`glib/2.84.0.2`。构建成功后，其两个上游 GUI 测试程序在目标端 Broadway
后端真实执行：

| 下游上游程序 | 结果 | 退出码 |
|---|---|---:|
| `test-dock` | 通过 | 0 |
| `test-paned` | 通过 | 0 |

结果为 2/2。下游验证中的测试适配仅加入自动退出/断言，并去除测试源码里两项
在该标签 `PanelWidget` 类上不存在的陈旧属性赋值；未修改本包源码。

## 二进制审计

- 目标共享库：AArch64 HarmonyOS ELF；
- SONAME：`libadwaita-1.so.0`；
- 符号链接：`libadwaita-1.so -> libadwaita-1.so.0`；
- `DT_NEEDED` 包含共享 `libglib-2.0.so.0`、`libgobject-2.0.so.0`、
  `libgio-2.0.so.0` 与 `libgtk-4.so.1`；
- 未定义 `g_object_new`、`g_type_register_static`、`g_malloc` 等核心
  GLib/GObject 符号；
- 无 RPATH/RUNPATH；
- 无 Conan 构建缓存绝对路径泄漏；
- `.codesign` 节存在；
- 安装头文件、翻译、资源和 `libadwaita-1.pc` 完整。

## 总结

- 编译：通过；
- 上游测试：37/37（208/208 TAP）；
- HarmonyOS 新增测试：1/1（8/8 断言）；
- 实际下游上游 GUI 程序：2/2；
- 制品审计：通过。
