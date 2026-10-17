# DRAFT-DEAD-UPSTREAM-SOURCE-RECONSTRUCTION-DEBIAN-BUNDLE-HOMEBREW-BOTTLE：上游站点死亡且全网无镜像时，用 Debian 源码包捆绑树重建完整源码 + Homebrew GHCR bottle 交叉验证

> Source: rmcast 2.0.0 适配（feat/rmcast-2.0.0-codex，2026-10-13）
> 状态：DRAFT — same-stem .md/.kv pair

## 一句话

上游官网 503/下线、无公开 git 仓库、GitHub/GitLab/Fossies/repology 均无镜像、
本机与设备对 web.archive.org 均不可达时，仍有第三条路：**发行版源码包里捆绑的
完整项目树**（sources.debian.org 可达性通常与 archive.org 不同）+ **Homebrew
官方 bottle blob**（ghcr.io 通常可达）做字节级交叉验证，可重建出足以审计与
交叉编译的完整源码树。

## 使用说明（可复制流程）

### ① 找到捆绑了该项目的发行版源码包

很多"孤本"项目因被更大的项目依赖而被发行版源码包整体收录（例：rmcast 2.0.0
被 Debian tgif 1:4.2.5-1.3 捆绑）。检索入口：repology、 Debian sources 搜索、
`sources.debian.org/api/src/<pkg>/<version>/` 的目录列表里找与目标同名的子目录。

### ② 经 sources.debian.org API 递归重建源码树

```python
BASE_API = "https://sources.debian.org/api/src/<pkg>/<ver>/<bundle>"
BASE_RAW = "https://sources.debian.org/data/main/<组>/<pkg>/<ver>/<bundle>"
```

实测要点（踩过的坑）：

1. **子目录列表 API 必须带尾部斜杠**（`.../rmcast/src/` 返回 200，
   `.../rmcast/src` 返回 404）。
2. urllib 直接请求会被 404（UA 差异），用 `curl` 子进程最稳。
3. 有速率限制：429/空响应时 sleep 重试；目录 walk 要容错跳过失败项。
4. `autom4te.cache/` 一类生成物目录跳过不下载。

### ③ 与 Homebrew bottle 交叉验证身份（防止重建树≠目标版本）

1. `https://formulae.brew.sh/api/formula/<name>.json` 拿 bottle blob 的
   ghcr.io 地址与源码 sha256（Homebrew 对源码包做过权威校验，可当 SHA-256
   的旁证来源）。
2. 下载 bottle blob（先 `ghcr.io/token?scope=repository:homebrew/core/<name>:pull`
   取匿名 token，再 `GET /v2/homebrew/core/<name>/blobs/sha256:...`），
   本地复算 blob sha256 一致。
3. **交叉判据**：bottle 内的文档文件（README/AUTHORS/ChangeLog/LICENSE 等）
   字节数与重建树逐一相同 + configure.in/版本文件声明同版本号 ⇒ 同一版本。
4. bottle 同时给出**产物布局与许可证文件名**，可直接指导 package() 设计。

### ④ 使用边界

重建树与官方 tarball **不保证逐字节相同**（打包元数据、可能的发行版微调）。
因此：

- conandata.yml **保持官方 URL + 官方 SHA-256**（R39），不写入重建树哈希；
- 本地/真机构建验证可用临时本地注入（`file://` URL + 重建树哈希，仅存在于
  job/设备目录，不提交），模式同 DRAFT-nift-3.0.3 的「临时注入 + 恢复」；
- 真实下载验证留待任一网络路径恢复官方站时补做。

## 适用范围

- 上游死亡/失联 + 无公开 git 镜像的孤本库；
- 项目被发行版源码包（Debian 系最常见）捆绑收录过；
- 目标只是获得可审计、可交叉编译的源码树，不追求 tarball 字节同一。

不适用：项目从未进过任何发行版源码包（无捆绑树可重建）。

## 输入 / 输出

- 输入：包名 + 目标版本；（可选）Homebrew formula 名（通常同名）。
- 输出：完整源码树（本地目录）+ 身份交叉证据（文件字节数对照、版本声明、
  bottle blob sha256）+ 可选的临时本地注入 tar.gz（自算 sha256）。

## 示例（rmcast 2.0.0 实证）

- 捆绑位置：`sources.debian.org/api/src/tgif/1:4.2.5-1.3/rmcast/`；
- 重建 104 文件（src/ 8 个 .c、rmchat/、mcastproxy/、config/、configure.in…）；
- 交叉验证：AUTHORS 162 / ChangeLog 27492 / README 1032 / LICENSE.QPL 4720 /
  TODO 1454 与 bottle 逐一相同，configure.in `AC_INIT(rmcast,2.0.0)`；
- 官方 SHA-256 引用 Homebrew formula commit a404a99；
- 重建树直接完成 W1 审计 + OHOS clang 交叉编译 + 真机 conan create 全链验证。

## 查重

| 既有条目 | 关系 |
|---|---|
| E999-A90F（上游死亡后的权威镜像认定） | 那条是"找到承继镜像仓"；本条是"无镜像时从发行版捆绑树重建"，互补 |
| DRAFT-nift-3.0.3-source-fallback-hash-provenance | 那条是 github 镜像 fallback + 临时注入模式；本条复用其注入/恢复纪律，新增"捆绑树重建"来源 |
| E299/E222（Conan 源码获取失败分层诊断） | 那两条是诊断框架；本条是其"无镜像分支"的具体出路 |
| E576-draft-B1A2（dawg） | 仅引用 sources.debian.org 的单文件 raw URL；本条是整树 API 递归重建 + bottle 交叉验证方法论 |

## 关键词

sources.debian.org, Debian source bundle, 捆绑树, Homebrew bottle, GHCR blob,
ghcr.io token, sha256 provenance, dead upstream, 无镜像孤本库, 交叉验证,
file:// 临时注入, 字节数对照
