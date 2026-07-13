# anyenv 1.1.5 适配笔记

## 编译环境
- 构建系统: custom（纯 Bash 脚本，无编译步骤）
- 编译日期: 2026-07-14
- 编译器: N/A
- 状态: built

## 编译步骤

```bash
python3 scripts/ohc-run.py init-build anyenv 1.1.5 --url=https://github.com/anyenv/anyenv/archive/refs/tags/v1.1.5.tar.gz --force
conan create archives/a/anyenv/1.1.5 --build=missing
python3 scripts/ohc-run.py conan-verify anyenv 1.1.5
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 自动搜索 latest 失败 | anyenv 未在自动 URL 注册表中 | 手动指定 GitHub tag v1.1.5 源码包 URL |
| 2 | 本机 Python HTTPS 证书校验失败 | 本地 CA 证书链缺失 | 先用 curl -k 取得源码并触发 init-build 环境检查安装 CA；归档仍使用正式 HTTPS URL 与 sha256 |
| 3 | `anyenv -v` 找不到 `anyenv---version`，且包内 `bin/anyenv` 为断链 | 上游 `bin/anyenv` 是指向 `../libexec/anyenv` 的软链接，复制到 Conan 包后目标不存在；同时子命令依赖 PATH 查找 | Conan package 从 `libexec/` 复制真实 `anyenv` 文件和 `anyenv-*` 子命令到包内 `bin/` |
| 4 | 消费者测试提示脚本 inaccessible/not found | Conan 测试环境 PATH 未包含当前 Bash 所在目录，`#!/usr/bin/env bash` 无法解析 | test_package 显式把 `command -v bash` 所在目录加入 PATH；配方不声明未发布的 `bash/5.3` 依赖 |

## 源码修改

无源码补丁。上游脚本已使用 `#!/usr/bin/env bash`，不需要 OHOS shebang 修复。

## 依赖版本

无 Conan 构建依赖。运行时需要系统 PATH 提供 Bash、coreutils/readlink、sed、awk、sort 等基础命令。

## 验证结果

消费者测试覆盖：
- `anyenv -v`
- `anyenv commands`
- `anyenv help version`
- `anyenv root`
- test_package PATH 注入当前 Bash 目录

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 纯脚本 Conan 配方 |
| `conandata.yml` | 上游源码 URL 与 sha256 |
| `test_package/` | Conan 消费者 smoke test |
| `manifest.yaml` | 版本级编译元数据 |
---

**编译结束**: 2026-07-14 01:20
**最终状态**: built
