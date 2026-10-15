# notes — pooch 1.9.0 适配 HarmonyOS PC

## 结论速览

- 纯 Python（noarch，顶层 `pooch/`），**零编译**；产物 = `lib/python3.12/site-packages/pooch/`
- **运行期依赖三件在仓库中均已有归档** → 直接 `requires`（**无需 pip 绕过/随包附带**）：
  `platformdirs/4.3.8`、`packaging/26.3`、`requests/2.22.0`
- 上游测试在**包内** `pooch/tests/`（9 个 .py）；按**上游自身标记**取离线子集
  （`-m 'not network'`）→ 实测 **62 passed / 13 skipped / 85 deselected**
- 消费者校验 `test_package/check_pooch.py` **7 项，全部离线**

## 关键实测点

1. **测试路径**：sdist **无顶层 `tests/`**，测试在包内 `pooch/tests/` → 习惯写法 `pytest tests/`
   首轮即 `ERROR: file or directory not found: tests/`；已改为 `pytest pooch/tests/`。
2. **网络用例口径**：上游以 `@pytest.mark.network` 标记需外网的用例（源码内实测 38 处）；
   本环境直跑会 `requests.exceptions.ConnectTimeout`，且**部分用例会挂住不返回**（首轮本地 CI
   即卡在该处，日志零增长）→ 改为 `-m 'not network'`（**上游认可的离线子集**），
   未被标记者的失败仍会硬失败。
3. **测试期依赖**：按上游 test extras 装 `pytest-httpserver` / `pytest-localftpserver` 到
   `<build>/test-deps`（**不进产物**）；pip 源先试清华镜像，失败退回官方源
   （实测镜像首次失败、退回官方源成功，并会清掉 pip 顺带装的同名包以免遮蔽 conan 版本）。
4. **PYTHONPATH 顺序**（prawcore 教训）：`pkg → test-deps → 各 conan 依赖 site-packages → 原环境`；
   `build()`/`test()` 里的 subprocess **不继承** conan 依赖 env，必须显式前置。
5. **OHOS 沙箱**：`/tmp` 只读 → `TMPDIR=/data/storage/el2/base/cache`。
6. **不依赖 curl**：取源用 conan `get()`（sha256 校验），测试期依赖用 `python -m pip`。

## 依赖判定（"已合入 > 可绕过"的落地）

| 依赖 | 判定 | 处置 |
|---|---|---|
| `platformdirs (>=2.5.0)` | 仓内**已有归档** 4.3.8 | `requires` |
| `packaging (>=20.0)` | 仓内**已有归档** 26.3 | `requires` |
| `requests (>=2.19.0)` | 仓内**已有归档** 2.22.0 | `requires` |
| `pytest-httpserver` / `pytest-localftpserver` | 仓内无归档（测试期） | pip 到 `<build>/test-deps`，不进产物 |

## 测试期 pip 源：**平台私有源必须排第一**（CI 构建 #89930 的修复）

CI 失败现象：

```
File ".../test-deps/pytest_localftpserver/servers.py", line 12, in <module>
    from pyftpdlib.handlers import FTPHandler, TLS_FTPHandler
ImportError: cannot import name 'TLS_FTPHandler' from 'pyftpdlib.handlers'
             … Did you mean: 'FTPHandler'?
```

链条：`pyftpdlib` 2.x 的 `handlers/__init__.py` 对 TLS 符号是**条件导出**——

```python
try:
    from OpenSSL import SSL
except ImportError:
    pass
else:
    from .ftps.control import TLS_FTPHandler      # 没有 pyOpenSSL 就不导出
```

而 `pyOpenSSL` 依赖的 `cffi` / `cryptography` 是**原生扩展**：清华镜像给的是 manylinux 轮子，
其 `.so` 在 OHOS(musl) 上加载不了 → `import OpenSSL` 失败 → 上面那行不执行 →
`pytest_localftpserver/servers.py` 的**无条件** import 直接炸。
本机之所以一直绿，是因为全局 pip 指向平台私有源 `pypi.cnb.cool`，拿到的是 **OHOS 轮子**
（`_cffi_backend.cpython-312-aarch64-linux-ohos.so`）。

