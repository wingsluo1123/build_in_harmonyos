# Viskores 1.1.1：HarmonyOS PC 原生验证

源码固定为官方 `v1.1.1`（`1d38698019f56ef2636d7283f4cac9bc2ee6c819`），
测试数据取 git 子模块精确提交 `eba37893ced2942f0fef8a3612207c92afbaea3b`。
两个归档均用 conandata.yml SHA256 验证。主 URL 保持单值 GitHub 格式以接受 CI 镜像注入，
设备下载失败时可回退到字节相同的官方 codeload；不修改配方中的预期哈希。

使用默认 Serial CPU 后端、完整标准库与软件渲染，无第三方 Conan 运行依赖。
关闭项均为上游默认的可选后端或功能：CUDA/Kokkos/MPI/TBB/OpenMP/ANARI/HDF5。
不把未交付的 GPU 或多线程后端作为已完成的挑战证据。

## 实际适配

1. Conan 原生检测得到 `HarmonyOS`，CMake 缺少相应平台模块；使用 E092/E1655 的
   Linux CMake 平台规则，SDK 编译器、头文件、链接 ABI 保持 OHOS。
2. Conan helper 的 `-j4 -- -j20` 覆盖资源上限；显式运行
   `cmake --build . --parallel 4`，消费者为 1。独立 zlib 四组对照及原文见 `reports/evidence.md`。
3. 保留原始 ViskoresConfig.cmake 及完整命名目标图，Conan 设置
   `cmake_find_mode=none`，而非用不完整的单一 target 替代所有过滤器和 DIY 组件。
4. 全部上游测试在 build() 中执行，发现清单与 JUnit 名称集合严格核对，零测试报错。
   唯一源码补丁修正 UnitTestMath 的 Float32 固定向量参考值及 Kahan 二次式中间系数；
   精确分数计算、硬件 FMA 和独立原始语料支撑两项修正，保留 `dist < 2`/`dist < 3`
   及 FMA guard，库算法与其他测试保持原样。证据见 `reports/math-oracle.md`。
5. `cmake_layout(src_folder="src")` 让源码与构建目录互为兄弟，防止上游 LicenseStatement
   递归把构建生成文件当作源码。原许可证检查完全保留。
6. 复用 E504/E077：相同路径仅换回原始链接字节，安装 smoke 从 RC127 变为 RC0。
   让首次链接即采用最终 `$ORIGIN/../lib`（模块另加 `$ORIGIN`），设置
   `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`，防止安装时改写 ELF。
   本次实际包的 26 个真实共享库与 build/lib 的 SHA256 一一相同，见
   [最终包及重定位原始记录](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/installed-result.json)。签名段存在不作为“已直接验证签名失效”的证据。

## 上游清点与结果

源码包含 771 个 C/C++ 源文件，其中 324 个 UnitTest 源文件。源文件数不等于用例数。
当前配置 CTest 清点与执行均为 371 个注册项，371 PASS、0 FAIL、0 SKIP。
CTest 项内可能包含多个类型/数据组合与断言；这些内部检查不重复相加。

| 分类 | 注册项 |
|---|---:|
| UnitTest | 295 |
| RenderTest | 10 |
| GuideExample | 53 |
| QuickStart | 1 |
| 系统信息/许可证 | 2 |
| 安装 fixture | 3 |
| 安装消费者及准备项 | 7 |
| 合计 | 371 |

原生 conan create RC=0，完整本地验证耗时 3175 秒。
安装包消费者为 1 个 CTest/C++ 程序、13 个检查，CTest 1/1、检查 13/13，0 跳过；包括排序/归约/扫描、
自定义 worklet、补偿乘积差、Kahan 二次式、Wavelet 网格、等值面、阈值提取、VTK 往返、缺失字段负例、
64×64 光线追踪有限非空像素读取与 PNG 编码头。VTK 检查拓扑数量、字段存在性、
坐标边界（1e-4）与标量范围（1e-3），不宣称逐点比较全部内容；
缺字段负例核对 ErrorBadValue 与字段名，PNG 检查限定八字节签名。
复制实际 Conan 包到新前缀后，临时隐藏本任务原包，在新目录重新配置、编译、执行消费者，
仍为 CTest 1/1、检查 13/13。它是同一消费者的重定位复验，不增加逻辑用例数。

## 基线与流水线状态

修复前已完整执行全部 371 项：366 PASS、5 FAIL、0 SKIP。
失败项为 LicenseStatement、UnitTestMathSERIAL 及三个安装 smoke，分别通过目录布局、
两处有独立数学依据的测试数据修正、安装 ELF 字节保持解决。
原始 JUnit、失败输出和构建日志保留在[固定历史提交](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/baseline)，不把初次失败改写为初次成功。

官方 W3 RC=1；真实失败位置见 [完整W3失败日志](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/w3-local-ci-output.txt)。
同步主分支热修复后，G0/KC已放行；第二次 W3 在第755步启动 SDK clang++ 执行链接时
由 shell 报 Out of memory、RC126，尚未进入本轮 CTest。其后无关环境启动命令也 fork 失败，
SSH exec 请求亦失败。记录这一实际进程资源中断，不把它改写成源码诊断或成功。
连接恢复后已取回完整正向及失败日志；同一失败目标以原对象单独链接复验 RC0，
仅说明该目标可链接，不将失败的完整 W3 改写为通过。
没有 .ci-result.json，不宣称 W3 或远端 CI 已通过。
本表成功数字来自最终配方的独立原生 conan create，不能替代官方门禁结果。

独立强制原生 conan create 取得 RC0，耗时 3175 秒。
本表及independent-native前缀证据来自同一次3175秒完整运行，副本不作为第二次通过。
强制从源码构建，没有复用已编译 Viskores 产物。
官方源码与数据归档均以 SHA256 校验；W3 预下载缓存只含已验哈希的源码归档，
不包含编译产物。实际读取来源以原始日志为准。

## 复跑

```sh
conan create archives/v/viskores/1.1.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build='viskores/*'
```

本机使用隔离 CONAN_HOME 内的原生 SDK profile；CI 使用 worker 提供的 profile。
原始结果及分类见 `reports/test-report.md`，原始日志/XML及复现脚本通过
`reports/evidence.md` 的固定历史提交查验，`reports/evidence-index.tsv` 列出原字节长度与SHA256。
`python3 archives/v/viskores/1.1.1/reports/verify-evidence.py` 从本分支祖先Git对象重算结果及7输入绑定。
当前PR仅保留必要代码、摘要与证据索引；全量原文未改写或丢弃。
