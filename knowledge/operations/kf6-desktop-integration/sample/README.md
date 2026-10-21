# sample/ —— 桌面集成组件必需化的最小复刻

本目录是 `knowledge/operations/kf6-desktop-integration/` 的**源码级**样例，只复刻结构，
不含业务代码，用来验证检测脚本的判定边界，并给人工对照一份「命中长什么样」。

## 结构

| 文件 | 复刻的上游写法 | 检测器归类 |
|---|---|---|
| `CMakeLists.txt` | `find_package(KF6 ... REQUIRED COMPONENTS CoreAddons DocTools)` | `doc-tools-component` |
| `CMakeLists.txt` | `kdoctools_install(po)` | `doc-tools-install-po` |
| `CMakeLists.txt` | `add_subdirectory(doc)` | `doc-subdirectory` |
| `doc/CMakeLists.txt` | `kdoctools_create_handbook(...)` | `doc-tools-handbook` |
| `mime/CMakeLists.txt` | `find_package(SharedMimeInfo REQUIRED)` | `mime-find-package-required` |
| `mime/CMakeLists.txt` | `update_xdg_mimetypes(${KDE_INSTALL_MIMEDIR})` | `mime-update-xdg` |

## 自测

```sh
sh ../detect-kf6-desktop-integration.sh sample          # 期望 hard=6, exit 1
```

本样例**不参与构建**（缺少真实依赖与 `kf6-di-sample-mimetypes.xml`），它的用途是让检测器
有一个稳定、无外部依赖的命中基线；构建级真实样例见
`archives/p/palapeli/26.04.0`（`reproduce.sh` 对它跑双向验证）。

## 处置后的对照

按 `../strategy.md` 的 B 策略处理后，本目录应变为：

```diff
-    DocTools
-add_subdirectory(doc)
-kdoctools_install(po)
-find_package(SharedMimeInfo REQUIRED)
-update_xdg_mimetypes(${KDE_INSTALL_MIMEDIR})
```

对应检测器 `hard=0`、`exit 0`。若只删其中一处，configure 仍会失败：
删组件表留下 `add_subdirectory(doc)` → `Unknown CMake command "kdoctools_create_handbook"`；
删 `add_subdirectory(doc)` 留下 `kdoctools_install(po)` → `Unknown CMake command "kdoctools_install"`。
