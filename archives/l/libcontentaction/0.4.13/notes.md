# libcontentaction 0.4.13 — Conan 配方笔记

## 软件信息

- **名称**: libcontentaction — 内容与动作关联库（MIME 默认动作、方案动作、内容高亮、桌面动作触发），附 `lca-tool` 命令行工具
- **版本**: **0.4.13**（上游 sailfishos/libcontentaction tag `0.4.13`，与 Arch extra/libcontentaction 0.4.13 同源）
- **许可证**: LGPL-2.1-or-later（上游 COPYING）
- **构建系统**: 上游 qmake6；本配方提供**等价 CMake 移植**（编译同一批上游 `src/*.cpp` 与 `tests/*.cpp`，零改动）
- **目标平台**: OHOS aarch64（HarmonyOS PC / DAYU200）

## 依赖（Conan）

| 依赖 | 版本 | 说明 |
|------|------|------|
| qtbase | 6.11.1.1 | Qt6 Core/DBus/Test/Xml（OHOS armv8 二进制已发布；`cmake_find_mode=none`，需手工注入 CMAKE_PREFIX_PATH。6.11.1.2 配方要求 host=build 原生构建、交叉消费被拦，固定 6.11.1.1） |
| glib | 2.84.0.2 | glib/gio（GKeyFile、GAppInfo/g_desktop_app_info、GFile/GContentTypes） |

### mlite 兼容层（port/mlite-compat/）

上游还依赖 nemomobile **mlite**（`MDesktopEntry` / `MDConfItem` / `MRemoteAction`）。
制品仓无 mlite 且「一库一 PR」不允许本 PR 捎带引入新库，故在配方内实现上游实际
调用的 API 子集，语义等价：

| 类 | 上游用途 | 兼容层实现 | 语义差异 |
|----|---------|-----------|---------|
| MDesktopEntry | `mime.cpp`/`dbus.cpp`/`service.cpp` 读 .desktop | freedesktop Desktop Entry 解析（含 `\s \n \t` 转义），键名沿用 `Desktop Entry/<Key>` | 不接 MeeGo 翻译目录，`name()` 走 `Name[<locale>]/Name` 兜底 |
| MDConfItem | `contentaction.cpp` 读 `/desktop/sailfish/application_desktop_paths` | 读 `$MD_CONF_FILE` ini（多值 `;` 分隔） | 未配置=键不存在=上游同语义回退（放行全部 .desktop 路径） |
| MRemoteAction | `dbus.cpp` 触发远端 DBus 动作 | QtDBus 直连会话总线（`asyncCall`/`call`） | 无 mapplauncherd 中转，方法调用语义一致 |

## 构建要点

- `port/CMakeLists.txt`（构建期置于源码根）：`libcontentaction6.so`（对齐上游 Qt6 下
  的 `libcontentaction6` 命名）、`lca-tool`、4 个 QTest 可执行文件；`DEFAULT_ACTIONS`
  宏默认 `/usr/share/contentaction`（与上游一致，运行期可被 `CONTENTACTION_ACTIONS` 覆盖）。
- `highlight1.xml` 构建期按上游 `data/data.pro` 规则生成（`gen-regexps` 产出
  `regex.sed` → `sed` 替换 `highlight1.xml.in` 模板），安装到 `share/contentaction/`。
- HarmonyOS PC 原生构建机自动做 XPM 签名（`/data/service/hnp/bin/binary-sign-tool` 存在时）。

## 测试策略

上游测试套件 = `tests/tests.xml.in` 的 **14 个用例**，全部经上游自带入口包装
`lca-cita-test`（PATH/XDG_DATA_HOME/XDG_DATA_DIRS/CONTENTACTION_ACTIONS）按原样驱动；
目标二进制经 `port/run-guest.sh` 执行（aarch64 原生直跑 / x86 交叉走 qemu-user +
OHOS musl 运行根）：

| 层级 | 是否运行 | 说明 |
|------|----------|------|
| 上游 tests.xml.in 14 用例 | **是**（build() 内 ctest，逐 case 记录） | 4 个 QTest 二进制（8 函数）、test-highlight.sh（约 100 断言）、gen-regexps 正则套件、test-defaults/test-regexps 等 CLI 用例、meta 负例；依赖 python-dbus/可写 /tmp 的用例环境缺失时记 **SKIP(77)** 并在报告列技术原因，绝不伪通过 |
| test_package 消费者端到端 | **是**（can_run 或 qemu 执行；真机另取证据） | 配置落盘 → ContentInfo → Action 查询 → 默认动作写读回环 → 方案动作 → 高亮检索 → `trigger()` 触发并校验执行痕迹 |

