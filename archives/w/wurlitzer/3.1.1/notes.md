# wurlitzer 3.1.1

本包是纯 Python 模块，通过 ctypes 调用目标平台 libc，捕获 C stdout 和 stderr。
使用 Conan 运行所用的 Python 解释器执行完整上游 test.py，共 16 个测试。
pytest 及其纯 Python 依赖已固定版本和 SHA256，只用于构建测试，不随安装产物发布。
安装内容为 wurlitzer.py、发行元数据和许可证。VirtualRunEnv 提供 PYTHONPATH。
消费者测试明确验证导入位置来自安装产物，并验证 C 输出捕获和线程恢复。
OpenDesk 完整 conan create 已通过。上游 16 个用例中 15 个通过，1 个按上游原有 skipif 跳过。
跳过 test_bufsize 的原因是 _get_max_pipe_size 仅在 Linux 提供数值，HarmonyOS 返回 None。
4 个消费者测试全部通过。未修改上游源码和测试。
pytest 使用当前构建目录下的独立 --basetemp，避免共享存储目录的所有者检查错误。
