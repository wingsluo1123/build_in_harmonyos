# tinyprog

TinyFPGA USB bootloader programmer.

`tinyprog` is the command-line programmer for [TinyFPGA](https://tinyfpga.com/)
boards. It talks to the TinyFPGA USB bootloader over the SPI flash
security-register interface to read board metadata, list attached boards, and
flash a bitstream (`tinyprog --update <file>` / `--boot`).

Pure Python application — no C/C++ compilation step. Built with setuptools,
installed via pip (R49: private staging prefix, no shared-prefix writes).

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.0.23  | built  | Pure Python, setuptools; `pip --target` flat payload, console script `bin/tinyprog` |

## Runtime dependencies

From the Conan registry (declared in `conanfile.py` `requirements()`):

| Package | Version | Role |
|---------|---------|------|
| pyserial | 3.5 | 串口枚举与读写（`tinyprog.get_ports` / `SerialPort`） |
| six | 1.17.0 | 上游 Python 2/3 兼容层（`tinyprog` 全局 import） |

> 两者均以 `run=True` 声明。这不是可选优化：Conan 2 对 `python-require`
> 依赖默认 `run=False`，会让节点被标 `BINARY_SKIP`（无 `package_folder`、
> 无 runenv `PYTHONPATH`），消费者运行期 `import serial` 直接失败
> （知识条目 E14723）。

Filled from PyPI inside `build()`（制品仓暂无可用配方）:

| Package | Version | Role |
|---------|---------|------|
| intelhex | 2.3.0 | Intel HEX 解析（bitstream） |
| jsonmerge | 1.9.2 | 多页 security-register 元数据合并 |
| tqdm | 4.70.1 | 烧写进度条 |
| pyusb | 1.3.1 | USB 端口模式（`UsbPort`） |
| packaging | 26.3 | 版本比较 |

> `packaging` 在制品仓**有配方但不可消费**：`conan install --requires=packaging/26.3`
> 报 `Invalid: 'settings.os.version' value not defined`，声明为 `requires()`
> 会让每次 CI 全红，故改为 pip 装配（实测，非假设）。

## Usage

```bash
conan install --requires=tinyprog/1.0.23 -g VirtualRunEnv
source conanrun.sh
tinyprog --help
tinyprog -l              # 列出已连接的 TinyFPGA 开发板
tinyprog --update bitstream.bin
```

## Test status

上游 `programmer/README.md` 原文声明 *"Tests have been removed for now pending
refactoring of test methodology"*，`setup.py` 无 `test_suite`/`tests_require`——
**上游无 Python 测试套件可运行**。仓库 `tests/` 下仅有 24 个 Verilog RTL
testbench，仿真的是 bootloader **固件**，需 icarus-verilog 模拟器（本环境无）。

因此本适配自带消费者测试证据：`test_package/test_tinyprog.py` **12 个用例
（56 处断言，另有 1 处 `subTest` 参数化覆盖 7 个依赖模块的 import 检查）**，
其中 3 个为鸿蒙特有断言。完整 census 见 `1.0.23/test_package/MANIFEST.yml`。

## Platform

HarmonyOS PC / aarch64 (`settings.os=OHOS`, `settings.arch=armv8`,
`settings.compiler=clang 15`, `python 3.12`).
