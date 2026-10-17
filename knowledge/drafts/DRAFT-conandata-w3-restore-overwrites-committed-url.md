# DRAFT — 修复必须落在"会入仓的那个文件"上

> 拟提升编号：E555（最终编号由知识库主编确认）
> 来源：termsvg / termshot / termshark 三包适配（2026-10-13）

## 错误特征

三包都出现同一个**反复复发**的 P0：

```
W3 日志末尾："[step] Pre-download: conandata.yml 已还原为官方 URL"
但实际入仓文件：
    sources:
      "2.4.0":
        url:
          - "https://gh-proxy.com/https://github.com/gcla/termshark/archive/refs/tags/v2.4.0.tar.gz"
          - "https://github.com/gcla/termshark/archive/refs/tags/v2.4.0.tar.gz"
```

而 `manifest.yaml` / `notes.md` 里写的却是干净的官方 URL —— 申报与入仓内容不一致。

## 根因：还原基准不是官方 URL

R39 + preflight PF7（fail-closed 硬闸）要求 `sources.url` 为**单一官方 URL**，
镜像前缀由 CI fallback 自动注入。

但本地 **W3 / pre-download 流程会先把 URL 改写成镜像**（ghfast.top / gh-proxy 等），
跑完再打印「已还原为官方 URL」。关键是：**"还原"的基准是本次改写前的运行状态**。

由此产生的三类错误：

### 1. 修复只落在备份件（最隐蔽）

`.gitignore` 忽略了 `*.orig` / `**/*.ghfast-bak`，所以：

| 文件 | 是否入仓 | 内容 |
|------|----------|------|
| `conandata.yml.orig` | ❌（gitignored） | 干净的官方 URL |
| `conandata.yml.ghfast-bak` | ❌（gitignored） | 干净的官方 URL |
| `conandata.yml` | ✅ **入仓** | 仍是 gh-proxy 列表 |

W3 每轮"还原"都把入仓文件还原回镜像态 → **修复永远不生效**，
而日志打印"已还原"制造了"已修复"的假象。

### 2. `git add -A` 把注入态提交

W3 改写工作区后，`git add -A` 会把镜像 URL、备份件、状态文件
（`.ci-result.json`、`.build-closed`、`.conan-verified`）一并带入 commit。

### 3. 只核对"申报"而非"入仓内容"

`manifest.yaml` / `notes.md` 的 URL 是人工撰写字段，与入仓 `conandata.yml`
可能不一致 → R52 证据一致性 FAIL。

## 解决方案

**只改会入仓的那个文件**，并消除还原源：

```bash
# 1. 写入仓文件为单一官方 URL
cat > <version_dir>/conandata.yml <<'EOF'
sources:
  "2.4.0":
    url: "https://github.com/gcla/termshark/archive/refs/tags/v2.4.0.tar.gz"
    sha256: "949c71866fcd2f9ed71a754ea9e3d1bdc23dee85969dcdc78180f1d18ca8b087"
patches:
  "2.4.0": []
EOF

# 2. 删除备份件（既是还原源，也是误提交源）
rm -f <version_dir>/conandata.yml.orig <version_dir>/conandata.yml.ghfast-bak

# 3. 只 add 明确的配方输入路径，绝不用 add -A
git add archives/t/termshark/2.4.0/conandata.yml
```

**校验必须回读入仓态**：

```bash
git show HEAD:archives/t/termshark/2.4.0/conandata.yml | grep -E "^\s+url"
```

工作区可能被 W3 改写，备份件不会入仓，manifest/notes 是申报——
**只有 `git show HEAD:` 才是入仓事实**。

若 W3 后工作区被污染，结束时恢复：

```bash
git checkout -- <version_dir>/conandata.yml
```

## 验证

```bash
# 入仓态应为单一官方 URL、无镜像前缀、无列表
git show HEAD:archives/t/<l>/<n>/<v>/conandata.yml
# 预期输出：
#   url: "https://github.com/.../v2.4.0.tar.gz"
#       sha256: "..."
```

三包修正后入仓态全部确认为单一官方 URL，`.orig` / `.ghfast-bak` 已清零。

## 推广价值

适用于**所有**需要下载源码的归档配方，凡 W3 / pre-download 会改写
`conandata.yml` 的包都命中。更一般的教训：

> **"修复"必须定义在"会被交付的那个文件"上**;
> 用版本控制（`git show HEAD:`）而非工作区或申报字段来验收。
