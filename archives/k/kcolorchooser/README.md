# kcolorchooser

KDE 调色板与颜色选择器（KColorChooser）：Qt6/KF6 Widgets 图形应用，封装
`QColorDialog` 并提供 KDE 命令行接口（`--color` 指定初始颜色、`--print`
把所选颜色输出到 stdout、`--author`/`--license` 元数据）。

- 上游：https://invent.kde.org/graphics/kcolorchooser
- 适配版本：26.04.0（archives/k/kcolorchooser/26.04.0/）
- 依赖：qtbase/6.11.1 + KF6 6.18.0 闭包（CoreAddons/I18n/XmlGui 及其运行时传递依赖）

## 上游测试

kcolorchooser 26.04.0 **无任何上游测试**（0 用例）：tarball 内无 `autotests/`、
无 `tests/` 目录，`CMakeLists.txt` 仅注册可执行目标 `kcolorchooser` 且未注册任何
测试（无 `add_test`/`enable_testing`/`BUILD_TESTING`/`ecm_add_test`）；上游 CI 的
`.gitlab-ci.yml` 引入构建/打包/lint 模板，但这些模板仅在项目注册了测试时才执行
ctest，本项目未注册；`.kde-ci.yml` 也未声明测试目标。清点证据与消费者用例详见
`26.04.0/test_package/MANIFEST.yml`。

## 许可

上游 `COPYING` 与 `org.kde.kcolorchooser.appdata.xml` 声明 **MIT**（Conan
`license` 字段据此填写）；注意上游 `kcolorchooser.cpp` 的 KAboutData 传的是
`BSD_2_Clause`，因此运行时 `--license` 输出为 BSD-2-Clause 文本（上游自身不一致）。
