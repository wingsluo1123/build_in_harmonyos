# E103: HMDFS config.status 临时文件创建失败

## 问题描述

在鸿蒙系统的 HMDFS（分布式文件系统）上编译使用 autotools 构建系统的软件时，`config.status` 脚本无法在当前目录创建临时文件，导致 configure 流程失败。

## 典型错误日志

```
./config.status[790]: can't create ./confUPJTsI/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

或

```
./config.status[4505]: can't create ./confhJkMcl/subs1.awk: Permission denied
```

## 根因分析

1. **HMDFS 文件系统限制**：鸿蒙的分布式文件系统（HMDFS）对用户目录施加了特殊限制，禁止创建临时子目录和某些类型的临时文件。

2. **config.status 工作机制**：autotools 的 `config.status` 脚本使用 `./confXXX/` 模式在当前目录创建临时子目录和文件（如 `subs1.awk`），用于生成最终的配置文件（Makefile、config.h 等）。

3. **冲突点**：HMDFS 禁止这种操作，导致 `config.status` 无法完成配置文件的生成。

## 文件系统分析

| 路径 | 文件系统类型 | 状态 |
|------|-------------|------|
| `/storage/Users` | tmpfs (HMDFS 映射) | 受限制 |
| `/tmp` | erofs (只读) | 无法使用 |
| `/data/local/tmp` | hmfs | 权限拒绝 |
| `$HOME/tmp` | tmpfs (HMDFS 映射) | 受限制 |

## 尝试过的绕过方案（均失败）

| 方案 | 描述 | 结果 |
|------|------|------|
| TMPDIR=$HOME/tmp | 设置 TMPDIR 环境变量 | config.status 仍在当前目录创建临时文件 |
| /data/local/tmp | 使用不受 HMDFS 限制的目录 | 权限被拒绝 |
| 源码目录构建 | 在源码目录执行 configure | 同样受 HMDFS 限制 |
| --srcdir 指定源码 | configure 时使用 --srcdir | config.status 仍在构建目录创建临时文件 |

## 受影响的软件范围

所有使用 autotools 构建系统的大型项目：
- gnutls（TLS 库）
- nettle（加密库）
- 以及其他使用 `configure` + `config.status` 的软件

## 当前解决方案

**无可用命令级解决方案**。需要：

1. **平台更新**：等待 HMDFS 文件系统更新，支持在用户目录创建临时子目录和文件。
2. **系统管理员介入**：修改 HMDFS 权限配置，或将用户目录映射到不受限制的位置。
3. **预编译包**：使用 cmd-pkgs 提供的预编译包（如果可用）。

## 验证方法

在构建目录执行以下命令，观察是否被拒绝：

```bash
mkdir -p ./confXXX
echo "test" > ./confXXX/test.txt
```

如果出现 `Permission denied`，说明 HMDFS 限制生效。

## 知识沉淀建议

当遇到此问题时，记录到软件的 `notes.md`：

```markdown
## HMDFS config.status 限制

- 编译失败原因：config.status 无法创建临时文件（HMDFS 限制）
- 需要的平台更新：HMDFS 支持临时文件创建
- 替代方案：等待预编译包或平台更新
```

## 相关 SKILL 铁律

- R11: 失败先查归档再动手
- R12: 先匹配错误模式再修复
- 此问题属于平台限制（E002 相关），但 E002 主要关注 /tmp 只读，E103 关注 HMDFS 当前目录限制

## 版本信息

- 记录日期：2026-05-28
- 影响平台：HarmonyOS（HMDFS）
- SKILL 版本：v7.8+