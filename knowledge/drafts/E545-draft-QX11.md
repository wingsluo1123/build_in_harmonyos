# Automake 测试头闭包与 Libtool 搜索路径分离

## 触发特征与根因

根库编译成功，make check 在包含库私有头时却缺 boost/cstdint.hpp。提供者实际有头、configure 已检查成功，不是缺依赖。根库 AM_CXXFLAGS 消费 BOOST_CFLAGS、ICU_CFLAGS，测试子目录独立定义 flags 却漏掉二者。configure 的变量不能补齐未消费变量的目标命令。

链接已通过 E236 的私有 .la-free 目录隔离陈旧 Libtool 元数据。为补头而恢复同时注入所有 -I/-L 的通用依赖环境，可能重新选中原 provider .la。编译头目录与链接搜索目录是两个独立闭包。

## 可复用决策步骤

1. 证明缺失头存在于当前发布提供者，排除裁剪版或错版本。
2. 对比库与测试 Makefile.am 及失败目标的实际编译命令；configure 成功不是测试闭包完整的证据。
3. 用 Conan AutotoolsToolchain extra_cxxflags 仅加入真实依赖 include 目录，正确引用路径，不依赖未定义环境变量。
4. 保持逐依赖 scoped LIBS 和私有 .la-free 目录，不恢复全局 provider -L，不修改共享缓存。
5. 全量 make check 后再测安装消费者；公共头 transitive_headers 是另一个契约，不能代替测试私有头修复。

## 本次证据

libqxp 发布包 src/lib/Makefile.am 含 BOOST_CFLAGS/ICU_CFLAGS，src/test/Makefile.am 缺二者却包含 src/lib 私有头。r2 首个失败为 libqxp_utils.h:21:10 缺 boost/cstdint.hpp。纯编译头闭包修复后 r3 根包和 CppUnit 9+2 通过，再由消费者发现公共头传播缺失；两层分别修复后 r5 完整通过。

当前正式 libqxp-finish-20261011-r1 从干净源码完成11/11上游用例及消费者1程序15断言、1 SVG页面，12阶段和release/postrelease完整。官方W3日志SHA-256 db21238f3fd19d54841e4a0527a28ae39911d9f4765c2dc3faec649c83516818，ci-result integrity f7bf5c880aa5d888。仅本地真机CI PASS，finish总RC1为已分离的旧后置readiness/staging。

- 原生运行：`libqxp-conan-20261011T0554Z-r5`。
- 端点：`10.62.201.39:2222`，HarmonyOS PC aarch64。
- 候选 SHA-256：`7142968128d4bc8ec9a3385bd67b522e377bd11f1e6fdbfe7f83e94dc15e1d8f`。
- 日志 SHA-256：`79fde89191569cda9ca18c491c5175802cdd0b80d1790ffd68f7b98f85a981f9`。
- 原始日志和回执保存在工作树 `evidence/libqxp-conan-r5.*`；不是比赛 worker CI。

## 与已有知识的增量和安全边界

已检索 graph/drafts/doc/operations。E236 解释 .la 隔离；DRAFT-libtool-la-cross-package-and-private-header-deps 解释私有依赖声明/configure；E6403 处理无 TESTS 的 check-only 示例；E480、E616 连带发现6及 shared-pkgconfig-requires-drop 解释公共 traits。本条新增保留 scoped Libtool 隔离时，独立测试子目录漏用依赖变量的纯编译闭包补齐，不重复申报公共 traits。

适用于真正注册 TESTS 且包含私有依赖头的 Automake 测试。提供者缺文件应修提供者或版本；没有陈旧 .la 风险不必照搬隔离；仅消费者公共头缺失直接处理 traits。不得删测试、放宽断言、硬编码消费者缓存路径或删除共享 .la。


## 2026-10-13 CI 反例与修复增量

A checkout-pr message saying main conflict can actually originate from missing binary patch data and an unsupported patch fallback option. Identify the first low-level Git apply error; encode and hash-restore the unchanged consumer sample rather than rebasing or deleting its test.

Separate patch-format loss from a true merge conflict and from the existing complete CppUnit inventory topic. The eleven original upstream cases and the same parser consumer remain; the decoded original fixture is never counted as an additional test.

验证：新事务 `libqxp-ci-repair-w3-20261013-r1` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `903166c1aa1c609b26b297f4ad11625925ab1d1e6869f56f9943a2d1dc339513`。上游声明 11 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。


## 2026-10-14 CI 反例与修复增量

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

Current worker logs provide the independent second-failure boundary after the earlier checkout/fixture repair: successful source retrieval and dependency installation are not proof that configure generated usable config files. Use both-branch source reconciliation, timestamp-preserving production-helper tests and complete native recipe/tests; do not treat a missing-curl predownload warning as the cause when source() already succeeded. This extends the existing evidence/transport topic with a causal validation boundary, not a new generic umask claim.

验证：新事务 `libqxp-ci-repair-w3-20261013-r101` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `1cce135bf987be9821bfc280da8f1770c88ea7801d61a153a0bb87e55decaf3f`。上游声明 11 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。
