# Zenmap

Nmap 的图形前端与扫描结果查看器（GTK3 GUI + 结果解析/对比库）。

- 上游：https://nmap.org/zenmap/
- 许可证：Nmap Public Source License (NPSL)
- 适配语言：Python（纯 Python，无 C/C++ 编译）
- 运行依赖：`nmap/7.99`（OHOS 适配版扫描器）

## 包内容

| 模块 | 说明 |
|------|------|
| `zenmapCore` | 纯 Python 核心：选项解析、XML 解析、结果搜索、配置 |
| `zenmapGUI` | GTK3 界面（运行期需要 PyGObject/GTK3） |
| `radialnet` | 拓扑视图（运行期需要 PyGObject/GTK3） |
| `bin/zenmap` | 图形前端入口脚本 |

## 平台说明

`zenmapGUI` / `radialnet` 在导入期即 `import gi`（PyGObject → GTK3）。当前
OHOS 制品仓中的 `pygobject/3.58.0` 产物无法被消费（扩展名带平台标签、且
gtk/gobject-introspection 未随包发布 `.typelib`），因此 GTK3 属于**平台运行期
前置条件**，不随本 Conan 包声明。纯 Python 的 `zenmapCore`（选项解析、nmap XML
解析、扫描结果搜索/对比）在鸿蒙上完全可用，并由 `test_package/` 验证。

详见 `7.99/notes.md`。
