**【申请人账号】** `akajhsbnz`（怜惜～）
**【队伍名称】** jumping_姜圣帝君
**【申请日期】** 2026/10/13
**【库名称】** libcaca
**【版本】** 0.99.beta20.1
**【关联 PR】** #15538（https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15538）
**【分支信息】** feat/libcaca-0.99.beta20.1 → main
**【当前提交】** 分支 `feat/libcaca-0.99.beta20.1` 最新提交 `2d7fce9017`（含递增版本目录、路径 B 草稿、notes 的「路径 B 材料」指向与本文；以分支最新为准）
**【PR 状态】** 开放中
**【当前 CI】** 截至回读时未确认（未获取远端 CI 通过证据，不宣称已通过）
**【平台活动】** 开源鸿蒙 PC 专项积分赛

## 一、申请路径 B 的理由

本包原源为上游 GitHub release asset，在受限网络（CI/沙箱）**整体不可达**（`Errno 110` 超时，多次重试）。换源过程中确认了一条**可迁移判据**：官方发行版缓存里的“pristine 产物”有两种形态——**dist tarball**（含 `configure` 等生成物，可直接构建）与**源码快照 / GitHub 归档**（无生成物，需 autoreconf）；只校验“可达 + 哈希”会在构建期以 `configure script is missing` 失败。本包最终采用 Fedora lookaside 的 dist tarball（893,319 B，含 `configure`，Fedora 记录的 sha512 逐字核验一致）。

## 二、推广价值

该判据对**所有需要换源的适配包**通用：本轮除本包外还用于 libcddb（Debian pristine orig）、libbs2b（sourceforge→Fedora）、live555（官方位 301 畸形/TLS 失败→Fedora）、samba（GitHub 归档→官方发布位），并记录了两条硬边界——Debian 的 `+dfsg` 属下游重打包（按 R39/PF7 不宜作替代源）；`*.dl.sourceforge.net` 官方镜像主机只 301 回 `downloads.sourceforge.net`，本项目域名整体不可达时无效。

## 三、知识库查重与新增价值

- **新增草稿**：`knowledge/drafts/DRAFT-ohos-offline-source-switch-criteria.kv` + 配对 `.md`
- **查重方式**：`python3 scripts/ohc-run.py draft-review DRAFT-ohos-offline-source-switch-criteria --json`
- **查重结论**：`verdict=create`（相似度最高 E017(0.17)，无现有条目覆盖该主题；本轮同批草稿之间已做主题切分，互不重复）
- **校验**：`python3 scripts/ohc-run.py graph validate` 全绿
- **新增价值**：把“换源”从‘找一个能下的链接’提升为**有判据的工程动作**：先看形态（生成物是否齐备）再验哈希，并把被排除的候选与理由写入 `conandata.yml`/`notes.md` 供复审。

## 四、证据表

| 类别 | 证据 | 说明 |
|------|------|------|
| 原始失败 | `urlopen error [Errno 110] Operation timed out`（GitHub release asset） | 原源全程不可达；Debian/Void/MacPorts 三份候选均为无 `configure` 的快照 |
| 修复方案 | `conandata.yml` 换为 Fedora lookaside 的 `libcaca-0.99.beta20.tar.bz2`（sha512 核验一致，sha256 `ff9aa641…5ac1`） | 另在 notes.md 记录 4 份候选的逐一排除过程 |
| 构建验证 | `conan create archives/l/libcaca/0.99.beta20 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing` → rc=0 | 上游 cppunit 套件 `# 18 checks, 0 failures` |
| 消费者测试 | test_package `ctest 1/1 Passed`（`./test_libcaca`，18 项检查） | 换源未改动既有补丁与构建逻辑 |
| 审查证据 | 无人工 review 记录 | 不手工 `/ai review`，如实标注 |
| 当前 CI 证据 | 尚未确认 | 截至回读时未获取远端 CI 通过证据 |

## 五、测试框架迁移类说明

不适用（本库为 autotools + cppunit 原生测试，无测试框架迁移需求）。

## 六、路径 B 贡献创新：10 分候选

把“官方替代源的形态判别”沉淀为可复用判据（含 4 份候选的排除证据与两条硬边界），非简单复用既有条目——本轮同批 no 现有条目覆盖（相似度最高仅 0.17）。
