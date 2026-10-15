# MVDSV

MVDSV 是一个面向 QuakeWorld 的高性能专用服务器，支持 UDP 游戏通信以及 QTV TCP 流。

## HarmonyOS 适配

- 使用 HarmonyOS clang 和 Conan CMake 工具链构建 AArch64 可执行文件。
- 使用官方固定提交源码及其 `qwprot` 子模块提交，不依赖未发布的第三方制品。
- 对最终安装的 ELF 原位签名，并检查 `.codesign`、动态依赖及路径可迁移性。
- 修复非阻塞 QTV TCP 发送队列在短写后缺少独立写就绪推进的问题。
- 在 HarmonyOS PC 上验证服务启动、版本输出、签名执行和确定性 TCP 背压三臂回归。

## 上游

- 项目：https://github.com/QW-Group/mvdsv
- 版本：https://github.com/QW-Group/mvdsv/releases/tag/1.11
