# isbnlib

isbnlib 是用于 ISBN 校验、转换、分段、书目格式化与在线元数据查询的纯 Python 库。

3.10.14 的 Conan 构建需 Python 3.10+（pytest 9 工具要求）；标准库迁移兼容 Python 3.8+ 返回形式但未实机验证旧版本；本次实测 HarmonyOS PC AArch64 / Python 3.12.9。无 C/C++ 编译步骤。包内包含完整 Python 模块与 ISBN 范围数据，不安装上游测试或开发工具。

适配点为标准库入口点发现、spawn 可导入工作函数及上游测试临时目录隔离。测试工具 pytest/9.1.1 由 Conan 提供。默认执行 55 项非网络上游测试，18 项在线测试另行实测和披露，消费者 15 项包含真实插件元数据及独立进程流程。网络测试可用 `-o isbnlib/*:network_tests=True` 启用。

来源：[官方仓库](https://github.com/xlcnd/isbnlib)。状态为本地 built，远端 CI、审核和发布分别核验。
