# E587 — nose 专属测试形态被 unittest discovery 静默丢弃，只报 `Ran N` 即少报

## 错误特征

```
Ran 126 tests in 4.951s
OK (skipped=3)
```

构建成功、零失败，但上游实际有 127 个定义（含 26 个 nose 专属形态），报告把
`Ran N` 当成上游全集 → **少报**。全部特征：退出码 0、没有任何 WARNING，只有数字对不上。

## 触发条件

- 工具链: Python 3 + `unittest discover`（上游原本由 nose 驱动）
- 阶段: 测试
- 前提: 上游测试里有 nose 能收集、unittest 不承认的形态

## 根因分析

`unittest` 的 discovery 只收集 `TestCase` 子类和模块级 `test_*` 函数；nose 还会收集：

- 生成器形 `test_*` 方法（方法体 `yield` 逐个产出用例）
- plain `object` 子类里的 `test_*` 方法（不是 `TestCase`，直接看不见）
- 模块级 `test_*` 函数之外的其它 nose 约定

这些用例不是“失败”，而是**从未被收集**，因此不会出现在 `Ran`、不会出现在失败列表里，
极易被写成“全部通过”。

补充：**不能靠安装 nose 来补齐** —— nose 1.3.7 是 Python 2 语法（`core.py` 仍用
`print` 语句），在 Python 3.12 下导入抛 `SyntaxError`（不是 `ModuleNotFoundError`），
所以“装一下 nose 就好”这条路不存在。

## 解决方案

### 推荐方案

1. **垫片**（声明式补丁，不改上游测试源码）：只提供上游实际用到的断言函数与
   `SkipTest`（本例 7 个函数 + `SkipTest` 共两个文件）。
2. **补跑执行器**（第二个声明式补丁）：忠实复现上游运行方式（`chdir` 到测试目录 +
   相对导入），逐个驱动鼻子专属定义。
3. **用例数下限闸门**：执行器内置 `MIN_CASES`，少于该数即失败——生成器静默缩水
   （例如某次 `yield` 被改成空循环）无法蒙混过关。
4. **覆盖率闸门**：从源码重新推导“鼻子专属实体集合”，任一未被驱动即失败。
5. **精确 xfail 白名单**：CPython 漂移按「完整用例标签 → 原因」逐条登记，**并做反向
   验证**——人为注入一个新失败必须使执行器退出码非 0，证明白名单不外溢。

报告口径：定义数（上游全集）/ 可发现定义数 / 鼻子专属定义数 / 两组展开后的用例数
分列，两个集合必须证明互不重叠，禁用 `Ran N` 冒充全集。

### 禁止做法

- ❌ 只报 `Ran N` 并称“上游测试全部执行”
- ❌ 删除/注释掉 discovery 看不到的用例，或整模块 `skip`
- ❌ 装 nose 1.3.7 并假设它能用
- ❌ 宽泛 xfail/`pytest.ini` 级别的忽略规则（会掩盖新增失败）

## 验证

```bash
python3 -m unittest discover -s <pkg>/tests -p 'test_*.py' -v        # 命令 1
python3 <pkg>/tests/_ohc_extra_upstream_tests.py                     # 命令 2
# 期望：ran=<下限之上> unexpected_failures=0 known_drift=<精确条数>
# 反向验证：注入一个人为失败 → 必须 rc!=0
```

实测（kitchen 1.2.6）：命令 1 `Ran 126`（123 通过 + 3 跳过 + 0 失败）；命令 2
`ran=464 unexpected_failures=0 known_drift=3`；101 + 26 = 127 个定义全覆盖，
两组定义互不重叠。

## 关联条目

- 相关: E586（同类“本地验证手段不足导致假绿”问题）
