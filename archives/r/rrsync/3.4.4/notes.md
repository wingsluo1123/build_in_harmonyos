# Notes — rrsync 3.4.4

## Build Date: 2026-10-03

## 软件定性

rrsync 是 rsync 官方源码树自带的纯 Python3 脚本（`support/rrsync`，390 行），
随 rsync 3.4.4 发布。rsync 上游通过 `configure --with-rrsync` 在 `make install`
时将其装入 bindir。本包为 **no-build 脚本工具族**（SKILL v12.21 headeronly
模板变体 C）：只装不编。

> 关于 R47 语言预检：本包为纯脚本重分发（无任何构建阶段），属 v12.21 明确
> 支持的"解释型脚本工具打包"类；未按 cpp 任务跑 lang-preflight，特此说明。

## 上游测试三步法（R51）申报

1. **清点**：rsync 3.4.4 源码 `testsuite/` 共 100+ 个 .test 用例，
   `grep -rn rrsync testsuite/` **0 命中** —— 上游无 rrsync 专项测试。
2. **运行**：上游 testsuite 针对 rsync 二进制（见 rsync/3.3.0 归档记录：
   因 whoami/SELinux 等平台限制基础设施无法完整运行），与 rrsync 脚本无关。
3. **补齐**：自行编写 test_package/test_rrsync.sh 共 4 项测试（见下），
   本机实测 4/4 通过，通过率 100%。

## Steps Performed

### 1. init-build
- URL: https://rsync.samba.org/ftp/rsync/src/rsync-3.4.4.tar.gz
- sha256: bd88cf82fa653da32314fb229136407c5c90f80d1758d8f4b091767877d8fa96
- 源码解压至 /storage/Users/currentUser/builds/rrsync-3.4.4.work

### 2. 适配分析
- rrsync 无编译；唯一平台相关点是 `RSYNC = '/usr/bin/rsync'` 硬编码。
- 鸿蒙/conan 环境下 rsync 不在 /usr/bin，改为 `shutil.which('rsync')`
  动态解析（补丁 0001，通用可移植性修改，无平台宏——PF5 合规）。
- shebang 保持上游 `#!/usr/bin/env python3`（env 解析，无需 E165 式修复）。
- `braceexpand` 为可选依赖（try/except 有回退），不需要安装。

### 3. 配方
- conanfile.py：package_type=application，source() 拉官方 tarball，
  package() 拷贝 support/rrsync → bin/、rrsync.1 → share/man/man1、
  COPYING → licenses/。package_id 清空（无构建产物）。
- test_package：requires rsync/3.3.0（e2e 测试用 rsync 二进制，
  conan 包 bindirs=["bin"] 提供），4 项测试见上。

### 4. W3 本地验证
- conan create 全量通过，test_package 4/4 PASS（100%）。
- 结果见 .ci-result.json（finish 自动写入）。
---

**编译结束**: 2026-10-03 08:25
**最终状态**: built
