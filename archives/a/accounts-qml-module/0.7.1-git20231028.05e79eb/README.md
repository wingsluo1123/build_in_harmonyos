# accounts-qml-module 0.7.1 — 无法适配说明

> 归档日期：2026-08-13
> 结论分类：`暂时搁置`（阻塞类别：`依赖链断裂`）
> 关联 Issue：#2107 / PR：#5233

## 结论

accounts-qml-module 目前**无法完成鸿蒙化适配**，主因是**依赖链断裂**（R36 阻塞）：其 4 个直接依赖中 3 个未发布到 ohpcd 制品仓，无法进入编译阶段。

## 阻塞原因

| 依赖 | 制品仓状态（conan list -r=ohpcd） |
|------|----------------------------------|
| libaccounts-qt/1.13 | ❌ 0 recipe（未发布） |
| libsignon-qt/8.61 | ❌ 0 recipe（未发布） |
| qt5-qtdeclarative/5.15.2 | ❌ 0 recipe（未发布） |
| qt5-qtbase/5.15.2 | ⚠️ 已发布，但以 `-no-feature-xml` 构建，**缺 QtXml 模块** |

上游构建为 qmake 工程，`Accounts.pro` 声明 `QT += core`，且 `service.h` 依赖 `<QDomDocument>`（QtXml）。qt5-qtbase/5.15.2 缺 QtXml（无 `libQt5Xml.so`、无 `qtxml-config.h`），故即使本地编译 libaccounts-qt 也会在 QtXml 处失败。

## 实测适配进展（2026-08-13）

1. **libaccounts-glib 1.27**：✅ 本地 conan 构建成功（meson，4 个平台补丁：禁用 gtkdoc/gir/pygobject/tools/tests、预生成 marshal、.pc 工具变量补齐）
2. **libaccounts-qt 1.13**：⚠️ 部分成功——qt5-qtbase 包内 qmake 的 QMAKE_MKSPECS 固化指向构建期 build 目录（打包缺陷），qmake 模块系统不可用；改用**手动 moc + clang++ 构建**后已通过大部分编译，最终卡在 QtXml
3. **qt5-qtbase/5.15.2.1**（含 QtXml 的修复版配方，仓库已存在但未发布）：❌ 本地 Qt5 全量构建在 OHOS HMDFS 上遇软链接（`ln -s` 被拒）、并行链接等平台问题，需 CI 完整构建机

## 建议路径

按拓扑序在 CI 完整构建机适配发布：

```
qt5-qtbase/5.15.2.1（含 Xml）→ libaccounts-qt/1.13 → libsignon-qt/8.61 → qt5-qtdeclarative/5.15.2 → accounts-qml-module/0.7.1
```

依赖就绪后重启本库适配。此归档供社区可见，避免重复投入。
