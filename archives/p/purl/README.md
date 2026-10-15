# purl

purl 是 Python 不可变 URL 操作库，提供 URL 解析、路径及查询参数修改、Unicode 编码和 RFC 6570 URI 模板展开。

- 上游：[codeinthehole/purl](https://github.com/codeinthehole/purl)
- 许可证：MIT
- 适配版本：1.6
- 目标环境：HarmonyOS PC / OHOS AArch64，Python 3.12.9，Conan 2.29.1
- 运行依赖：`six/1.17.0`
- 测试工具：`pytest/9.1.1`（Conan build context）

配方将纯 Python 模块安装至 `lib/python/site-packages/purl`，通过 Conan 的 `PYTHONPATH` 环境使用。上游测试 171 项和独立消费测试 10 项在真机通过。当前为本地构建状态，尚未发布到制品仓。

详见 [1.6 适配笔记](1.6/notes.md) 和 [测试报告](1.6/reports/test-report.md)。
