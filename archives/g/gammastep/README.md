# gammastep

gammastep 是 redshift 的活跃分支：**按时间与地理位置调整显示器色温（gamma）** 的命令行工具，
可设白天/夜间色温、附加 RGB gamma 校正、一次性设置或常驻跟随太阳位置。

- 主页: https://gitlab.com/chinstrap/gammastep
- 许可证: GPL-3.0-or-later
- 构建系统: autotools（上游以 git tag 分发，不含 `configure`）

## 版本

| 版本 | 状态 | 构建日期 |
|------|------|----------|
| 2.0.9 | built | 2026-10-16 |

## 四个调节后端

| 后端 | 依赖 | 说明 |
|------|------|------|
| `drm` | libdrm | 直接经 DRM 设置 gamma ramp |
| `wayland` | wayland-client + wayland-scanner | 经 `wlr-gamma-control` 协议向合成器请求 |
| `randr` | libxcb（`xcb-randr`） | X11 RandR 扩展 |
| `vidmode` | libx11 + libxxf86vm | XFree86-VidMode 扩展（老式 X11 路径） |

四个后端全部编译进本包（`gammastep -m list` 可逐条列出）。此外恒带 `dummy` 后端（不做实际调整）。

## 依赖

运行期：`wayland/1.24.0` · `libdrm/2.4.133` · `libxcb/1.16` · `xorgproto/2025.1` ·
`libx11/6.4.0` · `libxxf86vm/1.1.5` · `gettext/0.22.5.1`（libintl）。

构建期工具：`automake/1.18` · `libtool/2.5.4.1` · `intltool/0.51.0` · `gettext/0.22.5.1`。

> ⚠ X11 这一条必须整条同源：`libx11/6.4.0` 与 `libx11/1.8.13.x` 分属两条世代
> （前者钉 `libxcb/1.16 + libxau/1.0.11`，后者钉 `libxcb/1.17.x + libxau/1.0.12`），
> 混用会直接 `Version conflict`。

## OHOS 适配要点

- **源码形态**：git tag archive 不含 `configure` ⇒ `autoreconf -fi`，工具链走 `build_requires`。
- **构建期能力墙**：制品仓 `wayland-scanner` 在本机双向不可执行（未签名 EPERM；自签后
  `DT_NEEDED` 是构建机缓存绝对路径 ⇒ 加载失败）⇒ 从上游同版本源码**静态重建**该生成器，
  写 `wayland-scanner.pc` 顶到 `PKG_CONFIG_PATH`。
- **Libtool 元数据**：制品仓 `.la` 里留有构建机的 `//lib` 与 `.conan2` 绝对路径 ⇒
  **任务局部 libtool 递归 shadow**（重写整条 `dependency_libs` 闭包 + `libdir`，`-L` 前插）。
- **真实依赖面收窄**：`libwayland-cursor` 的 codesign 在本设备校验不过（`dlopen` EACCES），
  而本包源码并不使用 cursor/server ⇒ 把 wayland 的 libs 收窄为 `wayland-client`。
- **零补丁**：两处幂等改写打在 `autoreconf` 生成的 `configure` 上（受限文件系统的 `umask 077`
  临时目录、i18n 工具链的 XML 解析器探测），不回写上游源码。
- **运行期能力面（如实披露）**：四个后端全部编译通过，但在本平台**均不可用** ——
  `/dev/dri` 不存在（ENOENT）、无 Wayland 合成器、无 X 服务器。交付形态与同类无设备工具一致：
  编译与消费者断言照常，**不宣称可实际调节色温**。

## 包内文件

- `bin/gammastep` — 主程序
- `share/locale/*/LC_MESSAGES/gammastep.mo` — 上游 40 余种语言的翻译
- 配方与测试见 `2.0.9/`（`conanfile.py` / `conandata.yml` / `manifest.yaml` / `notes.md` /
  `test_package/`）；软件级 `commands.json` 声明本包为 `tool`。

## 使用

```sh
gammastep -V                 # 版本
gammastep -m list            # 列出编译进来的调节后端
gammastep -h                 # 用法
```

详细构建过程、首错与处置、B 证据与能力面披露见 `2.0.9/notes.md`。
