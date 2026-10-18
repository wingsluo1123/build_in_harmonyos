# haveged 1.9.26

haveged 提供 HAVEGE 用户空间随机数据生成命令和 `libhavege`。本归档在 HarmonyOS PC aarch64 上用 Conan 2 打包静态库、头文件及 `haveged` 命令；上游源码取自 `jirka-h/haveged` 的 `v1.9.26` 发布标签。

本设备 `/dev/random` 的 `RNDADDENTROPY` ioctl 返回 `ENOTSUP`，因此配方通过 `--disable-daemon` 关闭向内核熵池注入的守护进程功能。文件/流输出及库 API 的实测结果见 [适配笔记](1.9.26/notes.md)，不能把它们解释为内核熵注入已工作。
