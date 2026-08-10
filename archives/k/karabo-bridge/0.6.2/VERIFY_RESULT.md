# VERIFY_RESULT — karabo-bridge 0.6.2

## 编译状态: ✅ 成功

- **软件**: karabo-bridge 0.6.2
- **构建系统**: setuptools (纯 Python 包, pip install . --no-deps)
- **许可证**: BSD-3-Clause
- **源码**: PyPI sdist `karabo_bridge-0.6.2.tar.gz`
  (上游 GitHub tag `v0.6.2` 返回 404, 使用 PyPI sdist 作为源码)
- **SHA256**: `97d6c755a765708f2c25679d652b9b585fc57800f97a09b7a27211f9ba99c40b`

---

## 本地编译证据 (pip install / wheel 构建 / site-packages 产出)

### 1. pip install 本地安装 (日志行 77, 86-93)

```
Line 77: karabo-bridge/0.6.2: RUN: /storage/Users/currentUser/usr/local/bin/python3 -m pip install . --prefix=.../package --no-deps
Line 86: Building wheels for collected packages: karabo_bridge
Line 87:   Building wheel for karabo_bridge (pyproject.toml): started
Line 88:   Building wheel for karabo_bridge (pyproject.toml): finished with status 'done'
Line 89:   Created wheel for karabo_bridge: filename=karabo_bridge-0.6.2-py3-none-any.whl size=23657
Line 91: Successfully built karabo_bridge
Line 93: Successfully installed karabo_bridge-0.6.2
```

**关键证据**:
- `pip install . --prefix=... --no-deps`: 本地源码 pip 安装
- `Building wheel for karabo_bridge (pyproject.toml)`: wheel 从本地源码构建
- `Created wheel ... karabo_bridge-0.6.2-py3-none-any.whl`: wheel 产出
- `Successfully installed karabo_bridge-0.6.2`: 安装成功
- `--no-deps`: 禁止从远程拉取 Python 依赖

### 2. site-packages 模块文件产出 (日志行 253-270)

```
Line 253: site-packages location: .../lib/python3.12/site-packages
Line 256: .../site-packages/karabo_bridge/__init__.py
Line 257: .../site-packages/karabo_bridge/cli/__init__.py
Line 258: .../site-packages/karabo_bridge/cli/glimpse.py
Line 259: .../site-packages/karabo_bridge/cli/monitor.py
Line 260: .../site-packages/karabo_bridge/cli/simulation.py
Line 261: .../site-packages/karabo_bridge/client.py
Line 262: .../site-packages/karabo_bridge/serializer.py
Line 263: .../site-packages/karabo_bridge/server.py
Line 264: .../site-packages/karabo_bridge/simulation.py
Line 270: Total .py files in karabo_bridge/: 18
```

**关键证据**: 18 个 .py 文件正确安装到 `site-packages/karabo_bridge/`

### 3. 无远程预编译包下载

日志中**未出现** `Download (ohpcd)` 或 `Retrieving package ... from remote` 的预编译包下载。
`conan create` 显示 `Building from source` → `pip install .` 本地构建。

---

## conan create 结果: ✅ 成功

- **退出码**: 0 (日志行 159)
- **Full package reference**: `karabo-bridge/0.6.2#b49360701f7ab773027e392cdc58f70c:199b501a334fc7fce69568b5806901bfdcee316a#8c1f84560afc45d8ab985963ac3f8c25`
- **Package folder**: `/storage/Users/currentUser/.conan2/p/b/karabc353f42ed0d11/p`

### conan list 缓存证明 (日志行 248-250)

```
Local Cache
  karabo-bridge
    karabo-bridge/0.6.2
```

---

## test_package 执行结果

### conan test 结果: ✅ 成功

- **退出码**: 0 (日志行 244)

### 测试用例通过情况

| # | 测试名称 | 结果 |
|---|---------|------|
| 1 | Module import (`import karabo_bridge`) | ✅ PASS |
| 2 | Version assertion (`__version__ == "0.6.2"`) | ✅ PASS |
| 3 | Client class existence (`from karabo_bridge import Client`) | ✅ PASS |
| 4 | ServerInThread/Sender class existence | ✅ PASS |
| 5 | serialize/deserialize round-trip (模拟桥接管道数据接收验证) | ✅ PASS |

### 通过率: **5/5 = 100%**

---

## 失败分析: 无

所有 5 个 smoke test 均通过, 无失败用例。

---

## 完整日志路径

```
/storage/Users/currentUser/Desktop/build_in_harmonyos/.karabo-verify.log
```

日志共 278 行, 包含:
- STEP 1: conan create 完整输出 (pip install + wheel 构建 + site-packages 产出)
- STEP 2: conan test test_package 完整输出 (5 smoke test 结果)
- STEP 3: conan list 缓存证明
- STEP 4: site-packages 产物文件列表 (18 .py files)

---

## 总结

| 项目 | 结果 |
|------|------|
| 编译是否成功 | ✅ 成功 |
| 是否为本地编译 (非远程下载) | ✅ 是 (pip install . --no-deps 本地源码构建) |
| 测试通过率 | ✅ 100% (5/5) |
| 是否需要打回重做 | ❌ 不需要 |
