# kmines 26.04.0 鸿蒙 PC 适配笔记

上游: <https://invent.kde.org/games/kmines>
版本: 26.04.0（KDE Gear 26.04.0 发行版）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

产物（install 树）：

- `bin/kmines` —— 扫雷游戏本体（Qt6/KF6 QGraphicsView 应用，链接
  KDEGames6/libkdegames）；
- `share/kmines/themes/*.desktop` + `*.svgz` —— 六套内置主题：
  default（kmines_oxygen.svgz，397159 B）、classic（42023 B）、
  clean_blue（52137 B）、clean_blue_dark（52022 B）、
  graveyard-mayhem（703266 B）、green（1285377 B）；
- `.desktop`、appdata 元数据与 hicolor 图标。

平台适配 **0 个补丁**：上游对 KF6DocTools 全程可选
（`find_package(KF6DocTools)` 无 REQUIRED，`doc/` 与
`kdoctools_install(po)` 都在 `if(KF6DocTools_FOUND)` 内），未发布该组件时
手册与 po 安装自动跳过；其余源码在 OHOS 上直接可编译。

测试口径：

- 上游套件：**0 用例**（解包树中无任何名称含 test 的文件或目录；全部
  CMake 文件无 add_test/ecm_add_test/enable_testing/BUILD_TESTING/ctest
  用法），`BUILD_TESTING=OFF`；清点证据见 `test_package/MANIFEST.yml`；
- 消费者测试（`test_package/`，R51 第三步）：4 用例，每用例独立输出
  TEST PASS/TEST FAIL，末尾 TEST SUMMARY 汇总，任一失败则以 1 退出；
- 真机结果：`TEST SUMMARY: 4 passed, 0 failed`，
  `conan create` 完整通过；八门禁报告见
  `reports/conan-verify-report.md`。

## 二、问题与处置

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `kconfigwidgets/6.18.0` 解析到本地未发布修订，要求 kconfig/6.26.0，与 KF6 6.18 闭包冲突 | 本地 conan 缓存残留未发布的配方修订 `kconfigwidgets/6.18.0#4f543774…`，优先级高于 registry 已发布修订 | 确认无在跑构建后 `conan remove -c 'kconfigwidgets/6.18.0#4f54377428809eb35df4ba94e592c6d7'`，回到已发布的 6.18.0 修订 |
| 2 | `kiconthemes/6.18.0` 从源码构建撞 `download.kde.org` TLS 墙（bfsu 镜像证书校验失败），且已发布修订要求 karchive/6.19.0、本图无对应二进制 | 镜像劫持 + 配方修订漂移 | 改用 registry 已发布的 `kiconthemes/6.18.0.1` 并 `override=True`：它是同配方对 karchive/6.18.0 的重建，package_id 与本图一致（kmousetool 26.04.0 先例） |
| 3 | `ktextwidgets/6.18.0` 源码下载同样被 TLS 墙拦截 | 同上 | 从 NJU 镜像取 tarball 作为 `core.sources:download_cache` 种子（2486624 B，sha256 9afb13…8edf），先删除 blob 的 `.dirty` 标记后离线构建成功 |
| 4 | ktextwidgets 的 ctest 5/5 在 0.1 秒内失败：loader 报 `$HOME/.cache/conan2/p/<hash>/p/lib/…` 缺库 | 已发布 KF6 制品的 DT_NEEDED 记录的是构建机绝对路径（CI 的 CONAN_HOME 为 `$HOME/.cache/conan2`），本机 CONAN_HOME 是 `$HOME/.conan2`，路径不存在 | 在设备上把真实库复制到 CI 布局路径（`kwidg…/lib/libKF6WidgetsAddons.so`、`kcode…/lib/libKF6Codecs.so`），ktextwidgets 构建与测试通过 |
| 5 | kmines 的 test_package 首次运行 `Error 127`，报 `libKF6XmlGui.so`/`libKF6NewStuffCore.so` 缺符号 | 同问题 4：绝对 NEEDED 指向 CI cache 的 hash 目录，本机不存在；`_fix_absolute_needed` 只尝试 symlink，HMDFS 拒绝 symlink(2)，回退缺失 | 修复层补 `shutil.copy2` 兜底：建父目录后 symlink，失败则复制真实库到烘焙路径（真机日志 `created 8 absolute-NEEDED compatibility fallbacks`） |
| 6 | test_package 在 `KGameRenderer` 析构处 SIGSEGV（`renderer scope end` 之后） | 测试把 `KGameThemeProvider` 放在栈上；`KGameRenderer` 构造时对无 parent 的 provider 执行 `setParent(this)`，析构时 `delete` 该 provider——等于对栈指针执行 delete，双重释放 | 照上游 `KMinesScene` 的所有权模型：`new KGameThemeProvider` 后交给 renderer 托管；修复后 4 用例全绿 |
| 7 | 版本串校验最初按 `4.0.260400` 编写导致误判 | `KMINES_VERSION = "4.0." + RELEASE_SERVICE_COMPACT_VERSION`，compact 为 26/04/0 直接拼接、不补零 | 按安装后实际输出 `kmines 4.0.26040` 校验（rc=0） |
| 8 | `app_boot` 用例曾为假 PASS：进程因镜像无 DBus 会话总线在启动阶段即退出（rc=1），旧的 `msleep` + `state()` 读不到子进程退出通知，仍报存活 | 无事件循环时 `QProcess::state()` 不刷新；本镜像未运行会话总线，也无 `dbus-launch` | 改用 `waitForFinished(5000)` 驱动子进程状态机并持续排空管道；无总线镜像上以 KDBusAddons 的 `DBus session bus not found` 精确诊断作为「ELF/Qt/KF6 加载链已走通」判据，任何其他早退仍判失败 |
| 9 | 制品在 `package()` 后仍是无签名 ELF，依赖测试侧就地签名才能执行；且 `bin/kmines` 的 DT_NEEDED 记录构建机 Conan cache 绝对路径 | OHOS 加载器拒绝未签名 ELF；未签名的原因不是漏做，而是「签名后改写 DT_NEEDED 会使 .codesign 失效」，必须先规范化再签名，两步都必须发生在制品产出环节 | 仿 kbreakout 26.04.0：`package()` 内先将路径形 DT_NEEDED 改写为纯 basename（等长改写 .dynstr），再对包内全部 ELF 自签名；测试侧只保留运行时兼容层，不再改写被测包目录；绝对 NEEDED 兜底的写盘范围加 Conan cache/build 根校验 |

