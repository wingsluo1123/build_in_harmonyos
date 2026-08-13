# qbootctl

[qbootctl](https://github.com/linux-msm/qbootctl) 是 Qualcomm A/B 启动槽管理命令行工具（bootctrl HAL 的 Linux 移植），纯 C 实现，Meson 构建。

## 功能

- 查询当前/活跃启动槽（`-c`/`-a`）
- 查询槽位是否可启动/成功（`-b`/`-n`）
- 查询槽位后缀（`-x`）
- 切换活跃槽（`-s`）、标记启动成功（`-m`）、标记不可启动（`-u`）——**需要 root 与真实 A/B 设备**

## 平台接口边界（OpenHarmony 适配要点）

qbootctl 运行期依赖以下 Linux 平台接口，鸿蒙 PC 均已由 OHOS SDK sysroot 提供：

| 接口 | 用途 | OHOS 可用性 |
|------|------|-------------|
| `linux/bsg.h` + `scsi/scsi_bsg_ufs.h` | UFS BSG ioctl（`SG_IO`） | ✅ sysroot 提供 |
| `/dev/disk/by-partlabel` | 定位 GPT 分区 | 运行时设备相关 |
| `/proc/cmdline` | 读取 `slot_suffix` 当前槽 | ✅ |
| GPT 读写（`lseek64`/`BLKSSZGET`） | 读写 GPT 头与分区属性 | 运行时设备相关 |
| `geteuid()` | root 检查 | ✅ |

## 无损测试方案

上游无自动化测试；真实槽位操作（`-s/-m/-u/-i`）被赛事安全边界禁止。本归档通过补丁
`patches/0001-qbootctl.c.patch` 提供：

- 环境变量 `QBOOTCTL_BACKEND=mock` 注入**纯内存 backend**（不访问任何设备），
  可安全测试 CLI 只读路径（`-c/-a/-b/-n/-x`、dump、参数解析、非法槽位拒绝）；
- 默认（未设置环境变量）行为与上游完全一致，生产 backend 保留真实设备语义；
- `-h/--help` 在 root 检查前放行（帮助文本不访问设备），供非 root 环境 smoke test。

## 使用示例

```bash
qbootctl -h            # 帮助（非 root 可用）
QBOOTCTL_BACKEND=mock qbootctl -c   # mock 模式查询当前槽（无设备、无 root）
qbootctl -c            # 真实设备查询（需 root + A/B 设备）
```

## 参考

- [上游仓库](https://github.com/linux-msm/qbootctl)
- [postmarketOS A/B Slots 说明](https://wiki.postmarketos.org/wiki/Android_AB_Slots)
