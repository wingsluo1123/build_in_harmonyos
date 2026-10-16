# jpi-analyzer

jpi-analyzer 是一个用于解析 JPI EDM 飞行数据文件的纯 Python 库与命令行工具。

## 基本信息

- **上游仓库**: https://github.com/unicornlines/JPI-Parser
- **许可证**: MIT
- **语言**: Python >= 3.10

## 版本列表

- 0.2.0-git20260502.823a948（锚定上游 commit 823a948bf005941275b9c6d93bfc8037be63239d；tag v0.2.0 指向 e1a34c3，不采用）

## 描述

Parse JPI EDM flight data files and export them to CSV.

提供 `jpi_analyzer` 包（parser/decoder/metrics/exporter/cli 共 5 个模块）与
console scripts `jpi-analyzer`、`jpia`；运行时依赖 click（>=8.1，经 Conan
依赖闭包解析为 click/8.4.2，不进 pip 依赖树）。
