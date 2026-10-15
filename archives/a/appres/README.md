# appres

**X.Org 应用资源查看器**（X.Org Foundation，MIT）

`appres` 是一个小型 X11 客户端：连接到 X server 后，按 class/instance 名打印指定客户端的
资源数据库（resource database）。X.Org 官方 `app` 组的常规工具，常用于调试 X 应用的
资源匹配规则。

## 用法

```bash
appres [class [instance]] [-1] [-V] [toolkitoptions]
```

| 选项 | 说明 |
|------|------|
| `-V` / `-version` | 输出版本并退出（**不连接 X**） |
| `-help` | 输出用法并退出（**不连接 X**） |
| `-1` | 只列出指定层级的资源 |
| （无选项） | 连接 `DISPLAY`，打印根窗口资源数据库 |

本包提供命令行工具 `appres`，不含库与头文件（见 `commands.json`）。

## 构建系统

上游 tarball 同时带 `configure` + `Makefile.am`（**官方发布路径**）与 `meson.build`。
本仓走 **autotools**：设备与 CI 均无 meson，且 autotools 是上游发布时验证过的一条。

## OHOS 适配要点

详见版本级 `notes.md` 与 `1.0.7/manifest.yaml` 的 `ohos_adaptation`。摘要：

1. **依赖**：`libx11/1.8.13` + `libxt/1.3.1` + `xorgproto/2025.1`
   （`libxt/1.3.1` 自带 `libx11/1.8.13` 约束 ⇒ 与 `libx11/6.4.0` 互斥，须以 `conan graph info` 验可解）
2. **config.guess / config.sub** 不识 `uname -s = HarmonyOS` ⇒ 补 HarmonyOS case 与 `linux-ohos*` 白名单（E007/E072）
3. **config.status** 的 `umask 077 && mktemp -d` 建 700 目录，HMDFS 拒写 ⇒ 改 022 + `mkdir`（E110/E112）
4. **pkg-config**：上游要 `xproto >= 7.0.17`，conan 的 `xorgproto` 需在 `generate()` 内别名成 `xproto`
5. **不注入平台宏**（R8/PF5）：3 处修复以 `patches/` 下 3 个 portability 补丁落地
   （`conandata.yml` 注册 3 件；`1.0.7/manifest.yaml` 的 `patches_applied` 与
   `patch_generation.patches_count: 3`、磁盘 3 件同源），`build()` 经
   `apply_conandata_patches()` 应用

## 测试

- 上游测试资产 **0**（四口径清点：无 `test*/`、无 `*/res`、无 `*RUNTEST*`、无 `demo|examples`；
  `Makefile.am` 未注册 `TESTS`），`make check` 实测空转。
- `test_package/test.sh` 提供 **4 条**消费者断言（`-version` / `-V` / `-help` 退出码与用法文本），
  均在**连接 X 之前**返回，故在无 X server 的设备上可稳定执行。
