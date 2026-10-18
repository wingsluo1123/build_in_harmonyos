# SOAPsnp 1.03 测试报告

上游自动测试0个，0/0不适用；原始 Makefile 没有 check 目标。
新增集成测试8/8、鸿蒙完整消费者1/1，合计9/9（100%）。

| 用例 | 类型 | 结果 |
|---|---|---|
| reference_consensus | 集成测试 | 通过 |
| variant_consensus | 集成测试 | 通过 |
| monoploid_consensus | 集成测试 | 通过 |
| snp_only | 集成测试 | 通过 |
| calibration_roundtrip | 鸿蒙完整消费者 | 通过 |
| missing_alignment | 集成测试 | 通过 |
| missing_reference | 集成测试 | 通过 |
| unknown_chromosome | 集成测试 | 通过 |
| missing_matrix | 集成测试 | 通过 |
| 合计 | 8个集成 + 1个完整消费者 | 9/9 |

完整消费者生成校准矩阵，再在独立进程中读取并比较全部共识字段。W3移走安装包bin目录后测试失败，恢复后9/9复测通过。

实际验证环境：OHOS 7.0.0.32 Beta/API26/AArch64 QEMU，官方 profile 元数据为 OHOS6。
