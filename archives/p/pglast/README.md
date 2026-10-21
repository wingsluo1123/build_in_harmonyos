# pglast

pglast 将 PostgreSQL SQL 和 PL/pgSQL 解析为抽象语法树，提供 SQL 扫描、分句、指纹、格式化和 `pgpp` 命令行入口。

运行依赖为 Conan `python/3.12.9`，扩展保留 OHOS/AArch64/编译器包身份。构建工具使用已发布的 setuptools 84.0.0、Cython 3.3.0 与 pytest 9.1.1。软件内部携带 libpg_query，不新增运行库依赖。

鸿蒙适配采用完整的通用 popcount 实现，避免源包中冻结的 CPU 特性配置误选 SVE/不完整的 NEON 分支；扩展显式链接 libpython，并在构建与安装路径分别签名。`pgpp` 按自身位置解析 Python 载荷，可通过 Conan 运行环境消费。

类型检查工具存在平台边界：ty 的官方 Linux/musl AArch64 程序在本真机崩溃，因此对应原版测试在目标端跳过，并在 Windows 上另行验证；详见版本笔记和原始报告。本地通过不代表远端 CI、合并或制品发布完成。

官方来源：[源码仓库](https://github.com/lelit/pglast)、[PyPI 8.2](https://pypi.org/project/pglast/8.2/)。

2026-10-17独立平台机制验证：除安装消费者8项外，另测签名ELF写入保护及新签名inode替换后的实际解析1项；不将普通消费者重分类冒充平台机制。当前本地原生验证通过，正式W3及远端状态单列。
