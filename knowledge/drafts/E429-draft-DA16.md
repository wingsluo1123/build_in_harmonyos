# E429 — 上游"测试"未必是 pytest 套件：可能是一组自带 runner 的可执行脚本，探测依据不能用文件名 test*

## 错误特征
配方里"动态探测测试目录"报
`未在 sdist 内探测到测试目录（候选 ['tests','ppft/tests','test']）`；
换成 pytest 直跑则该目录 `no tests ran`（没有任何 `test_*.py`）。
上游 `tox.ini` 却明确写着测试命令——说明**不是没有测试，是跑法/探测依据错了**。

## 触发条件
- 构建系统: 无（纯 Python 包，sdist 安装）
- 阶段: testing（`build()` 内跑上游套件）

## 根因分析
1. `ppft/tests/` 里是一组**可执行脚本**：`auto_diff.py` / `callback.py` / `dynamic_ncpus.py` /
   `quicksort.py` / `reverse_md5.py` / `sum_primes.py` / `sum_primes_functor.py`
   —— **一个 `test_*.py` 都没有**。
2. 官方跑法在其 `tox.ini`：
   ```
   commands = {envpython} -m pip install .
              {envpython} ppft/tests/__main__.py
   ```
   `ppft/tests/__main__.py` 把目录内**除 `__*` 外**的每个 `.py` 当子进程逐个执行，
   任一失败即 `exit 1`（其 `__init__.py` 也写明 `python -m ppft.tests`）。
3. 于是"按文件名 `test*` 开头探测"和"上 pytest"两条路都会得出错误结论（误判"上游无测试"），
   而早期凭直觉预估的测试期依赖（`dill`/`pytest`）其实**并不需要**。

## 解决方案

### 推荐方案
1. **先看上游怎么跑**：`grep -A3 '^commands' <sdist>/tox.ini`（或 README / CI 配置），
   以**上游自己的跑法**为准，而不是套一个通用假设。
2. **探测依据改成"目录内有上游 runner"**：即存在 `__main__.py`，而不是文件名匹配 `test*`。
3. **用上游 runner 真跑**：`PYTHONPATH=<sdist> python3 <sdist>/<pkg>/tests/__main__.py`，
   按 **rc 硬判**（rc≠0 即让 build 失败），并自行清点待跑脚本个数用于回填。
4. **测试期依赖按实测**：实测这些脚本只 import `math/sys/time/hashlib` 与包自身
   → **零测试期依赖**，构建全程离线（省掉 pip 与网络）。

### 禁止做法
- ❌ 探测不到就宣称"上游无测试"并跳到消费者校验（应先看 `tox.ini`/CI）
- ❌ 把"目录里没有 `test_*.py`"等同于"没有测试"
- ❌ 凭直觉预装 `dill`/`pytest` 等依赖（会让构建绑定网络，且掩盖真实跑法）

## 验证
```bash
ls <sdist>/<pkg>/tests/                      # 看到的是 quicksort.py / sum_primes.py 这类脚本
grep -A3 '^commands' <sdist>/tox.ini        # 官方命令：python <pkg>/tests/__main__.py
PYTHONPATH=<sdist> python3 <sdist>/<pkg>/tests/__main__.py; echo "rc=$?"
# 期望：7 个脚本逐个执行、rc=0（ppft 1.7.8 实测 7/7 通过）
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它 Python 测试期条目：sdist 测试落点、pytest 插件型 addopts）
