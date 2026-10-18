# 处理策略：桌面集成组件（KF6DocTools / SharedMimeInfo）

本文件给出 `detect-kf6-desktop-integration.sh` 命中后**该做什么、禁止做什么**，每条策略附适用前提与验证口径。

## 0. 先说清这两样东西是什么

| 组件 | 上游怎么用 | 在 OHOS 上算不算运行期依赖 |
|---|---|---|
| `KF6DocTools`（kdoctools） | 顶层 `find_package(KF6 ... REQUIRED COMPONENTS ... DocTools ...)`；`add_subdirectory(doc)` + `kdoctools_create_handbook()` 生成手册；`kdoctools_install(po)` 安装翻译 | **否**。手册是发行版文档产物，游戏/工具本身不读取它 |
| `SharedMimeInfo` | `find_package(SharedMimeInfo REQUIRED)` + `update_xdg_mimetypes(${KDE_INSTALL_MIMEDIR})`，装机后刷新系统 MIME 数据库 | **否**。ECM 的 `FindSharedMimeInfo` 只找 `update-mime-database` 工具；MIME 数据库刷新是桌面会话的装机步骤 |

## 策略选择总表

| 命中形态 | 首选策略 | 禁止 |
|---|---|---|
| `DocTools` 落在 REQUIRED 组件表，且制品仓没有**与闭包同线**的 kdoctools | **B：可选化裁剪**（补丁同时处理组件表 / `add_subdirectory(doc)` / `kdoctools_install(po)`） | 把 6.19.0 硬塞进 6.18 闭包（见 §2 实测后果）；把 `REQUIRED` 改 `QUIET` 却不删 `add_subdirectory(doc)`（下一层仍报 `Unknown CMake command`） |
| `DocTools` 落在 REQUIRED 组件表，但制品仓有**同线**版本 | **A：官方包满足**（`requires` 该版本，源码零改动） | 惯性地先打补丁（白白丢掉手册，且增加补丁维护面） |
| `SharedMimeInfo` 被 REQUIRED，且制品仓有 shared-mime-info | **A：`tool_requires("shared-mime-info/<ver>")`**，让 ECM 找到 `update-mime-database` | 手写空壳 stub 冒充 `update-mime-database`；删掉 `install(FILES *.xml)` |
| `SharedMimeInfo` 被 REQUIRED，但制品仓没有该包 | **B：可选化**（`QUIET` + `if(SharedMimeInfo_FOUND)` 守卫 `update_xdg_mimetypes`），保留 MIME XML 安装 | 直接删掉整个 mime 子目录（MIME 定义本身是有效的运行期数据） |

## 策略 A：用官方包满足（首选，源码零改动）

**前提**：制品仓存在与闭包同版本线的包，或该组件只需要一个**工具**在 PATH 上。

`SharedMimeInfo` 属于后者——它不需要同线，只需要工具可用：

```python
def build_requirements(self):
    self.tool_requires("shared-mime-info/2.5.1")
```

实测（palapeli 26.04.0，本机 OHOS aarch64）：

```
-- Found SharedMimeInfo: .../shared-mime-info/2.5.1/bin/update-mime-database (found version "2.5")
package(): Packaged 1 '.cache' file: mime.cache        # update-mime-database 真的跑过
```

`mime.cache` 出现在包里，说明 `update_xdg_mimetypes()` 正常执行，源码一行未改。

**为什么 DocTools 不走 A**：`kdoctools/6.19.0` 的配方把整条 6.19 线当依赖——
`karchive/6.19.0`、`extra-cmake-modules/6.19.0`、`libxslt/1.1.45.1`、`libxml2/2.15.Z`、`openssl/3.5.6.1`、
`qtbase/6.11.Z`，且其 `KF6DocToolsConfig.cmake` 会对 `KF6Archive` 做 6.19 的版本校验；
而 palapeli 所在的闭包被 `libkdegames/26.04.0.1`、`kiconthemes/6.18.0`、`knewstuff/6.18.0`
钉在 **6.18.0**。引入 6.19.0 等于在一个图里放两条 KF6 线，只能靠 `override` 强行压回去——
压回去之后 `KF6DocToolsConfig` 的版本校验就对着 6.18 的 `KF6Archive`，属于把「版本线断裂」
从 CMake 层挪到 conan 图里，问题没解决，只是更难诊断。