## 三、依赖版本

```
qtbase/6.11.1  qtsvg/6.11.1
kconfig/6.18.0  kconfigwidgets/6.18.0  kcoreaddons/6.18.0
kcrash/6.18.0   kdbusaddons/6.18.0     kdnssd/6.29.0
ki18n/6.18.0    ktextwidgets/6.18.0    kwidgetsaddons/6.18.0
kxmlgui/6.18.0  kiconthemes/6.18.0.1 (override)
libkdegames/26.04.0.1                  karchive/6.18.0 (override)
ecm/6.26.0 (tool_requires)
```

test_package 额外显式声明 `openal-soft/1.25.2`，补齐
`libKDEGames6.so` 的运行时 DT_NEEDED 闭包。

## 四、验证结果

真机（HarmonyOS PC，ohos-aarch64 profile）`conan create`：

```
kmines/26.04.0@ohpcd/stable (test package): Running test()
TEST PASS: installed_binary_version
TEST PASS: theme_discovery
TEST PASS: theme_sprite_render
TEST PASS: app_boot
TEST SUMMARY: 4 passed, 0 failed
kmines/26.04.0@ohpcd/stable (test package): consumer test passed
```

消费者用例内容：

1. `installed_binary_version`：离屏执行安装后的 `bin/kmines --version`，
   退出码 0 且输出含 `kmines` 与 `4.0.26040`；
2. `theme_discovery`：`KGameThemeProvider::discoverThemes("themes")` 发现
   六套主题，逐一检查 graphicsPath 存在、大小 > 1000 且首三字节为
   gzip 魔数 `1f 8b 08`；
3. `theme_sprite_render`：`spriteExists("mainWidget")` 为真，
   `spritePixmap("mainWidget", 64x64)` 返回非空 64x64 QPixmap（真实
   SVGZ -> QSvgRenderer -> QPixmap 链路）；
4. `app_boot`：以隔离 HOME 离屏启动安装的 kmines，要求启动链路取得
   进展——进程存活满 5 秒，或无 DBus 会话总线的镜像上以 KDBusAddons
   的 `DBus session bus not found` 精确诊断退出（证明 ELF/Qt/KF6 加载
   链已完整走完；其他早退判失败）。

## 五、注意事项

- KGameRenderer 会托管无 parent 的 KGameThemeProvider，测试与二次开发
  不要把 provider 放在栈上；
- 制品在 `package()` 内完成 DT_NEEDED 路径规范化与 ELF 自签名（kbreakout
  26.04.0 先例：先改写再签名，否则 .codesign 失效）；消费者测试直接运行
  该已签名制品，不再就地改写 Conan 缓存中的包目录；
- KSharedDataCache 在 HMDFS 上会打印
  "Couldn't establish file backed memory mapping, will fallback to
  anonymous memory"；属无害回退，渲染与析构均正常；
- 已发布 KF6/KDEGames6 制品的 DT_NEEDED 残留构建机绝对路径与
  `../../bin/*.so` 相对路径，消费者需要 test_package 里的
  fallback/symlink-copy 农场；HMDFS 禁 symlink 时以复制代替；
- kmines 的版本串为 `4.0.26040`（compact 版本不补零），不是
  `4.0.260400`。
