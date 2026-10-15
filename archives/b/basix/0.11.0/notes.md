# Basix 0.11.0 适配记录（正式目标验证已完成，平台流程待完成）

Task15119，必要的 FEniCS 依赖，分支 feat/basix-0.11.0。真实上游版本
0.11.0，CPython测试运行时固定为3.12/OHOS arm64。生产候选尚未推送、
创建PR或发布；native与正式Conan分别列证据，不称平台CI或发布通过。

原工具链的 libc++ ranges 功能缺口采用标准算法与等价 iterator 范围替代，
不生成stub、不减断言。ELF SONAME、原 Python runtime 的实际共享链接、
Windows专属runtime dependency collector的功能条件均在原源码/CMake修复。
所有十个补丁均由官方 refresh-patch --auto 生成，整176文件源码已匹配
同轮实际测试输入；没有手工diff或修改生成的build文件。

原连续性用例的宽RuntimeError捕获掩盖缺 variant 输入。按同版本原
test/utils.py为RT/N1E、BDM/N2E设置显式参数，原函数、装饰器和断言保留。
四个“slow”测试不接受豁免，保留原数学断言后已在同一全量运行真正执行。

同轮原10471个独立用例：10121 PASS、327 SKIP、23 XFAIL、0意外失败；
327是90混合cell支持边界和237无tensor factorisation组合，23为原已知
未实现或不稳定配置。用户接受上游支持域，本分母和这些非PASS结果原样
保留，不写10471/10471或100%。未知、普通缺依赖和真实失败不豁免。

原NumPy wheel与Conan OpenBLAS具有同SONAME但不同字节。生产候选仅取
已发布openblas/0.3.34，测试运行时不物化NumPy的另一个BLAS；native
configure/cache选定这个真实provider，全套数学与原C++消费者完成。
已有native观察证明输入/配置/结果，live maps读取时进程已结束，不能
补称观察到了实际映射；正式生产验证需绑定实际产物和加载身份。

Native独立报告SHA256：51a12e677ff20b4dcbbc017e2841eef6eb35082a1fd8313cd730d4e350f8e0d0。
正式r1448已在fresh目标事务执行canonical ConanVerifier和官方Finish step35，
二者RC0；每次原10471项分别10121PASS/327SKIP/23XFAIL/零失败与错误，
原四慢测试在每次均真正通过。Cpp消费者2/2、安装后Python数学2/2、
Harmony真实归属/计算状态1/1；15回执30WAL/唯一launch/own0/releasepost。
正式逐源码支持域报告SHA256：
2bfb72859ed7f42d7becfbdf31a9bf8be06c5cddaa00a98686e8403595032596。
公开边界见reports/upstream-supported-domain.json，不把350项非PASS改写为通过。
Issue3958已提出高难候选申请，尚非官方认定。平台CI/正式评审/提审和
合并后发布仍是后续门禁；原失败r1436/r1439保留，不重放或跨run拼PASS。