## 策略 B：可选化裁剪（补丁模板）

以 palapeli 26.04.0 为例，**三处必须同时处理**，缺一仍会在 configure 阶段失败：

```diff
@@ find_package(KF6 ... REQUIRED COMPONENTS ...)
-    DocTools
@@ 顶层目录
-add_subdirectory(doc)
@@ 顶层目录末尾
-kdoctools_install(po)
```

- 只删 `DocTools` 组件 → `add_subdirectory(doc)` 里的 `kdoctools_create_handbook()`
  变成 `Unknown CMake command`；
- 只删 `add_subdirectory(doc)` → 顶层 `kdoctools_install(po)` 仍报未知命令；
- 三处一起删 → 手册与文档翻译不再安装，程序本体、插件、MIME、图标、desktop 文件全部保留。

MIME 侧若制品仓没有 shared-mime-info，用下面的等价改造（保留 XML 安装）：

```diff
-find_package(SharedMimeInfo REQUIRED)
+find_package(SharedMimeInfo QUIET)

 install(FILES <app>-mimetypes.xml DESTINATION ${KDE_INSTALL_MIMEDIR})
-update_xdg_mimetypes(${KDE_INSTALL_MIMEDIR})
+if(SharedMimeInfo_FOUND AND TARGET SharedMimeInfo::update-mime-database)
+    update_xdg_mimetypes(${KDE_INSTALL_MIMEDIR})
+endif()
```

补丁落地约定（与仓库其它补丁一致）：

- 补丁文件放 `archives/<首字母>/<软件名>/<版本>/patches/`，`conandata.yml` 用
  `patch_file:` 完整相对路径登记；
- 补丁必须能被 `git apply --check` 干净应用（本机 `/usr/bin/patch` 是 toybox 实现，
  对任何补丁都是静默 no-op，**不能**用它验证）；
- hunk 计数必须精确：`@@ -6,6 +6,14 @@` 这类头部错一个数字，patch(1) 会静默不动。

## 验证口径（双向，缺一不可）

| 方向 | 做法 | 期望 |
|---|---|---|
| 关策略 | `conandata.yml` 的 `patches` 置空后 `conan create` | configure 失败，日志含 `Could NOT find KF6 (missing: DocTools)` 与 `Missing the following required components: DocTools` |
| 开策略 | 补丁登记后 `conan create` | `rc=0`，包内容含 `bin/<app>`、插件 `.so`、`mime.cache`、`.desktop`、图标 |
| 检测器 | `detect-kf6-desktop-integration.sh <源码树>` / `--log <日志>` | 源码树 6 处 HARD；失败日志 3 处 HARD；干净树 0 处 |

## 限制与不适用

- 本策略**放弃手册与文档翻译**。若交付物必须带手册（例如面向桌面发行版的手册包），
  应改为在制品仓补发与闭包**同线**的 kdoctools，而不是套用本策略。
- 只对「文档/MIME 这类桌面集成产物」成立。若某个 `find_package(... REQUIRED)`
  指向的是**运行期真的会用**的库（如 `KIOWidgets`、`Qt6::DBus`），删除它属于篡改功能，
  不在本策略范围内——那类问题应走补依赖/补变体包的路子。
- 不涉及 `KDEInstallDirs` 之外的安装路径改动，也不改变 `install(FILES ...)` 的目标目录。
- 若上游把手册绑进运行时资源（极少数应用在 about 页内嵌 `index.docbook`），裁剪后该页面会缺内容，
  需在 notes 里明示。
