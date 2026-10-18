# POA 2.0-20060928

任务9621；账号A1038；分支 feat/poa-2.0-20060928。
依赖仅系统C库/libm，无Conan三方依赖。官方main基线：
2446216757be20359617ac140c2e103fac6398f0。

三份官方 refresh-patch 补丁：CMake完整构建/安装、CLI帮助/分发版本、
black_flag全局变量extern。静态库保留上游LIBOBJECTS并提供公开评分回调；
USE_WEIGHTED_LINKS/USE_PROJECT_HEADER由Conan消费者目标传播。

上游注册测试0；README示例1；Debian下游6；新增CLI10；库API场景8。
CLI17/17在构建及安装后各运行一次，API8/8。共识测试使用12残基，满足
上游至少10残基的条件；未删减既有测试或放宽断言。

实际OHOS7.0.0.32 Beta/API26 AArch64 QEMU；官方OHOS6 profile仅为包元数据。
W3及产物破坏反向测试通过。finish整体exit=1：全仓知识校验及旧就绪检查。
旧submit所需本地产物由Conan cache save导出真实W3包满足，压缩包不入Git。
默认PF9误拒软件级README/commands.json；独立审核批准仅对此使用命令级例外，
保留R38/PF8要求的commands.json，不修改框架或关闭远端CI。

**编译结束；最终状态：built（未上传，非远端CI/发布/合入/积分验收）。**
