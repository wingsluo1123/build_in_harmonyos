# zathura

zathura 是一个高度可定制、界面极简的文档查看器。文档格式由插件提供，
主程序负责窗口、输入绑定、快捷键、会话、书签与插件管理。

## 功能概述

- 键盘驱动的极简界面（vim 风格快捷键）
- 通过插件支持 PDF / PostScript / DjVu / Comic Book 等格式
- 书签、跳转历史、标记、双页/连续视图、搜索
- 会话保存与恢复；设置与书签使用 sqlite 数据库持久化

## OHOS 适配

- **构建系统**: meson + ninja
- **GUI 依赖**: 2026.07.x 起为 **GTK4**（`gtk4/4.22.4`）；此前的 2026.05.20 为 GTK3
- **便携性补丁**: 2 个（C23 `stdckdint.h` 兜底、块作用域静态断言移至文件作用域），
  均为针对 clang 15 的 C23 支持不全；补丁 0002 保持编译期语义，不降级为运行期检查
- **本版本新增依赖**: `libmagic`（内容类型嗅探）、`xxhash`（文档缓存哈希）

## 包内容

| 路径 | 说明 |
|------|------|
| `bin/zathura` | 主程序（`export_dynamic`，导出插件 API 符号） |
| `include/zathura/*.h` | 插件 API 头文件（plugin-api / types / document / page / links） |
| `lib/pkgconfig/zathura.pc` | 插件构建用 pkg-config 元数据（Requires: girara, cairo） |
| `share/` | desktop、metainfo、dbus 接口、图标、27 种语言翻译、shell 补全 |

## 插件构建说明

`libzathura` 是 `static_library`，只链入 CLI，不单独安装。第三方插件
（zathura-pdf-poppler、zathura-pdf-mupdf、zathura-djvu、zathura-cb …）在构建期
只需要本包的**头文件与 pkg-config**，运行期从宿主 `zathura` 进程的动态符号表
解析 `zathura_*` API 符号。

## 运行依赖

- girara（UI 基础库）
- gtk4、glib、pango、cairo、gdk-pixbuf
- json-glib、libmagic、sqlite3、xxhash

## 验证结果

| 项目 | 结果 |
|------|------|
| conan create（OHOS aarch64） | 通过 |
| 上游 headless 测试（qemu + OHOS musl 运行根） | 5/5 通过 |
| 消费者端到端测试（test_package，dlopen 宿主 + 图像缓冲回环） | 14/14 CHECK 断言通过（15 个 TAP 测试点） |
| 真机 DAYU200-RK3568（OpenHarmony 6.0.0.47） | 11/11 通过 |

上游 `session` / `config` / `setting` 三个用例需要 xvfb-run(X11) 或
weston(Wayland) 显示服务器，交叉编译环境不具备，已通过上游的
`-Dtests-x11=disabled -Dtests-wayland=disabled` 选项关闭。

## 参考资料

- 源码: https://github.com/pwmt/zathura
- 版本: 2026.07.18
- 项目主页: https://pwmt.org/projects/zathura
