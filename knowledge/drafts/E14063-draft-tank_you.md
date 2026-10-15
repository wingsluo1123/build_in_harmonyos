# E14063 — 静态 Qt QML 插件的安装包导入不能由上游 CTest 代证

## 现象

在授权的鸿蒙 PC 上，`kitemmodels/6.26.0` 的 `shared=False` 候选完成构建，
上游 CTest 为 12/12；包内有 `libKF6ItemModels.a` 和
`libitemmodelsplugin.a`。但是已安装包消费者通过普通
`import org.kde.kitemmodels 1.0` 创建 `KNumberModel` 时报告
`module "org.kde.kitemmodels" plugin "itemmodelsplugin" not found`。
消费者的 C++ 行为检查 4/4，通过 QML 导入及构造等检查后总计只有 4/9。

## 根因与处理

静态配置把 QML 插件交付为 `.a`；普通运行时 QML 导入不会自动加载该静态
归档。上游测试在构建树中执行，其 12/12 结果不能替代已安装包的 QML 导入
验证。若需要支持静态包，必须额外实现插件的显式注册和链接并用安装包消费
者证明；本次没有完成这条路径，因此不对外暴露 `shared=False`。最终配方
使用 `package_type = "shared-library"` 和 `BUILD_SHARED_LIBS=ON`。

## 验证与适用边界

在相同授权真机、独立 Conan home 中，最终共享专用候选重新从官方源码完整
运行 `conan create`，退出码 0，上游 CTest 12/12，安装包 C++/QML 消费者
9/9，包内 2 个 OHOS ELF 已签名。失败静态运行日志 SHA-256 为
`b7a0123e315bd0565f63eb9ad15fc4201a56ebb5063f387add064e40313fd8da`；
最终共享运行日志 SHA-256 为
`d9c96cf22563f511390edb4995c49447e1f901b099dda3735799bd45d0b6c66e`。
两份日志均已从目标独立逐字节回读，路径和其余身份记录见任务目录
`ADAPTATION-STATUS.md`。这些是真机探索性构建结果，不代表正式 W3 回执、
平台 CI、AtomCode 检视或比赛提审已通过。

这条经验适用于向消费者提供普通运行时 QML 导入的 Conan 包；若包明确
要求静态插件注册且已对其安装包消费者完成验证，不应机械地禁用静态包。
