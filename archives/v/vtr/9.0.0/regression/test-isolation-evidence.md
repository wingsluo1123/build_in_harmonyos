# 单元测试执行分组（进程隔离证据）

> 本文件是 PR 正文「单元测试的执行分组」一节的完整证据，随 PR 一同提交。
> 结论先行：**未修改任何上游测试源码**；`test_vpr` 的 60 个用例全部执行、全部断言全部求值。

## 1. 上游注册方式与实测现象

上游把 `test_vpr` 的 **60 个 `TEST_CASE` 注册成单个 ctest 测试**（`vpr/CMakeLists.txt:328`）。
单进程全量运行时**确定性段错误**（非偶发）。

实测二分到最小复现：

**`test_compressed_grid` 与 `connection_router` 不能共存于同一进程，且正反两个顺序都崩。**

| 调用 | 结果 |
|---|---|
| `test_vpr "test_compressed_grid,connection_router"` | SIGSEGV |
| `test_vpr "connection_router,test_compressed_grid"` | SIGSEGV |
| `test_vpr "test_compressed_grid"` | 通过 |
| `test_vpr "connection_router"` | 通过 |
| `test_vpr "~[vpr_compressed_grid]"` | 通过 |

这两个用例各自单独运行、以及 `test_compressed_grid` 与其余任何用例组合，都通过。

## 2. 根因

`vpr/test/test_compressed_grid.cpp` 把**测试自造的**设备上下文直接写进**进程级全局** `g_vpr_ctx`：

- 10 个**栈局部**的 `t_physical_tile_type` / `t_logical_block_type` 对象的地址被发布进
  `equivalent_tiles` / `equivalent_sites` / `EMPTY_PHYSICAL_TILE_TYPE`；
- 全局 `grid` 被整个替换成自造的 `DeviceGrid("test_device_grid", …)`；
- **既不初始化也不还原。**

于是进程内任何随后走完整 `vpr_init()` / `vpr_free_all()` 的用例都会踩到这份残留状态
（悬垂指针 + 假 grid）；反向顺序（`connection_router` 先跑完 `vpr_free_all()`）同理。

上游把 60 个注册用例塞进**单个** ctest 测试，而 5 个 workflow **没有任何一处调用 ctest
或 `make test`**，所以该缺陷在上游一直潜伏、未被上游 CI 触发。

该缺陷是这两个测试用例自身的性质，**与本平台无关**：补丁 0001–0005 触及的 19 个文件
没有一个在这两条执行路径上。

## 3. 处理方式（只改执行分组，不改测试）

```
ctest --output-on-failure --test-dir <build> -E "^test_vpr$"   # 另外三个 Catch2 目标
cd <src>/vpr/test && <build>/vpr/test_vpr --colour-mode none "~[vpr_compressed_grid]"   # 59 用例
cd <src>/vpr/test && <build>/vpr/test_vpr --colour-mode none  "[vpr_compressed_grid]"   #  1 用例
```

（`test_vpr` 相对于 `vpr/test` 解析 `wire.eblif` / `testarch.device` / `../../vtr_flow`，
故工作目录必须是源码侧的 `vpr/test`——与上游 `add_test()` 的 `WORKING_DIRECTORY` 一致。）

**与上游的唯一差异是进程分组（1 个进程 → 2 个进程）。**
60 个用例全部执行，没有跳过、没有降级断言、没有改动 `golden` 或期望值。

## 4. 最终日志实测数字（SHA `0de984df64`）

数字取自最终 SHA 的 farm 日志，未沿用任何历史摘要。

| 目标 | 运行方式 | 结果 |
|---|---|---|
| `test_archfpga` / `test_vtrutil` / `test_fasm` | `ctest -E '^test_vpr$'` | `100% tests passed, 0 tests failed out of 3` |
| `test_vpr`（59 用例） | `"~[vpr_compressed_grid]"` | `All tests passed (10479 assertions in 59 test cases)` |
| `test_vpr`（1 用例） | `"[vpr_compressed_grid]"` | `All tests passed (40 assertions in 1 test case)` |

合计 **60 个用例 / 10519 条断言**，全部通过。

> `ctest` 在测试通过时不输出各目标内部的用例/断言数，故上表只对 `test_vpr` 给出细分数字；
> 另外三个目标不为它们填数。源码统计：`test_vpr` 有 80 个 `TEST_CASE`，其中 20 个被上游
> 条件编译排除，80 − 20 = 60，与日志一致。

## 5. 已排除的替代方案

曾给那 10 个栈局部对象加 `static` 延长生命周期，**实测仍 rc=139**，证明单靠延长对象寿命
不足——全局上下文里的假 grid / 假 `logical_block_types` 本身即致命。**该实验已回滚**，
仓库中不含该改动的任何痕迹。
