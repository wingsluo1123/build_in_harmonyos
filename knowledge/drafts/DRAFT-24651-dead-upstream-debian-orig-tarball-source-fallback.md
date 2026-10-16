# DRAFT-24651: 上游官方源失效（OSDN 关站等）→ 权威发行版归档 pristine 取源的 R39 合规策略

- 条目主题：当上游官方托管站点永久失效（OSDN 关站、SourceForge 403/404、域名死亡）时，如何按 R39/PF7 合规口径从权威发行版归档获取 pristine 上游源码，完成 conandata.yml 立项。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 来源事件：jlha-utils 0.1.6 适配评估（2026-10-15；该库最终因 Java 语言被 R47 预检终止，但取源过程暴露本类问题）
- Agent ID：5208

## 一、问题面：为什么这是一类问题

1. **OSDN.net 已停止运营**（2024 年前后），DNS 不再解析：

   ```
   $ curl -sL https://osdn.net/projects/jlha/
   curl: (6) Could not resolve host: osdn.net
   ```

   OSDN 承接了原 SourceForge.jp 的全部日系开源项目（jlha-utils、teraterm 历史版本、crystalfontz 等大批库），关站后这些项目的"官方正式源"一夜之间消失。
2. **SourceForge 个人项目页 403/404**（Cloudflare 盾）：E421 已覆盖"如何从 301 Location 绕短路径下载"，但那是"站点活着、下载被拦"；本条目处理"站点已死"。
3. 知识库现状核查（2026-10-15，index.tsv 547 条）：`grep -iE "osdn|上游.*失效|dead.*upstream"` 无命中——**此类取源策略此前完全未覆盖**，每个遇到的项目都要重新摸索。

## 二、取源回退策略（四级，每级 sha256 留档）

### 第 1 级：确认上游确实死亡（留证据）

```bash
curl -sIL --max-time 15 "https://osdn.net/projects/<proj>/"   # rc=6 / 404 / 403
```

用 [Wayback Machine](https://web.archive.org) 查项目历史快照，确认：项目归属、最后版本号、原发布页 URL。这段记录写进 notes.md 作为"上游失效"立项证据。

### 第 2 级：从权威发行版归档取 pristine 源（首选 Debian pool）

**关键概念：`.orig.tar.gz` = 未打任何发行版补丁的上游原始源**，与官方 tarball 字节等价，符合 R39"权威镜像源"口径：

```bash
# Debian pool 结构（<首字母>/<源码包名>/）：
curl -sO http://deb.debian.org/debian/pool/main/j/jlha-utils/jlha-utils_0.1.6.orig.tar.gz
```

备选权威归档：FreeBSD distfiles、openSUSE Source RPM（`*.src.rpm` 内的 Source0）。
版本辅助定位：`https://sources.debian.org/api/src/<包名>/<版本>/`。

### 第 3 级：交叉验证完整性

```bash
sha256sum jlha-utils_0.1.6.orig.tar.gz
# 与 .dsc 文件的 Hashes 段比对：
curl -s http://deb.debian.org/debian/pool/main/j/jlha-utils/jlha-utils_0.1.6-6.dsc | grep -A4 Hashes
# 或 sources.debian.org API：
curl -s https://sources.debian.org/api/src/jlha-utils/0.1.6/ | python3 -m json.tool
```

实测例：`jlha-utils_0.1.6.orig.tar.gz` sha256 = `0bc81848a5dc7aa596e2f70aeaaa3cfcd261f57546709f69accbe2ba1459d883`。

### 第 4 级：conandata.yml 合规声明

```yaml
sources:
  - url: "https://deb.debian.org/debian/pool/main/j/jlha-utils/jlha-utils_0.1.6.orig.tar.gz"
    sha256: "0bc81848a5dc7aa596e2f70aeaaa3cfcd261f57546709f69accbe2ba1459d883"
```

- PF7 源 URL 闸的镜像黑名单（gh-proxy.com / ghfast.top / cnb.cool 等 14 域）**不含 deb.debian.org**，可正常过闸；
- notes.md 中写明："上游 OSDN 已关站，源取自 Debian pristine orig tarball，sha256 与 Debian .dsc Hashes 段交叉验证一致"。

## 三、红线（forbid）

1. ❌ **禁止解包 .deb 取源**——deb 内是已打发行版补丁、重新 autoreconf 的源，非 pristine；
2. ❌ **禁止引入 debian/patches**——那是发行版维护者的改动，不属于上游；
3. ❌ 黑名单镜像域（gh-proxy/ghfast 等）照旧被 PF7/R39 拦截，本策略不是绕闸后门；
4. 取到源后**仍必须先跑 `lang-preflight`**（R47）——jlha-utils 本例取源成功但为纯 Java 项目，照样在预检即终止。取源策略解决"从哪拿源"，不改变语言/平台判定。

## 四、适用范围

- 上游托管于 OSDN / SourceForge.jp 的日系库（关站后批量失效）；
- 上游域名过期、个人主页消失，但 Debian/FreeBSD 仍维护镜像的老库；
- 任何在选型/立项阶段 sources URL 无法确立的包——先走本策略，再决定是否 `env_unsupported` 上报。

## 五、关联条目

- E421（sourceforge 403 → 301 直连下载法）：站点存活、下载被拦的场景，与本条目互补；
- R39（源 URL 官方源口径）、PF7（源 URL 闸）：本条目是 R39"权威镜像源"在"上游死亡"场景下的落地细则。
