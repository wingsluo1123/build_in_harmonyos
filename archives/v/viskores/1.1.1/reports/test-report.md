# Viskores 1.1.1 验证台账

设备：HarmonyOS 6.1 aarch64 / HongMeng Kernel 1.12.0。
工具：OHOS SDK Clang 15、Conan 2.29.1、CMake 4.4.3、Ninja 1.13.2。
输入绑定与实际构建信息见 `native-result.json`，完整过程见 [native-create-output.txt](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/native-create-output.txt)。

| 集合及单位 | 发现 | 执行 | PASS | FAIL | SKIP | 通过率 |
|---|---:|---:|---:|---:|---:|---|
| 上游 CTest 注册项 | 371 | 371 | 371 | 0 | 0 | 371/371（100%） |
| 消费者 CTest 注册项（1 个 C++ 程序） | 1 | 1 | 1 | 0 | 0 | 1/1（100%） |
| 消费者程序内部检查（单列，不加入注册项合计） | 13 | 13 | 13 | 0 | 0 | 13/13（100%） |

注册与执行名称一一对应，安装 fixture/准备项保留在分母中；没有额外相加内部断言。
全量 build() 内执行，不以消费者替代上游测试。conan create RC=0，
完整本地验证耗时 3175 秒。当前无失败或跳过条目需要例外归因。
26/26 安装共享库保持原始链接字节；隐藏原包后的新前缀消费者复验 1/1 CTest、13/13 检查，
不重复增加注册项。修复前完整基线为 366/371，失败台账见 [完整基线](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/baseline)。

官方 W3 RC=1；真实失败位置见 [完整W3失败日志](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/w3-local-ci-output.txt)。
同步主分支热修复后，G0/KC已放行；第二次 W3 在第755步启动 SDK clang++ 执行链接时
由 shell 报 Out of memory、RC126，尚未进入本轮 CTest。其后无关环境启动命令也 fork 失败，
SSH exec 请求亦失败。记录这一实际进程资源中断，不把它改写成源码诊断或成功。
连接恢复后已取回完整正向及失败日志；同一失败目标以原对象单独链接复验 RC0，
仅说明该目标可链接，不将失败的完整 W3 改写为通过。
没有 .ci-result.json，不宣称 W3 或远端 CI 已通过。
本表成功数字来自最终配方的独立原生 conan create，不能替代官方门禁结果。

上游默认关闭的可选后端未纳入本配置的执行覆盖；不宣称 CUDA/Kokkos/MPI/TBB/OpenMP
或 ANARI/HDF5 能力已经适配。源文件数、模板展开次数和重复运行不当作新增用例。

独立 zlib 对照证据只用于验证并发控制知识，不计入 Viskores 的 371 或消费者 13 个检查。
