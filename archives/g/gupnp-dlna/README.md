# gupnp-dlna

GUPnP DLNA 是 GNOME 生态的 DLNA profile 定义与识别库：内置 80+ 个
DLNA profile 的 XML 定义（MP3/JPEG/LPCM/MPEG-TS/AVC 等），通过可插拔的
元数据后端（默认 GStreamer）读取媒体文件的容器/音频/视频/图像信息，
再按 profile 的限制条件匹配出 DLNA profile 名称与 MIME 类型。

- 上游：https://gitlab.gnome.org/GNOME/gupnp-dlna
- 构建系统：meson + ninja
- 许可证：LGPL-2.1-or-later

## 组成与命令行工具

| 产物 | 说明 |
|------|------|
| `libgupnp-dlna-2.0.so` | 核心库：profile 加载、限制条件匹配、猜解 API |
| `libgupnp-dlna-gst-2.0.so` | GStreamer 元数据后端库 |
| `lib/gupnp-dlna/libgstreamer.so` | 后端模块，核心库经 `g_module_open()` 运行时加载 |
| `gupnp-dlna-info-2.0` | 识别单个媒体文件的 DLNA profile（命令行工具） |
| `gupnp-dlna-ls-profiles-2.0` | 列出当前可用的 DLNA profile（命令行工具） |

命令行工具见 `commands.json`。

## 鸿蒙适配要点

1. **共享库构建**：上游的 GStreamer 后端是 `shared_module`（运行时经
   GModule 加载的 `libgstreamer.so`），因此 `default_library=shared`。
   静态构建会把后端库和 glib 复制进多个对象，运行时出现多份 GObject。
2. **静态依赖嵌入与平台限制**：制品仓的 glib2、gstreamer、gst-plugins-base
   都是静态包。本包的共享对象按需嵌入这些静态归档，但后端模块与
   核心库各自持有一份 glib，跨 DSO 的 GType 注册表会分裂：运行时
   `dlopen` 后端模块会触发 `g_type_register_static` 断言（设备隔离探针
   复现 SIGABRT）。包仍按上游结构完整构建（共享库 + 后端模块），消费者
   测试以 ELF 结构校验（`.codesign` + 导出入口）代替 `dlopen`；限制说明
   见 `0.12.0/notes.md`「平台限制」。
3. **pkg-config wrapper**：PkgConfigDeps 只生成 glib-2.0.pc 与
   libxml-2.0.pc 等平铺包 .pc；配方在 generate() 里补写
   gobject-2.0/gio-2.0/gmodule-2.0、gstreamer-1.0、gstreamer-pbutils-1.0
   等 wrapper，pbutils 的 Libs 携带完整静态 gst 链，满足 meson 默认的
   `-Wl,--no-undefined`。
4. **运行时目录寻址**：`DATA_DIR` 与默认后端目录都是 configure-time
   prefix（conan 下为 `/`）。配方用 `runenv_info` 注入
   `GUPNP_DLNA_PROFILE_DIR`（profile XML 目录）与
   `GUPNP_DLNA_METADATA_BACKEND_DIR`（后端模块目录），并注入
   `GST_PLUGIN_PATH` 指向 gst-plugins-base 的插件目录。
5. **zlib PIC**：静态 glib 嵌入共享对象，根级把 zlib override 到 PIC 变体
   `1.3.1.1`（非 PIC 归档会报 R_AARCH64 重定位错误）。
6. **签名保护**：meson install 会改写 ELF 的 DT_RUNPATH，破坏 OHOS 的
   `.codesign` 内嵌哈希（加载时报 Permission denied）。安装后用 build
   目录原始产物覆盖 `lib/`、`lib/gupnp-dlna/`、`bin/` 下的 ELF。
7. **关闭 introspection/vapi/gtk_doc**：构建机没有 g-ir-scanner；
   introspection 关闭后 vala 子目录与 gtk_doc 一并跳过。
8. **soname 别名物化**：meson 对 `version: '4.0.0'` 的共享库只以符号链接
   发布 `libX.so.4` / `libX.so`，OHOS 沙箱拒绝 `symlink(2)`。配方在编译后
   与安装后把两个别名重建为实体拷贝，保证加载器按 DT_NEEDED 查找与消费者
   `-lX` 链接都能命中（atk 2.38.0.1.1 同款处理）。

## 测试

- 上游 `meson test`（OHOS 真机原生执行）：
  - `test-sets`：9 个 GLib g_test 用例（value-type/value-list/restriction/
    info-set）；
  - `discoverer`：脚本型 CTest，需要上游独立的 `gupnp-dlna-media` 媒体集
    （不随源码发布），缺媒体目录时按上游设计 `exit 77` 跳过。
- `test_package` 消费者端到端：通过公开 API 加载 15 个 profile XML、校验
  MP3 profile 与 mime、校验 relaxed/extended 模式，并解析安装的
  `libgstreamer.so` 后端模块 ELF（`.codesign` 节与 `.dynsym` 导出入口）。
  模块 dlopen 与基于 GStreamer 插件的实际解码链路受平台静态 glib 生态
  限制（跨 DSO GType 注册表分裂），设备实测结果见 `0.12.0/notes.md`。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.12.0 | built | 首轮适配，详见 0.12.0/notes.md |
