# xmbmon 2.05 真机验证

环境：HarmonyOS 6.1.0.115、aarch64、HNP SDK26.0.0.18、Clang15.0.4、Conan2.29.1、Python3.12，普通HiShell身份。

| 分类 | 发现/执行/通过 | 验证入口 |
|---|---|---|
| 上游自动测试 | 0/0/0 | 无make check目标 |
| 上游硬件诊断（OHOS aarch64） | 4/0/0 | 四项保留，因 x86 端口 I/O 前提不适用，未在目标设备执行 |
| 上游硬件诊断（WSL x86_64 对照） | 4/4/0 | 四项均实际运行，退出码均为 255；不是通过，也不计入 OHOS 通过率 |
| 原生温度/API/CLI/TCP消费者 | 22/22/22 | test_package/test_native.py、measurement_consumer.c |
| 风扇记录解析fixture | 9/9/9 | test_package/test_fan_snapshot.py |
| HDC真实双通道采集 | 25次发布 | collect_fans_hdc.py，单位raw |
| 应用消费实时风扇 | 3/3/3 | mbmon --fan-raw |
| 实际停止采集后的过期处理 | 1/1/1 | N/A、exit3 |
| 本机GUI | 4/4/4 | display/local_viewer.py：映射、刷新、缩放、重绘 |

新增Conan消费者31/31（100%），22项与9项分组统计；不将传感器fixture视为真实硬件成功。
API消费者内部20次采样属于一项检查。重复执行和25次采集均不增加测试分母。
GUI及实时风扇是独立集成证据。四项原始诊断在 x86_64 对照环境执行失败，
在 OHOS aarch64 不具备运行前提；两种口径均没有记为通过。

## 上游诊断适用性与对照证据

“不适用”仅指这四项旧主板硬件诊断不能验证本次 OHOS 测量后端，不表示其源码无效或测试可以算通过。
原始 `Makefile.in` 将 `testpci`、`testsmb`、`testhwm`、`testfan` 列在 `TESTPROG` 和 `testprog` 构建目标中，
没有 `check` 运行目标；`testfan` 是以 `-DFAN_DIV_CHK` 重新编译 `testhwm.c`。
四项均经过 `pci_smb.c` / `pci_pm.c` 扫描旧式 PCI/SMBus 控制器，
`io_cpu.h` 在 Linux 调用 `iopl(3)`，并使用 `inb/inw/inl/outb/outw/outl` x86 端口指令。
这不是跨平台测量 API 的行为测试。原始头文件的 aarch64 编译探针
`clang --target=aarch64-linux-ohos -I<upstream> -c port_asm.c`（`port_asm.c` 包含原始 `io_cpu.h`）
退出 1，分别在 `inb/inw/inl` 的 `=a` 输出约束及 `outb/outw/outl` 的 `a` 输入约束处报错，
共六处 `invalid ... constraint`。完整编译输出见
[upstream-aarch64-asm.md](upstream-aarch64-asm.md)。

原始源包 SHA-256 `65b10ebfe53585ac22d6a31d8ef3fea552cb266cf2c124c00421dec1df5a4a4f`。
在 WSL x86_64 上用未修改的上游源码构建四个程序后，以普通 UID 1000 逐一运行；
完整命令、退出码与原始输出见 [upstream-diagnostics-20261014.md](upstream-diagnostics-20261014.md)。
`testpci`、`testsmb` 均以 255 退出并报告 `Cannot open IO-port, needs privilege!`；
`testhwm`、`testfan` 均以 255 退出并报告 `No SMBus candidates found!!`。
进一步以 WSL root 运行 `testpci` 和 `testhwm`，仍分别得到上述错误且运行失败
（见日志末尾）；提权不等于宿主向 WSL 提供端口 I/O。
尤其 `pci_pm_smb_prob()` 在 `OpenIO()` 失败时返回 -1，
而 `testhwm.c` 的 `n <= 0` 同时将 -1 和真实零候选打印为“无候选”。
故本次输出不能证明机器确实没有 SMBus 控制器，更不能推断 OHOS 设备有无风扇。
要单独验证这些上游诊断，需要支持端口 I/O 且配有被其识别的控制器的原生 x86 环境。

## 补充测试的对应关系与局限

新后端通过平台热服务 C 桥接读取三路具名温度，不访问原始 PCI/SMBus 端口。
`test_package/measurement_consumer.c` 对安装后的 C 接口校验空参数错误、20 次真实服务采样、
有效位、数值基本范围与标签格式；`test_native.py` 的 22 项验证 CLI 格式、温标换算、
缺失风扇/电压的显式状态、TCP 消费和前端可装载性。这些是在 OHOS 真机对当前实际后端的验证。
`test_fan_snapshot.py` 的 9 项只覆盖 HDC 快照格式、时间、通道和错误路径，不证明传感器本身可用。
真实风扇双通道采集 25 次、应用消费 3 次、停止采集后的过期处理 1 次另列集成证据；
GUI 的 4 项本机检查另列，不混入 Conan 消费者 31 项。
这些补充测试覆盖已交付的温度、辅助 raw 风扇和显示行为，不能替代旧 x86 硬件诊断的
PCI/SMBus 芯片覆盖，也不能证明 RPM 单位、独立应用风扇接口或跨固件 ABI 稳定性。

原生构建入口（在仓库根目录，CONAN_HOME与TMPDIR设为本任务目录）：

```sh
conan create archives/x/xmbmon/2.05 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=1 --build='xmbmon/*' --format=json > native-graph.json
```

原始设备功能记录的断言、数值、退出码和SHA256索引见[verification.json](verification.json)。
本机GUI复现见[display/README.md](display/README.md)。显示截图由相同xmbmon二进制生成。
四项原始诊断的架构限制、主板电压排除、风扇raw语义及HDC依赖需要评审确认验收口径。
本报告记录本地真机结果；CI 状态以 PR 平台最新流水线为准，C 专项结论由评审形成。
