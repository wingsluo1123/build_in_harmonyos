# kcolorchooser 26.04.0 — Conan `Environment.append()` 空格连接路径导致 Qt 插件找不到

## 现象

KF6 应用的 `conan create` 到 test_package 阶段：

```
[test] 用例 1b: --version
Signal 6 (core dumped)
qt.qpa.plugin: Could not find the Qt platform plugin "offscreen" in
  "/<...>/qtbase/p/plugins/platforms /<...>/qtbase/p/plugins/platforms"
This application failed to start because no Qt platform plugin could be initialized.
```

注意路径被**空格**连接、且重复两次——Qt 把它当成一个目录名。

## 根因

`conan.tools.env.Environment.append(var, value)` 对普通变量默认分隔符是**空格**，
不是 `os.pathsep`。Qt/KF 的 test_package 常见写法：

```python
for dep in self.dependencies.values():
    for rel in ("plugins", os.path.join("lib", "plugins")):
        d = os.path.join(dep.package_folder, rel)
        if os.path.isdir(os.path.join(d, "platforms")):
            env.append("QT_QPA_PLATFORM_PLUGIN_PATH", os.path.join(d, "platforms"))
```

Qt 因此收到 `"/a/plugins/platforms /b/plugins/platforms"`，在 `/a/plugins/platforms /b/plugins/platforms`
（一个字面目录名）下找 `libqoffscreen.so` → 找不到 → `QApplication` 构造失败 →
`qFatal` → OHOS 上 Signal 6 core dumped。

插件其实**就在**正确目录里，也没有签名/NEEDED 问题——容易被误判为"插件未打包"。

## 修复

```python
env = Environment()
env.define("LD_LIBRARY_PATH", os.pathsep.join(lib_dirs))
env.define("QT_QPA_PLATFORM", "offscreen")
if plugin_dirs:
    env.define("QT_PLUGIN_PATH", os.pathsep.join(plugin_dirs))
if platforms:
    env.define("QT_QPA_PLATFORM_PLUGIN_PATH", os.pathsep.join(platforms))
```

要点：
1. 用 `define()` 注入**已用 os.pathsep 连接**的值；或使用 path 语义的
   `prepend_path()/append_path()`，不要用 `append()`。
2. 收集目录时去重（同一 qtbase 常出现两次）。
3. 诊断：`QT_DEBUG_PLUGINS=1` 会打印 Qt 实际检查的目录；看到
   `checking directory path "A B"`（含空格的一个目录）即命中本模式。
   若目录正确仍报同一句，才继续排查插件自身 NEEDED / `.codesign`。

## 验证

kcolorchooser/26.04.0 修正后在 OHOS 6.0 aarch64 上 `conan create` 全绿：
`--version` / `--help` / `--author` / `--license` 与共享库 closure 加载用例全部通过。

## 适用范围

任何在 Conan test_package 中用 `self.dependencies` 组装 Qt 插件搜索路径的
Qt6/KF6 配方（kblocks / kjumpingcube / kteatime 同款代码结构）。
