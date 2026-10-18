# POA 2.0-20060928 测试结果

实际环境：OHOS7.0.0.32 Beta/API26 AArch64 QEMU；Clang15、Conan2.29.1、CMake4.1.2。
官方OHOS6 profile只标包元数据，不证明OHOS6真机运行。

| 来源/场景 | 结果 |
|---|---:|
| 上游注册套件 | 0（无tests目录或check/test目标） |
| 上游README示例 | 1/1 |
| Debian下游回归 | 6/6 |
| 新增CLI回归 | 10/10 |
| 安装库API场景 | 8/8（一个真实CMake消费者内的八组检查） |

CLI17/17在构建和安装后各运行一次，不重复计数。官方Conan及W3通过；
W3 L1e破坏安装产物后消费者失败，确认真实包依赖。W3日志SHA-256：
b507c6b6a491843178df1f933b29db0eb4dd08b8db0d163fe3ef774c6bd2b859。
ConanVerifier G4未定位cache，其L2/L4/L5跳过；实际CLI/产物检查来自W3。
finish整体exit=1（全仓知识和旧就绪检查）；原始失败日志保留。
Conan cache save导出的真实W3包通过完整性校验；本地旧submit自检六项通过。
未取得远端CI、发布、合入或积分结果；完整日志本地留存。
