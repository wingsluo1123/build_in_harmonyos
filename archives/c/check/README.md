# Check

Check 是一个 C 语言的单元测试框架，支持多种测试模式和自动检测内存泄漏。

## 功能概述

- 提供 C 单元测试框架
- 支持 Suite/TC/TCase 多层测试组织
- 自动检测内存泄漏
- 支持 fork 模式隔离测试
- 输出 XML/HTML/TAP 格式测试报告

## OHOS 适配

- 构建系统：上游 CMake
- 关闭上游自测试，避免测试运行阶段依赖临时文件和 fork 场景
- 通过 Conan `test_package` 编译并执行 Check 公共 API 消费测试
- 用于其他 C 项目的单元测试

## 依赖关系

- C 编译器
- CMake 3.15+
- 系统库：OHOS 使用 libm / libpthread；Linux/glibc 场景可能额外需要 librt

## 参考资料

- 官网: https://libcheck.github.io/check/
- 源码: https://github.com/libcheck/check
