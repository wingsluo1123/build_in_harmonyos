# kitemmodels 6.28.0 鸿蒙 PC 候选

此版本延续 6.26.0 线，而非对已发布 `6.18.0.1` 的结果改名。上游源码及散列以 KDE 官方 6.28.0 发布包为准（`kitemmodels-6.28.0.tar.xz`，SHA-256 `e03c5dbfc97fa298de9be58bfeb686518a52ae1236389fbc2436ff84165e7e2b`）。其 C++ 核心库仅要求 QtCore，但 KDE 消费者还使用 `org.kde.kitemmodels` QML 模块，因此候选明确依赖 `qtdeclarative/6.11.1`，保留 QML 插件并已在目标设备运行相关测试。

本版本继承 6.26.0 配方的平台检查覆盖、Qt/ECM 查找路径、Qt 工具运行时库路径、共享库 SONAME 规则与安装 ELF 重新签名；并新增 HMDFS 符号链接处理：本机文件系统对 `symlink(2)` 返回 EPERM，CMake 为带版本库生成的版本化软链（`libKF6ItemModels.so.6 -> .so.6.28.0`）无法落地，配方在 OHOS 上设置 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`，保留无版本 DT_SONAME 并跳过该软链链（KF5/expat 已验证路线）。

上游 `autotests/CMakeLists.txt` 静态登记 9 个普通 C++ 测试、1 个 smoke test 和 Qt6Qml 存在时另外 2 个 QML 测试。目标 CMake/CTest 实际启用并通过 12/12。安装包消费者检查 `KNumberModel` 的 C++ 行为与 QML 模块导入/构造，实际通过 9/9，两类验证分开报告。

2026-10-16 真机证据（本轮）：在鸿蒙 PC 真机（aarch64）通过 `conan-verify` 全流程干净重建，G0/G1/G2/G3/G4 全部 PASS（L2/L4/L5 按设备常态跳过——无 cache 路径）。源码获取为本机 sources 下载缓存命中（日志原文 `Source https://download.kde.org/stable/frameworks/6.28/kitemmodels-6.28.0.tar.xz retrieved from local download cache`；缓存经官方镜像 mirrors.aliyun.com 预置，SHA-256 与上游发布一致，设备直连 download.kde.org 的重定向镜像证书校验失败）。结果为上游 CTest 12/12、安装包消费者 9/9、2 个 OHOS ELF 重新签名。conan-verify 报告随档 `reports/conan-verify-report.md`（SHA-256 `9f3573d0bb7c767b5e693ff54066d65d41d7a0f3a2ddf4a40a9cae9032c96b16`）；完整构建日志 SHA-256 `1da8223f7686cda8334dfc4ab6540a6481cf835911cf56a4c1dd18a562940e7e`（51,344 字节，未随档、可按需提供）。

对外暴露的 `shared=False` 未在本版本提供：同族 6.26.0 线的真机试验表明静态包 QML 插件变为 `libitemmodelsplugin.a`，普通 `import org.kde.kitemmodels` 无法在运行时加载（安装包消费者仅 4/9）；本适配要求提供可用的 QML 模块，因此只交付共享库构建。

以上为本任务真机 conan-verify 结果，不冒充正式 W3 事务回执、平台 CI、AtomCode 检视或赛事提审；这些环节待平台侧执行。
