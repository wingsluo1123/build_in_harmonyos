# ufiformat

ufiformat 是 UFI 兼容 USB 软驱的命令行格式化工具，可按驱动支持的容量
（1440/1200/720KB 等）格式化软盘、校验介质，也可查询设备信息与列出已接
USB 软驱（`-i`）。

## OHOS 适配

- **构建系统**：Autotools（上游自带 `configure` + `Makefile.in`，2011 年
  生成；无 triplet 规范化，原生构建，无需 config.guess/sub 改造）。
- **依赖链**：仅 `e2fsprogs`（提供 `libext2fs`，用于格式化前检查设备挂载
  状态），复用制品仓已发布的 `e2fsprogs/1.47.4`。
- **编译选项**：终端工具全静态链接（`-static`）；产物经 `binary-sign-tool`
  自签名，否则 HongMeng 内核拒绝执行。
- **已知限制**：格式化/查询路径依赖 Linux 专属设施（`/dev/sg*`、
  `SG_IO` ioctl、`/sys/class/scsi_host`），OHOS 上无对应节点；本配方保证
  编译可移植与无硬件行为（帮助、参数校验、空设备枚举）与上游一致，真实
  格式化需接 USB 软驱硬件（详见版本 notes.md 的 R40 声明）。

## 依赖

- e2fsprogs 1.47.4（`ext2fs`/`com_err`/`uuid`，静态）

## 功能验证

```bash
ufiformat --help   # 期望输出 Usage: ufiformat [OPTION]... [DEVICE]
ufiformat -i       # 无软驱时打印表头后退出 0
```

## 参考

- 上游仓库：<https://github.com/tedigh/ufiformat>
- 规范文档：Universal Serial Bus Mass Storage Class - UFI Command
  Specification Revision 1.0（见上游 README）
- Debian 打包：<https://packages.debian.org/source/sid/ufiformat>
