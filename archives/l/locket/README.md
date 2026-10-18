# locket

locket 1.0.0 提供基于文件路径的 Python 锁。同一路径的锁在线程和进程之间互斥，支持阻塞等待、超时和上下文管理器。

- 官方项目：[mwilliamson/locket.py](https://github.com/mwilliamson/locket.py)
- 许可证：BSD-2-Clause。
- Conan 引用：`locket/1.0.0`；配方接受 Linux 和 OHOS，实测为 HarmonyOS PC AArch64 / Python 3.12.9。
- 运行依赖：Python 标准库 `fcntl`、`threading` 等，无第三方运行依赖。
- 包内容：`lib/python/site-packages/locket/__init__.py` 和 `licenses/LICENSE`。
- 验证：原版上游 16 项测试和消费者 10 项测试均已在真机通过。远端 PR CI 和发布状态另行核验。
- 上游全部测试和断言保留；仅补充测试子进程 ready/Acquired 同步，避免固定 100 ms 等待在高负载下产生误报，生产模块无修改。

消费者声明 `requires("locket/1.0.0", headers=False, libs=False, run=True)`，生成并使用 `VirtualRunEnv`，Python 即可从传播的 `PYTHONPATH` 导入模块：

```python
import locket

with locket.lock_file("/writable/path/task.lock", timeout=5):
    # 保护同一文件路径对应的共享资源。
    pass
```

锁文件父目录必须可写；锁不支持重入，fork 后行为未定义。该版本保留上游实现，不承诺跨不同路径别名、网络文件系统或所有 Python 版本的语义。
