# gtkgreet 0.8 — 适配笔记

## 上游与定位

- 上游：https://sr.ht/~kennylevinsen/gtkgreet（git.sr.ht 归档 API）
- 归档实测：`GET https://git.sr.ht/~kennylevinsen/gtkgreet/archive/0.8.tar.gz`
  → **HTTP 200 + `application/gzip` + 28694 字节**，
  `sha256=e5c70219da191a60e2e009412603e05c36cee15bbbf7657dbbeaa1d21a692873`，
  `file` 判定 `gzip compressed data`。
- 定位：greetd 的 GTK 欢迎界面（greeter 客户端）。会话列表 + 登录表单，
  经 greetd IPC 协议（JSON over unix socket）与 daemon 通信，
  计划以 cage/gtk-layer-shell 之类的 Wayland 合成器承载。

## 依赖判定（W0，实测读数）

`conan install --build=never -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64`
（探针 `conanfile.txt` 要求 gtk/3.24.43 + json-c/0.18 + gettext/0.22.5.1）：
**rc=0，全部 `Package installed`（无 `--build` 触发）** ⇒ 二进制齐备。

| 依赖 | 版本 | 角色 | 读数 |
|---|---|---|---|
| gtk | 3.24.43 | 构建+链接（broadway 后端 OHOS binary） | Package installed |
| json-c | 0.18 | 构建+链接（greetd IPC JSON 编解码） | Package installed |
| gettext | 0.22.5.1 | 仅构建期 msgfmt（po/ i18n.gettext） | Package installed |

⚠ **greetd 不是本包的构建依赖** —— `gtkgreet/proto.c` 自己实现 greetd IPC
（`json-c` 编解码 + `AF_UNIX` socket），运行期才需要 `greetd` daemon。
故本包**无需**因 greetd 未发布而转手；greetd 0.10.3 仍在主表候选行
（`候选`，任务号空），属**运行期**配套件。

制品仓未见 `gtk-layer-shell`、`scdoc`（`archives/g/` 实测无目录）⇒ 两项可选
特性显式关闭。

## 构建系统

上游 `meson.build`：`c_std=c11`、`warning_level=2`、**`werror=true`**、
`meson_version >= 0.47.0`；`gtkgreet/meson.build` 直接
`dependency('gtk+-3.0')` + `dependency('json-c')`，可选
`gtk-layer-shell-0`；`po/meson.build` 无条件 `i18n.gettext()`。

## 配方要点

1. `generate()` 里 `PkgConfigDeps` 后补 `glib-2.0.pc` 的 `-lintl`
   （gtk/glade 同款；glib 2.84 的 `g_libintl_*` 符号在 `libintl.so`）。
2. `-Dlayershell=disabled -Dman-pages=disabled`（制品仓无 gtk-layer-shell/scdoc）。
3. gettext 包 `bin/` 前置进 PATH 供 `msgfmt` 使用。
4. machine file 注入 `ar/ranlib/pkg-config/ninja` 绝对路径（裸名 ENOENT 守则）。
5. `package()` 对 `bin/` 下 ELF 两轮 `remove-section .codesign` + `selfSign`
   （HMFS 未签名 ELF 不可执行）。

## 测试

上游**无测试套件**（无 `test/` 目录、无 `meson test` 用例）⇒ 上游静态/运行
测试数 **0**；`test_package` 做可执行性冒烟（`bin/gtkgreet` 存在 +
cross-build 时仅校验产物，本机 OHOS 目标可跑时执行 `--help`）。
`--help` 是上游唯一不依赖运行中 greetd daemon 的入口。
---

**编译结束**: 2026-10-16 20:33
**最终状态**: built
