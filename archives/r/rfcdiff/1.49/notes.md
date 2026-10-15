# rfcdiff 1.49 适配笔记

## 编译环境
- 构建系统: 无（单文件 bash 脚本 + 内嵌 awk，Conan 配方只做补丁 + 复制安装）
- 编译日期: 2026-10-04
- 编译器: 不涉及（无编译单元）
- 状态: built
- 语言预检: `detect_language` 判 `other`（build_system=none，无可统计源文件）；文件仅 `rfcdiff`（`#!/bin/bash`，约 1160 行 bash + awk）、`README.md`、`LICENSE`。这是 Shell 库，按赛事口径照常适配，`lang-preflight --lang other` 如实申报。

## 编译步骤

无编译。`init-build` 下载官方 GitHub tag 1.49 源码包（sha256 `a4401868…93a7`）→ 解压后立即 `cp --remove-destination` 断开 `.work` 与 `.orig` 硬链接（E543）→ 修改 `rfcdiff` → `refresh-patch --auto` 生成补丁 → 手写脚本包配方（`no_copy_source`，`build()` 应用补丁并校验 shebang，`package()` 复制 `bin/rfcdiff`、许可证与 README）。`package_id` 删除 arch/compiler/build_type，保留 os。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 安装后的 `rfcdiff` 无法直接执行 | 鸿蒙无 `/bin/bash`（E165），上游 `#!/bin/bash` | shebang 改为 `#!/data/service/hnp/bin/bash`（脚本用了 `$(< file)`、`echo -en`、`[ == ]`，不能降级到 `/system/bin/sh`） |
| 2 | 任何输出模式都报 `Failed to create temporary directory '/tmp/rfcdiff-<pid>'` | 鸿蒙 `/tmp` 只读（E002），上游工作目录硬编码 `/tmp/$basename-$$` | `workdir="${TMPDIR:-/tmp}/$basename-$$"`，`$TMPDIR` 显式设置时原样尊重 |
| 3 | `--keep` 打包失败 | 上游 `cd /tmp; tar czf $basename-$$.tgz $basename-$$` 把 /tmp 写死 | `cd "${workdir%/*}"`（工作目录的父目录，即 `$TMPDIR`） |
| 4 | `conan-init` 生成 autotools 配方 + CMake test_package + `libs=["rfcdiff"]` | init-build 对无构建系统脚本包误判 autotools | 整体改写为脚本包配方；删除 CMakeLists.txt/test.c，改用 shell 消费者用例 |

## 源码修改

`patches/0001-rfcdiff.patch`（`-p1`，3 个 hunk，各 1 行）：shebang、`workdir`、`--keep` 分支的 `cd`。无平台宏、无条件编译。

## 依赖版本

无 Conan 依赖。运行时仅需操作系统自带的 `bash`、`awk`（gawk/nawk/awk 均可）、`diff`、`sed`、`grep`、`tr`、`tar`。可选：`wdiff`（按词差异，制品仓已有 `wdiff/1.2.3` 但不作为硬依赖——缺失时脚本自动回退内置着色）、`wget`（http/ftp 参数，制品仓无此包）、浏览器（`--browse`）。W0：无必需依赖，不触发 R36。

## 上游测试清点（R51）

- `tar tzf rfcdiff-1.49.tar.gz`：只有 `LICENSE`、`README.md`、`rfcdiff`；无 `tests/` 目录、无 Makefile/CMake/meson、无 ctest/pytest 注册、发布树内无 CI 测试工作流。
- 上游测试 N = 0，N′ = 0，无可运行项；功能测试全部由 `test_package` 补充（见下）。

## 验证结果

适配机（x86_64，bash 5 / gawk / GNU diff，无 wdiff）上实跑：

```text
$ bash test_package/test_rfcdiff.sh      <patched rfcdiff> <workdir>   -> pass=10 fail=0
$ bash test_package/test_rfcdiff_ohos.sh <patched rfcdiff> <workdir>   -> pass=5  fail=0 skip=0
# 对照实验：同样的用例跑在未打补丁的上游脚本上
$ bash test_package/test_rfcdiff.sh      <pristine rfcdiff> <workdir>  -> pass=10 fail=0
$ bash test_package/test_rfcdiff_ohos.sh <pristine rfcdiff> <workdir>  -> pass=2  fail=3 (用例 1/3/5 失败，rc=1)
```

- 通用用例 10 条：`--version`、`--diff` 逐字节比对（页眉页脚已剥离）+ hunk 头行数、`--chbars` 恰好 3 行变更条、`--html` 词级 insert/delete span 且无页脚泄漏、`--nostrip` 保留页脚、默认输出文件名、同一文件检测、缺参数输出 usage 且 exit 1。
- 鸿蒙特有用例 5 条（rule12，完整消费者流程：Conan 取包 → 对真实草稿运行包内 `bin/rfcdiff` → 校验输出字节/文件落点/退出码）：shebang 为 OHOS bash、经该解释器实际 diff 两份草稿、`--keep` 的工作目录与 tgz 落在 `$TMPDIR`、自定义 `$TMPDIR` 下运行成功且不留残渣、不可用 `$TMPDIR` 明确报错而不是悄悄回退 /tmp。
- 本机 `/data/service/hnp/bin/bash` 是指向 `/bin/bash` 的软链。对 `.work` 工作副本直测时用例 2 走「显式解释器」分支（无执行位）；`conan-verify` 的 `conan create` 中 test_package 对打包产物实跑 15/15（用例 2 走 direct 分支：经 shebang 直接执行）。解释器不存在时报 SKIP，不记为通过。
- 未做的事：x86 runner 无法验证真实 OHOS 设备上的 `/tmp` 只读场景，只能通过「不可用 `$TMPDIR` 必须报错」与「`--keep` 落在 `$TMPDIR`」间接证明补丁生效。设备 toybox `diff` 是否支持 `-Bwd -U` 未验证（上游行为，非补丁范围）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/rfcdiff` | 补丁后的上游脚本（GPL-2.0-or-later） |
| `share/doc/rfcdiff/README.md` | 上游文档 |
| `licenses/LICENSE` | 许可证正文 |

## 注意事项

- 软件级 `commands.json` 声明命令 `rfcdiff`（tool 类型）。
- 用例用 `printf` 构造夹具，不使用 here-document（E547：设备 `/system/bin/sh` 的 here-doc 依赖只读 /tmp）。
- `--wdiff`/`--hwdiff` 模式需要 `wdiff`，本包未把它作为依赖；测试一律 `--nowdiff` 以保证确定性。
