# 真实测试失败不一定到达进程退出码：CppUnit 与 ODEPACK 两种驱动的修复

草稿，贡献者 `frj__`。来源：Siconos 4.4.0、任务 10598，2026-10-17 HarmonyOS arm64 真机实验。

来源PR：[#16511](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/16511)；[C申请 #4196](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/4196)；[B申请 #4197](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/4197)。

CTest 默认采用进程退出状态。测试驱动若丢弃框架成功值或数值错误计数，断言已经失败也会产生通过结果。增加执行数量、查看进程是否正常退出，无法恢复已丢失的内部状态。

识别签名要求同一次驱动的内部失败与正常 RC0 同时成立。正常失败并退出1不属于本条；不能仅因出现 `Failures: 1` 或非零错误汇总就自动套用此根因。

## 两种已经复现的机制

Siconos 的 `kernel/tests-common/TestMain.cpp` 建立真实 CppUnit registry 后调用：

```cpp
runner.run("", false, true, false);
```

该 API 返回布尔成功值。原 main 忽略它，正常结束即返回 0。一个故意失败的真实 CppUnit fixture 已打印 `Failures: 1`，原驱动仍退出 0。

捆绑的 Netlib ODEPACK 测试采用另一种机制：DLSODA、DLSODAR、DLSODE、DLSODES、DLSODI、DLSODIS、DLSOIBT 七个驱动把数值超差或求解器异常累计到 `nerr`，最后打印汇总并无条件 `STOP`。原驱动即使报告错误也不返回非零。

## 真机对照

| 驱动 | 输入/结果 | 原版退出码 | 修版退出码 |
|---|---|---:|---:|
| CppUnit 共用主程序 | 同一个 fixture，断言成功 | 0 | 0 |
| CppUnit 共用主程序 | 同一个 fixture，断言失败、Failures=1 | 0 | 1 |
| DLSODA 原数值驱动 | 在汇总前强制 nerr=1，两版都打印错误数1 | 0 | 1 |

共六次结果透传负例/正例运行。最终 TestMain 另做两次零 registry 回归：原版 `OK (0 tests)`/RC0，修版拒绝空集合/RC1；零用例机制按既有 E1732 处理，不申报为新增知识。它们是结果传递实验，不计入上游通过用例数量。`nerr=1` 仅注入独立实验副本，正式源文件没有注入、清零或改变任何数值容差。

CppUnit 原/修版本使用同一 CppUnit 制品、同一 fixture、同一编译器。Fortran 对照使用相同 DLSODA 驱动、相同已构建的 externals/OpenBLAS 库与同一 Flang 工具包。改变的只有错误状态是否传到进程返回值。

## 最小修法

CppUnit 将 bool 明确映射成进程约定：

```cpp
return runner.run("", false, true, false) ? 0 : 1;
```

不能写 `return runner.run(...)`，那会把成功的 true 转为退出码 1。

已有 `nerr` 的固定格式 Fortran，在原有汇总之后、原有 STOP 之前增加：

```fortran
      if (nerr .ne. 0) stop 1
      stop
```

保持原数值判断、累计、日志和参考解不变。

没有 `nerr` 的 DLSODPK/DLSODKR 演示，在现有失败分支打印诊断后退出非零。DLSODKR 的 `istate=3` 是正常根事件，不能当失败。

八个 Hairer 示例只有求解器状态，没有现成的误差累计。只按求解器的已有契约拒绝 `IDID<0`，仍列为 demo/status 验证，不宣称建立了新的数值正确性判据，不自行添加容差或 golden。

## 与已有知识的边界

| 条目 | 已有覆盖 | 本次实测差异 |
|---|---|---|
| E1707 | CTest 容器与 CppUnit 内部用例的双层分母、成功输出解析 | 此处用例已经执行且真实失败；正确分母和详细输出仍不能让 CTest 的退出码判据失效转正 |
| E1732 | 测试程序链接不完整，0用例也退出0 | 本次 fixture 明确执行1项、失败1项，ODEPACK 汇总错误数也为1 |
| E807 | 启动失败、信号、126/127/255 的弱判定 | 两个原驱动均正常启动、正常退出0，WIFEXITED 为真；内部结果丢失发生得更早 |
| E924 | 配置时没有找到测试框架，整个套件静默未构建 | 此处框架、用例和 Fortran 驱动均已真实运行，失败信息已打印，丢失的是内部失败到进程状态的映射 |
| E883 | 自研 CRC 测试清点、返回码和失败输出双判 | CppUnit 的 bool 与 Fortran 的 nerr/STOP 是具体可复用子族；本次直接恢复驱动的退出状态，保留原 oracle |

2026-10-17 在主仓 `a9a60dda6` 检索正式 `knowledge/graph/E*.kv`：`runner.run`、`TextUi::TestRunner`、完整短语 `Number of errors encountered`、`ODEPACK`、完整单词 `nerr` 均为0直接命中；`CppUnit` 为9命中，逐项核对其框架探测、依赖闭包、用例分母与崩溃处理。子串 `nerr` 有30命中，多为 errno 等其他单词，不能称为0命中。该检索只用于本子族的边界判定，不声称整个假绿问题族为空白。

本草稿不主张“所有退出码假绿都是新知识”。建议按这些既有条目的覆盖边界评审新增子族；跨两种上游驱动机制的负例已验证，未声明完成第二个软件的移植。

## 不应采用的做法

- 泛匹配 `error` 判失败：正常的 `Number of errors encountered = 0` 同样包含该词。
- 只检查进程正常退出或总数非零：本次两个失败反例都满足这些条件。
- 清零 nerr、删断言、降低误差要求或把失败输出称作预期通过：都会改变上游检验语义。
- 把演示程序运行完成直接写成数值断言全通过：没有 oracle 的输出必须保持 demo/status 口径。

## 交付和验证关联

补丁位于同一 Siconos 配方的 `patches/`；实验驱动、原始状态和正式测试清单由同一 PR 的报告提供。最终上游结果以正式构建和逐组日志为准，本条负例实验不替代那一轮测试。

`draft: true`；`contributor_id: frj__`；作者 `frj__`；更新日期 2026-10-17。
