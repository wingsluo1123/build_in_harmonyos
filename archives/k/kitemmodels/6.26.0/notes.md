# kitemmodels 6.26.0 鸿蒙 PC 候选

此版本是新包候选，而非对已发布 `6.18.0.1` 的结果改名。上游源码及散列以 KDE 官方 6.26.0 发布包为准。其 C++ 核心库仅要求 QtCore，但 KDE 消费者还使用 `org.kde.kitemmodels` QML 模块，因此候选明确依赖 `qtdeclarative/6.11.1`，保留 QML 插件并已在目标设备运行相关测试。

参考旧版 OHOS 配方保留平台检查覆盖、Qt/ECM 查找路径、Qt 工具的运行时库路径、共享库 SONAME 规则和安装 ELF 重新签名。最初静态草稿尚未在目标机验证；下述结果是本版本的新鲜真机证据，而非沿用旧版结论。

上游 `autotests/CMakeLists.txt` 静态登记 9 个普通 C++ 测试、1 个 smoke test 和 Qt6Qml 存在时另外 2 个 QML 测试。目标 CMake/CTest 实际启用并通过 12/12。安装包消费者检查 `KNumberModel` 的 C++ 行为与 QML 模块导入/构造，实际通过 9/9，两类验证分开报告。

2026-10-03 本地隔离 Conan home 的 `--build=never` 依赖下载和候选 `conan install`/`generate()` 已通过；这不是编译、真机测试、平台 CI、AI 审核或比赛提审。

同日用户授权的 `10.62.201.39:2222` 网络恢复后，候选通过 SSH 新鲜精确字节传输与独立回读，并在设备上独立 Conan home 原生 `conan create` 成功。通用 profile 的编译器路径已由任务私有 profile 按设备实况修正；配方的 CTest 调用改为绝对路径；分包 Qt 的消费者查找加入 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`。完整结果为上游 12/12、安装包 C++/QML 9/9、2 个 OHOS ELF 重新签名；日志 SHA-256 为 `0ce7ed6542af27732c44389e7148f1dc316c18d53fe1f7e36221acac7d46ff2d`，详见任务目录 `ADAPTATION-STATUS.md`。尚无正式 W3 receipt、平台 CI、AtomCode 结论或提审，不能以此宣称赛事完成。

对外暴露的 `shared=False` 还进行了一次单独真机试验：上游测试仍为 12/12，但包中 QML 插件变为 `libitemmodelsplugin.a`，普通 `import org.kde.kitemmodels` 无法在运行时加载；安装包消费者仅 4/9。因本适配要求提供可用的 QML 模块，最终配方不再提供 `shared=False` 选项，只保留共享库构建。此前共享配置的成功日志不自动证明这一最终收窄版本已完成正式 W3/平台 CI。

收窄后的最终 `shared-library` 配方已重新完整原生 `conan create`，上游 12/12、安装包消费者 9/9、签名 ELF 2 个，日志 `conan-create-shared-final-20261003.log` SHA-256 为 `d9c96cf22563f511390edb4995c49447e1f901b099dda3735799bd45d0b6c66e`。仍待正式 W3 receipt、平台 CI 与 AtomCode。
