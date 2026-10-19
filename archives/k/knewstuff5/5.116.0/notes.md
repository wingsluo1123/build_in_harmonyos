# knewstuff5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (Ninja)
- 编译日期: 2026-10-03
- 编译器: clang/clang++ 15 (OHOS NDK)
- 状态: built

## 软件简介
KNewStuff 是 KDE "Get Hot New Stuff" 框架。本次 scoped 构建交付：
- libKF5NewStuffCore.so（核心库）
- org.kde.newstuff QML 插件（qtquick）
- knewstuff-dialog（内容浏览/安装对话框工具）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package 找不到 KF5 Completion/IconThemes/KIO/Service/XmlGui | 对应 KF5 组件未在制品仓发布 | 新增 KNEWSTUFF_OHOS_SCOPED 选项，收缩到依赖闭包完整的目标（补丁 0001-0004） |
| 2 | Qt5::Qml/Quick target 未找到 | CMakeDeps 为 qtdeclarative 生成独立 Qt5QmlConfig，COMPONENTS 形式不加载 | paths 文件中 include Qt5QmlConfig 并为 Qt5::Quick 建别名 |
| 3 | qt_add_resources 未知命令 | 命令定义在 qtbase Qt5CoreMacros，CMakeDeps 不加载 | paths 文件直接 include Qt5CoreMacros.cmake |
| 4 | po 翻译生成失败 | qt5-qtbase 无 LinguistTools，msgfmt 未接入 | 补丁 0013 scoped 下跳过 ki18n_install(po) |
| 5 | 测试运行时依赖库无法解析 (E505) | musl loader 无法经版本化 soname 符号链接别名解析 | 实体化共享库闭包为真实文件（107 个） |
| 6 | dlopen Permission denied (E212) | 包内 ELF 自签名不被当前系统信任 | binary-sign-tool 对镜像库逐个重自签名 |

## 上游测试
- 上游 core 测试 3 个程序 / 18 个 QtTest 断言：**全部通过（100%）**
- widgets 层 2 个测试（knewstuffentrytest、kmoretools）scoped 排除，依赖未发布组件
- test_package L1 消费者测试：**1/1 通过**

## 依赖版本
- qt5-qtbase/5.15.2.2
- qt5-qtdeclarative/5.15.2
- attica5/5.116.0、karchive5/5.116.0、kconfig5/5.116.0
- kcoreaddons5/5.116.0、ki18n5/5.116.0、kpackage5/5.116.0
- ecm/6.26.0（tool_requires）

## 注意事项
- widgets 层（KNewStuff/KNewStuffWidgets）未构建，待上游 KF5 依赖链发布后可扩展
- 运行时执行依赖实体化重签名镜像，配方内已自动化
