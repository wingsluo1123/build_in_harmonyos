# snappy 1.3.1 原生测试报告

2026-10-13，HarmonyOS PC aarch64，10.62.201.39:2222，UID 20020084。
boot_id：0a624b09-f722-42ec-8bf1-a2ce7720a040；clang 15.0.4 / CMake 4.1.2 / Conan 2.29.1。

## 清单与结果

| 口径 | 数量 | 执行通过 |
| --- | ---: | ---: |
| 上游默认启用测试 | 25 | 25 |
| 上游原本禁用压力测试 | 1 | 未执行，不计入通过分母 |
| 新增安装包/鸿蒙消费者组 | 1 | 1 |

snappy_unittest.cc 共定义 26 个 TEST，其中 Snappy.DISABLED_MoreThan4GB 为上游明确默认禁用项，源码说明 CI constraints。配方保留该定义，不传 --gtest_also_run_disabled_tests，不新增过滤或跳过。默认启用 25/25（100%），已启用用例失败/跳过均 0。CTest 1 个容器中运行全部 25 项，不少报为 1。

保持上游全部断言和随归档提供的语料；使用已发布 GTest，Conan 图中的真实 RREV/PID/PREV 与冻结预期完全一致。BENCHMARKS 独立性能入口不计单元测试。

消费者使用安装后的 Snappy::snappy，19 处 CHECK；C/C++ API、二进制/UTF-8 数据、损坏头拒绝、输出容量不足后恢复、空输入往返，均通过。鸿蒙特有功能为私有 TMPDIR 压缩文件写入、读回、再解压并与原始数据比较，不是只检查平台宏或路径存在。

## 冻结事务证据

snappy-official-w3-20261013-r3，唯一 launch=1，12/12 PASS 回执，runner 已退出。官方 finish.step35_local_ci 自动生成 .ci-result.json，字节和日志哈希经独立回读校验。

原始 conan-create.log SHA-256：e5f2249878081cbc584397e4d96d3699f0017895c500940585b9d6ca0b6797c0。
终态标记：UPSTREAM_25_OF_25_PASS、CONSUMER_1_OF_1_PASS、OHOS_COMPRESSED_PRIVATE_FILE_CPP_DECODE_PASS。
L0/L1/L4/L5=pass；L2 因库无安装 bin/ 不适用。

GTest ref：gtest/1.17.0.2#c0ad35b749c5e9797ce120c8c8b57f89。
PID：21b17f8b2bc0e9511e276e3d57a23893067cefe5。
PREV：836923d784c48da57f9b7b2a51a0c7dc。

r1/r2 原始失败记录保留，最终结果只引用 r3。任务私有 global.conf 串行下载绕过 ThreadPool 同步原语依赖；不代表修改了比赛 worker 配置。静态选项、额外压力项及其他架构不在本报告通过声明中。当前未声明平台 Review/比赛 CI 或 release upload 已通过。
