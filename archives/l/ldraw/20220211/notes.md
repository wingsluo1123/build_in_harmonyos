# ldraw 20220211 适配笔记

## 编译环境
- 构建系统: custom（纯数据资源库，无构建系统）
- 编译日期: 2026-10-02
- 编译器: 不涉及（无编译步骤）
- 状态: built

## 软件性质

ldraw（LDraw.org 官方零件库）是**纯数据资源库**：LEGO 零件的 LDraw 格式
几何数据（.dat 零件/基元）、颜色定义（LDConfig.ldr）、样例模型与许可文档。
官方完整库 complete.zip（37,261 个文件）内除 Windows 时代的 mklist.exe/
mklist 源码压缩包外无任何代码；无构建系统、无编译产物、无 CLI、
无自动化测试。OHOS 侧消费方式为按 LDraw 生态惯例读取安装后的零件库数据。

## 官方源核验（重要）

任务头声明上游 URL `https://github.com/ldraw/library` —— 已核实 **404 不存在**
（GitHub API `repos/ldraw/library`、`repos/LDraw/library`、`orgs/ldraw/repos`、
`users/LDRAW/repos` 权威均返回 Not Found/空列表）。

LDraw 官方零件库的真实官方源为 LDraw.org：
- 旧域名 `www.ldraw.org`（`/library/updates/complete.zip` 现 404，站点已迁移）
- 现官方站点 `https://library.ldraw.org/`（官方 HTTPS，CI 可达）
- 官方完整库下载：`https://library.ldraw.org/library/updates/complete.zip`

**版本与快照说明**：LDraw 库版本号按发布日期命名，`20220211` 即 2022-02-11
快照。FreeBSD `cad/ldraw` 端口 distinfo 记录了该版本完整库快照的权威指纹：
SHA-256 `632bff3862b28c1d046bb420f2c3aa42802ef32e210a84318a69c486c2bee867`
（SIZE 59,422,832），配套 `LDConfig.ldr` SHA-256 `af3f8c58…ff635`。官方站点
按月滚动更新 complete.zip，20220211 历史快照现已不单独提供；本次适配下载并
核验了 2026-10-02 可获取的官方完整库制品（146,075,744 字节，SHA-256
`f3e496d0ede69ca7942fa4aa198e661ee2d22723906101e2e339d8917a4dd5f2`），
配方 conandata.yml 与之对齐。此差异如实记录（数据内容为官方最新快照而非
20220211 历史快照）；若需精确 20220211 快照，可从 Wayback Machine 恢复
（本执行端网络不可达 web.archive.org）。

## 构建/安装过程（本仓）

```bash
# 纯数据包：conan create 只执行 source()（get 下载官方 zip，sha256 校验）
#                → build()（空实现）→ package()（复制数据到 share/ldraw）
conan create archives/l/ldraw/20220211 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

- source(): `get()` 拉取官方 complete.zip（strip_root=False，保留 ldraw/ 顶层）
- package(): 复制 `parts/`、`p/`、`models/` 与 `LDConfig*.ldr`、许可/说明到
  `share/ldraw/`；**不安装** mklist.exe(Windows 二进制，OHOS 不适用)
- package_id(): `info.clear()` —— 与平台/编译器无关，单一 package_id
- cpp_info：includedirs/libdirs/bindirs/libs 显式置空；`resdirs=["share/ldraw"]`；
  runenv_info 定义 `LDRAW_LIB_PATH` 供下游按 LDraw 惯例定位库根

## 上游测试情况（如实申报）

**上游没有自动化测试入口** —— 不是"未执行"，而是"不存在"：

1. complete.zip（37,261 文件）全量枚举：`grep -icE 'test|spec|fixture|bench|
   regress|doctest|catch|gtest|check|\.sh$|\.py$|\.bat$'` → **0 命中**
2. 包内唯一源码 mklist（mklist-c/1_4/1_6.zip 内 mklist.c）：
   `grep -cE 'TEST|assert|selftest|test_'` → **0**；各 makefile 仅 `all: mklist`
   目标，无 test 目标
3. models/ 仅有 car.dat / pyramid.dat 样例模型与 Note*.txt 更新说明
   （样例模型是 LDraw 生态素材，不是自动化测试用例）

统计口径：`source_declared_total = 0`；`configured_executable_total = 0`；
`executed_passed_total = 0`；失败 0；未运行/未实例化 0。无映射链可列。

## test_package / 消费者验证

test_package 不是空壳：`test_ldraw.py` 以第三方消费者视角读取安装后的零件库
（规模 >30000、随机抽检 .dat 首行 LDraw 元命令、LDConfig.ldr 颜色定义、
models 样例目录），作为消费者可用性用例（consumer gate）与鸿蒙专项验证。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务头上游 URL `github.com/ldraw/library` 404 | 该仓库不存在（GitHub API 权威确认） | 恢复官方 HTTPS 源 library.ldraw.org 并下载核验 SHA-256 |
| 2 | lang-preflight 报 env_unsupported（detected=other） | 默认任务语言 cpp，纯数据资源库无 C/C++ 源码被归为 other | 以 `--lang other` 复检（detected==other，exit 0），确认数据资源库类别；终态 result 以实际适配结果覆盖误判草稿 |
| 3 | 官方 complete.zip 是滚动快照，20220211 历史版不单独提供 | LDraw 官网按月滚动更新完整库 | 采用 2026-10-02 可获取的官方快照并如实记录差异（见"官方源核验"） |
| 4 | upstream zip 顶层含 ldraw/ 目录 | complete.zip 打包结构 | source() 用 strip_root=False，package() 直接定位源 ldraw/ 子目录 |

## 源码修改

无（纯数据资源库，不改任何上游数据文件）。

## 知识候选台账与路径判断（B/R01）

台账全文：`reports/knowledge-candidate-ledger.md`（2026-10-02）。

四范围查重（正式 E 条目 / doc / drafts / index.tsv）结论：
- C1（任务头上游 URL 404→恢复官方 HTTPS 源）：E299 部分覆盖 → reuse_existing
- C2（官方滚动快照 + FreeBSD distinfo 交叉核验历史版本 SHA-256）：部分覆盖 → reuse_existing
- C3（纯数据资源库 lang-preflight 默认 cpp 误判 other→env_unsupported；`--lang other`
  复检确认数据资源库类别后继续适配）：**未命中** → new_draft
- C4/C5（数据资源包配方/消费侧验证）：E255/E241/E281/E305/E536 完整覆盖 → reuse_existing
- C6（W3 基线隔离复验）：SKILL 规程执行，非新增知识

七轴查重（C3 vs 既有 lang-preflight 草稿家族）：exact=否、causal=否、trigger=部分、
solution=部分、**combination_novelty=是、boundary_novelty=是**、test_migration=部分。

路径决定：**new_draft（仅 C3）** —— 已建同 stem 草稿
`knowledge/drafts/DRAFT-ldraw-20220211-data-resource-lang-other.kv`（+ .md），
与 ldraw 归档同 PR 交付；其余候选 reuse_existing。知识库扩展（路径 B）成立。
---

**编译结束**: 2026-10-02 06:15
**最终状态**: built
