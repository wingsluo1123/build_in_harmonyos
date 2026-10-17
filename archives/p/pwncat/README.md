# pwncat

`pwncat` 是 netcat 的增强替代品：一个**纯 Python 单文件脚本**（`bin/pwncat`，仅用标准库），在 netcat 的连接/监听/端口扫描基础上增加防火墙与 IDS/IPS 规避、绑定/反向 shell、端口转发，并提供 PSE（Pwncat Scripting Engine）——用 Python 的 `-c`/`-e` 方式在连接两端注入自定义逻辑。

## 功能概述

- **模式**：connect（`host port`）、listen（`-l`）、zero-I/O / 端口扫描（`-z`，含 `--banner` 版本探测）、本地转发（`-L [addr:]port`）、远程转发（`-R addr:port`）
- **反向/绑定 shell**：`-e <cmd>`、`--self-inject cmd:host:port[s]`（支持列表/区间/递增端口写法）
- **规避**：`-C/--crlf` 行尾转换、`--ping-intvl`/`--ping-word` 周期载荷、`-4`/`-6` 地址族选择、`-n/--nodns`
- **连接策略**：`--keep-open`（服务端重接受）、`--reconn`/`--reconn-wait`/`--reconn-robin`（客户端重连与轮转）
- **PSE**：`-c <code>` / `-e <file.py>` 在收发通路上挂 Python transform，配合 `__pwncat_*` 魔术变量
- 形态：单一可执行脚本，`setup.py` 只声明 `scripts=["bin/pwncat"]` 与 `install_requires=[]`

## OHOS 适配

- **纯 Python，无编译，无补丁**：`bin/pwncat` 不含任何平台特定调用（不调用 `ps`/`/proc`），在 OHOS aarch64 运行时（Python 3.12）上原样运行。配方按 `package_type = application` 打包：`source()` 取官方 PyPI sdist，`build()` 校验 shebang 并实跑 `--version`/`--help`，`package()` 把脚本安装为 `bin/pwncat`（保留上游 `#!/usr/bin/env python3` shebang，`chmod 755`）。**没有 `patches/` 目录。**
- **测试期 shim（不进入包）**：上游 bash 集成套件在 OHOS 上需要两处环境适配，均属测试侧、与产物无关：
  1. **`ps`**：OHOS 的 toybox `ps` 拒绝 BSD 风格 `auxw`（且 `-A` 会把 CMD 截断为进程名），而上游用 `ps auxw | grep ... | awk '{print $2}'` 轮询进程；用一个 `PATH` 前置的 `ps` shim 把 `auxw`/`aux` 归一为 `-ef`。
  2. **`localhost` 的 IPv6 别名**：运行时 `/etc/hosts` 只有 `::1 ip6-localhost ip6-loopback`，缺 `::1 localhost`，于是 `getaddrinfo("localhost", ..., AF_INET6)` 报 `gaierror`（字面量 `::1` 正常）。上游 CI 本身就是用 `sudo tee /etc/hosts` 补这一行；OHOS 上 `/etc/hosts` 不可写、无 `sudo`/`unshare`，故用 `PYTHONPATH` 注入 `sitecustomize.py` 在解析层补别名（并尊重 `AI_NUMERICHOST`，以免改变 `--nodns` 语义）。
- **已知差异**：
  - 上游 4 个用例**硬编码 `www.google.com:80`**（`01/200`、`01/201`、`10/000`、`11/000`），需要出网访问 google，本环境不可达；其机制已用本地 HTTP 服务替代验证（见 `0.1.2/reports/test-report.md`）。
  - 上游文件传输用例用 `-vvvv` 时 pwncat 会把载荷 TRACE 到 stderr，而 OHOS 的 `/bin/ls`（toybox 多元二进制）内嵌字面量 `ERROR :Range for -f is 1 to %ld`，会触发上游 harness 的 `grep ERROR` 误报；传输本体经校验逐字节一致。
  - `30-cnc---self_inject` 的 5 个变体中 `000`/`003` 通过；`001`/`002`/`004` 在使用 `revshell.py`（逐字节发送 + banner/suffix）作反向 shell 替身时于 CnC 握手处失败（pwncat 日志 `Unable to create tmpfile`）。同一 `--self-inject` 全链路在 `000` 上通过，且 `bin/pwncat` 无硬编码 `/tmp`，故非平台可移植性缺陷。
  - `python3.12` 下上游 `threading.Thread.getName()` 会打印一条 `DeprecationWarning`（纯提示，不影响功能）。
  - 上游 72 个集成脚本在 OHOS aarch64 上实测 **63/72 通过、506/515 已执行轮次通过**；上述 9 个失败全部为环境/测试替身原因。
- **不可运行的上游用例**：6 个 `tests/smoke/*`（docker-compose）与 `make code-*`（docker 镜像做 lint/black/mypy）需要容器运行时；OHOS aarch64 无 `docker`/`docker-compose`/`podman`/`nerdctl`，且冒烟镜像为 `python:*-alpine`（x86_64/glibc）。

## 依赖关系

| 类型 | 依赖 | 说明 |
|------|------|------|
| 构建 | 无 | 无 setuptools/pip 构建后端，脚本原样安装 |
| 运行 | 无 | `install_requires=[]`；仅需 Python 3 解释器 |

## 参考资料

- 上游仓库：https://github.com/cytopia/pwncat
- 官网 / 文档：https://pwncat.org/ ・ https://docs.pwncat.org/
- PyPI：https://pypi.org/project/pwncat/
