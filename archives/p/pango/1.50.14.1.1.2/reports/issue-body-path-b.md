**【申请人账号】** `akajhsbnz`（怜惜～）
**【队伍名称】** jumping_姜圣帝君
**【申请日期】** 2026/10/13
**【库名称】** pango
**【版本】** 1.50.14.1.1.2
**【关联 PR】** #15527（https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15527）
**【分支信息】** feat/pango-1.50.14.1.1.2 → main
**【当前提交】** 分支 `feat/pango-1.50.14.1.1.2` 最新提交 `66b4435d84c1`（含知识库草稿、notes 的「路径 B 材料」指向与本文；以分支最新为准）
**【PR 状态】** 开放中
**【当前 CI】** 截至回读时未确认（未获取远端 CI 通过证据，不宣称已通过）
**【平台活动】** 开源鸿蒙 PC 专项积分赛

## 一、申请路径 B 的理由

消费者要同时纳入两条已发布依赖链时（gtk2 GUI 链 + libass 字幕链 / libmng MNG 链），图直接报 `Version conflict: Conflict between harfbuzz/14.2.0 and harfbuzz/14.2.0.1.1.1 in the graph`（以及 libjpeg-turbo 3.2.0↔3.0.4）。消费者侧 `override=True` 会迫使 libass/libmng 等**已发布依赖在 CI 源码重建**（违 R36），`force=True` 又只在本配方参与解析时生效（samba/4.21.0 实测：本包能过、消费者图仍硬冲突）→ 正解是**依赖侧递增一个只改钉版的版本**，并由上层包递增要求它。

## 二、推广价值

该模式本轮落成一条三件套链（pango→harfbuzz、gdk-pixbuf→libjpeg-turbo、gtk2 要求二者），可直接复用到任何“两条已发布链互相钉死”的场景；同时给出关键细节：**`test_package` 内的显式钉版必须同步**，否则测试包自身图冲突（本包实测踩到）。

## 三、知识库查重与新增价值

- **新增草稿**：`knowledge/drafts/DRAFT-ohos-cross-package-pin-conflict-resolve-on-dependency-side.kv` + 配对 `.md`
- **查重方式**：`python3 scripts/ohc-run.py draft-review DRAFT-ohos-cross-package-pin-conflict-resolve-on-dependency-side --json`
- **查重结论**：`verdict=create`（相似度最高 E538(0.17)，无现有条目覆盖该主题；本轮同批草稿之间已做主题切分，互不重复）
- **校验**：`python3 scripts/ohc-run.py graph validate` 全绿
- **新增价值**：把“钉版冲突”从‘用 override 硬压’改写为**依赖侧最小增量（只改钉版 + 递增版本）**，并记录 force 的跨图语义边界。

## 四、证据表

| 类别 | 证据 | 说明 |
|------|------|------|
| 原始失败 | `ERROR: Version conflict: Conflict between harfbuzz/14.2.0 and harfbuzz/14.2.0.1.1.1 in the graph` | 消费侧实构图复现；改 pango 钉版后 test_package 亦曾图冲突（已修） |
| 修复方案 | `pango/1.50.14.1.1.2`：`harfbuzz/14.2.0.1.1.1` → `14.2.0`；源/补丁/选项/布局不变；`test_package` 钉版同步 | 配套 `gdk-pixbuf/2.44.6.1.1.1`（libjpeg-turbo→3.0.4）与 `gtk2/2.24.33.1`（要求二者） |
| 构建验证 | `conan create archives/p/pango/1.50.14.1.1.2 …` → rc=0 | 同链条另两件亦各自 rc=0 |
| 消费者测试 | test_package：`pango ok version=1.50.14 (pangocairo)` | 目标态整图（mplayer+gtk2 链+live555+cddb+dga+samba）无 Version conflict |
| 审查证据 | 无人工 review 记录 | 不手工 `/ai review`，如实标注 |
| 当前 CI 证据 | 尚未确认 | 截至回读时未获取远端 CI 通过证据 |

## 五、测试框架迁移类说明

不适用（meson 原生测试，沿用既有 failing-suite 补丁）。

## 六、路径 B 贡献创新：10 分候选

钉版冲突的依赖侧解法此前无条目覆盖（相似度 0.17），且附带 force 的跨图语义边界与 test_package 同步陷阱，属新增方法论。
