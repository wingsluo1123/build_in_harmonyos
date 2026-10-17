# E429 — 上游 setup.py 的 console_scripts 入口必须落成脚本产物并声明 commands.json；脚本应自定位

## 错误特征
- 适配后**产物面不全**：包里只有 `lib/pythonX.Y/site-packages/<pkg>/`，而上游 `setup.py` 明明声明了
  `entry_points.console_scripts`（例：websocket-client 的 `wsdump=websocket._wsdump:main`）
  → 用户拿不到上游的那个命令行工具。
- 若把入口朴素地落成一个直接 import 的脚本，在未设 `PYTHONPATH` 时调用会
  `No module named <pkg>`。
- 仓库侧门禁：CI L0k / R38 要求"产出可执行文件的包必须在软件级目录声明 `commands.json`"，
  缺了判 fail。

## 触发条件
- 构建系统: 无（纯 Python 包，sdist 安装）
- 阶段: installation（打包与产物声明）

## 根因分析
1. 纯 Python 库的适配容易只盯"模块能不能 import"，**漏掉上游声明的非模块产物**：
   `console_scripts`（CLI）、man 页、bash completion 等。
2. `console_scripts` 的运行时语义是"由 pip 在 `bin/` 生成一个入口脚本，其 import 目标是你安装的包"；
   我们的配方不走 pip install，**必须自己把这一步等价实现**，否则少产物。
3. 入口脚本对 `sys.path` 有隐含依赖：pip 生成的脚本之所以能跑，是因为包已装在解释器默认
   `site-packages` 里；而 Conan 包在私有前缀下，脚本必须**自定位**（把自己的
   `<prefix>/lib/pythonX.Y/site-packages` 插进 `sys.path`）才不依赖外部 `PYTHONPATH`。
4. 仓库还有配套规矩（R38）：`archives/<letter>/<name>/commands.json` 里声明 `type: "tool"`、
   `name` 与包名一致、`binary: false`（脚本，不是预编译二进制）。

## 解决方案

### 推荐方案
1. **清点上游声明的产物面**：`grep -A6 'console_scripts' <sdist>/setup.py`（或 `pyproject.toml`）——
   有入口就一定要落成脚本。
2. **落成自定位脚本** `bin/<tool>`（可执行位 0755），核心三行：
   ```python
   import os, sys
   _here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # <prefix>
   _site = os.path.join(_here, "lib", "python%s.%s" % (sys.version_info.major,
                                                       sys.version_info.minor),
                        "site-packages")
   if os.path.isdir(_site) and _site not in sys.path:
       sys.path.insert(0, _site)
   from <pkg>._cli import main
   sys.exit(main())
   ```
3. **声明 commands.json**（软件级目录）：`/archives/<letter>/<name>/commands.json`，
   `{"name": "<name>", "type": "tool", "description": "...", "versions": {"<ver>": {"ref": "<name>/<ver>", "binary": false}}}`；
   并在 `package_info()` 里 `self.cpp_info.bindirs = ["bin"]`。
4. **消费者校验里真跑一次**：`python <pkg>/bin/<tool> --help` 期望 rc=0 且打印用法——
   把它当作"入口真的可用"的证据（websocket-client 实测 `wsdump --help` rc=0 并打印
   `WebSocket Simple Dump Tool`）。

### 禁止做法
- ❌ 只拷模块、把上游 CLI 当"可有可无"（少产物，且与 R38 冲突）
- ❌ 落成写死绝对解释器路径或依赖外部 `PYTHONPATH` 的脚本
- ❌ 预编译一个二进制充当脚本（R19 禁止仓库内提交预编译二进制；此处应是**脚本**，`binary: false`）

## 验证
```bash
grep -A6 'console_scripts' <sdist>/setup.py          # 确认上游入口
ls -l <pkg>/bin/<tool>                                # 存在且 0755
python <pkg>/bin/<tool> --help; echo "rc=$?"          # 期望 rc=0
python -c "import json;print(json.load(open('archives/<letter>/<name>/commands.json')))"
```

## 关联条目
- 相关: E429（同一草稿 id 下的 Python 测试期条目：sdist 测试落点 / 上游自带 runner / 离线子集 marker /
  src 布局与 pytest 插件型 addopts）
- 互补纪律: **接活前先验证"上游测试能不能跑"**——跑不了按规矩放弃该库（反例：ply 3.11 的
  `testlex/testyacc` 依赖 Python 3.11 已移除的 `unittest.TestCase.assert_`、`testcpp` 超时，
  在 3.12 上 42/43、36/42、3/3 全错 → 直接放弃，而不是改上游测试凑通过率）
