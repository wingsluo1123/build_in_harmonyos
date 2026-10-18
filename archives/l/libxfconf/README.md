# libxfconf — Xfce 配置存储系统（HarmonyOS PC / OHOS aarch64）

`libxfconf`（上游包名 `xfconf`）是 Xfce 的层级化配置存储系统：`libxfconf-0`
客户端库 + `xfconf-query` 命令行 + `xfconfd` 会话守护进程。4.20 起后端由
dbus-glib 迁移到 GDBus，只依赖 GLib/GIO 与 `libxfce4util`。

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名 | libxfconf（上游 `xfconf`） |
| 上游仓库 | https://gitlab.xfce.org/xfce/xfconf |
| 上游下载 | https://archive.xfce.org/src/xfce/xfconf/4.20/xfconf-4.20.0.tar.bz2 |
| 许可证 | GPL-2.0-or-later（库部分为 LGPL-2.0-only） |
| 构建系统 | Autotools（发行 tarball 自带 `configure`） |
| 软件级声明 | `commands.json`（CLI `xfconf-query`，R38） |

## 版本索引

| 版本 | 状态 | 依赖 | 适配要点 | 备注 |
|------|------|------|---------|------|
| 4.20.0 | built | glib/2.84.0.1、libxfce4util/4.20.1 | 2 个补丁：config.guess/sub 识别 `ohos`；`configure` 去掉 config.status 临时目录的 `umask 077`（hmdfs 权限语义）；`generate()` 补 `gio-unix-2.0.pc` 并钉住 `GDBUS_CODEGEN` | [notes](4.20.0/notes.md)、[配方](4.20.0/conanfile.py) |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS，内核 HongMeng Kernel 1.12.0 |
| 架构 | aarch64（conan `arch=armv8`） |
| 编译器 | clang 15（OHOS SDK） |
| conan profile | `ci/conan/profiles/ohos-aarch64`（os=OHOS os.version=6.0） |

## 制品内容

```
bin/xfconf-query                                           CLI
include/xfce4/xfconf-0/xfconf/*.h                          公共头（5 个）
lib/libxfconf-0.so.3.0.0                                   SONAME libxfconf-0.so.3
lib/pkgconfig/libxfconf-0.pc                              pkg-config: libxfconf-0
lib/xfce4/xfconf/xfconfd                                  会话守护进程（libexec 语义）
lib/gio/modules/libxfconfgsettingsbackend.so              GIO GSettings 后端模块
share/dbus-1/services/org.xfce.Xfconf.service             D-Bus 会话服务元数据
share/bash-completion/completions/xfconf-query            bash 补全
```

## 构建与验证

```bash
export CONAN_HOME=<conan 缓存目录>
conan create archives/l/libxfconf/4.20.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

- 消费者测试（`test_package/`，本适配新增的 HarmonyOS 用例）：19/19 断言通过。
- 上游测试（`make check`，automake TESTS）：34/34 通过，0 失败 / 0 跳过。
  逐用例结果与执行环境见 `4.20.0/notes.md` §5 与 `4.20.0/reports/`。

## 依赖

- `glib/2.84.0.1` — glib-2.0 / gobject-2.0 / gio-2.0 / gio-unix-2.0 / gthread-2.0 / gmodule-2.0（含 proxy-libintl）
- `libxfce4util/4.20.1` — Xfce 核心工具库（`configure.ac` 最低要求 4.17.3；4.20.0 未发布到制品仓）

`libxcb`/`xtrans` 与本包无直接依赖，`dbus` 仅在上游测试的运行期（私有会话总线）由测试装置引入，不是本包构建依赖。

## 参考

- 上游文档：https://docs.xfce.org/xfce/xfconf/start
- 适配笔记：`4.20.0/notes.md`
