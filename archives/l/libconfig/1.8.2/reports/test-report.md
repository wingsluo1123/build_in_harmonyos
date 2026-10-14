# libconfig 1.8.2 原生测试报告

日期：2026-10-13。设备：10.62.201.39:2222，currentUser；boot_id：0a624b09-f722-42ec-8bf1-a2ce7720a040，UID：20020084。
工具：clang 15.0.4 / CMake 4.1.2 / Conan 2.29.1，host/build 均为真实原生 OHOS armv8 档位。

## 测试口径

| 项目 | 声明 | 实跑通过 | 跳过 |
| --- | ---: | ---: | ---: |
| 上游默认受测配置 | 16 | 16 | 0 |
| 安装包消费者组 | 1 | 1 | 0 |

上游分母依据：tests/tests.c 的 16 个 TT_SUITE_TEST；CTest 的 1 个容器实际运行全部 16 个 tinytest，用例不能按容器数少报为 1。
消费者组含 36 处 CHECK 断言；断言数不等同于上游用例数。C/C++ 两个安装包消费者：include、UTF-8、整数宽度、错误解析、类型/缺失异常、文件往返。
鸿蒙特有功能验证：鸿蒙私有 TMPDIR 里生成子配置，通过被测库 include 解析并读写 UTF-8/整数配置；不是只检查目录或平台宏。

上游断言、预期结果与源码未修改，没有用消费者代替上游套件。非受测配置不计入通过：共享库 Release 为实际验证配置，静态库选项及其他架构/密码后端没有在本报告中声称验证。

## 证据与终态

- 独立事务：libconfig-official-w3-20261013-r4，唯一 launch=1。
- 12/12 事务回执通过，包括 release/postrelease；runner 已退出。
- 官方 finish 的 step35_local_ci 执行生成 .ci-result.json，原始结果独立回读、校验完整性；未手写或改写结果文件。
- 原始日志：本机任务目录 libconfig-official-w3-20261013-r4/collected/conan-create.log。
- 日志 SHA-256：e885175f1eb2e7a4e0e725177e35a225790da4f9ddb0f5ccd19fe00ac37eec41。
- 原始判据：L0=pass，L1=pass，L2=skip（库无安装 bin/），L4=pass（无补丁），L5=pass。

第一次缺少 readelf 的误报与旧事务仍保留；本报告仅使用以上新事务，不拼接旧测试证据。私有工具桥接不改变源码/配方输入。

## 流程状态边界

这是本地真机编译、完整上游测试、安装包消费者及产物检查 PASS。聚合 finish 尚未执行，Issue/PR 未创建，平台 AI Review、比赛 worker CI 和 release upload 未执行。不声明发布成功。
