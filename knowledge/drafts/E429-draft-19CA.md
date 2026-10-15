# E429 — 上游 pytest 套件取离线子集应以其自身 marker 为准；并先核对 sdist 的测试落点（包内 vs 顶层）

## 错误特征
`python3 -m pytest tests/ -q` 直接报
`ERROR: file or directory not found: tests/`；
若改成"直跑整个套件"则在含网络用例处报
`requests.exceptions.ConnectTimeout`，个别用例**挂住不返回**（日志零增长，最后被 timeout 截断）；
pytest 汇总里出现大量 `deselected`/`skipped`。

## 触发条件
- 构建系统: 无（纯 Python 包，sdist 安装）
- 阶段: testing（`build()` 内跑上游套件）

## 根因分析
1. **测试落点不在你以为的位置**：不少库把测试放在**包内**（pooch 为 `pooch/tests/`，sdist **没有**顶层 `tests/`）。
   习惯性照抄 README 里的 `pytest tests/` 会直接失败——不是"上游没测试"，是路径错。
2. **上游套件里混着需要真实外网的用例**：上游用 `@pytest.mark.network` 自己标注了这些用例
   （pooch 源码内实测 38 处）。本环境直跑会连接超时；**部分用例在无网时会挂住不返回**，
   比失败更糟——它不产生结论，只消耗时间。
3. 于是产生两个错误结论：①误判"上游无测试"（其实在包内）；②为绕开网络而**私自挑文件或整批跳过**——
   这既改了上游口径，也会把"没跑"写成"通过"。

## 解决方案

### 推荐方案
1. **先清点落点**：`find <sdist> -maxdepth 2 -name 'test_*.py' | head`（或 `src/*/tests/`），
   据此定 `test_path`；把结论写进 notes/manifest。
2. **离线子集以上游 marker 为准**：`grep -rc 'mark.network' <tests 目录>` 确认标记存在后，
   用 `-m 'not network'` 取离线子集；**未被标记者的失败仍让 build 硬失败**（不宽恕、不冒充通过）。
3. **测试期依赖按"缺环境就下"**：pooch 需要 `pytest` + `pytest-httpserver` + `pytest-localftpserver`
   （后两个提供本地 HTTP/FTP 服务，属**离线**）→ `pip --target` 装到 `<build>/test-deps`，**不进产物**。
4. 实测口径：pooch 1.9.0 → `-m 'not network'` = **62 passed / 13 skipped / 85 deselected**。

### 禁止做法
- ❌ 因为 `tests/` 不存在就断言"上游无测试"（先找包内）
- ❌ 整批 `--ignore` / 干脆不跑，然后把通过率写成 100%
- ❌ 自己挑几个文件跑出来充数（口径必须来自上游 marker）

## 验证
```bash
find <sdist> -maxdepth 2 -name 'test_*.py' | head
grep -rc 'mark.network' <tests 目录>
PYTHONPATH=<pkg>:<test-deps> python3 -m pytest <test_path> -q -m 'not network'
# 期望：末行形如 "62 passed, 13 skipped, 85 deselected"
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它 Python 测试期条目：sdist 布局、pytest 插件型 addopts）
