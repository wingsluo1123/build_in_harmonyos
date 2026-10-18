# oRTP 5.2.0 OpenHarmony 适配

生产库依赖 bctoolbox/5.3.115。保留四项既有补丁：CMake 最低版本、
OHOS CMSG_NXTHDR 告警、Conan CMakeDeps 目标/宏兼容、相对 SONAME。

## 2026-10-15 真机上游测试补全

已在新真机核实并下载已发布的 bctoolbox/5.3.115 与 bcunit/5.3.113
二进制。bctoolbox 包含真实 libbctoolbox-tester.a 和 tester.h，不能继续
沿用旧的“制品不可核实，因此测试未运行”说明。

新增 0005 补丁通过 imported target 接入该 tester 库及 BCUnit；
ENABLE_UNIT_TESTS=ON，保留全部上游 tester 源码和断言。配方构建后
直接执行原始 ortp_tester，非零退出即失败，LD_LIBRARY_PATH 同时包含
当前 build/src 和宿主依赖库。tester 是构建测试工具，不作为公共 CLI 打包。
src/tests 的 RTP 收发工具仍为 ENABLE_TESTS=OFF，不计为已运行测试。

完整上游套件只有 FEC/first 一个用例，内容仅为 NULL 指针断言。
真实结果为通过 1、失败 0、跳过 0；这是原始框架用例，不代表 FEC 算法覆盖。
安装后 consumer 另计 1 项，实际执行初始化、调度器初始化、会话创建、
调度/阻塞模式配置、127.0.0.1 本地端点绑定及销毁。真实运行 1/1 通过。
负向测试破坏包 bin/lib/include 后，consumer 按预期失败，证明依赖真实包。

先前 Windows/WSL 六项预检只作为历史主机检查，不混入上述真机计数。
先前 CI #92908 对 90261cae 仅验证 consumer；新提交需单独远端复核。

## 真实 W3 证据

使用官方 b544378a4ea82b4959135eebb21f5e509eeebf91 的完整未修改基础设施，
在 HarmonyOS 6.1.0.117 arm64、OHOS Conan 2.29.1、Clang 15、Release
配置下执行原始 FinishPipeline.step35_local_ci，返回 exit 0。
G0/KC/JC/L0/L1/L4/L5 通过；L2 因不交付 CLI 而跳过。
完整日志 SHA256 `2d92a85b0878b89dd531527e94a4ee891ffbd2cb6a735571498d6425b57ada2a`；Conan 正向日志 SHA256 `18ff954a0b87515cf39f6f293cacf474654bb1ee6d0cc433c16b098c0d1b1af0`。
marker 与完整日志哈希一致，原件保存在本地，未伪造或修改。

调试期间的三次失败均保留：补丁顺序冲突、CMake include 列表格式、
未加入当前 build/src 导致 libortp.so 无法加载；逐一修复后重跑完整 W3。
当前通过只覆盖默认共享构建和上述 1+1 测试，不宣称网络收发互通、
静态构建、FEC 算法、全部 RTP 行为或制品发布已经验证。
