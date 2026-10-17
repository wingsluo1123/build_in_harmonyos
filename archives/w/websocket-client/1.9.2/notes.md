# websocket-client 1.9.2 适配笔记

## 结论速览
- **类型**：纯 Python（noarch），顶层 `websocket/` 包；**零运行期依赖**（`install_requires=[]`）
- **上游测试**：sdist **自带** `websocket/tests/`（16 个 `test_*.py` + `data/*.txt` + `echo-server.py`），
  纯离线即可跑通 → 实测 **195 passed / 26 skipped / 21 subtests passed**
- **额外产物**：上游 CLI `wsdump`（setup.py 的 `console_scripts` 入口）→ 落成 `bin/wsdump` + `commands.json`
- **状态**：built（本地 conan create 全绿：上游 195 passed + 消费者 8/8）

## 打包步骤
```bash
conan create archives/w/websocket-client/1.9.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1) 先验证"测试能不能跑"（按规矩：跑不了就放弃该库）
解包 sdist 后**先不写配方**，直接按上游方式跑一遍：

```bash
PYTHONPATH=<sdist> TMPDIR=/data/storage/el2/base/cache \
  python3 -m pytest websocket/tests/ -q --no-header
# → 195 passed, 26 skipped, 21 subtests passed   ← 可跑，继续适配
```

26 个 skip 全部来自**上游自己的环境开关**（不是我们挑的）：
`TEST_WITH_INTERNET`（默认 `"0"`，16 个）与 `TEST_WITH_LOCAL_SERVER`
（判据 `LOCAL_WS_SERVER_PORT != "-1"`，走 `echo-server.py` 起的本地服务）。
配方里显式 `pop` 掉这两个环境变量，避免宿主环境把它们打开后结果不可复现。

### 2) 依赖
- **运行期：零依赖**（`install_requires` 为空）→ 不声明任何 Conan `requires`
- **测试期：仅 `pytest`**，装到 `<build>/test-deps`（**不进产物**）
  - ⚠️ **pytest 必须显式装**，不能依赖宿主自带 —— prawcore 的 CI 构建 #89394 就是因此报
    `No module named pytest` 而失败（本机宿主恰好有 pytest，容易漏）
  - 上游 extra `test` 里还有 `websockets`：它只被 `echo-server.py` 的本地服务路径使用，
    本适配未启用 `TEST_WITH_LOCAL_SERVER` → 不装，并在 manifest/MANIFEST 里如实披露

### 3) 产物
- 模块 `websocket/`（含 `tests/`、`data/*.txt`，与上游 `find_packages()` + `package_data` 一致）
- **`bin/wsdump`**：上游 `entry_points.console_scripts` 的入口（`websocket._wsdump:main`）。
  配方落成**自定位**脚本——自己把 `<prefix>/lib/pythonX.Y/site-packages` 插进 `sys.path`，
  因此不依赖外部 `PYTHONPATH`；并按 R38 在软件级目录声明 `archives/w/websocket-client/commands.json`

## 实测结果（本地 conan create）
```
[upstream tests] 套件目录 = websocket/tests（16 个 test_*.py）；跑法 = python -m pytest（PYTHONPATH = pkg : test-deps）
[upstream tests] 195 passed, 26 skipped, 21 subtests passed in 7.72s
[ok]   产物齐备：websocket 模块位于 lib/python3.12/site-packages/websocket
[ok]   模块文件齐备：15 个关键文件（含 tests/ 与 data/，与上游 find_packages 一致）
[ok]   import websocket 成功（零运行期依赖）
[ok]   __version__ == '1.9.2'（与包版本一致）
[ok]   真实离线 API：parse_url() 正确解析 wss/ws 两种 URL（含默认端口与 secure 位）
[ok]   真实离线功能：ABNF.create_frame('hello')→format() 得 11 字节、首字节 0x81（FIN|TEXT），ABNF.validate() 通过，validate_utf8() 判定正确
[ok]   上游 CLI 真跑：bin/wsdump --help rc=0 且打印用法（入口 websocket._wsdump:main 可用）
[ok]   证据：websocket 模块总字节 …；python 3.12.9
checks=8 fails=0
RESULT: PASS
```

## 踩坑/要点
1. **先验可跑性**：本库 sdist 自带测试且离线可跑，适配风险低；同类里 ply 3.11 的上游套件在 Python 3.12
   上根本跑不起来（`unittest.TestCase.assert_` 已被移除 → `testlex` 42/43、`testyacc` 36/42 报错；
   `testcpp` 3/3 "Time limit exceeded"）→ 按规矩**直接放弃该库**，不改上游测试凑通过率。
2. **CLI 入口别漏**：上游有 `console_scripts` 就要落成脚本产物并声明 `commands.json`（R38）；
   脚本做成自定位可免掉用户手工设 `PYTHONPATH`。
3. **测试期依赖不靠宿主**：`pytest` 一律进 `test-deps`；宿主有不算数（CI worker 没有）。
4. `/tmp` 只读 → `TMPDIR=/data/storage/el2/base/cache`。
