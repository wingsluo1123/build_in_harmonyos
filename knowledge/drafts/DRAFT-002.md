# DRAFT-002: Go 编译产物未经 ELF 签名无法在 OHOS 执行

> **结构化数据**: [DRAFT-002.kv](DRAFT-002.kv) | **原则**: P-TOOLCHAIN-001
> **严重度**: 🔴 blocking | **分类**: platform/go/elf-signing/selinux | **自动修复**: ✅ shebang-fix
> **状态**: 草稿 (待审查)

---

## 错误特征

```
Permission denied
can't execute: Permission denied
inaccessible or not found
```

**关键词**: Go binary, permission denied, can't execute, ELF signing, binary-sign-tool, selfSign, static ELF, Go build output

## 根因

OHOS 要求所有 ELF 二进制文件必须经过签名才能执行。Go 编译器 (`go build`) 生成的静态 ELF 二进制默认未签名，因此无法在 OHOS 上直接执行。

与动态链接的二进制 (如 Python) 不同，Go 生成的静态 ELF 二进制需要额外的签名步骤。

## 影响范围

所有 Go 语言编译产物的二进制文件，在 OHOS 上执行时。

## 解决方案

```bash
# 1. 创建 module.json
echo '{"module":{"name":"ytt","type":"feature","deviceTypes":["default"]}}' > module.json

# 2. 自签名
binary-sign-tool sign \
  -keyAlias "default" \
  -signAlg SHA256withECDSA \
  -inFile ytt \
  -outFile ytt.signed \
  -selfSign 1 \
  -moduleFile module.json

# 3. 替换原文件
mv ytt.signed ytt && chmod +x ytt
```

## 验证

```bash
binary-sign-tool display-sign -inFile ytt 2>&1 | grep -q "success" && echo "SIGNED" || echo "UNSIGNED"
```

## 相关知识

- **E046** — chmod 不生效 (同为 OHOS 平台 SELinux 限制)
- **DRAFT-001 (E300)** — Go linker mmap 输出失败 (Go 项目在 OHOS 上的另一个问题)

---

*DRAFT-002.md · knowledge drafts · 2026-07-02*
