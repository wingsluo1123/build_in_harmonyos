# unfurl test_package 说明

本 test_package 针对 unfurl 0.4.3 Go CLI 工具的实质校验:

1. 检查包内 `bin/unfurl` 存在且可执行 —— 验证 Go 交叉编译产物已打包;
2. 实际运行 `echo 'https://example.com/foo?a=b' | unfurl -u domains` ——
   验证工具能正确从 stdin 提取 URL 域名 (上游核心功能);
3. 无编译步骤 (`build()` 为空) —— unfurl 为 Go 工具,
   CI 通过 `conan create` 自动调用本 test_package 完成 L1 级校验。

说明: unfurl 无 C/C++ 库产物, 测试只校验可执行文件与其运行时行为。
