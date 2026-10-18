# DRAFT-tofi-0.9.1: 手写 TAP 套件的退出码与断言结果解耦 —— 用退出码判定必然假绿

## 症状

上游自带手写 TAP harness 的包，接进配方后出现「怎么跑都是绿」的假象：

- 直接执行被测二进制（`test/config`、`test/utf8`）永远 `rc=0`；
- 若配方/消费者测试用「跑二进制 + 看退出码」的方式集成，断言全挂也判通过；
- 只有 `meson test` 的汇总行（`Ok: N / Fail: M`）会反映真实结果。

本包（tofi 0.9.1）实测的最小复现（同一份 `test/tap.c`）：

```c
/* repro.c */
#include "tap.h"
int main(void)
{
	tap_version(14);
	tap_is(1, 2, "synthetic failing assertion");  /* 故意失败 */
	tap_plan();
	return 0;                                     /* 上游 test/*.c 就是这么写的 */
}
```

```console
$ clang -std=c2x -D_GNU_SOURCE -o repro repro.c tap.c && ./repro; echo exit_code=$?
TAP version 14
not ok 1 - synthetic failing assertion
1..1
exit_code=0
```

断言失败、退出码为 0。上游 `test/config.c`、`test/utf8.c` 结尾都是
`tap_plan(); return EXIT_SUCCESS;` —— 退出码与断言结果**没有任何关系**。

## 根因

`test/tap.c` 是一个打印型 harness：

| 函数 | 行为 | 对退出码的影响 |
|------|------|----------------|
| `tap_version(n)` | 打印 `TAP version n` | 无 |
| `tap_ok(m)` | 打印 `ok N - m` | 无 |
| `tap_not_ok(m)` | 打印 `not ok N - m` | 无 |
| `tap_plan()` | 打印 `1..N`（已执行条数） | 无 |
| `tap_todo(m)` | 给下一条打 `# TODO` 注释 | 无 |

判定权因此**只在 TAP 解析器手里**：上游 `test/meson.build` 用
`test(test_file, t, protocol: 'tap')` 注册，meson 解析 TAP 流，遇到 `not ok`
即计入 Fail 并使 `meson test` 返回非零。任何绕开解析器、只看子进程返回码的
集成方式都拿不到这个信息。

## 已完成/已尝试方案

- ✗ 直接执行测试二进制并判 rc：恒为 0（上方最小复现）。
- ✗ 用 `test/*.c` 文件个数当用例数、用「二进制 rc」当通过率：分母/分子都错。
- ✓ 配方 `build()` 内调用 `meson.test()`（conan Meson 助手），由 TAP 解析器判定，
  失败即让构建失败——本包以此形态在 `conan-verify` G2 真跑上游 2 个目标。
- ✓ 用例数按断言宏的**调用点**清点：`test/config.c` 的 `is_valid`/`isnt_valid`
  39+29=68 条、`test/utf8.c` 的 `is_match`(×2)/`isnt_match`(×2)/
  `isnt_simple_match`/`isnt_fuzzy_match` 共 12 条 ⇒ `N_static=80`。

## 适用范围 / 反例

- 适用：`protocol: 'tap'` / `prove` / 任何「打印 TAP，由外部解析器判定」的套件；
  尤其当 harness 是仓库内手写的（`tap.c`、`tap.h` 这类）。
- 不适用：套件主程序自己按断言失败调用 `abort()`/返回非零（如 GLib `g_test` 默认
  行为）——那时退出码是可信的，不要据此把真失败改判为通过。
- 边界：`tap_todo()` 只是 `# TODO` 注释，是否计失败取决于解析器；报告须单列，
  不能并入「通过」，也不能从分母里删除。
- ⛔ 禁止反向使用本条：不能因为「反正退出码不可信」就把上游 0 执行/整体跳过
  写成通过（`AGENTS §10`：整体 0 执行不可交付）。

## 查重与新增价值

- 查重：知识库无「TAP harness 退出码脱钩」条目；`E781` 讲的是「上游测试可执行
  边界按依赖图推导 + GLib `--tap` 按用例数计通过率」，症状与解法均不同
  （E781 的前提正是 harness 会正确反映失败）。
- 新增价值：给出**判据位置**（TAP 解析器 vs 进程退出码）、**最小复现形态**、
  以及**用例数清点口径**（按断言宏调用点，而非二进制个数），可直接迁移到任何
  手写 TAP 的 meson 项目。
