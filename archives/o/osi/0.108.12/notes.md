# Osi 0.108.12 OHOS 适配笔记

## 适配范围

- 构建核心 `libOsi` 静态库。
- 关闭 GLPK、SoPlex、CPLEX、Mosek、Xpress、Gurobi 等可选求解器绑定。
- 依赖 `coinutils/2.11.13`。

## 验证

- 本地 Windows 环境无 OHOS Conan，已完成 recipe/test_package 结构检查与 Python 语法校验。
- OHOS AArch64 `conan create` 由 PR CI 执行。

## 风险

- 如果远端制品仓尚未发布 `coinutils/2.11.13`，CI 会在 R36 依赖检查阶段失败，需要先发布 coinutils。
