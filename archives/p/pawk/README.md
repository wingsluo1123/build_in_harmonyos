# PAWK

上游：https://github.com/alecthomas/pawk 。0.8.1为发行包/tag版本，原模块和pyproject内部仍为0.8.0，保留该来源差异。

配方直接安装唯一模块与 `pawk:main` wrapper，以 Conan Python 3.12.9 为运行依赖，不调用 Poetry，不安装开发格式化工具。

修复仅涉及 `-F/-O/-L` 对已Unicode字符串再次解码的三处代码。PAWK9336-H1-001 已取得 OpenHarmony 原生补丁、Conan create、九个未改原函数9/9及一个安装包消费者1/1通过；消费者4场景/4次CLI调用/12条功能assert与2条身份assert单列。原函数直接调用，不称pytest。

旧完整finish rc1、G0失败及旧W3基线拦截历史保留；G0工具固定使用configure/make，本sdist没有这些入口，官方将该检查列为非阻塞。后续orrkri-9336-pawk-W3-002已取得固定17文件的完整W3 rc0，内部Conan create/九原函数9/9/消费者1/1通过；L0/L1/L4/L5 PASS，L2为version/help失败后的非阻塞SKIP，不写全分项通过。独审、完整AtomCode、官方CI与有效提审仍待证，整体NOT_READY。详细统计和适用边界见0.8.1/notes.md。
