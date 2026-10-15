# kwrited 6.7.2 适配笔记（OHOS / HarmonyOS PC，aarch64）

## 1. 软件与形态判定（本版本的核心结论）

- 上游：Plasma 6.7.2 的 kwrited —— 接收 `write(1)`/`wall(1)` 发往终端的消息并**以桌面通知呈现**的守护进程
  （上游自述：`kwrited is a write(1) receiver for KDE`；实现依赖 `KNotification` + `kwrited.notifyrc`）。
  注意：**本形态不写 utmp/wtmp**（OHOS 侧 `KPty_HAVE_UTEMPTER=FALSE`，上游据此走可执行分支）。
- 上游源码包 15 个条目：`CMakeLists.txt`、`kwrited.cpp`/`kwrited.h`（顶层，无 `src/` 子目录）、
  `kwrited.json`、`kwrited.notifyrc`、`kwrited-autostart.desktop`、`config-kwrited.h.cmake`、`LICENSES/` 等；
  **`kwrited.cpp` 150 行 + `CMakeLists.txt` 108 行**；包内无 `po/`、无 `tests/`（上游不带测试用例）。
- **形态由上游自己决定，且对我们的平台自动选对了**：

  ```cmake
  cmake_dependent_option(BUILD_AS_EXECUTABLE "Whether to build kwrited as executable" OFF
      "KPty_HAVE_UTEMPTER" ON)
  ```

  `KPty_HAVE_UTEMPTER` 由 **KF6Pty 的包配置**导出；OHOS 侧 `kpty/6.26.0` 是无 UTEMPTER 构建
  （包内实测 `KPty_HAVE_UTEMPTER="FALSE"`）→ 选项被置为 `ON` → 走**独立可执行程序**分支：

  - 编出 `bin/kwrited`（实测 35456 字节）；
  - **不** `find_package(KF6DBusAddons)`（上游把它写在插件条件里：`CMakeLists.txt:39-45` 的 `if (NOT BUILD_AS_EXECUTABLE)`；第 90 行的 `else()` 才是插件分支，只在该分支第 97 行链接 `KF6::DBusAddons`），因此**不需要 kdbusaddons 依赖**；
  - 安装 `etc/xdg/autostart/kwrited-autostart.desktop`（可执行分支专属）与
    `share/knotifications6/kwrited.notifyrc`。

- 结论：**零补丁**交付——没有平台宏、没有 stub、没有伪造会话总线；形态选择完全由依赖包的真实能力宏驱动。

## 2. 依赖（W0 实测）

| 依赖 | 针脚 | 制品仓（实测） |
|---|---|---|
| qtbase | 6.11.1 | ✅ 已有 |
| kcoreaddons | 6.26.0.1 | ✅ 已有 |
| ki18n | 6.26.0 | ✅ 已有 |
| knotifications | 6.26.0 | ✅ 已有 |
| kpty | 6.26.0 | ✅ 已有（2026-10-14 随【依赖项】PR #15405 合入 main 并发布制品仓，revision `32850cf489da395267d4cfe789ffce7e`） |
| ecm（tool） | 6.26.0 | ✅ 已有 |

传递依赖：`kconfig/6.26.0`、`gettext/0.22.5`。**无需 kdbusaddons**（见 §1 形态判定）。

> 上表“制品仓”列口径：用 `conan download <ref> -r=ohpcd --only-recipe` 逐个实测——2026-10-12 首次探测时
> qtbase/kcoreaddons/ki18n/knotifications/ecm 命中、**kpty/6.26.0 未命中**（当日本地 W3 被 L0i 依赖闸拦下）；
> **2026-10-15（kpty 发布后）复测全部命中**，本地 W3 全绿（见 §4）。

## 3. 上游测试清点（R51 第一步，禁“没环境/没测试”式搪塞）

- `ctest -N`：无目标；源码树无 `autotests/`、`tests/`、`test/`；
- `CMakeLists.txt` 中无 `add_test()` / `ecm_add_test()` / `include(ECMAddTests)`；
- `.gitlab-ci.yml` / `.kde-ci.yml` 存在但未定义任何测试作业；
- 证据汇总见 `test_package/MANIFEST.yml` 的 `inventory_evidence` 段（含归档 sha256 与条目数）。

→ 按积分赛口径**上游无测试即补鸿蒙独有消费者测试**：`test_package/` 的消费者用例对打包产物做**真实执行**
（非空壳断言），见 §4。

## 4. 验证结果（本机实测，aarch64 OHOS profile）

