# kcharselect 26.04.0 — 上游可选的 KF6DocTools 缺失时 doc/ 与 kdoctools_install(po) 自动配置掉

## 现象

`conan create` 的 CMake 配置阶段：

```
-- Found KF6: success (found suitable version "6.18.0", minimum required is "6.6.0")
   found components: Bookmarks CoreAddons Crash I18n WidgetsAddons XmlGui ConfigWidgets IconThemes
CMake Warning at CMakeLists.txt:42 (find_package):
  By not providing "FindKF6DocTools.cmake" in CMAKE_MODULE_PATH this project
  has asked CMake to find a package configuration file provided by
  "KF6DocTools", but CMake did not find one.
...
-- The following OPTIONAL packages have not been found:
 * KF6DocTools (required version >= 6.6.0), Tools to generate documentation
...
[100%] Built target kcharselect
```

构建、安装、消费者用例全部成功——只有一条 Warning 与 FeatureSummary 里的 OPTIONAL 记录。

## 根因

上游 `CMakeLists.txt`：

```cmake
find_package(KF6DocTools ${KF_MIN_VERSION})      # ← 没有 REQUIRED
set_package_properties(KF6DocTools PROPERTIES DESCRIPTION
    "Tools to generate documentation" TYPE OPTIONAL)
...
if (KF6DocTools_FOUND)
    add_subdirectory(doc)
    kdoctools_install(po)
endif()
```

`find_package` 无 `REQUIRED` ⇒ 找不到不致命；`if (KF6DocTools_FOUND)` ⇒ doc 手册子目录与
`kdoctools_install(po)` 整段被跳过。

## 判据与反误判

1. 看到 `Could not find a package configuration file provided by "X"` 先确认上游那句
   `find_package(X ...)` **有没有 REQUIRED**；没有则是可选依赖，不是缺依赖。
2. 反例参考：poXml（`DRAFT-poxml-kf6-doctools-docbook-dtd-and-gettextpo-probe`）确实提供了
   kdoctools，但 OHOS 上 doc/ 手册链还需要 DocBook XML 4.5 DTD，最终仍要裁剪 `add_subdirectory(doc)`
   + `kdoctools_install(po)`。所以"补 kdoctools"往往并不能让文档链在 OHOS 上跑通。
3. 只要 FeatureSummary 把该包列在 OPTIONAL 段、且 `Built target <app>` 出现，即视为通过；
   配方里如实记录该行作为证据。

## 修复

kcharselect 26.04.0 配方**不声明** kdoctools 依赖，靠上游可选语义自然配置掉；在
`conanfile.py` docstring、`notes.md`、`manifest.yaml`、`reports/test-report.md` 里如实记录
"KF6DocTools 为上游可选依赖，未提供 → doc/ 与 kdoctools_install(po) 被配置掉"。

## 验证

kcharselect/26.04.0 在 OHOS 6.0 aarch64 上 `conan create` + `conan-verify`（G0–G4/L2/L4/L5）
全绿；consumer 用例 4 用例 / 5 断言全通过。

## 适用范围

所有 ECM/KDE 工程（KDE Gear 26.04.0、KF6 系）在 OHOS 上的配方：
`KF6DocTools`、`Qt6LinguistTools` 一类"可选工具"缺失属预期，不应视为依赖缺口。
