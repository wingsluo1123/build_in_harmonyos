# 严格 F 逐项说明（19 项）

F = 已执行但未严格通过。**其中 0 项为适配缺陷**（FAIL_ADAPTATION = 0）。

## TIMEOUT（9 项）

该 invocation 超过单次调用上限被截断（rc=124）。成因是平台算力与电路的绝对时长，非算法差异；已逐项登记命令、阶段、产物 mtime 与估算依据。语义上属「未在限时内取得终态」，既非 PASS 也非缺陷。

- `vtr_reg_nightly_test1_odin/power_extended_circuit_list`
- `vtr_reg_nightly_test3/complex_switch`
- `vtr_reg_nightly_test3/vtr_reg_qor`
- `vtr_reg_nightly_test3/vtr_reg_qor_chain`
- `vtr_reg_nightly_test3/vtr_reg_qor_chain_depop`
- `vtr_reg_nightly_test3_odin/complex_switch`
- `vtr_reg_nightly_test3_odin/vtr_reg_qor`
- `vtr_reg_nightly_test3_odin/vtr_reg_qor_chain`
- `vtr_reg_nightly_test3_odin/vtr_reg_qor_chain_depop`

## FAIL_UPSTREAM（3 项）

VTR 自带的 yosys 没有开源 SystemVerilog 前端（VERIFIC 为商业组件）；已用未修改 VTR 9.0.0 的 Linux 对照复现同一失败。

- `vtr_reg_system_verilog/f4pga_button_controller`
- `vtr_reg_system_verilog/f4pga_pulse_width_led`
- `vtr_reg_system_verilog/f4pga_timer`

## EXPECTED_FAILURE_STATUS_MISMATCH（2 项）

上游 golden 自身声明该 (arch,circuit,param) 组合应当失败，并在 `error` 列存了错误串；run_vtr_flow 做**字符串精确比较**。裸进程在 Linux 与鸿蒙上都是 SIGABRT，仅 `time(1)` 把同一死亡表示为 **134（GNU time）vs 6（本平台）**，故精确串不匹配而报失败。CAD 行为三方一致（golden 声明 / Linux 对照 / 设备实测），**不是适配缺陷**。语义口径按 PASS_EXPECTED_FAILURE 计。

- `vtr_reg_nightly_test1/arithmetic_tasks/figure_8`
- `vtr_reg_nightly_test1_odin/arithmetic_tasks/figure_8`

## TIMEOUT_POLICY_PENDING_REVIEW（2 项）

新超时签名，按裁定归 TIMEOUT_POLICY_PENDING_REVIEW：不自动 HOLD、不重跑，保留命令/阶段/日志/估算依据待复核。

- `vtr_reg_nightly_test3_odin/vtr_reg_qor_chain_predictor_off`
- `vtr_reg_nightly_test4_odin/koios_medium`

## PLATFORM_ENVIRONMENT_DIFFERENCE_DETERMINISTIC（2 项）

上游 `fix_clusters` 测试把**簇名写死**在 constraints 文件里，因此对打包结果敏感。两端输入 sha256 逐字节相同、命令与 cwd 相同、适配补丁仅为 `#include` 增补；实测第一处分歧位于打包器的**候选分子枚举**（`greedy_clusterer.cpp:try_grow_cluster` → `cluster_legalizer.cpp`），Linux 与设备各自可复现（非随机）。IPO 假设已用独立对照实验**否定**（Linux IPO=off 与 IPO=on 结果逐字节一致，且均成功）。剩余变量为编译器/标准库/CPU 架构。**不计 FAIL_ADAPTATION**。

- `vtr_reg_strong/strong_fix_clusters`
- `vtr_reg_strong_odin/strong_fix_clusters`

## TIMEOUT_POLICY（1 项）

启动前时长门禁判定 est_device > 单次上限，**未启动**（不可能取得成功终态，启动只会浪费设备时间）。

- `vtr_reg_nightly_test1/power_extended_circuit_list`

