# grilo-plugins 0.3.16 Conan 适配笔记

## 基本信息
- 软件名称: grilo-plugins
- 版本: 0.3.16
- 构建系统: meson
- 编译日期: 2026-08-06
- 状态: built (Conan 适配完成)

## 源码信息
- URL: https://download.gnome.org/sources/grilo-plugins/0.3/grilo-plugins-0.3.16.tar.xz
- SHA256: fe6f4dbe586c6b8ba2406394e202f22d009d642a96eb3a54f32f6a21d084cdcb

## 编译环境
- 目标平台: OpenHarmony (aarch64)
- 编译器: clang 15.0.4
- 构建工具: meson 1.11.1, ninja 1.13.1

## 插件状态

### 已启用插件 (11个)
1. chromaprint - 音频指纹识别插件 (依赖: gstreamer)
2. dleyna - DLNA/UPnP 媒体服务器插件 (依赖: gio, gio-unix)
3. gravatar - Gravatar 头像插件 (无额外依赖)
4. local-metadata - 本地元数据插件 (依赖: gio, libmediaart)
5. lua-factory - Lua 工厂插件 (依赖: lua, libarchive, grilo-net, json-glib, libxml2)
6. magnatune - Magnatune 音乐插件 (依赖: sqlite3, grilo-net)
7. metadata-store - 元数据存储插件 (依赖: sqlite3)
8. opensubtitles - OpenSubtitles 字幕插件 (依赖: gio, libsoup-2.4)
9. raitv - Rai.tv 插件 (依赖: grilo-net, libxml2)
10. shoutcast - Shoutcast 电台插件 (依赖: grilo-net, libxml2)
11. tmdb - TMDb 电影数据库插件 (依赖: json-glib, grilo-net)

### 自动禁用插件 (12个) - 缺少依赖
| 插件 | 缺失依赖 |
|------|----------|
| bookmarks | gom |
| dmap | libdmapsharing |
| filesystem | grilo-pls (totem-pl-parser) |
| flickr | oauth |
| freebox | grilo-pls, avahi |
| optical-media | totem-plparser |
| podcasts | totem-plparser |
| thetvdb | gom |
| tracker | tracker-sparql-2.0 |
| tracker3 | tracker-sparql-3.0 |
| youtube | libgdata, totem-plparser |

## Conan 依赖
- glib2/2.88.0 (Conan repo)
- libxml2/2.15.3 (Conan repo)
- sqlite3/3.49.1 (Conan repo)
- lua/5.4.8 (Conan repo)

## 非 Conan 依赖 (通过 pkg-config 在 CI 环境中解析)
- grilo-0.3 >= 0.3.19 (本地从源码编译安装)
- json-glib-1.0 >= 1.6.6 (预编译包)
- libsoup-2.4 >= 2.74.3 (预编译包)
- libarchive >= 3.7.4 (预编译包)
- gstreamer-1.0 >= 1.28.3 (预编译包)
- libmediaart-2.0 >= 1.9.7 (预编译包)

## 编译步骤

1. 安装预编译依赖: glib, json-glib, libsoup, libarchive, gstreamer, libxml2, sqlite3, libmediaart, pcre2, libffi, brotli, libpsl
2. 从源码编译 lua 5.4.8 并安装
3. 从源码编译 grilo 0.3.19 并安装 (启用 grl-net, 禁用 grl-pls 因 totem-pl-parser 不可用)
4. 修复 pkg-config 依赖: 创建 libpsl.pc, libbrotlidec.pc, gdk-pixbuf-2.0.pc; 修复 libarchive.pc
5. 创建 clang wrapper 脚本解决 lld linker 的 libxml2.so.16 加载问题
6. 修复 libffi 损坏的共享库 (用 HNP 版本替换)
7. 创建共享库符号链接 (glib, gstreamer, libarchive 等)
8. 运行 meson setup 配置 grilo-plugins
9. 运行 ninja 编译
10. 运行 ninja install 安装到测试目录

## 编译产物
- 11 个插件共享库 (.so) 安装到 lib/grilo-0.3/
- 1 个 pkg-config 文件 (grilo-plugins-0.3.pc)
- 12 个 Lua 源文件 (lua-factory 插件资源)
- 51 个翻译文件 (.mo)

## 测试
- 上游测试: meson test --list (4 个测试可执行文件)
- Conan test_package: dlopen 加载插件 .so 验证