修复：`PIP_INDEXES` 改为**平台私有源优先**（并加 `--trusted-host pypi.cnb.cool`），
清华 / 官方源作后备（仓库既有配方 `archives/g/gym/0.26.2` 同样用法）。

实测核对（修复后 conan create）：日志 `测试期依赖已安装（https://pypi.cnb.cool/…）`；
新 `test-deps` 内为 OHOS 轮子 → `import OpenSSL` 26.4.0 成功 → `pyftpdlib` 导出
`TLS_FTPHandler` → `pytest_localftpserver.servers` 可导入；上游 `62 passed`、消费者 `7/7`。

## 测试期 shim（重要披露：只补一个占位符号，不改用例与断言）

**CI 构建 #90269 实测**：即使测试期依赖已从平台私有源装成功，本平台 ABI 下 pyOpenSSL
**仍不可用**（本机拿到的轮子标签是 `cp312-cp312-ohos_aarch64`，CI 选到的不是它）→
`pyftpdlib.handlers` 不导出 `TLS_FTPHandler` → `pytest_localftpserver/servers.py:12` 的
**无条件 import** 会在**收集阶段**把整个 pytest 会话打死（同一错误在 #89930 与 #90269 两次出现）。

处置（仅测试期，**不碰上游测试与断言**）：`<build>/test-shim/sitecustomize.py` 在
`pyftpdlib.handlers` 缺 `TLS_FTPHandler` 时补一个**占位类**。

为什么这是安全的：
- `pytest-localftpserver` 的**明文** `ftpserver` 夹具走 `FTPHandler`，**只有** `ftpserver_TLS`
  才用 `TLS_FTPHandler`（读其 `servers.py` 的 `run()` 即知）；pooch 的 FTP 用例全是明文
  （`FTPDownloader` + `ftp://`）→ 占位不会被触碰；
- **若真有 FTPS 用例，占位会立刻 `RuntimeError` 而不是静默通过**（不制造假通过）。

外加 **shim 自检**：把 `OpenSSL` 置成 `None` 模拟"无 pyOpenSSL"，要求 pyftpdlib 仍导出
`TLS_FTPHandler` 且插件可导入；不成立一律响亮失败（防 shim 静默失效再去 CI 挂一次）。
另给测试期 pip 安装加了**按源重试 1 次**（本机实测三源曾同时 `ReadTimeoutError`，传输层抖动
不该让 build 挂）。

实测（本地 conan create）：
```
WARN: pip 安装失败（https://pypi.cnb.cool/…），同源重试 1 次
测试期依赖已安装（https://pypi.cnb.cool/…）
[upstream tests] shim 自检通过：无 pyOpenSSL 时 pyftpdlib 仍导出 TLS_FTPHandler（占位），pytest_localftpserver 可导入
[upstream tests] 62 passed, 13 skipped, 85 deselected
```

## 上游测试统计

| 项 | 值 |
|---|---|
| 测试位置 | 包内 `pooch/tests/`（9 个 `.py`） |
| 运行命令 | `python3 -m pytest pooch/tests/ -q -m 'not network'` |
| 实测结果 | **62 passed / 13 skipped / 85 deselected** |
| deselect 依据 | 上游自身标记 `@pytest.mark.network`（需真实外网；本环境 `ConnectTimeout`） |
| 修改上游用例 | **否**（`pooch/tests/` 原样使用） |

## 路径判定

未命中路径 C 四项条件（纯 Python、依赖已合入、无私有系统接口/工具链/汇编/闭源二进制、依赖链不庞大）
→ 属**路径 A 基础适配**；知识贡献见 `manifest.yaml` 的 `knowledge_gained`（离线子集以上游 marker 为准、
sdist 测试布局差异、运行期依赖复用优先级）。
