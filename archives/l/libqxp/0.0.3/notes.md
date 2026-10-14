# libqxp 0.0.3 原生适配记录

## 当前验证状态

2026-10-11 在 HarmonyOS PC aarch64、10.62.201.39:2222 完成原生 Conan create，退出码 0。W3 `libqxp-conan-20261011T0554Z-r5` 的 12 个阶段完整回读，release/postrelease PASS；不是比赛 worker CI 或发布结果。官方框架 finish、知识查重、Pre-PR 合同尚未执行，未创建 Issue/PR。

- 官方 CppUnit：11/11，主测试 9 条、格式识别 2 条，日志分别为 `OK (9)`、`OK (2)`。
- 独立 Conan 消费者：15 个断言，使用发布源码原有的 QXP 3.1 Windows 文档，实际导出 1 页 SVG；同时验证 HarmonyOS 身份和任务私有 TMPDIR 下的文件写入、读取、关闭、删除。
- 素材：`src/test/data/qxp31win.qxd`，3840 字节，未经修改；SHA-256 `1bbf407a05415bace9811a3ed7826aa17c50814c05dd913047fc0540c7c8b294`。
- 配方/消费者候选 SHA-256：`7142968128d4bc8ec9a3385bd67b522e377bd11f1e6fdbfe7f83e94dc15e1d8f`。
- 完整原生 Conan 日志 SHA-256：`79fde89191569cda9ca18c491c5175802cdd0b80d1790ffd68f7b98f85a981f9`，原始记录在工作树 `evidence/libqxp-conan-r5.log` 和配套结果/回执 JSON。

## 修复与边界

1. GNU config.guess 增加实际编译器验证的 aarch64 HarmonyOS tuple；config.sub 已接受 linux-ohos，不添加交叉编译 --host/--build。
2. librevenge 已发布静态包的 .la 包含 `libdir='//lib'`。按 E236 采用当前 build_folder 下无 .la 的私有归档目录；只复制指定的三个 .a，不修改或删除 provider cache。移除会抢先选择原始 .la 的全局 AutotoolsDeps 链接路径。
3. 链接闭包与头文件闭包分开处理：上游测试目标缺少 Boost/ICU 头文件路径，必须通过当前依赖图给实际 C++ 编译命令补齐。
4. 已发布 librevenge 依赖 boost/1.90.0.3 与 zlib/1.3.1；不能用最新精简 Boost 包替代完整头文件或擅自提升版本制造冲突。
5. libqxp 的公共头包含 librevenge 头文件。Conan 2 共享库消费者需要 requirements 显式 `transitive_headers=True, transitive_libs=True`，否则根库构建通过仍会在独立 test_package 报公共头缺失。

失败的 r1–r4 都保留真实终态并完成释放。r4 的 Conan 构建和测试已经通过，但冻结结果解析器的转义错误导致 W3 FAIL；不修改旧回执。r5 只修复解析器，先对实际成功日志及删去成功标记的反例做定向检查，再从干净源码完整重新验证，未拼接跨事务测试结果。
