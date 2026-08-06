# gst-libav 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built (conan create + test_package 通过)

## Conan 适配

### 依赖链
gst-libav/1.28.3 → gstreamer/1.28.3 + gst-plugins-base/1.28.3 + glib/2.84.0.1 + ffmpeg/7.1.5

由于 gstreamer/1.28.3 和 gst-plugins-base/1.28.3 此前仅有手动编译记录（manifest+notes），
无 conan 配方，本次同时创建了三个包的 conanfile.py + conandata.yml + test_package/。

### 关键问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | glib conan 包缺少 gmodule-no-export-2.0.pc | PkgConfigDeps 只生成已声明组件的 .pc | generate() 中创建 .pc 别名 |
| 2 | glib conan 包缺少 gio-unix-2.0.pc | 同上 | generate() 中创建 .pc 别名 |
| 3 | glib-2.0.pc 缺少 glib_mkenums 变量 | conan 组件不自动暴露工具路径 | generate() 中从 glib 包 bin/ 补充 |
| 4 | glib-2.0.pc 缺少 -lintl | glib 组件 package_info 未声明 libintl | generate() 中向 Libs 行追加 -lintl |
| 5 | gio-2.0.pc 缺少 giomoduledir 等变量 | 同 #3 | generate() 中从 glib 包补充 |
| 6 | ffmpeg .pc 文件版本号不正确 | PkgConfigDeps 使用 conan 版本号 7.1.5 | generate() 中从实际 .pc 读取正确版本号 |
| 7 | docs/meson.build 在 doc=disabled 时不跳过 | meson.build 未检查 disabled 状态 | 补丁 0001-skip-docs-when-disabled.patch |
| 8 | meson 选项名 "documentation" 无效 | gstreamer 用 "doc" 而非 "documentation" | 修正为 "doc" |
| 9 | gst-plugins-base 选项 "gl_api" 不接受 "disabled" | gl=disabled 已足够 | 删除多余 GL 子选项 |

### 补丁
- `0001-skip-docs-when-disabled.patch`: docs/meson.build 在 doc=disabled 时 subdir_done()

### 验证结果

```bash
# conan create 通过
conan create archives/g/gst-libav/1.28.3/conanfile.py -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing

# test_package 通过
gst-libav/1.28.3 (test package): Running test()
Loaded plugin: libgstlibav.so
Found gst_plugin_libav_get_desc symbol
Found gst_plugin_libav_register symbol
Plugin size: 449088 bytes
gst-libav plugin test: OK
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/gstreamer-1.0/libgstlibav.so | 449,088 bytes | GStreamer FFmpeg wrapper plugin |

## 注意事项

1. gst-libav 是纯插件包，没有 bin/ 目录下的可执行文件
2. FFmpeg 库静态链接到插件中（449KB）
3. 依赖 gstreamer/1.28.3 和 gst-plugins-base/1.28.3 的 conan 配方（本次同时创建）
4. 需要在 CI 环境中先 export gstreamer 和 gst-plugins-base 的 conan 配方

---

**编译结束**: 2026-08-06
**最终状态**: built
