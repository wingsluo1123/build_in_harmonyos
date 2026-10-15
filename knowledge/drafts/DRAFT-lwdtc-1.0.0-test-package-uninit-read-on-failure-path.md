# DRAFT: lwdtc 1.0.0 R03 — test_package 断言在 API 失败路径读取未初始化输出参数（P3）修复

> 来源：lwdtc 1.0.0 R03 赛事评审整改轮（task lwdtc-1.0.0-r03-invalid-log-removal-and-metadata-repair-pc2-9-20260929T041500Z，AI 检视评论 191767088 P3）
> 状态：pending-editor-review（拟提升编号 E###，最终由主编确认）

## 错误特征

`test_package/test.c`（lwdtc 1.0.0，R02 交付态）在调用 `lwdtc_cron_next(&ctx, now, &next)`
后，把 `next <= now` 断言写成与返回码检查**并列**的无条件语句：

```c
if (lwdtc_cron_next(&ctx, now, &next) != lwdtcOK) {
    printf("FAIL: lwdtc_cron_next\n");
    fails++;
}
if (next <= now) {              /* 失败路径仍读取未初始化的 next（P3） */
    printf("FAIL: next <= now\n");
    fails++;
}
```

直接表象：`next` 声明时未初始化（`time_t now, next;`），当 `lwdtc_cron_next`
失败（如无效 ctx）时 `next` 未被写入，第二个断言无条件读取它——既是未初始化
读取（不确定值），又可能产生误导性的额外 `FAIL: next <= now`，掩盖真实失败
（API 调用失败）。

## 根因

1. **测试代码结构缺陷**：输出参数（out-param）断言被放在 API 返回码检查的
   **分支之外**（并列 if），失败路径未进入成功分支却仍读取 out 参数。
2. **未初始化读取**：C 语言中 `next` 未初始化即参与比较，行为不确定（UB）；
   即便在某实现上"碰巧"通过，也无法保证。
3. **误导性输出**：垃圾值可能命中/未命中比较，产生与真实失败无关的额外
   `FAIL: next <= now`，干扰对真实失败（API 返回错误）的定位。
4. 该缺陷可被 `-Wall -Wextra -Werror` 静默放过（clang 对"经函数调用后读取
   可能未赋值变量"通常不告警），因此需要结构修复而非仅靠编译器。

## 方案

把输出参数断言**移入 API 成功分支**（`else if`），失败路径只报告 API 返回
错误、不再读取 `next`；保留并加强断言强度，不删除任何检查点、不用平台宏：

```c
if (lwdtc_cron_next(&ctx, now, &next) != lwdtcOK) {
    printf("FAIL: lwdtc_cron_next\n");
    fails++;
} else if (next <= now) {       /* 仅成功分支读取 next */
    printf("FAIL: next <= now\n");
    fails++;
}
```

## 验证

- 修复后 `test_package/test.c` 用 OHOS clang（`-Wall -Wextra -Werror`）与
  库源码真实编译成功（build rc=0，零警告零输出）
- 正常路径运行：`lwdtc test_package: PASS (parse + valid + next)`，exit 0
- 失败路径负例（NULL ctx 触发 `lwdtc_cron_next` 返回错误，`next` 故意不初始化，
  与 test.c 同构）：输出 `lwdtc_cron_next(NULL) returned error (0x02), failure
  path does not read next` + `negative-path test: PASS`，exit 0——证明失败分支
  不再读取 `next`、不产生误导性 `FAIL: next <= now`
- 修复后文件 sha256：`c80ed371e88770abec20600884417541b0f1a065181b639e48673f13ff119bc6`
  （交付态 `git show HEAD:test_package/test.c` 实测）
- 断言强度未降低：4/4 检查点（parse、valid(30s)、valid(31s) 不匹配、next 严格晚于 now）全保留

## 适用边界

- **适用**：任何在 `test_package/` 或消费性测试中调用带输出参数 API
  （`time_t*`、`int*`、`struct*` 等）后无条件断言该输出值的 C/C++ 库配方；
  任何"先检查返回码、再读取 out 参数"的测试代码模式（不限于 lwdtc）。
- **不适用**：API 失败时明确写入 out 参数（文档保证失败也有定义值）的场景；
  输出参数已显式初始化（`time_t next = 0;`）且断言不掩盖真实失败的场景。

## 反例/限制

- 反例：保留并列 if 结构——失败路径读取未初始化 `next`（UB + 误导性
  `FAIL: next <= now`），AI 检视 P3 复现。
- 反例：删除/弱化 `next <= now` 检查点，或把测试改成恒绿空壳——违反 R34，
  测试闸（PF3）拦截。
- 反例：用 `#ifdef` 平台宏规避或只编译不运行——无真实运行证据，无法验证
  失败路径语义。
- 限制：`else if` 结构使失败分支不再报告"次生断言"结果，属预期（真实失败
  只有一个：API 返回错误）；若需要保留次生诊断，应显式初始化 out 参数并
  单独记录，但不得把未初始化读取保留为交付态。
