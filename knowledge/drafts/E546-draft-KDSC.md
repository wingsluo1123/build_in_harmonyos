# 导出的 CMake Config 使用 find_dependency 前需包含宏模块

状态：草稿；来源为 HarmonyOS aarch64 上 kdsoap-ws-discovery-client 0.4.0 的 Conan L1 消费者配置失败。

## 错误特征

消费者调用 find_package(KDSoapWSDiscoveryClient 0.4.0 CONFIG REQUIRED) 后，在已安装包的 KDSoapWSDiscoveryClientConfig.cmake 第 31 行报错：

Unknown CMake command "find_dependency"

库本身已编译、安装，错误发生在独立消费者的 CMake 配置阶段。

## 根因

上游 KDSoapWSDiscoveryClientConfig.cmake.in 通过 CMakePackageConfigHelpers 生成安装配置，但在 @PACKAGE_INIT@ 后直接调用 find_dependency(Qt6Core ...) 和 find_dependency(KDSoap-qt6)，没有包含 CMakeFindDependencyMacro。独立消费者只 include 生成后的包配置，不保证之前加载过定义该命令的宏，因此 find_package 失败。

## 修复方式

在模板的 @PACKAGE_INIT@ 之后、首个 find_dependency() 之前加入：

include(CMakeFindDependencyMacro)

将修改作为有 SHA 校验的上游补丁应用，并运行独立 Conan test_package：它应查找已安装 Config、编译调用公开 API 的程序，并在 HarmonyOS 上执行真实 loopback SOAP 测试。本次补丁后已安装包配置、消费者构建和两个 CTest 均通过。

## 验证与边界

原始 Conan 日志将错误定位到已安装包的 KDSoapWSDiscoveryClientConfig.cmake 第 31 行。HarmonyOS PC 6.0 aarch64 的回归通过。此模式适用于其它漏载宏模块的导出 CMake 包配置，不限于 HarmonyOS；构建证据在版本档案 reports/conan-create.log。
