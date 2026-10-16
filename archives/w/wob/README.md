# wob

wob（**w**ayland **o**verlay **b**ar）是一个轻量的 Wayland overlay 进度条：通过
wlr-layer-shell 在屏幕上叠加显示进度/音量/亮度等状态，配合 sway/i3 等
compositor 的输出管道使用。

## 特性

- 纯 C99，依赖极少（wayland-client、wayland-protocols、inih）
- 颜色/边框/位置/超时等均可经 INI 配置（inih 解析）
- 支持 fractional-scale 分数缩放

## OHOS 适配说明

- 构建期需要 wayland 包的 `wayland-scanner`（OHOS ELF，staging+重签名）
- `seccomp`（运行期 self-sandbox）显式关闭：上游 musl CI 同款，不影响构建与测试
- 运行期需要 Wayland compositor（OHOS 沙箱无 compositor，不影响构建/测试）

## 官方地址

- GitHub: https://github.com/francma/wob
- License: ISC
