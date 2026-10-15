# 平台补丁通道是文本通道：PR 差分（gitcode .diff 端点）对二进制文件只输出占位行，含二进制资产的 MR 必触发 git apply 失败

- **草稿 ID**: DRAFT-11418-uboot-pr-text-blob-binary-assets
- **来源**: u-boot 2026.07 HarmonyOS PC 适配（MR 首轮 CI：二进制夹具使平台工作机 checkout 必然失败——首轮 8 件，SDL 接入后终版 13 件；修复=base64 文本随包 + sha256 钉死 + 构建时物化复验）
- **分类**: platform / ci / patch-channel / packaging / binary-assets
- **状态**: 本地草稿（路径 B 知识库扩展中）
- **关联**: 对应交付件 `test_package/fixtures/fixture-blobs.py`（13 件二进制文本化载荷）+ `mkfixtures.sh` 物化段；与 DRAFT-11418-uboot-fixture-staging-hex-carrier 同源（同一批夹具资产）

## 问题 / 错误签名

- **平台工作机 checkout 失败**（构建日志末尾，被机器人评论掩盖）：
  ```
  error: missing binary patch data for 'archives/u/uboot/2026.07/test_package/fixtures/boot.bmp'
  error: archives/u/uboot/2026.07/test_package/fixtures/boot.bmp: patch does not apply
  ```
  对每个触碰的二进制重复一次，随后 `git apply --3way` 与 `patch -p1 --fuzz=3` 回退同样失败。
- **机器人评论误诊**：`类别: 网络问题 / 问题: 源码下载超时`——与真实根因（补丁载荷缺失）完全无关；若据此按「网络抖动」重试，永远不可能成功。
- **复现**：任何向该平台提交、差分中含二进制文件（新增或修改）的 MR，确定性地在 checkout 阶段失败。

## 根因

1. 平台构建在取 PR 内容时下载 `https://gitcode.com/<org>/<repo>/pull/<n>.diff`，然后 `git apply`（回退 `--3way` / `patch`）到基准树上。
2. gitcode 的 **`.diff` 端点对二进制文件只输出 `Binary files ... differ` 占位行**，不携带 `GIT binary patch` 数据段（对照实验：同一 PR 的 **`.patch` 端点**输出 48.8MB、含 19 个 `GIT binary patch` 段，`git apply` 正常）。
3. `git apply` 遇到「需要二进制载荷但补丁没带」的文件即硬错误；三个回退通道都无法凭空还原字节。
4. 机器人分类器只读评论可见的错误摘要，把「补丁应用失败」归入网络类，掩盖真因。

## 最小修复方案

**把二进制资产改为纯文本随包**（本题：13 件夹具，合计约 57KB → base64 约 77KB）：

1. 生成 `fixture-blobs.py`：13 件二进制的 base64 内联为文本常量，**每件 sha256 钉死在文件内**。
2. 构建脚本（`mkfixtures.sh`）在 seed 段调用 `python3 $H/fixture-blobs.py $F`：逐件解码 → sha256 复验 → 写入 `$F`；任一不符即非零退出（硬失败），下游消费点路径不变（全部经 `$F/<name>`）。
3. 二进制原文件从仓库移除（diff 中不再出现任何二进制 hunk）。
4. 自检链：本地 round-trip（解码字节 vs 原文件 sha256 全等）+ 真机全链复跑（见「验证」）。

## 验证

1. **本地 round-trip**：解码产物 13 件 sha256 与原始文件全等（脚本内置钉死值任何环境可复验）。
2. **端点对照**：同一 PR `.diff` 里 `GIT binary patch` 计数 0（`Binary files` 占位）vs `.patch` 里 19 —— 实证端点差异，定位平台侧必然失败。
3. **真机全链复跑**：二进制文本化后 test_package 全链（夹具重建 + 879 子测试）真机复跑全绿，设备侧物化文件 sha256 与本地全等。

## 教训 / 泛化

- **MR 差分是文本通道**：提交前若含二进制资产，用平台的 `.diff` 端点（或本地 `git diff` 不带 `--binary`）试 apply 一遍，通过才算可提交；`.patch` 端点能过不蕴含 `.diff` 能过。
- **机器人分类不可信**：checkout/构建失败的评论「类别」只是摘要推断；根因必须以构建日志原始错误为准（本项机器人说网络、实际是补丁格式）。
- **资产文本化的通用形态**：base64 文本 + sha256 钉死 + 消费端物化复验——字节自证、可 diff、可评审；比「让平台换端点」可控得多（后者依赖外部行为）。
- **修复的完整性口径**：改变随包输入后，验证不只看解码而是全链（夹具重建 + 全部子测试）复跑，防止「解码对但路径/消费断」类残余缺陷。
