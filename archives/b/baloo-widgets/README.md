# Baloo Widgets (baloo-widgets)

KDE 文件索引框架 Baloo 的 Qt Widget 组件库：把文件元数据（类型、大小、标签、评分、
创建/修改时间、音频视频属性等）以控件形式提供给应用。属于 KDE Frameworks 生态
（KF6 6.14 系列配套版本号 26.04.0），被 Dolphin 等文件管理器使用。

- 上游主页：<https://invent.kde.org/libraries/baloo-widgets>
- 版本：26.04.0（KF6 分支）
- 构建系统：CMake
- 许可：LGPL-2.1-or-later

## 公开 API

头文件安装在 `include/KF6/BalooWidgets/Baloo/`：

| 类 | 用途 |
|----|------|
| `Baloo::FileMetaDataWidget` | 展示/编辑一个文件的元数据（标签、评分、注释、时间、类型专属属性） |
| `Baloo::TagWidget` | 标签输入控件（自动补全 + 新建标签）；**构造需传 parent**，内部解引用 `parent->foregroundRole()` |
| `Baloo::FileMetaDataConfigWidget` | 文件元数据属性在详情视图中的显隐配置 |

## 适配要点（OHOS PC / arm64）

- 依赖 KF6 6.14 全线（Config/CoreAddons/I18n/KIO/Baloo/FileMetaData/WidgetsAddons）与 Qt 6。
- 两个 KF6 插件安装到 `lib/plugins/kf6/{propertiesdialog,kfileitemaction}/`（KIO 的属性页与
  文件项动作），未做裁剪。
- i18n：`ki18n_install(po)` 在 OHOS 下原生可用，locale 目录正常产出，无需补丁。
- **构建/测试期阻塞点**：已发布的部分 KF6 包缺 `DT_SONAME`，其 `DT_NEEDED` 里带
  `../../bin/...` 相对路径，构建期/测试期加载失败。解决办法是在构建目录各级祖先构造
  `bin/` 兼容软链（本包 `kb_compat_shim` 选项，默认开启）。知识条目见
  `knowledge/tools/kf6-relative-needed/`（E2296）与 E537。
- 产物侧**不要**做任何构建后 ELF 改写（本平台改写后的 `.so` 加载报 `Permission denied`）。

## 验证

- `conan create` 全流程通过（G0-G4 全 PASS，`.ci-result.json` exit 0）。
- test_package：18 项公开 API 消费者断言全 PASS。
- 上游测试 6 项实测执行：3 项通过；3 项因已发布 `kfilemetadata/6.14.0` 不含 taglib
  音频抽取器而失败（已在 `26.04.0/notes.md` 申报原因）。
