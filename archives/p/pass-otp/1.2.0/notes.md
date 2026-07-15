# 编译笔记 - pass-otp 1.2.0

## 基本信息

- **软件名称**: pass-otp
- **版本**: 1.2.0
- **构建系统**: Makefile（纯 shell 脚本，无需编译）
- **编译日期**: 2026-07-15

## 编译过程

### Step 1: 源码获取

从 GitHub 官方源获取 v1.2.0 tarball：
- URL: https://github.com/tadfisher/pass-otp/archive/refs/tags/v1.2.0.tar.gz
- SHA256: 5720a649267a240a4f7ba5a6445193481070049c1d08ba38b00d20fc551c3a67

### Step 2: 安装

pass-otp 是纯 shell 脚本扩展，无需 configure 和编译步骤。
直接执行：
```bash
make install PREFIX=/usr DESTDIR=staging
```

安装产物：
- `usr/lib/password-store/extensions/otp.bash`（扩展脚本）
- `usr/share/man/man1/pass-otp.1`（man 手册）
- `etc/bash_completion.d/pass-otp`（bash 补全）

### Step 3: Conan 配方

生成 conanfile.py，特点：
- `settings = "os", "arch"`（纯脚本，无需编译器设置）
- `build()` 运行 `make install PREFIX=/usr DESTDIR=staging`
- `package()` 从 staging 复制到 package_folder，确保 otp.bash 可执行
- `package_info()` 无 libs/libdirs/bindirs（pass 扩展，非库非二进制）
- conandata.yml 使用官方 GitHub URL

### Step 4: 测试

test_package 验证：
- otp.bash 扩展脚本存在
- bash -n 语法检查通过
- man 手册文件存在

## 运行时依赖

pass-otp 需要以下运行时组件：
- **必需**: `pass` >= 1.7.0（密码管理器）
- **必需**: `oathtool`（OTP 生成工具，来自 oath-toolkit）
- **可选**: `qrencode`（QR 码生成）

## 特殊说明

1. pass-otp 是 pass 密码管理器的扩展，不是独立软件
2. 安装路径遵循 pass 的扩展目录约定：`lib/password-store/extensions/`
3. 无需 ELF 签名（纯文本脚本）

---
**编译结束**: 2026-07-15
**最终状态**: built
---

**编译结束**: 2026-07-15 20:06
**最终状态**: built
