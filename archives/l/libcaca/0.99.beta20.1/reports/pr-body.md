## 三方库信息

- **三方库名称**：libcaca（彩色字符画渲染库，`-vo caca` 后端）
- **上游版本**：0.99.beta20（本提交新增 **libcaca/0.99.beta20.1**）
- **上游仓库地址**：https://github.com/cacalabs/libcaca（官方发布位在本沙箱不可达，见「换源」）
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展，候选）
- **使用知识库**：openharmony-compile-agent

## 为什么开递增版本

本包本轮的唯一实质改动是**换源**：`0.99.beta20` 的源为上游 GitHub release asset，在本沙箱**整体不可达**
（`Errno 110 Operation timed out`，多次重试）。制品仓当前**尚无** `0.99.beta20`（属首次发布，严格按 R37 可直接改配方），
仍按维护要求**递增为 `0.99.beta20.1`**，使换源修订以独立版本交付：与旧版本变更解耦，便于回滚、复审与后续复用。

> 说明：本 PR 的分支名沿用了首轮创建名（内容已切换为 `0.99.beta20.1`）；同一换源修订不再另开 PR，避免同包两开。

## 变更范围（相对 `0.99.beta20` 仅两处文件）

| 文件 | 变化 |
|---|---|
| `conandata.yml` | `sources` 换为 Fedora lookaside 的 **dist tarball**；`patches` 新增 `0.99.beta20.1` 版本键（补丁集完全一致） |
| `conanfile.py` | 仅 `version` 字段：`0.99.beta20` → `0.99.beta20.1` |

## 换源（含一条可迁移判据）

| 候选（均为官方渠道） | 结果 |
|---|---|
| 原源：GitHub release asset | **不可达**（`Errno 110`，多次重试） |
| Debian `libcaca_0.99.beta20.orig.tar.gz` | 可达，但**不含预生成 `configure`**（源码快照）→ 需 autoreconf；本机 conan 侧 autoreconf 不可用（perl 模块 `Cwd.so` 重定位失败）→ 不采用 |
| Void sources `libcaca-0.99.beta20/v0.99.beta20.tar.gz` | 与 Debian **同一份**（sha256 `3edb8763…84f2` 完全相同），同样无 `configure` → 不采用 |
| MacPorts distfiles `libcaca-0.99.beta20.tar.gz` | 文件名同上游 release asset，但展开为 `cacalabs-libcaca-<sha>/`（**GitHub 归档**）→ 仍无 `configure` → 不采用 |
| **Fedora lookaside `libcaca-0.99.beta20.tar.bz2`** | **dist tarball**（893,319 B，**含 `configure`**），Fedora 记录的 sha512 逐字核验一致 ✓ → **采用**（sha256 `ff9aa641af180a59acedc7fc9e663543fb397ff758b5122093158fd628125ac1`） |

**可迁移判据**：换源不能只看「可达 + pristine」，还要校验**本轮构建方式所需的内容是否齐备**——
autotools 配方依赖 dist tarball 里预生成的 `configure`，而同一上游版本的"源码快照"式镜像（Debian/Void/MacPorts/部分 Gentoo）
恰好缺它。另两条硬边界：Debian 的 `+dfsg` 属下游重打包（按 R39/PF7 不宜作替代源）；
`*.dl.sourceforge.net` 官方镜像主机只 301 回 `downloads.sourceforge.net`（本项目域名整体不可达时无效）。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 上游自带套件（`caca/t`，cppunit） | 有 | 既有配方以 `--enable-cppunit` 在 `build()` 内**真实执行**（本 PR 未改动该机制） |
| **合计** | 同 `0.99.beta20` | 与递增前一致 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 说明 |
|----------|-------------|------|
| 上游 cppunit 套件（构建期） | **18 checks / 0 failures** | 本轮换源后实跑 |
| 消费者测试（test_package） | ctest `1/1 Passed`（18 项检查） | `./test_libcaca` |
| **合计** | 上游套件 + 消费者测试 | `conan create` 内执行并通过 |

## 上游测试用例修改说明

- [x] **否**，未修改上游测试与既有补丁（`0.99.beta20.1` 的补丁集与 `0.99.beta20` 完全一致）

## 验证结果

- 编译状态：**通过** —— `conan create archives/l/libcaca/0.99.beta20.1 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing` → rc=0
- 上游内部套件：`# 18 checks, 0 failures`
- test_package：`1/1 Test #1: test_libcaca .....................   Passed    0.03 sec`

## 路径评估（按仓内口径）

- **路径 A（基础适配）**：已完成（换源后重建通过，含上游套件与消费者测试）。
- **路径 B（知识库扩展）**：**可申报（候选）** —— 草稿 `knowledge/drafts/DRAFT-ohos-offline-source-switch-criteria.{kv,md}`
  （查重 `verdict=create`，相似度最高 0.17）：换源判据的**反例样本**（pristine 快照 ≠ dist tarball）+
  4 份候选的逐一排除证据 + 两条硬边界；配套【知识库扩展】issue 稿在
  `archives/l/libcaca/0.99.beta20.1/reports/issue-body-path-b.md`。
- **路径 C（高难度挑战）**：**不主张** —— 单体库 + autotools + 换源。
