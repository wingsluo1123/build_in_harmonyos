# websocket-client

- **上游**：https://github.com/websocket-client/websocket-client
- **版本**：1.9.2
- **形态**：纯 Python（noarch）——低层 WebSocket 客户端；**零运行期依赖**（`install_requires=[]`）
- **要求**：上游 `python_requires=">=3.10"`（本环境 3.12 满足）

## 归档内容

```
websocket-client/
  commands.json            软件级命令声明（R38：本包产出上游 CLI wsdump）
  1.9.2/
    conandata.yml          源（官方 sdist + sha256，钉死）
    conanfile.py           配方（source → build(测试期 pytest + 上游套件) → package(模块 + bin/wsdump)）
    manifest.yaml          版本级 manifest（dependencies / upstream_tests / knowledge_gained）
    notes.md               适配要点（先验可跑性、CLI 落地、测试期依赖不靠宿主）
    test_package/          消费者校验（8 项，全部离线）
```

## 产物

- 模块 `websocket/`（含 `tests/`、`data/*.txt`，与上游 `find_packages()` + `package_data` 一致）
- **`bin/wsdump`**：上游 `setup.py` 的 `console_scripts` 入口（`websocket._wsdump:main`）落成的
  **自定位**脚本（自己把本前缀的 `site-packages` 插进 `sys.path`，不依赖外部 `PYTHONPATH`）

## 上游测试

测试随 sdist 发布在**包内** `websocket/tests/`（16 个 `test_*.py` + `data/*.txt` + `echo-server.py`），
纯离线即可跑通：**195 passed / 26 skipped / 21 subtests passed**。
26 个 skip **全部来自上游自己的环境开关**（`TEST_WITH_INTERNET` 默认 0；`TEST_WITH_LOCAL_SERVER`
判据 `LOCAL_WS_SERVER_PORT != "-1"`），配方显式清掉这两个变量以免结果不可复现。
测试期依赖仅 `pytest`（装到 `<build>/test-deps`，**不进产物**）；上游 extra `test` 里的 `websockets`
只服务本地服务路径，本适配未启用该路径 → 不装（如实披露）。

## 消费者校验

`test_package/check_websocket_client.py` **8 项，全部离线**：产物齐备 / 15 个关键文件齐备 /
真实 `import websocket` / `__version__ == '1.9.2'` / 真实 API `_url.parse_url()`（wss 与 ws 两种 URL）/
真实功能 `ABNF.create_frame('hello')→format()`（11 字节、首字节 `0x81`）+ `validate_utf8()`/
**上游 CLI 真跑 `bin/wsdump --help`** / 证据。实测 `checks=8 fails=0` / `RESULT: PASS`。
