# mscompress 0.4 —— 适配笔记

## 目标平台
- HarmonyOS PC (aarch64)，os=OHOS arch=armv8，clang 15（`/data/service/hnp/bin/clang`，target aarch64-unknown-linux-ohos）
- Conan 2.29.1（OHOS 适配版），profile: `ci/conan/profiles/ohos-aarch64`（与 `~/.conan2/profiles/ohos-aarch64` 一致）

## 上游信息
- 仓库: https://github.com/stapelberg/mscompress
- 标签: 0.4 = commit `988955729c1537f441e746a41b8977db860e4d65`（同时为 master HEAD）
- 源码: `https://github.com/stapelberg/mscompress/archive/refs/tags/0.4.tar.gz`，sha256 `71ca0f6216e0be5315ec80c5699c4026a7b7c9872a6248510d3cdf56377da83f`
- 许可: GPL-2.0

## 构建系统
- autotools（configure.ac + Makefile.am，无外部依赖，纯 libc）
- **关键坑**：tag tarball 不含预生成的 `configure`，只有 configure.ac/Makefile.am/autogen.sh；conanfile.py 必须在 build 阶段先 `autoreconf -fiv` 再 configure/make
- 产出两个 CLI 程序：`mscompress`（LZ77 压缩）、`msexpand`（解压），无库文件 → `package_type = "application"`

## 上游测试
- `test/test.sh`：压缩 test.txt → test.txt_，msexpand 解回 test.new，diff 校验（与 test.compressed 及原文一致）
- test_package/test.sh：安装后对含重复字节的样本做压缩→解压往返，校验字节一致与大小一致（HarmonyOS 专项测试，≥1 例实测）

## 依赖
- 无第三方依赖；跳过 W0 依赖发布检查（无需 registry 探测）

## 门禁状态（随构建更新）
- [x] conan create（W3，.ci-result.json exit_code=0）
- [x] 上游测试（make check，1/1 PASS）
- [x] test_package / HarmonyOS 专项测试（HST_EXIT=0，1/1 PASS）
- [x] finish（finish_success，.build-closed）
- [x] W2（结构完整性 L0a-L0e 通过）
- [x] W3（本地 CI：L0/L1/L2/L4/L5 全 pass，Pass rate 100%）
## 基线隔离审计（W3 JC5）
- 触发：W3 本地 CI 模拟 full 全仓扫描（git ls-files 回退）命中 `archives/u/util-linux-login/2.42.2/.ci-trigger`
- 审计：该文件在 HEAD 已跟踪（`git ls-tree HEAD` = 100644 blob e69de29bb2d1d6434b8b29ae775ad8c2e48c5391，0 字节），属于其他库 util-linux-login，不在本任务 delivery_allowed_paths 内，判定为无关历史基线
- 隔离：`git rm --cached`（仅 index，工作区保留）→ 复验 finish W3 → 恢复：`git restore --staged` 使 index 与 HEAD 无差异；该路径绝不进入本任务 commit
---

**编译结束**: 2026-09-28 23:30
**最终状态**: built

## 知识判定（路径 A：reuse_existing）
- 决策：knowledge_decision = reuse_existing（等价命中 → 路径 A，不创建新草稿）
- 快照：/storage/Users/currentUser/tianyi/knowledge-snapshot-mscompress-0.4-r01-bootstrap-and-adapt-pc2-53-20260928T150732Z（HEAD 401c1e75，main，sparse=knowledge）
- 候选 → 命中对照（逐字段适用性验证）：
  - config.guess 无法识别 HarmonyOS → 显式 --build/--host=aarch64-unknown-linux-ohos：等价命中 E007（cannot guess build type）/E072（config.sub invalid configuration *ohos）/E122/E099 + 草稿 DRAFT-E656-hongmeng-config-guess-and-mtime、DRAFT-E564-oldstyle-config-guess-ohos-reanchor
  - 配置文件生成临时目录 HMDFS 权限（umask 077/config.status）→ E114（bypass-mktemp）/E011/E125/E129，方案一致（剔除 umask 077 / 预处理临时目录）
  - 上游 tag tarball 无预生成 configure → autoreconf -fiv + tool_requires automake/libtool：等价命中 E058（missing configure）+ DRAFT-E652-parasail-conan-autoreconf-triplet-pin、DRAFT-689-gnome-no-configure（先例 repo 内 abiword 同法）
  - W3 镜像回退污染 conandata.yml ghfast-bak → 恢复纯官方 URL+清理：等价命中 DRAFT-E323-conan-verify-ghfast-bak-rollback、DRAFT-ci-predl-curl-missing-conandata-mirror-list-fallback、DRAFT-8960-raqm-conandata-comment-url-predl-pollution（infra/基线，永不路径 B）
- 无新增跨库复用价值候选 → 依据"基线噪声/共享框架/基础设施永不路径 B"；不创建草稿
- 结论：路径 A（前置标题【积分赛】），交付 PR-only，issue_action:none
