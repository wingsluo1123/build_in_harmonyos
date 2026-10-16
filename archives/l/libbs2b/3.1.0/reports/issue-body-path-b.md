**【申请人账号】** `akajhsbnz`（怜惜～）
**【队伍名称】** jumping_姜圣帝君
**【申请日期】** 2026/10/13
**【库名称】** libbs2b
**【版本】** 3.1.0
**【关联 PR】** #15533（https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15533）
**【分支信息】** feat/libbs2b-3.1.0 → main
**【当前提交】** 分支 `feat/libbs2b-3.1.0` 最新提交 `a38f2ef29972`（含知识库草稿、notes 的「路径 B 材料」指向与本文；以分支最新为准）
**【PR 状态】** 开放中
**【当前 CI】** 截至回读时未确认（未获取远端 CI 通过证据，不宣称已通过）
**【平台活动】** 开源鸿蒙 PC 专项积分赛

## 一、申请路径 B 的理由

在 HMDFS 上以 autotools 构建时连续踩到三类问题，均已定位到根因并给出可复用处置：①**umask 077 是双重的**——`configure` 与**它生成的 `config.status`** 都用 `(umask 077 && mktemp -d ./confXXXXXX)` 建 2700 目录，hmdfs 经 group 位中介访问且 `chmod` 无效 → `could not setup config files machinery`；只改 `configure` 不够；②补丁触及 `configure.ac`/`Makefile.am` 后触发 `$(srcdir)/configure: $(am__configure_deps)` 与 `config.status --recheck`，会**重新生成带 077 的 config.status** → 需把生成物置新、输入置旧，且**不能用未来时间戳**（autoconf 健全性检查报 `newly created file is older than distributed files`）；③自实现 `strip_root` 时被 `patches/` 干扰 → 补丁报 `source/target file does not exist`。

## 二、推广价值

HMDFS 的 umask 行为与 autotools 的再生规则组合是**跨包同构问题**：本轮 libcddb、libXxf86dga、libdvdread 等 autotools 包同样需要 077→022；“生成物置新 / 输入置旧”的时间戳处置可直接复制到任何补丁触及 autotools 输入的配方。

## 三、知识库查重与新增价值

- **新增草稿**：`knowledge/drafts/DRAFT-ohos-hmdfs-umask-and-autotools-regeneration.kv` + 配对 `.md`
- **查重方式**：`python3 scripts/ohc-run.py draft-review DRAFT-ohos-hmdfs-umask-and-autotools-regeneration --json`
- **查重结论**：`verdict=create`（相似度最高 E129(0.25)，无现有条目覆盖该主题；本轮同批草稿之间已做主题切分，互不重复）
- **校验**：`python3 scripts/ohc-run.py graph validate` 全绿
- **新增价值**：把三条零散踩坑收敛为一套**处置函数**（`_relax_umask()` + 相对时间戳排序 + staging 解包），并给出每条的错误签名与验证方式。

## 四、证据表

| 类别 | 证据 | 说明 |
|------|------|------|
| 原始失败 | `config.status: error: could not setup config files machinery`（只改 configure 仍失败）；`newly created file is older than distributed files`（时间戳用未来值）；`source/target file does not exist`（strip_root 误判） | 三条均为本包实测、可逐条复现 |
| 修复方案 | 配方内 `_relax_umask()`（configure+config.status 双改）+ 输入置旧/生成物置新的时间戳处置；解包改 staging 子目录 | 同时在 notes.md 记录四类踩坑的完整证据 |
| 构建验证 | `conan create archives/l/libbs2b/3.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing` → rc=0 | 另修通“`get()` 不支持 `.tar.lzma`”与“硬性 PKG_CHECK_EXISTS(sndfile) 需显式注入 CPPFLAGS/LDFLAGS” |
| 消费者测试 | test_package 5 条断言全绿：`level_fcut=700 level_feed=30`、`cross_feed_f: left=0.754334 right=0.039345`、版本 `0x30100` | 串扰处理为真实生效（非空实现） |
| 审查证据 | 无人工 review 记录 | 不手工 `/ai review`，如实标注 |
| 当前 CI 证据 | 尚未确认 | 截至回读时未获取远端 CI 通过证据 |

## 五、测试框架迁移类说明

不适用（上游无测试目标；本包补的是消费者功能测试）。

## 六、路径 B 贡献创新：10 分候选

HMDFS+autotools 的三重伏击此前分散在多个包的临时修补里，本条将其收敛为**可复制的处置函数**并附逐条错误签名，属新增诊断模式。