- `conan create archives/k/kwrited/6.7.2 --build=missing`（`ci/conan/profiles/ohos-aarch64`）：**通过**；
- 消费者测试（`test_package/test_app.sh`，offscreen QPA）实测输出（2026-10-12 手动 `conan create`；pty 编号随运行环境变化，最新 W3 复跑为 `/dev/pts/6`）：

  ```
  OK: kwrited alive after 5s (pid=2606)
  OK: kwrited holds a pty on stdin -> /dev/pts/1
  OK: kwrited consumer test passed
  ```

  即：链接闭包在 OHOS 可加载（Qt6/KF6 全部依赖就位）、`KPtyDevice` 成功开 pty 且
  `dup2(pty->slaveFd(), 0)` 生效（`/proc/<pid>/fd/0` 指向该次运行的 `/dev/pts/1`），SIGTERM 走优雅退出路径。
- 上游无测试 → 不存在“上游测试失败”项；CI 侧 ctest 段为空是**预期**，非跳过。
- ✅ **finish 内嵌的 W3 本地 CI 模拟已全绿**（2026-10-15 重跑，kpty/6.26.0 发布后）：依赖闸实测命中
  `kpty/6.26.0#32850cf489da395267d4cfe789ffce7e`，`L0_RESULT=pass`、`L1_RESULT=pass`、
  `L2_RESULT=skip`（守护进程无 --version/--help，烟雾测试不适用）、`L4_RESULT=pass`、`L5_RESULT=pass`，
  Pass rate 100% (1/1)；`.ci-result.json` 已写入（`exit_code=0`）。证据：`reports/w3-local-ci.log`（2026-10-15 09:51）。

## 5. 平台适配说明（无桌面会话）

OHOS PC 无桌面会话：没有会话 D-Bus 总线、没有 KDED 装载器。kwrited 的 KDED 插件形态
（`plugins/kf6/kded` + `ServiceTypes=KDEDModule`）在该平台上“能编译但永不加载”，因此本次交付的
可执行分支才是有效产物；判定与处理策略见知识库拓展主题
`knowledge/operations/no-desktop-session-dbus-kded/`（检测脚本 + 策略 + 样例 + 复现脚本）。

> 平台判断写法说明（R32 对齐口径）：配方内两处平台守卫（`conanfile.py:174` 的
> `apply_conandata_patches` 守卫与 `conanfile.py:186` 的 `LD_LIBRARY_PATH` 兜底）写作
> `if self.settings.os == "OHOS":`，与已合入 main 的 KF6 6.26 先例
> `archives/k/kitemviews/6.26.0/conanfile.py:114/124/157` 逐字一致（README.md 所述“与 6.26 先例对齐”即指此处）；
> 未写成 `in ("Linux", "OHOS")` 是刻意的：这两处只在 OHOS 目标上需要生效，扩到 Linux 会改变非目标平台行为。
> 本包 `patches/` 为空，第一处守卫当前无补丁可打，不影响产物。

### 5.1 功能降级清单（SOFT 命中项，按主题 strategy.md 策略 D 记录）

本包在本主题检测脚本下有 SOFT 命中（`KNotification` 使用点 ×3：`kwrited.cpp:136/141/142`），
无会话总线时的行为边界如下——均为「静默降级、不崩溃」，非形态判定项：

| 能力 | 无桌面会话时的行为 | 依据 |
|---|---|---|
| 消息通知（`KNotification`） | 会话总线缺失 → 通知无法投递，进程照常存活（不 fallback 到终端输出） | 运行时观测：offscreen 启动存活 5s、持 pty（§4）；`KNotification` 无对端时不终止进程 |
| 会话内通知配置（`share/knotifications6/kwrited.notifyrc`） | 文件已安装但无人读取（无会话服务读取方） | 包内实测该文件存在（`test_package/conanfile.py` 断言之） |
| 插件形态（`plugins/kf6/kded`） | 上游在本平台不会编出该形态（能力宏为假，见 §1） | 本机 `conan create` 产物清单 |
| 自启条目（`etc/xdg/autostart/kwrited-autostart.desktop`） | 已安装；无桌面会话时由用户/系统按需拉起，不由会话自启器加载 | 包内实测该文件存在（同上） |

> 降级不改变交付结论：本包的适配目标（可执行形态可构建、可运行、持 pty）已由 §4 实测覆盖。

## 6. 本地构建的离线取源（仅本机环境，不入 PR）

本机 `download.kde.org` 与镜像均不可达，为完成 W3 采用 conan 的备份源机制：
源码包以 **sha256 命名**放在 `~/.conan2/global.conf` 的 `core.sources:download_cache` 指向目录的 `s/` 子目录下
（`s/<sha256>` + 同名字 `.json` 边车记录官方 URL）。**该改动仅存在于本机构建环境，用后还原**，
配方内的 `conandata.yml` 始终指向官方源 `https://download.kde.org/stable/plasma/6.7.2/kwrited-6.7.2.tar.xz`。
---

**编译结束**: 2026-10-15 09:46
**最终状态**: built
