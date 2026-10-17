# lxi-tools 2.8 适配笔记

## 状态

已完成官方源码固定、语言与唯一性准入、依赖闭包检查、Linux 辅助构建、OHOS AArch64 原生构建、Conan 消费者测试和 HarmonyOS PC 真机三臂验证。当前状态为 `built`；尚未通过 release 上传，因此不标为 `published`。

## 源码与构建

- 官方源码：`https://github.com/lxi-tools/lxi-tools/archive/refs/tags/v2.8.tar.gz`。
- SHA256：`ef9d013189c9449f850d467dd35ac3840929e76a888cdb77e0edbce067da0b2d`。
- 构建系统：Meson；编译器为 HarmonyOS clang 15，目标为 AArch64 OHOS。
- 保留上游默认 GUI，交付 `bin/lxi` 与 `bin/lxi-gui`，没有用关闭 GUI 规避依赖。
- 上游发行归档没有 Git 元数据，版本脚本回退为固定发行版本 `2.8`。
- 最终两个 ELF 均原位签名，恰有一个 `.codesign` 段；无 `RPATH/RUNPATH`，不包含 Conan 缓存或构建目录。

## 依赖闭包

直接依赖及固定版本如下：

- `liblxi/1.22`
- `lua/5.4.8.1`
- `readline/8.3`
- `gtk4/4.22.4`
- `glib/2.84.0.1.1`（共享构建，供 GTK4 依赖图统一使用）
- `libadwaita/1.2.0`
- `gtksourceview5/5.22.0`
- `json-glib/1.10.6.1`
- `cairo/1.18.4`
- `gdk-pixbuf/2.44.6`

为统一现有 GUI 依赖图，配方还固定覆盖 `harfbuzz/14.2.0.1.1.1`、`zlib/1.3.1.1`、`fontconfig/2.18.1.1`、`pango/1.56.4` 与 `zstd/1.5.7.1`。上述依赖均使用制品仓中已有的 OHOS armv8 包。

## 兼容性修复

1. 以 libadwaita 1.2 可用的 about/preferences API 和 UI 父类型实现上游默认 GUI。
2. 通过 Conan 生成的 pkg-config 元数据解析 readline 与完整 GTK4 依赖，不搜索构建机 `/usr`。
3. OHOS 原生 `glib-compile-resources` 不支持新 Meson 传入的 `--dependency-file`；配方仅在能力探测缺失时生成构建目录内的兼容包装器，删除该不支持参数并在成功后生成 depfile。包装器和原生工具的 libffi 路径只影响构建，不进入制品。
4. RAW/SCPI 查询不再把一次 `lxi_receive()` 返回的当前字节批次当作完整响应。文本响应以换行结束；IEEE 488.2 definite-length block 按 `#<n><length><payload>` 声明长度组帧；所有读取共享同一个单调时钟总截止时间，并拒绝畸形、超限、提前关闭和无法在持久连接上判定边界的 `#0`。

liblxi 提供字节接收接口，并未承诺一次调用返回完整 SCPI 消息；组帧责任属于 lxi-tools 应用层。本修复只覆盖 RAW/TCP SCPI 路径，不把 VXI-11 RPC、截图插件或 DNS-SD 发现行为纳入同一知识主张。

## 上游测试清点（R51）

| 清点项 | 数量 | 实际结果 |
|---|---:|---|
| `test/`、`tests/` 自动化目录 | 0 | 官方 2.8 源码没有通用单元测试目录 |
| Meson 条件测试定义 | 3 | desktop、AppStream、GLib schema 元数据验证器 |
| 当前 OHOS 环境注册并运行 | 2/3 | `Validate desktop file`、`Validate schema file` 均 PASS |
| 未注册的条件验证器 | 1/3 | 制品仓无提供 `appstream-util` 的 `appstream-glib`，未执行且不计为通过 |

示例 Lua/脚本需要物理仪器，并非上游注册的自动测试；没有将其虚报为通过或跳过的上游用例。

## 新增验证

- 安装制品消费者共 14 个端到端场景，执行 31 项外部可观察断言，严格多于上游实际运行的 2 项。
- 覆盖 CLI/GUI 存在性、CLI 版本、GUI 帮助入口、AArch64 ELF、HarmonyOS 签名、无 RPATH 与构建路径、目标系统身份；无图形 display 的 SSH 环境不宣称验证窗口呈现。
- 公共 `lxi scpi --raw` 对接持久假仪器，覆盖拆分文本换行、逐字段拆分的 definite-length block、含 NUL payload，以及完整帧后服务器继续保持连接。
- 负测覆盖非数字块头/长度字段、`#0`、声明超限、提前 EOF 与总截止时间超时；同时检查输出字节和退出码。
- 其中 4 类为 HarmonyOS 目标端专项验证；详细计数和证据见 `reports/test-report.md`。

## 路径 B 实证

同一官方源码、配方依赖、目标编译器和公共 CLI 在 HarmonyOS PC 真机形成三臂：上游一次读取以返回码 0 截断为 `ACME,`；等待对端关闭的伪修复在长连接上超时；按协议边界组帧的正确实现于连接关闭前返回完整 `ACME,MODEL\n`。共同条件、命令、输出与仓外原始证据哈希见 `reports/path-b-evidence.md`。

## 交付物

- `bin/lxi`
- `bin/lxi-gui`
- `share/man/man1/lxi.1`
- 上游 GUI 的 desktop、AppStream、schema 与图标资源
- `licenses/LICENSE`
---

**编译结束**: 2026-10-14 06:26
**最终状态**: built
