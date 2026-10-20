# DRAFT-juke-0.7-transparent-decompression-hash-mirror-first
> 官方小众源透明解压致哈希失配时前置字节一致镜像
## 问题特征（真实日志片段/标记）
- 真机 `source()` 中断：`ERROR: juke/0.7: Error in source() method, line 40` + `ConanException: sha256 hash failed for 'juke-0.7.tar.gz' file.`
- 真机哈希对账：期望 `b19d6bb46ece9f47b07bcd52e371b447fbef580ffb9ded59257305962f47cae0`，实算 `9a5eb5cf4a2e523d8859a0f590867d91c331bd3151a1bf1a3593946839a9af68`（`Provided hash ... vs Computed hash ...`）。
- 本地复现：`curl` 官方 URL 得 266240 字节、sha256 与真机一致、文件头为 tar；`curl` pkgsrc distfiles 镜像得 64103 字节、sha256 与配方完全一致、gzip 魔数 `1f8b`。
- 门禁指纹：`v2:compile:download_unavailable`；关键词 `autotools_configure, hmbs_repair_method, no_tests`。
## 根因
- moll.no 经传输链路返回了解压后的 266240 字节 tar（仍命名 `.tar.gz`），与 64103 字节 gzip 原件字节不同，非偶发截断。
- 配方单 URL 直连官方源时，真机与本地同现哈希失配，无法仅靠重试通过。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 本地取证：分别 `curl -L -o official.tgz <moll.no URL>` 与 `curl -L -o mirror.tgz <pkgsrc distfiles URL>`，核对 `wc -c + sha256sum + file` 双一致（官方 266240/9a5eb5cf/tar，镜像 64103/b19d6bb4/gzip）。
2. `archives/j/juke/0.7/conandata.yml`：`sha256` 保持 `b19d6bb46ece9f47b07bcd52e371b447fbef580ffb9ded59257305962f47cae0` 不变，`url` 改为有序列表，pkgsrc 镜像在前、官方 URL 在后回退，并在注释说明该镜像仅支持 http（https 证书无效，属上游不支持 HTTPS 的例外）。
3. `archives/j/juke/0.7/manifest.yaml`：同步 `source.url` 与 `mirror_note`；`archives/j/juke/0.7/notes.md` 新增一行记录；PR 草稿补充说明。
4. 验证：真机 `source()` 校验通过即关闭 `download_unavailable`；后续 `configure`/`ncurses`/`no_tests` 问题按各自条目处理，不在本条目内猜改 `-static`/LIBS。
## 禁止策略
- 禁止为迎合透明解压后字节将 `sha256` 改为 `9a5eb5cf...`；镜像必须本地验证尺寸与哈希双一致。
- 禁止删除官方 URL 回退后伪装为长期多源策略；本排序仅为 juke 单库临时补丁。
## 与相近条目的边界（查重）
- 本条目核心修法自认复用现有经验（jamnntpd/myman 编译器 PATH 探测回退、dhex/dialog 的 libncurses 兼容链接、libofa/aldo 的 no-tests 接线、ADAPTATION_GUIDE §5），未产生现有技能库解决不了的新类问题，镜像排序亦只是 juke 单库临时补丁，故 Q1 不通过。
- Q2 虽通过（命中仅相邻但不相同），但官方口径要求同时满足可抽象通用解法与增量性，缺一即不走知识库扩展；若抽象则限于“官方小众源透明解压致哈希失配时前置字节一致镜像”，仍属单库临时绕过，不建议立项。
- 与编译器死路径、config.sub 三元组、`-lncurses` 缺失、空 `make check` 等条目正交，不得混用。
## 适用判断
- 仅当同时满足才用本条目：官方小众源可复现透明解压或字节变化；权威镜像（pkgsrc/FreeBSD distfiles）可提供同尺寸同哈希原件且本地验证为合法 gzip；`sha256` 不做任何迎合修改。
- 否则走正常换源或上游修复通道；本镜像前置不得推广为通用多源立项。
