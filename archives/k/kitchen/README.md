# kitchen

kitchen 是一组用于 Python 文本处理、Unicode 转换、国际化和兼容性处理的实用工具。

## 适配版本

- `1.2.6`：适配 HarmonyOS PC（aarch64），使用纯 Python Conan 配方安装。

## 验证

上游共 366 个测试定义（`kitchen2/tests` 239 + `kitchen3/tests` 127）。适配后
`kitchen3` 的 127/127 个定义全部执行：126 条 unittest 用例（123 通过 + 3 按上游
`skipUnless` 跳过）+ 464 条补跑用例（nose 专属定义，0 意外失败、3 条 CPython 3.12
已知漂移按精确白名单记录），另有 8 项消费者集成测试（含 1 项 HarmonyOS 特有测试）。
`kitchen2` 的 239 项为 Python 2 专用，环境无 Python 2 解释器，**未执行并如实披露**。
