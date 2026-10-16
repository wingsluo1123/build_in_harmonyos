# DRAFT-kcron-26.04.1-qml-kcm-consumer-verification

> 来源: kcron 26.04.1 适配（archives/k/kcron/26.04.1）| Status: Draft | 2026-10-16

## 现象 / 问题

QML KCM（kcmutils 消费者）以插件形态交付，没有 CLI：一个 MODULE 目标
`kcm_cron.so`（配 `kcmdesktopfilegenerator` 生成的 `.desktop`），KAuth 型
另带提权助手（`kcron_helper` + `local.kcron.crontab` 激活文件）。常见的
弱验证——文件存在性、`dlopen` 成功——都不能证明消费者契约：

- 插件加载成功 ≠ KCM 能构造：本包 KCM 构造函数在无 `/etc/passwd` 条目的
  uid 下会走 `getpwuid()` 空路径（补丁 0004 前直接终止宿主进程）；
- 只跑 `import` 不驱动组件，会漏掉应用自己的 QML 逻辑（本包
  TaskValidator 的空命令/绝对路径分支全部在 QML 组件内）；
- 交互槽（`save()`/add/modify/remove）需要完整 Plasma 会话，目标平台
  根本没有 System Settings 可点——不申报就会把"未验证"伪装成"已通过"。

## 推荐方案（kcron 已实证）

消费者用例按三层组织（`test_package/test_kcron.cpp`，7 组 25 断言）：

1. **产物定位**：`kcm_cron.so` / `kcm_cron.desktop` / `kcron_helper` /
   KAuth 激活文件逐一断言（激活文件 backend 依赖，可降级为 INFO）；
2. **插件加载**：`QPluginLoader::metaData()` 断言 className/IID；
   `KPluginFactory::instantiatePlugin<QObject>()` 走 KCMUtils 同款路径
   实例化（KCM 的 QObject 接口沿继承链匹配，不要求精确类型）；
3. **QML 资源面**：真实 `QQmlEngine` + `QT_QPA_PLATFORM=offscreen`，
   `QML2_IMPORT_PATH` 指向包的 `qml/`（应用私有模块
   `org.kde.private.kcms.cron`），驱动组件跑真实文件系统校验三分支
   （空命令拒绝 / 真实可执行通过 / 缺失绝对路径 File not found）。

配套要点：

- 环境归一化：独立 `HOME`/`XDG_RUNTIME_DIR`，`QT_PLUGIN_PATH` /
  `QML2_IMPORT_PATH` 用 **os.pathsep 显式拼接**（Conan `Environment.append()`
  用空格拼接，Qt 会把整串当单个目录——kcolorchooser 先例）；
- 平台降级路径写**自适应断言**：无 passwd 条目 uid 下断言
  `CTInitializationError` 出现且 KCM 仍可实例化、模型空但属性可达；
- **交互面如实申报**：`save()` 等只在完整会话可达的槽，在 test_package
  与配方 docstring 双向写明"仅交互可达、未验证"，不用桩冒充；
- 断言计数按 PASS 口径（25），INFO 仅回显不计入分母。

## 验证证据（真机，2026-10-16）

```
[test] PASS CASE 1a..1c  kcm_cron.so / kcron_helper / kcm_cron.desktop
[test] PASS CASE 2a..2b  QPluginLoader load + metadata (className=KCMCronQmlFactory)
[test] PASS CASE 3a..3d  KPluginFactory instantiate + No password entry found for uid
[test] PASS CASE 5d..5g  QML TaskValidator: empty rejected / real validates / File not found
[test] ALL CONSUMER CASES PASSED (0 failure(s))
ctest: 1/1 Test Passed              （reports/test-package-ctest.log）
conan-create.log:1057-1062  100% tests passed, 0 tests failed out of 1
```

上游套件另有 `taskvalidatortest`（1 目标 9 用例）在 `build()` 内实跑
（`BUILD_TESTING=ON`）；`QCoreApplication::applicationFilePath()` 是
无 `/usr/bin` 平台上绝对路径用例的可移植锚点（补丁 0007）。

## 关联

- 插件构造期平台假设族：getpwuid 空值（DRAFT-10175 rmlint / DRAFT-cpdb-libs）、
  无 crontab 后端空模型容忍（kcron 补丁 0005/0006）；
- KCM 插件组基线（KIO 依赖面）：kinfocenter-6.7.2-kcm-pluginset 草稿；
- 上游测试计数与清点：test_package/MANIFEST.yml（R51 三步）。
