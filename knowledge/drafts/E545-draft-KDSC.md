# KDE CMake 测试运行前将 build/bin 加入动态库搜索路径

状态：草稿；来源为 HarmonyOS PC aarch64 上 kdsoap-ws-discovery-client 0.4.0 的 Conan G2 首轮测试失败。

## 错误特征

CTest 启动 test_wsdiscoveryclient 时报告找不到 libKDSoapWSDiscoveryClient.so.0，随后列出多个 WSDiscoveryClient / WSDiscoveryTargetService 符号无法重定位。编译和链接本身均已完成。

## 根因分析

本次链接日志将共享库写入 build/Release/bin/libKDSoapWSDiscoveryClient.so.0。KDE ECM 的构建设置将共享库与测试可执行文件输出到同一 bin 目录。Conan 配方为测试准备的运行环境仅加入 build/Release/lib，因而动态加载器看不到刚生成的共享库。Conan verifier 另外将日志匹配到 E537，但实际错误行请求的是库的 SONAME basename；此处不是 DT_NEEDED 泄漏，而是构建树库目录没有加入搜索路径。

## 解决方案

在调用 CTest 的 build() 环境中，同时加入 build_folder/bin 与依赖包的 lib 目录。保留 CMAKE_SKIP_RPATH=ON，避免将临时 Conan 构建路径固化到安装包。先从链接行或 find 输出确认本次 CMake 的真实构建输出目录，不要仅凭 install libdir 推断构建树布局。

## 验证

修复后于 HarmonyOS PC 6.0 aarch64 重跑 Conan G2 与 W3。上游 CTest 1/1 目标通过，Conan test_package 的两个消费者测试通过，W3 为 1/1 包成功。原始证据位于版本档案 reports/conan-create.log 和 reports/w3-local-ci.log；后者 SHA-256 为 e79e0d8fe661d162848de78444a25a58c36ce93d5d2541db093efe7c0474e174。
