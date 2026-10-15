# sqlparse 0.5.5

## 软件与环境

sqlparse 是纯 Python SQL 解析和格式化库，需要 Python 3.8 或更高版本。
本配方将 Python 模块安装到包内 lib/python，通过 Conan 环境提供 PYTHONPATH。
消费者需要已有 Python 解释器。命令行可使用 python3 -m sqlparse。

## 源码

使用 PyPI 官方 0.5.5 源码包，SHA256 已在服务器复核。
上游地址为 https://github.com/andialbrecht/sqlparse。
没有修改上游源码或测试。

## 验证

build() 先收集 tests/ 中全部 pytest 用例，再运行完整测试套件。
消费者测试使用包内模块，验证模块来源、解析、拆分、格式化和命令行。
上游测试和消费者测试分别统计，不合并冒充上游结果。
2026-10-10 的 OpenDesk 验证使用 Python 3.12.9 和 pytest 9.1.1。
官方收集 482 个用例，479 passed、2 xfailed、1 xpassed，没有普通失败或错误。
消费者测试 5 个全部通过。
预期失败标记来自上游，未删改或跳过任何用例。
pytest 默认临时目录的所有者检查在 HarmonyOS 失败，因此使用构建目录内的 --basetemp。

## CI 测试依赖修复

2026-10-14 检查 PR 15258 的 CI 91325 和 91295，源码下载成功。
实际失败是 /data/service/hnp/bin/python3 没有 pytest。日志末尾的 429 提示不能说明本次失败原因。
配方现在通过带 SHA256 的源码包提供 pytest 8.3.5 及其依赖。
依赖只解压到本包构建目录，通过临时 PYTHONPATH 使用，不要求 pip，也不修改共享 Python 环境。
Python 3.8 至 3.10 另外提供 exceptiongroup 和 tomli。
关闭外部 pytest 插件自动加载，保留完整官方测试。
服务器独立 Python 3.12 环境中预先没有 pytest，Conan 完整构建成功。
收集 482 个用例，479 passed、2 xfailed、1 xpassed，消费者测试 5 个通过。
该结果是服务器验证。修复后的 OpenDesk 验证仍待执行。

## 已知限制

该库不验证 SQL 语法，也不连接数据库。
Conan 使用设备已有 Python 解释器，测试依赖只存在于本包构建目录。
