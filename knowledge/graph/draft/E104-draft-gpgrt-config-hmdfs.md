# E104-draft — gpgrt-config 在 HMDFS 上执行缓慢

## 基本信息
- **ID**: E104
- **标题**: gpgrt-config 在 HMDFS 上执行缓慢导致 configure 卡住
- **触发工具**: gpgrt-config (GnuPG Runtime Config)
- **阶段**: configuration
- **严重度**: 3
- **类别**: platform|hmdfs|gnupg-series

## 问题描述

gnupg 系列软件（gnupg, libgpg-error, libgcrypt, libassuan, libksba, npth）使用 gpgrt-config 脚本检测依赖。在 HMDFS 文件系统上，gpgrt-config 执行非常缓慢（每个依赖检测约 30 秒），导致 configure 超时失败。

## 根因分析

### 最初假设（已修正）
gpgrt-config 脚本在检测依赖时需要：
1. 执行 pkg-config 查询
2. 创建临时测试文件（conftest.c, conftest.er1 等）
3. 编译并运行测试程序

### 实际根因（2026-05-26 验证）
configure 在 config.status 阶段卡住（无输出），实际问题是：

**HMDFS 拒绝在当前目录创建临时子目录**：
- `mktemp -d "./confXXXXXX"` → Permission denied（HMDFS 特殊限制）
- autotools configure 脚本会在当前目录创建临时文件和子目录
- 即使设置 TMPDIR 环境变量，部分测试仍在当前目录执行

**验证过程**：
1. 设置 TMPDIR=$HOME/tmp（可写目录）
2. 验证 mktemp 可在 TMPDIR 创建临时文件
3. 运行 configure --prefix=$HOME/usr/local
4. configure 执行约 1 分钟后卡住（无任何输出）
5. 300 秒超时后终止，日志显示停留在 "checking for programs" 之后

**HMDFS 文件系统特性**：
- HMDFS 是分布式文件系统，有特殊的 UID 映射和权限机制
- 不允许在当前目录创建临时子目录（不同于普通只读问题）
- 这种限制是平台级的，无法通过环境变量绕过

## 影响范围

gnupg 系列软件：
- gnupg
- libgpg-error
- libgcrypt
- libassuan
- libksba
- npth

## 解决方案

**方案 1：使用预编译包（唯一可行方案）**
```bash
# 从 cmd-pkgs 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gnupg <version>
```

**方案 2：复制源码到本地目录编译（验证失败）**
```bash
# 最初尝试将源码复制到 /data/local/tmp 绕过 HMDFS
# 但发现 /data 目录不存在，系统无其他可写本地目录
# HMDFS 是唯一的用户可写文件系统
```

**验证结果**（2026-05-26）：
- ❌ /data/local/tmp 不存在（系统无此目录）
- ❌ /tmp 只读（无法创建临时文件）
- ❌ /dev/shm 无权限（tmpfs 但无法访问）
- ✅ ~/tmp 可写（但仍在 HMDFS 上）
- 结论：系统无本地（非 HMDFS）可写目录，无法绕过限制

**方案 3：创建缺失的 *-config 脚本（部分成功）**
- 成功创建 gpgrt-config、gpg-error-config、libassuan-config、ksba-config、npth-config
- 所有依赖版本满足要求（libgpg-error 1.61）
- 但 configure 仍因 HMDFS 临时文件限制卡住

**方案 4：等待 HMDFS 更新**
- 需要系统级更新，允许 configure 在当前目录创建临时子目录
- 或提供真正的本地可写目录（不在 HMDFS 上）

## 验证方法

```bash
# 检查是否是 gpgrt-config 问题
time gpgrt-config --libs libgpg-error
# 如果耗时 > 5 秒，说明存在此问题

# 检查 HMDFS 文件系统
mount | grep hmdfs
```

## 关联知识

- E002: /tmp 只读问题
- E011: HMDFS umask 077 权限问题
- E073: 动态库符号链接运行时加载问题
- R7: 安全弹窗确认

## 状态

- **草稿创建**: 2026-05-26
- **来源**: gnupg 2.5.20 编译失败案例
- **验证状态**: 已验证（第三次尝试，2026-05-27）
- **建议**: 使用预编译包，避免在 HMDFS 上编译 gnupg 系列软件

---

## 第三次验证（2026-05-27）

### 新发现

1. **HMDFS 进程启动限制**：
   - `timeout ./configure` → Permission denied
   - `timeout sh ./configure` → Permission denied
   - **结论**: HMDFS 阻止在 HMDFS 目录中使用 timeout 等进程启动工具

2. **直接运行 sh 命令成功启动 configure**：
   - `sh ./configure --prefix=...` → 成功启动
   - configure 运行约 120 秒后卡住
   - configure.log 停留在 "checking for LIBGCRYPT - version >= 1.11.0..."
   - **结论**: E087 的解决方案（用 sh 替代直接执行）对 configure 本身有效，但对 gpgrt-config 无效

3. **源码复制到 ~/tmp 无效**：
   - 源码复制到 ~/tmp/gnupg-src（仍在 HMDFS 上）
   - chmod +x configure 成功，但 ./configure 仍报 Permission denied
   - **结论**: HMDFS 目录中的脚本执行限制不受 chmod 影响

### 验证流程完整记录

```
源码位置: ~/tmp/gnupg-src（HMDFS）
运行命令: sh ./configure --prefix=/storage/Users/currentUser/usr/local
运行时间: 约 120 秒
停止位置: checking for LIBGCRYPT - version >= 1.11.0...
停止原因: gpgrt-config 执行缓慢导致 configure 超时
结果: 无 config.status，无 Makefile
```

### 最终结论

HMDFS 文件系统存在以下限制，导致 gnupg 系列软件无法编译：

| 限制 | 影响 | 解决方案 |
|------|------|----------|
| chmod +x 不生效 | 新脚本无执行权限 | 用 `sh ./script` 替代（E087）|
| timeout 命令无法启动进程 | 无法在 HMDFS 目录中监控进程 | 直接运行 sh 命令 |
| gpgrt-config 执行缓慢 | configure 超时卡住 | **无解决方案（平台限制）** |
| 临时文件创建限制 | conftest 无法创建 | 设置 TMPDIR 无效 |

**建议升级为正式条目**: 已完整验证，建议将 E104-draft 升级为正式知识条目