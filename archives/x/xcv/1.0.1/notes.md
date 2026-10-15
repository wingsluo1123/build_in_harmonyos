# xcv 1.0.1 适配笔记

## 软件简介

xcv 是单个 bash 脚本（`xcv`，约 60 行），用 `x|c|v|l` 四个子命令在命令行完成文件的剪切/复制/粘贴/列出，
暂存目录固定为 `$HOME/.xcv`（每次剪切/复制都会 `rm -rf` 后重建）。纯脚本，无需编译。

## 语言预检（R47）

- 只读预判 `detect_language()` 输出：`nodejs`（build_system=npm，manifest=`package.json 含 main/scripts/engines/bin`，source_stats=无源文件可统计）。
- 实际是 Shell 库：仓库仅 `xcv`（`#!/bin/bash`，Bourne-Again shell script）、`README.md`、`package.json`（仅用于 npm 分发，无 JS 源码）。
- 检测器误判（`package.json` 触发 nodejs）。大赛接受 Shell 适配，故以 `--lang nodejs`（检测器判定值，如实申报，未伪报 cpp）
  通过预检并继续适配，输出留存于 `/data/harmony-compact/xcv-logs/lang-preflight.txt`。

## 构建要点

- **无编译**：`package_type = application`，`build()` 仅应用（空的）补丁，`package()` 安装 `bin/xcv` 与 `share/doc/xcv/README.md`。
- **shebang 修复**：上游 `#!/bin/bash`，OHOS 无 `/bin/bash`；`package()` 把首行改写为 `#!/usr/bin/env bash`，
  通过 PATH 找 bash。改写前校验首行确实是 `#!/bin/bash`，上游变动时会直接失败而非静默跳过。
- **运行时依赖**：`bash/5.3`（W0：`conan download bash/5.3 -r=ohpcd --only-recipe` 已发布）。
- **源码**：GitHub tag `v1.0.1` 官方归档，`strip_root=True`；sha256 `f2898f78...c0644` 为本机下载实算。
- **危险行为**：脚本会清空 `$HOME/.xcv`，所有测试使用 `mktemp -d` 出来的临时 HOME。

## 上游测试清点（R51）

- 上游仓库文件仅 `xcv` / `README.md` / `package.json`：`tests/` 目录数 0，ctest/pytest/make check 注册数 0，
  package.json 无 `scripts.test`。上游测试 N=0，N′=0，通过率 不适用。
- 因此由 `test_package/test_xcv.sh` 补真实功能测试（6 个场景）。

## 鸿蒙特有测试（rule12）

`test_package/conanfile.py` 通过 Conan 消费 `xcv/1.0.1`，定位已安装的 `bin/xcv`，用 hnp bash 运行 `test_xcv.sh`：
- T1 适配点：安装后首行为 `#!/usr/bin/env bash`，并在仅含私有 `bash` 软链的 PATH 下**直接执行** xcv（不经 /bin/bash）成功；
- T2 参数错误走 stderr；T3 复制→列出→粘贴往返（含点文件/子目录，`cmp` 逐字节比对）；
- T4 剪切→粘贴（源被移除、内容完整）；T5 暂存区被最新复制覆盖；T6 暂存目录位于临时 HOME。
共 6 个用例，均是实际运行 xcv 并校验可观测行为。

## 验证结果

- 本机 x86 runner：脚本为纯 bash，不涉及 aarch64 ELF，直接用 `/data/service/hnp/bin/bash`（本机为 /bin/bash 软链）运行 test_xcv.sh，6/6 通过，exit 0。
  这验证的是脚本逻辑与 shebang 改写；OHOS 上 toybox 的 cp/mv/ls 行为差异由 CI 上的 `conan create` 再次执行验证。

## 注意事项

- 不要在真实 HOME 下运行 `xcv x|c`，会清空 `~/.xcv`。
- 命令行工具，软件级目录含 `commands.json`（`binary: false`，脚本类）。
---

**编译结束**: 2026-10-07 21:28
**最终状态**: built
