# GnuPG

GNU Privacy Guard (GnuPG) 是一个完整的 OpenPGP 标准实现，用于加密、签名数据和通信。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.5.20 | built | 2026-05-27 |

## 快速安装

```bash
# 1. 安装依赖库
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libgcrypt 1.11.0
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libksba 1.6.7
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- npth 1.8

# 2. 安装 gnupg
tar xzf gnupg-2.5.20-ohos-aarch64.tar.gz -C ~/usr/local

# 3. 验证
gpg --version
```

详细安装指南: `2.5.20/INSTALL.md`

## 编译状态

### 2.5.20

**状态**: failed

**失败原因**: HMDFS 文件系统临时文件限制

在 configure 阶段，config.status 脚本尝试在当前目录创建临时子目录（`mktemp -d "./confXXXXXX"`），HMDFS 文件系统拒绝此操作，导致 configure 卡住超时。

**尝试的方案**:
- 替换 config.guess/config.sub → 成功识别平台
- 设置 TMPDIR 环境变量 → 无效
- VPATH out-of-tree 构建 → 无效
- 预创建临时目录 → 无效

**依赖库状态**（通过预编译包安装）:
- libgpg-error: 1.55（需要 >= 1.56）
- libgcrypt: 1.11.0 ✅
- libassuan: 3.0.2 ✅
- libksba: 1.6.7 ✅
- npth: 1.8 ✅

**结论**: HMDFS 文件系统限制阻塞了所有 gnupg 系列软件的 configure 执行。建议等待文件系统更新或使用其他编译环境。

## 相关知识

- E007: config.guess 无法识别 HarmonyOS（已通过补丁解决）
- E073-draft: HMDFS 临时文件限制（新发现）

## 补丁

- `0001-build-aux-config.guess.patch`: OHOS 平台识别
- `0002-build-aux-config.sub.patch`: OHOS kernel-os 组合验证