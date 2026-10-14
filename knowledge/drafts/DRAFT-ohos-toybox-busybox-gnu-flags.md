# DRAFT-ohos-toybox-busybox-gnu-flags — OHOS toybox/busybox 工具不支持 GNU 长选项与 GNU 特有 flag，上游测试脚本运行期炸

> 对应结构化数据：`knowledge/drafts/DRAFT-ohos-toybox-busybox-gnu-flags.kv`
> Contributor: Ember5843 / Status: DRAFT / Updated: 2026-09-27 / Severity: 2
> 触发事件：本轮多库真机测试（libdebuginfod 0.195 等）中上游测试脚本用 GNU 特有
> flag（如 `wc --lines`）在设备 toybox 上运行失败

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条目的增量（差异化） |
|---|---|---|---|
| DRAFT-ohos-toybox-ln-long-option | 草稿 | toybox **ln** 单命令不认长选项 → 安装脚本阶段 | 本条覆盖**全套工具**（wc/diff/sort/head/tail 等）且发生在**测试运行期**（跑上游 .sh 测试时），不是安装期 |
| DRAFT-toybox-diff-e-ed-script | 草稿 | toybox diff 缺 **-e** 功能 → PATH 前置 GNU diffutils | 同为"GNU diffutils 先行"方案的单命令特例；本条给出跨命令通用判定与 coreutils-fmt 同款安装模式 |
| DRAFT-tar-1.35-toybox-touch-nanosecond | 草稿 | toybox touch 纳秒精度缺失 | 单命令精度问题，非选项语法 |
| E010/E106/E188 | 正式 | toybox sed/expr/cat/install 与 GNU 行为差异 → 安装 GNU coreutils 替换 | 本条是**运行期测试脚本**场景的同类归纳 + 设备侧已有 coreutils-fmt/9.11 先例可复用 |

## Scope（何时用）

- **触发特征**：真机/CI 跑上游测试脚本（.sh）时报 `wc: Unknown option --lines`
  `sort: invalid option -- 'parallel'` `head: Unknown option --quiet` 等运行期错误；
  脚本本身能起、一调用到 GNU 特有 flag 就炸。构建期能过（toybox 够用）、
  **测试期**才暴露是本条与 E 码安装期条目的关键区分。
- **典型实例**：上游 autotools 测试脚本（tests/*.sh）惯用 `wc --lines`、
  `sort --parallel`、`diff --unified`、`head --quiet` 等 GNU coreutils 写法。

## Symptom（真实报错形态）

```
$ wc --lines foo.txt
wc: Unknown option --lines (see "wc --help")
$ wc -l foo.txt        # 短选项正常
3 foo.txt
```

## Root Cause

OHOS 用户空间命令由 toybox（部分环境叠加 busybox）提供，实现的是**POSIX/常用短选项
子集**，不识别 GNU coreutils 长选项（`--lines`）与 GNU 特有行为（GNU fmt 的
`--prefix` 等）。上游测试脚本作者按 Linux/glibc 环境习惯写 GNU flag，脚本一执行
即报 Unknown option 非零退出 → 上游测试假失败。

## Recommended Solution（主方案 + 回退）

**判定步骤**：
1. 逐个收集脚本用到的命令+选项，对照 toybox `--help` 判定缺口清单；
2. 缺口少（1-2 处）→ **脚本侧改写**为 POSIX 等价（`wc --lines`→`wc -l`）；
3. 缺口多或无法等价改写 → **工具侧补齐**：设备已有 `coreutils-fmt/9.11` 先例
   （conan 包 `/data/service/hnp/bin/` 优先于 PATH），照此打包所需 GNU 工具，
   测试 job 里前置 PATH。

**主方案（脚本侧改写，改动最小优先）**：

```sh
- N=$(wc --lines < "$f")
+ N=$(wc -l < "$f")
```

**回退（工具侧，缺口多时）**：配方或测试 job 注入 GNU coreutils 到 PATH 前列
（coreutils-fmt 模式）；禁止改上游脚本超出选项等价改写的范围。

## 单库实证

| 库 | 缺口 | 修法 | 结果 |
|---|---|---|---|
| libdebuginfod/0.195 测试 | wc --lines 等少量 | 脚本/调用侧等价改写 | 上游测试真机全过（PR #12349） |
| 设备工具链 | GNU fmt | coreutils-fmt/9.11 conan 包先行 | 已在用，模式可复制 |

## 测试覆盖边界

- 本条只解决"脚本因 GNU flag 假失败"，不改变 rule2/3 归因义务：真实平台差异
  （如 musl 行为差异导致的断言失败）仍须逐条归因，不许借改写掩盖。
- 差异定位表逐条核验：与 ln/touch/diff-e 单命令条目及 E010/E106/E188 非重复申报。

