# port-for

上游：<https://github.com/fizyk/port-for>，MIT，版本1.0.0，Python>=3.10。上游CLI和库API均提供，配置文件默认 `/etc/port-for.conf`；使用库的 `PortStore` 可显式传用户可写的私有文件。不因测试改HOME或写系统配置。

本项为GCW task9665的新适配A+B，平台分支 `feat/port-for-1.0.0`。生产仅一行排序修正，原端口包含、border和socket策略保持。生产声明Conan包运行时环境以使用 `port-for --help`；目标Conan构建、23项pytest和真实包消费者已通过，正式W3实际RC0。裸CLI version/help因未设置包模块路径失败，官方W3中的L2 skip保留。已实测固定缓存包生成的标准VirtualRunEnv：激活conanrun.sh后 `port-for --version` 输出1.0.0、`port-for --help` 输出usage，两者RC0，解释器和模块均来自Conan生产依赖及交付包。标准环境是使用条件；本次包仍仅在私有缓存，未远端发布。准确测试与限制见版本目录notes.md，知识草稿为 `knowledge/drafts/E9665-draft-9665.{kv,md}`。
