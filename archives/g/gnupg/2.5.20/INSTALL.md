# gnupg 2.5.20 安装指南

## 预编译包信息

- 文件: `gnupg-2.5.20-ohos-aarch64.tar.gz` (13 MB)
- 平台: OpenHarmony aarch64
- 状态: built（编译成功）

## 快速安装

### 1. 安装依赖库（必须）

gnupg 运行需要以下依赖库，请先安装：

```bash
# 安装 libgcrypt（加密库）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libgcrypt 1.11.0

# 安装 libksba（X.509 库）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libksba 1.6.7

# 安装 npth（线程库）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- npth 1.8

# 安装 libgpg-error（错误处理库）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libgpg-error 1.55

# 安装 libassuan（IPC 库）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libassuan 3.0.2
```

### 2. 安装 gnupg 预编译包

```bash
# 解压到 ~/usr/local
cd ~/usr/local
tar xzf gnupg-2.5.20-ohos-aarch64.tar.gz

# 或使用安装脚本（如果上传到 cmd-pkgs）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gnupg 2.5.20
```

### 3. 验证安装

```bash
# 设置环境变量
export PATH=~/usr/local/bin:$PATH
export LD_LIBRARY_PATH=~/usr/local/lib:~/usr/local/lib/external:$LD_LIBRARY_PATH

# 验证版本
gpg --version
```

预期输出：
```
gpg (GnuPG) 2.5.20
libgcrypt 1.11.0
...
```

## 包含的二进制文件

| 文件 | 功能 |
|------|------|
| `gpg` | OpenPGP 加密/签名 |
| `gpgv` | 签名验证 |
| `gpgsm` | S/MIME 加密/签名 |
| `gpg-agent` | 密钥代理 |
| `scdaemon` | 智能卡守护进程 |
| `gpgconf` | 配置管理 |
| `gpg-card` | 智能卡工具 |
| `gpgtar` | tar 加密/签名 |
| `gpg-wks-client` | Web Key Service |

## 未包含的组件

以下组件因缺少依赖未编译：

| 组件 | 缺少依赖 | 影响 |
|------|----------|------|
| `dirmngr` | gnutls | 无法访问密钥服务器（需手动配置） |
| `keyboxd` | sqlite3 | TOFU 功能受限 |

如需这些组件，请选择方案 B（完整解决）。

## 运行时依赖

预编译包已包含：
- `libgpg-error.so.0`
- `libreadline.so.8`
- `libassuan.so.9`

用户需安装：
- `libgcrypt.so.20`
- `libksba.so.8`
- `npth.so.1`
- `libiconv.so.2`（可选）

## 故障排查

### 问题: gpg 无法启动

检查依赖库是否安装：
```bash
ldd ~/usr/local/bin/gpg | grep "not found"
```

安装缺失的库后重试。

### 问题: 找不到共享库

设置 LD_LIBRARY_PATH：
```bash
export LD_LIBRARY_PATH=~/usr/local/lib:~/usr/local/lib/external:$LD_LIBRARY_PATH
```

或添加到 ~/.bashrc：
```bash
echo 'export LD_LIBRARY_PATH=$HOME/usr/local/lib:$HOME/usr/local/lib/external:$LD_LIBRARY_PATH' >> ~/.bashrc
```

## 平台限制说明

- HMDFS 文件系统有特殊限制，部分功能可能受影响
- 测试套（make check）因平台限制未执行
- 预编译包已通过质量门禁验证（G1-G4）

## 参考资料

- GnuPG 官方文档: https://gnupg.org/documentation/
- cmd-pkgs 预编译包: https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs
- 编译笔记: `archives/g/gnupg/2.5.20/notes.md`