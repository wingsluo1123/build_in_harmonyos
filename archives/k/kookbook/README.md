# KookBook

KookBook 是 KDE 出品的食谱管理器，面向**结构化 Markdown**食谱集合：
食谱以 `*.recipe.md` 存放，文件里用 `# 标题`、`### Ingredients`、
`### Directions`、`### Metadata` 等固定小标题承载结构化信息，其余部分按
CommonMark 渲染。KookBook 扫描一个集合目录（含子目录）中的全部
`*.recipe.md`，解析出标题、配料（数量/单位/食材）、tags 与元数据，并按
标题列表、tags 树、配料树三种视图检索，同时提供原始 Markdown 视图。

一个上游源码树产出两个前端：

| 产物 | 说明 |
|---|---|
| `bin/kookbook` | Qt6 Widgets 桌面应用（本平台主产物） |
| `bin/kookbooktouch` | Qt6 Qml/Quick 触屏应用 |

其余交付物：`share/applications/*.desktop`、`share/metainfo/*.appdata.xml`、
`share/icons/hicolor/**`、`share/kookbook/doc/krecipes.py`（krecipes 数据库转换数据）。

- 官网 / 上游仓库：<https://invent.kde.org/utilities/kookbook>
- 许可证：MIT
- 本仓已归档版本：见 [manifest.yaml](manifest.yaml)

## HarmonyOS PC 适配状态

| 版本 | 状态 | 构建系统 | 说明 |
|---|---|---|---|
| [0.3.0](0.3.0/) | built | cmake | Qt6 移植版；裁剪 PrintSupport 打印功能，保留双前端 |

### 已知限制（0.3.0）

- **打印 / 打印预览不可用**：上游顶层 `find_package(Qt6 … COMPONENTS
  Widgets PrintSupport Qml)` 同时要求 `PrintSupport` 与 `Qml`。制品仓中带
  `Qt6::PrintSupport` 的 Qt6 base 线是 `qtbase/6.11.1.3`，但唯一可用的
  `qtdeclarative`（`6.11.1` / `6.11.1.1`）在 `requirements()` 内精确声明
  `qtbase/6.11.1`（conan 版本冲突），而面向 `6.11.1.3` 的
  `qtdeclarative/6.11.1.2` 缺 `qtshadertools/6.11.1` 在该组合下的 binary。
  二者当前不可兼得，本配方保留 `Qml`（触屏前端）并裁剪 `PrintSupport`，
  与 `kgraphviewer`、`kdiagram`、`kapow`、`conducteo` 等配方同一取舍。
  被移除的是主工具栏的"打印当前食谱"与"打印预览当前食谱"两个动作，
  其余功能不受影响。
- 恢复打印能力需要先把 `qtshadertools` 针对 `qtbase/6.11.1.3` 重建发布
  （属独立依赖项任务），再切换到 `qtbase/6.11.1.3 + qtdeclarative/6.11.1.2`。

详细适配记录（依赖拓扑实测证据、补丁清单、测试统计、规则 12 用例）见
[0.3.0/notes.md](0.3.0/notes.md)。
