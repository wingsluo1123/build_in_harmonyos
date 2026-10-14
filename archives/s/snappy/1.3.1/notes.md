# snappy 1.3.1 适配笔记

分支 feat/snappy-1.3.1，任务 #15137；团队 诶，云朵。日期 2026-10-13。

## 源码和配置

官方 tag archive 不包含 googletest git submodule。exports_sources 带一个只补空子项目的 gtest-subproject/CMakeLists.txt，通过 find_package(GTest) 与自有 INTERFACE 转发目标提供 gtest/gmock/gmock_main；上游 set_property 能作用于这些自有目标，不修改 Conan 导入依赖，也不使用不能 set_property 的 ALIAS。不存在覆盖已有 vendor CMakeLists 的行为；若上游将来打包该文件，配方 fail closed 要求重评估。

GTest 作为 test_requires("gtest/1.17.0.2")，W0 --build=never 已解析并下载真实 OHOS 预编译包。保持 SNAPPY_BUILD_TESTS=ON；独立性能 benchmarks 关闭，不将它们当单元测试。比较编解码器 z/lzo/lz4 的测试工具可选检测关闭，产品无运行依赖；完整 Snappy 默认单元套件仍运行。

OHOS 使用公开 CMake SONAME 标志，避免版本软链接，构建和安装后 ELF 均签名。仅对平台包装器链接参数在 -c 下造成的 unused-command-line-argument 降级，保留其他 -Werror。

## 失败和恢复

r1 首个失败是依赖二进制下载器创建 ThreadPool 所需 SemLock 得到 ENOSPC，不是缺失依赖或产品编译问题。任务私有 global.conf 使用 core.download:parallel=0；不改用户全局配置或平台 CI，不在库配方修改 Conan 内部实现。

r2 上游和消费者通过，但 W3 控制器的依赖回读器未接受 Download (ohpcd) 后缀。旧 FAIL 保留，仅修复新事务中的后缀解析，错误 PREV 的定向检查仍拒绝。

r3 完整独立验证 PASS，12/12 回执和精确回读完成，任务 runner 已退出；各轮日志不拼接。

## 测试边界

源码定义 26 项：默认启用 25 项全部通过；Snappy.DISABLED_MoreThan4GB 从上游开始就禁用（构造 2^32-1 字节输入及多个副本）。未修改该测试、未启用该额外压力测试、未将它算作通过。声明分母为默认启用清单 25，不能写成 26/26。

安装包消费者 19 处 CHECK：C/C++ 压缩/解压，损坏头、空输入、输出容量不足后重试；在鸿蒙私有 TMPDIR 写入真实压缩数据后读回并通过 Snappy 解压验证。没有用消费者替代上游套件。

详见 reports/test-report.md。知识草稿仅申报新增的下载 ThreadPool/SemLock/core 配置边界；共享库/签名/CMake 已有知识正常复用。比赛 worker CI 和平台 Review 状态以真实 PR 回读为准，不声称已发布。
---

**编译结束**: 2026-10-13 16:22
**最终状态**: built
