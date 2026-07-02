# E300: Go linker mmap 输出失败 (OHOS SELinux 限制)

> **结构化数据**: [graph/draft/E300-draft-0BBD.kv](../graph/draft/E300-draft-0BBD.kv) | **原则**: P-TOOLCHAIN-001
> **严重度**: 🔴 blocking | **分类**: platform/go/linker/selinux | **自动修复**: ✅ set-env-var

---

## 错误特征

```
mapping output file failed: permission denied
link: mapping output file failed: permission denied
```

**关键词**: go build, mapping output file failed, permission denied, link, mmap, GODEBUG, Go linker, static ELF

## 根因

OHOS SELinux 策略限制 Go linker (cmd/link) 的 `mmap(PROT_WRITE|MAP_SHARED)` 系统调用。Go linker 使用 mmap 创建输出二进制文件，而 OHOS 上签名的静态 ELF 二进制运行在受限 SELinux 域中，该域不允许对用户文件进行 mmap 写操作。

Python 等动态链接二进制的 mmap 不受此限制，因为它们运行在不同的 SELinux 域中。

## 影响范围

所有使用 Go 语言编译的项目 (`go build`/`go install`)，特别是生成静态 ELF 二进制的项目。

## 解决方案

```bash
export GODEBUG=mmap=0
```

设置 `GODEBUG=mmap=0` 禁用 Go linker 的 mmap 输出，改用 `write()` 系统调用写入输出文件。

在 conanfile.py 中，需要在 `build()` 方法的 `self.run()` 调用中通过 `env` 参数传递：

```python
build_env = [
    "GODEBUG=mmap=0",
    "GOTOOLCHAIN=local",
    "CGO_ENABLED=0",
    ...
]
self.run(cmd, env=build_env)
```

## 验证

```bash
GODEBUG=mmap=0 go build -o test main.go && echo "PASS" || echo "FAIL"
```

## 相关知识

- **E046** — chmod 不生效 (同为 OHOS 平台 SELinux 限制)
- Go 编译产物还需要 ELF 签名 (binary-sign-tool) 才能在 OHOS 上执行

## 涉及软件

所有 Go 语言项目在 OHOS 上编译时。

---

*doc/E300.md · knowledge graph draft · 2026-07-02*
