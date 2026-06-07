# x264 master 编译与修复笔记

## 编译信息
- **软件**: x264
- **版本**: master (0.165.x)
- **构建系统**: autotools
- **编译日期**: 2026-05-31

## 编译过程
x264使用autotools构建系统，在HMDFS环境下configure无法正常执行。
通过手动创建config.mak和config.h文件，手动修改Makefile完成编译。
编译成功，生成静态库和可执行文件。

### HMDFS限制
- HMDFS不支持heredoc，导致configure无法生成配置文件
- 通过手动修改Makefile绕过heredoc限制

## 运行问题修复（2026-06-07）

### 问题现象
编译完成后，usr/local/bin/x264无法执行：
```bash
zsh: permission denied: usr/local/bin/x264
```

### 问题诊断
通过检查发现：
1. 文件权限正确（-rwxrwx---）
2. 文件位于HMDFS文件系统上
3. 文件缺少ELF签名（鸿蒙系统要求）

### 根本原因
**E077 - ELF 签名失效导致 Operation not permitted**

鸿蒙系统的 ELF 可执行文件必须包含有效的 `.codesign` 签名段才能被内核加载执行。
通过 `make install` 安装到 usr/local/bin 的二进制文件缺少签名，
导致内核拒绝加载执行。

### 解决方案
使用 `ohc-run.py sign-elf` 对二进制文件进行签名：
```bash
python3 "$HOME/.opendesk/apps/skills/resources/openharmony-compile-agent/scripts/ohc-run.py" sign-elf usr/local/bin/x264
```

### 修复结果
签名成功后，x264可以正常运行：
```bash
x264 0.165.x
built on May 30 2026, clang: 15.0.4
x264 configuration: --chroma-format=all
libx264 configuration: --chroma-format=all
x264 license: GPL version 2 or later
```

### 预编译包状态
预编译包（x264-master-ohos-aarch64.tar.gz）中的x264已经包含签名，
可以正常运行，无需额外处理。

## 质量门禁
- **G1 Binary Integrity**: PASS ✅
- **G2 Functional**: PASS ✅
- **G3 Portability**: PASS ✅
- **G4 Archive**: PASS ✅

## 知识提取
此问题已在知识图谱中记录为 **E077**：
- 关键词：ELF, signature, codesign, permission denied
- 解决方案：sign-elf 签名工具
- 原则：P-PACK-002（预编译包必须重新签名）

## 最终状态
- **编译**: 成功 ✅
- **签名**: 已修复 ✅
- **功能**: 可正常运行 ✅
- **状态**: 从 partial 升级为 built