**测试床（testbed）**：复刻上游 `CONTENTACTION_TESTDIR` 布局（`bin/`、`data/`、
`applications/`、测试脚本与数据）；`.in` 夹具按上游 qmake 规则做 `@PATH@` 替换。

**两个配置落点的区分**（上游语义）：
- `lca-cita-test` 环境 → `testbed/data/`（`highlight1.xml` + `hl-examples.xml` 并存，
  与上游 `data.pro` testdata 一致）：test-findhighlights / test-regexps 等用例；
- 部署区 → `testbed/share-action/`（仅部署版 `highlight1.xml`，等价上游
  `/usr/share/contentaction`）：`test-highlight.sh`（上游显式 export 该绝对路径）与
  `gen-regexps test`（不经 lca-cita-test）。二者重名正则会被后读文件覆盖，必须分开。

**mime 数据库夹具**：上游 test-info/test-action 依赖系统 shared-mime-info 的类型
描述/内容探测（"Plain text document" / "PNG image"）。OHOS 无该组件，测试床提供
最小数据库（`port/mime-fixture/`，文案与上游期望一致，glob/magic 取自
freedesktop.org.xml 同名条目）。三个实测约束（见 `port/mime-fixture/README.md`）：

- GIO 只读 `update-mime-database` **生成后**的库；裸 `packages/*.xml` 不生效
  （只有 XML 时 `forFile()` 返回 `application/octet-stream`，描述退化为 `"text/plain type"`）；
- 生成产物必须**整棵**提供，`<media>/<subtype>.xml`（如 `text/plain.xml`）不能少：
  类型描述取自这些文件，只给 `mime.cache`+`globs2`+`magic` 则文件探测正常但描述退化；
- 生成产物**含 NUL 字节（本质二进制），不得提交进仓库**：GitCode 导出的 PR diff 会把它
  渲染成缺 `GIT binary patch` 段的 binary patch，CI 的 `checkout-pr` 步骤 `git apply`
  报 `error: missing binary patch data for '.../mime.cache'` 而失败。
  故仓库只提交 XML 源，数据库由 `port/CMakeLists.txt`（测试床）与
  `test_package/conanfile.py`（消费者）在构建期用宿主 `update-mime-database` 生成。

落点为 `<XDG_DATA_HOME>/mime`（lca-cita-test 的 `${HOME}/tests-home`），优先级高于
`XDG_DATA_DIRS` 中的系统库，保证用例结果不随构建机是否安装 shared-mime-info 而变。

**环境等价要点（GIO ≥ 2.80 启动路径）**：`GDesktopAppInfo` 触发动作时经
`gio-launch-desktop` 助手落地子进程；发行版把它装在 PATH 内，Conan 的 glib 包放在
`<pkg>/bin`。`port/CMakeLists.txt` 自动定位该目录并置于测试 PATH 首部（`GLib::GLib`
等 CMakeDeps 目标为 INTERFACE IMPORTED，无 LOCATION，故按链接库/头文件/包目录三种
途径解析包根）。缺失时触发型用例报
`Failed to execute child process "gio-launch-desktop"`。

## 已知限制

1. `gallery.py` / `uberprogram.py` / `servicemapper.py` 上游夹具是 python-dbus 服务，
   需要 python3-dbus + python3-gi + 会话总线；触发型夹具的 `.desktop` `Exec=`
   为 `python3 -c ...` 写 `/tmp/<marker>`。执行环境具备时 `run_py_case.sh` 自动拉起
   私有会话总线全量执行，缺失时对应 case 记 SKIP(77) 并附技术原因（不计入通过率分母之外的谎报）。
2. `test-mimes.py` 的 2 个 DBus 方法（`testInvokeMeego`/`testInvokeMimeOpen`）依赖
   `uberprogram.py`；其余 3 个方法（含 `trigger()` Exec 回环）由
   `upstream-test-mimes-subset` 以**上游原始断言**按方法抽取执行（零改动）。
3. `declarative/`（QML 插件）与 `tools/` 里非 lca-tool 部分不构建：QML 插件面向
   Sailfish QML 场景，OHOS 无对应 QML 运行环境，非库核心能力。

### ctest 超时口径（`--timeout 120`）

`conanfile.py` 的 `_run_upstream_tests()` 对 ctest 施加 **120 秒/测试** 的超时。
该超时是**逐测试进程**的：`run_py_case.sh` 拉起的 `dbus-daemon` 或 `gio-launch-desktop`
在极端负载下若触顶，ctest 会把该用例记为 **Failed 而非 Skipped**（与"环境性失败
不阻断打包"的设计意图存在口径差异）。因 `ignore_errors=True` 兜底，触顶**不会阻断
`conan create`**，但报告里会多出一条 Failed。实测余量充足
（最慢的 `upstream-generated-regex-testsuite` 为 13.28s，约为上限的 1/9）。
