# rrsync 3.4.4 for HarmonyOS PC (aarch64-linux-ohos)

## 概述

rrsync 是 rsync 官方源码自带的 Python3 包装脚本（位于 rsync 源码树 `support/rrsync`），
用于将 rsync 限制到 `.ssh/authorized_keys` 中声明的子目录，常用于为 SSH 用户提供
受限的 rsync-only 访问（只读 `-ro` / 只写 `-wo` 等）。

- 上游版本：3.4.4（与 rsync 3.4.4 同步发布）
- 上游源：https://rsync.samba.org/ftp/rsync/src/rsync-3.4.4.tar.gz
- 协议：GPL-3.0-or-later
- 类型：解释型脚本工具（无编译，no-build 族）

## 鸿蒙适配要点

| 项 | 说明 |
|----|------|
| 构建系统 | 无（脚本直接安装到 bin/） |
| 补丁 0001 | `RSYNC` 常量由硬编码 `/usr/bin/rsync` 改为 `shutil.which('rsync') or '/usr/bin/rsync'`，在 conan/鸿蒙环境下按 PATH 解析 rsync |
| 运行期依赖 | python3 解释器；rsync 二进制（conan `rsync/3.3.0` 包可提供） |
| shebang | 保持上游 `#!/usr/bin/env python3`，通过 PATH 解析 python3 |

## 测试（test_package）

上游 rsync testsuite 无 rrsync 专项测试（已清点：`testsuite/` 下 0 命中），
自行补齐 4 项测试（见 test_package/test_rrsync.sh）：

1. `rrsync -h` 帮助输出，exit 0
2. 无 `SSH_ORIGINAL_COMMAND` 时正确拒绝（"Not invoked via sshd"，exit 1）
3. 端到端受限拉取：客户端 rsync 通过 rsh shim（模拟 sshd）经 `rrsync -ro` 拉取文件，内容一致
4. 只读强制：向 `-ro` 服务器写入被拒绝（"sending to read-only server"）
