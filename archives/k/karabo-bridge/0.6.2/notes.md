# karabo-bridge 0.6.2 适配笔记

## 软件简介

karabo-bridge 是 European XFEL 开发的 Python 3 工具包，用于从 Karabo 控制系统
请求数据。它通过 ZeroMQ (pyzmq) 进行数据传输，使用 msgpack (配合 msgpack-numpy)
进行序列化。主要组件：

- `Client`: 客户端，通过 REQ/SUB socket 从 Karabo bridge server 请求数据
- `ServerInThread` / `Sender`: 服务端，通过 REP/PUB/PUSH socket 发送数据
- `serialize` / `deserialize`: 数据序列化/反序列化
- `SimServer` / `start_gen`: 模拟服务器，用于生成假检测器数据

## 编译环境

- 构建系统: setuptools（纯 Python 包，无 C 扩展）
- 编译日期: 2026-08-10
- 编译器: 无（纯 Python，无需 C 扩展编译）
- 状态: built

## 依赖

### Python 运行时依赖 (setup.py install_requires)

- `msgpack >= 0.5.4`: 二进制序列化
- `msgpack-numpy`: msgpack 的 numpy 扩展
- `numpy`: 数值计算
- `pyzmq >= 17.0.0`: ZeroMQ Python 绑定

### 测试依赖 (extras_require['test'])

- `pytest`, `pytest-cov`: 测试框架
- `h5py`: HDF5 文件读取（测试用）
- `testpath`: 文件系统测试辅助

## 适配说明

### 源码选择

上游 GitHub tag `v0.6.2` 返回 404（tag 不存在），tag `0.6.2` 也不可用。
使用 PyPI sdist `karabo_bridge-0.6.2.tar.gz` 作为源码。

### 构建方式

纯 Python 包，使用 `pip install . --prefix=... --no-deps` 进行本地安装。
`--no-deps` 确保不从远程拉取依赖（msgpack/numpy/pyzmq 等由系统或 Conan 管理）。

### R32 平台兼容

`validate()` 中使用 `self.settings.os not in ("Linux", "OHOS")` 判断平台兼容性。

## 质量门禁

- conan create: ✅ 本地源码 pip install 构建成功
- test_package: ✅ 5/5 smoke tests 通过 (模块导入/版本断言/Client类/Sender类/serialize round-trip)
- 远程下载: ✅ 无远程预编译包下载 (pip install . --no-deps 纯本地构建)
