# gtkgreet

gtkgreet 是 greetd 的 GTK 欢迎界面（greeter 客户端）：显示会话列表与登录表单，
通过 greetd 的 IPC 协议（JSON over unix socket）与 daemon 通信完成登录，
通常由 cage 之类的 Wayland 合成器承载。

- 主页: https://sr.ht/~kennylevinsen/gtkgreet
- 源码归档: https://git.sr.ht/~kennylevinsen/gtkgreet/archive/0.8.tar.gz
- 许可证: GPL-3.0-or-later
- 构建系统: meson (C)

## 版本

| 版本 | 状态 | 构建日期 | Conan 引用 |
|------|------|----------|-----------|
| 0.8 | built | 2026-10-16 | `gtkgreet/0.8` |

## 依赖

| 依赖 | 版本 | 角色 |
|------|------|------|
| gtk | 3.24.43 | 构建 + 链接（broadway 后端 OHOS 二进制） |
| json-c | 0.18 | 构建 + 链接（greetd IPC 消息编解码） |
| gettext | 0.22.5.1 | 构建期提供 `msgfmt`（`po/` 的 `i18n.gettext`） |
| meson | 1.11.0 | 构建工具（`tool_requires`） |

**gtkgreet 不依赖 greetd 构建**：它自带 greetd IPC 协议实现
（`gtkgreet/proto.c`，json-c 编解码 + `AF_UNIX` socket），源码既不包含
greetd 头文件也不链接 greetd 库。greetd daemon 是**运行期**配套件。

## 适配要点

- **构建期工具**：本机 PATH 无 `meson`，配方 `tool_requires("meson/1.11.0")`；ninja 由构建环境提供。
- **i18n 工具注入**：meson 的 `i18n.gettext()` 在**配置阶段**就需要 PATH 上有 `msgfmt`，而 gettext 位于
  host 依赖时其 `bin` 不进构建环境 PATH。配方在 `generate()` 中把该包 `bin` 目录前置进 PATH，
  使 `msgfmt` 取自制品仓中为 OHOS 构建的那份，而不是构建机共享前缀里按 glibc 假设构建的那份。
- **可选特性收窄**：上游 `layershell` / `man-pages` 默认 `auto`；制品仓暂无 `gtk-layer-shell` 与
  `scdoc`，配方显式传 `-Dlayershell=disabled -Dman-pages=disabled`，避免配置行为随构建机环境漂移。
- **`-lintl` 补齐**：制品仓 `gtk/3.24.43` 的 `glib-2.0.pc` 缺 `-lintl`（glib 2.84 的 `g_libintl_*`
  符号在 `libintl.so`），在 `generate()` 中补入，避免链接期 undefined symbol。
- **`GOptionEntry` 终止项补丁**：上游 `meson.build` 设 `werror=true`，clang15 的 `-Wextra` 会对
  `main.c` 中 `{ NULL }` 收尾的 `GOptionEntry` 数组报 `missing field 'short_name' initializer`
  并升级为硬错误。补丁 `patches/0001-fix-GOptionEntry-terminator-missing-field-init.patch`
  把终止项补全为全部字段，**不用** `-Wno-missing-field-initializers` 全局压制，以保留上游对其余告警的拦截能力。
- **ELF 签名**：OHOS HMFS 上未签名 ELF 不可执行，`package()` 对 `bin/` 逐个做两轮
  `remove-section .codesign` + `selfSign`。
- **软件级 `commands.json`**：本包构建可执行文件，按 R38 在 `archives/g/gtkgreet/commands.json`
  声明该 CLI 工具（注意位置在**软件级目录**，不在版本目录内）。

## 包内文件

| 路径 | 说明 |
|------|------|
| `bin/gtkgreet` | greeter 客户端可执行文件 |
| `share/locale/<lang>/LC_MESSAGES/gtkgreet.mo` | 上游 `po/` 编译出的翻译（es / fr / ru） |
| `licenses/LICENSE` | 上游许可证 |

## 使用

```sh
conan install --requires=gtkgreet/0.8
# 可执行文件安装到包的 bin/ 目录；运行期需要 greetd daemon 与可用的显示后端
gtkgreet --help
```

## 测试

上游无测试套件（无 `test/` 目录、无 `meson test` 用例）。`test_package/` 做产物级冒烟：
校验 `bin/gtkgreet` 实物存在，并在非交叉构建时执行 `--help` 断言退出码 0
（`--help` 是上游唯一不依赖运行中 greetd daemon 与显示后端的入口，选项解析发生在 `gtk_init` 之前）。

详细配方、补丁与验证证据见 `0.8/`（含 `notes.md` 与 `patches/`）。
