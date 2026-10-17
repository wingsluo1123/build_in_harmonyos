# wayout

wayout 从标准输入读取文本，并把内容渲染成 Wayland 桌面上的 layer-shell 小部件
（可当作 OSD/状态栏/时钟/日历使用）。支持按行、按空行或自定义正则分隔符周期性
刷新（feed），并支持 pango markup 与颜色/边框/字号/位置配置。

上游要求合成器实现 Layer-Shell 与 XDG-Output 协议（wlroots 系 compositor）。

## 包内容

| 路径 | 说明 |
|------|------|
| `bin/wayout` | 可执行文件（HarmonyOS PC aarch64 / clang 15 / musl，已自签名） |
| `licenses/LICENSE` | 上游 GPL-3.0 许可证 |

## 依赖

`wayland/1.24.0`、`wayland-protocols/1.48`、`cairo/1.18.4.2`、`pango/1.58.2`
（`expat` 统一为 2.8.2.1 override）。均为动态链接，使用 Conan 运行时环境
（`VirtualRunEnv`）提供 `LD_LIBRARY_PATH`。

## 用法

```sh
cal | wayout                       # 静态日历
while true; do date +%H:%M:%S; sleep 1; done | wayout --feed-line
echo '<b>bold</b> <span foreground="red">red</span>' | wayout
wayout --help
```

## OHOS 适配要点

1. 上游 `meson.build` 使用 `dependency.get_pkgconfig_variable()`，该 API 在
   Meson 1.6 已移除 → 补丁改为 `get_variable(pkgconfig: ...)`。
2. Conan 的 `PkgConfigDeps` 只按 `pkg_config_name` 生成一个 `.pc`，因此
   `wayland-cursor` / `pangocairo` / `wayland-scanner` / 带 `pkgdatadir` 的
   `wayland-protocols` 需要配方侧桥接 `.pc`（prefix 指向真实包目录）。
3. wayland 包的 `bin/wayland-scanner` 带构建机绝对 `DT_NEEDED` 且未签名，
   HMFS 上直接执行 EPERM → staging（patchelf 改写 soname + 重签名）+ wrapper
   注入 `LD_LIBRARY_PATH`，构建期用它生成三个协议绑定。
4. OHOS 上 Python subprocess 不能以裸名查找可执行文件 → meson 机器文件注入
   `pkg-config`/`ninja`/`ar`/`ranlib` 绝对路径。
5. 产物 ELF 自签名后才能在 HMFS 上执行。

## 上游资源

- 上游仓库: https://git.sr.ht/~proycon/wayout
- 上游源自 wlclock: https://git.sr.ht/~leon_plickat/wlclock
- 许可证: GPL-3.0-or-later

## 已知限制

- 运行需要一个实现了 `wlr-layer-shell`（以及 xdg-output）的 Wayland 合成器；
  HarmonyOS PC 默认没有该合成器，因此本包在设备上验证的是「加载 + CLI 契约 +
  真实 `wl_display_connect` 失败路径」，未做真实显示渲染。
- 上游无自动化测试套件（无 `tests/`、无 `meson test` 注册），验证依赖
  消费者测试（见 `test_package/`）。
- 二进制不带 RPATH，运行时依赖 Conan 运行时环境（`conanrun` /
  `VirtualRunEnv`）提供依赖库路径。
