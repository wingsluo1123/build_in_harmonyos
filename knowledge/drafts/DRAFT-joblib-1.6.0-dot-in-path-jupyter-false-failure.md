# DRAFT-joblib-1.6.0-dot-in-path-jupyter-false-failure — 路径中的「点」导致的假失败

> 初版标题为 `...-space-in-path-...`，把原因归为「路径含空格」。
> **该归因已被实验推翻**：在无空格的干净路径下失败依旧复现；
> 真因是**路径中的「点」**（详见下「四组对照实验」）。

## 可复现症状与稳定错误签名

```
joblib/test/test_memory.py::test_parallel_call_cached_function_defined_in_jupyter[True] - AssertionError
joblib/test/test_memory.py::test_parallel_call_cached_function_defined_in_jupyter[False] - AssertionError
joblib/test/test_memory.py:191: AssertionError
    >  assert "ipython-input" in f_cache_relative_directory
```
稳定特征：`assert "ipython-input" in` + `f_cache_relative_directory`，
且**只随工作/源码路径变化**（换路径即消失）。

## 根因与最小复现

- 该用例用 `filename="<ipython-input-0-000000000000>"` 模拟 Jupyter 单元定义函数，
  再断言 joblib 生成的缓存目录名**含** `ipython-input`。
- joblib `func_inspect.get_func_name`（`module == "__main__"` 分支）：
  ```python
  filename = os.path.abspath(inspect.getsourcefile(func))   # cwd 决定 abspath
  parts = filename.split(os.sep)
  ...
  filename = "-".join(parts)
  module = module + "-" + filename
  module = module.split(".")        # ← 关键：整串再按「点」拆
  ```
  **顺序陷阱**：路径先被 `os.sep` 切成段拼成一整串，**之后**才对整串
  `split(".")`。于是路径中的**点**会把拼接结果截断成多段 →
  `<ipython-input...` 落进后面的段里，缓存目录名只剩前半段 → 断言失败。

插桩实测（源码路径 `.../joblib-1.6.0/`，含点）：
```
co_filename   : <ipython-input-0-000000000000>
exists(cid)   : False
get_func_name : (['__main__--storage-Users-currentUser-tmpskip-joblib-1',
                  '6', '0-<ipython-input-000000000000>'], 'f')
cache dirs    : ['__main__--storage-Users-currentUser-tmpskip-joblib-1']
含 ipython-input: False            ← 截断于 ".0"
```

最小复现（不改任何代码）：
```bash
B=/tmp/p; mkdir -p "$B/nospace/dot.1.6.0" "$B/cleanpath"
cp -r <joblib-src>/{joblib,conftest.py} "$B/nospace/dot.1.6.0/"
cp -r <joblib-src>/{joblib,conftest.py} "$B/cleanpath/"
cd "$B/nospace/dot.1.6.0" && PYTHONPATH=$PWD python3 -m pytest <该用例>   # -> 2 failed
cd "$B/cleanpath"         && PYTHONPATH=$PWD python3 -m pytest <该用例>   # -> 2 passed
```

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 初版归因为「路径含空格」→ 换无空格路径 | **归因错误**：无空格的含点路径下**仍失败**（场景 B/C），说明空格不是触发条件 |
| 把该用例加入 `ALLOWED_TEST_FAILURES` | **错误做法**——把环境问题固化成"已知失败"，会掩盖真实回归（R51） |
| 改配方/加补丁去"修" | 无效——根因在路径形态，不在配方 |
| **从"无点的 cwd"运行**（`getsourcefile` 走 abspath，路径由 cwd 决定） | **通过，采用** |

## 最终方案、输入输出与真实验证

**四组对照实验（决定性）**

| 场景 | 路径特征 | 结果 |
|------|---------|------|
| A | `.../with space nodot/`（含空格、**无点**） | **2 passed** |
| B | `.../nospace/dot.1.6.0/`（**含点**、无空格） | **2 failed** |
| C | `.../.cachedir/joblib-src/`（**点开头目录**） | **2 failed** |
| D | `.../cleanpath/`（无点无空格） | **2 passed** |
| E | cwd 无点、源码在含点目录 | **2 passed** |

→ **空格无关，点是触发条件**；且**含点即失败**（B/C）。

**⚠️ CI 会复现**：CI worker 工作目录为
`/storage/Users/currentUser/.cache/buildbot-worker/conan-pr-check/build`
——**含 `.cache` 点目录**（场景 C 同型）。初版"CI 不会复现"的结论**错误**。

**采用方案**：让测试进程的 **cwd 不含点**（场景 E 已验证 2 passed），
无需改动上游测试、无需加入允许清单。

**真正的最终结果（干净口径）**：`1326 passed / 103 skipped / 3 xpassed`。
> 初版记录的 `1 error`（`fixture 'caplog' not found`）系**我方调用错误**：
> 命令行加了 `-p no:logging`，禁用了提供 `caplog` fixture 的插件；
> 去掉后 error 消失（1325→1326 passed），非包缺陷。

**R34 消费者测试**（独立证据链）实跑通过：
```
joblib 1.6.0
OK: Memory.cache replayed the cached result (1 real call)
OK: Parallel(n_jobs=2) computed [0, 1, 2, 3, 4, 5, 6, 7]
```

## 注意事项

1. **不要用「含空格」解释路径类假失败**——先做对照实验：
   本例空格无关，**点**才是触发条件。判据是"分别构造含空格/含点两条路径"。
2. **`.cache` 这类点目录很常见**（conan cache、CI worker、`~/.local`）——
   凡库内按**绝对路径**做名字 mangling/哈希的（joblib 等），
   含点路径都可能改变结果。
3. **看到失败先怀疑环境，再怀疑代码**，但环境归因必须用对照实验支撑，
   不能凭"路径里有空格"就下结论（本文件初版即栽在此）。
4. 允许清单（`ALLOWED_TEST_FAILURES`）只用于**已确证的平台限制**，
   **不得**用来吞环境性假失败。
5. 加 `-p no:logging` 会禁用 `caplog` fixture，制造假 error —— 慎用。
