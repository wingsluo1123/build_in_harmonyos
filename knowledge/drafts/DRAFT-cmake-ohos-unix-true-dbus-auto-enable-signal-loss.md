# OHOS 平台模块使 `UNIX` 为真 → 上游按平台默认自动启用 D-Bus 通知；无会话总线时通知在总线回环处静默丢失（构建全绿、数据库已更新而内存模型不刷新）

- **形态**：knowledge/drafts 条目草稿（E 编号由知识库主编确认后回填）
- **配套 kv**：`knowledge/drafts/DRAFT-cmake-ohos-unix-true-dbus-auto-enable-signal-loss.kv`
- **申报路径**：B【知识库扩展】
- **来源 run**：kpeople 6.28.0 HarmonyOS PC 首次适配（KDE Frameworks 6.28.0；2026-10-16 真机实测）

## 1. 一句规则

在 HarmonyOS PC 上用平台真名 `CMAKE_SYSTEM_NAME=OHOS` 配置 CMake 时，SDK 自带的
`Platform/OHOS.cmake` 全文是 `include(Platform/Linux)`，于是 `UNIX` 为真；上游若按
「Unix 桌面 ⇒ 有 D-Bus」的默认逻辑自动打开 D-Bus 支持，会把库内部的**进程内信号**通知
改为**经会话总线回环**投递。设备上没有会话总线时，`sessionBus().send()` 静默失败、
回环永不触发——数据库写入已经提交、构建与链接看不出任何异常，只有内存侧模型拒不刷新。
适配动作：在这类库的配方里**显式把能力开关钉到 OFF**，选择上游为所有非 Linux 系统保留的
进程内路径。

## 2. 现象（失败面极安静）

- 构建与打包全程成功，无相关 warning。
- 唯一异常输出是模型类用例在「合并后行数」处的比较失败（`QTRY_COMPARE(rowCount, 3)`：
  Actual 4 / Expected 3），随后测试进程对空列表取首元素触发 QFATAL，进入 OHOS 崩溃处理
  循环（同一信号反复重放、进程不退出、不收 TERM，与 DRAFT-10175 记录的信号重放形态同族
  ——本条只把它记为旁支现象，不重复承载）。
- 数据面极具迷惑性：合并事务**已提交**（`mergeContacts` 返回了合法 `kpeople://1`），
  数据库里的映射行真实变化；但 `PersonsModel::rowCount` 保持旧值。只看数据库会得出
  「功能正常」的错误结论。

## 3. 机理链（kpeople 6.28.0 全链实测）

1. 配方按平台真名口径设 `CMAKE_SYSTEM_NAME=OHOS`
   （`tc.blocks["generic_system"].values["cmake_system_name"]`）；SDK/cmake 的
   `Platform/OHOS.cmake` 内容即 `include(Platform/Linux)`，`UNIX` 为真。
2. kpeople 上游 `CMakeLists.txt:33-43` 自己推导默认值：
   `set(USE_DBUS_DEFAULT OFF)`；`if(UNIX AND NOT APPLE AND NOT ANDROID AND NOT HAIKU)`
   时置 ON（注释原话 "enabled per default on Linux & BSD systems"）；
   `option(USE_DBUS "Build components using DBus" ${USE_DBUS_DEFAULT})`。
   设计意图覆盖的是「有桌面会话的 Unix」，OHOS 落到 `UNIX` 真值时被顺带打开。
3. `if(USE_DBUS)` → `find_package(Qt6 … DBus)` 成功（本配方依赖 qtbase-sql-dbus 变体，
   携带 DBus 模块）→ `HAVE_QTDBUS=1` 写进编译定义，`src/CMakeLists.txt` 据此链接
   `Qt6::DBus`。
4. 源码里通知路径被整体换血（`src/personmanager.cpp`）：
   - 构造函数在 `#if HAVE_QTDBUS` 下把总线信号回环到本地槽（67-80 行）：
     `QDBusConnection::sessionBus().connect(… "/KPeople", "org.kde.KPeople",
     "ContactAddedToPerson", this, SIGNAL(contactAddedToPerson(QString,QString)))`；
   - `mergeContacts()` 成功后，`#if HAVE_QTDBUS` 分支用
     `QDBusConnection::sessionBus().send(message)` 广播，`#else` 分支才直接
     `Q_EMIT contactAddedToPerson(…)`（219-239 行）。
   也就是说：总线在时，通知走一圈总线再由回环连接变回本地信号；总线不在时，
   本地信号从头到尾**没有**被发过。
5. 消费者侧：`PersonsModel` 连接的正是这两个**本地**信号
   （`src/personsmodel.cpp:95-96`），不做任何总线订阅。设备上 `sessionBus()` 无连接，
   `send()` 的失败返回值被忽略 → 待发通知凭空消失 → 模型维持旧行数。
6. 与上游测试的碰撞：`personsmodeltest` 合并后 `QTRY_COMPARE(model->rowCount(), 3)`
   （第 77 行）失败（保持 4）；随后的 `gettersTests` 对空 `indexList` 取 `first()`
   触发 QFATAL。
7. 对照排除：把 `QTRY_TIMEOUT` 提到 60000 无济于事——行数不是「慢」，是永远不会到 3，
   时序/starvation 因素排除。
8. 姊妹口径：仓库内 KF5 的 kpeople5/5.116.0 天然没有 `QT_DBUS_LIB`，走的正是进程内路径
   （其 notes 原文：「PersonManager 的 dbus 通知在 QT_DBUS_LIB 未定义时编译掉」）。
   KF6 只是把「非 Linux ⇒ 进程内」作为默认，本适配把 OHOS 显式归回这一类。

## 4. 诊断（构建标记三件套 + 一次对照）

- **构建标记**：`CMakeCache.txt` 里 `USE_DBUS:BOOL=ON`；编译核心库的
  `CMakeFiles/<target>.dir/flags.make` 里 `-DHAVE_QTDBUS=1`。
- **源码读法**：在库源码里 grep `#if HAVE_QTDBUS` / `sessionBus()`，确认「本地信号是否只在
  该分支之外发射」；再确认「谁在听」（本例 PersonsModel 只连本地信号）。
- **运行期对照**：在无会话总线的环境里跑模型级用例，观察**内存状态**（行数/信号计数）与
  **数据库状态**是否分叉——只要数据库变了而内存没变，问题就在通知链而非业务逻辑。
- **修复对照**：把开关钉 OFF 重跑同一用例（同环境、同数据），由失败转全绿。

## 5. 推荐修复（producer 侧一行）

```python
# conanfile.py generate()，OHOS/无会话总线平台口径下：
tc.variables["USE_DBUS"] = "OFF"
```

即把「有 D-Bus 会话」这一**平台能力**的默认推导在构建期显式纠正为本平台的真实情况，
选择上游为非 Linux 系统保留的进程内信号路径。库内通知回到同进程直接投递，数据库与内存
模型的行为恢复一致。仓库内同口径先例：kstatusnotifieritem 6.26.0（"headless OHOS
baseline"）、kio（USE_DBUS=OFF）。

## 6. fallback（诚实权衡）

- **运行期补一条会话总线**：产品确需跨进程联系人变更广播时，按
  DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime 起匿名 TCP 会话总线。代价：把运行期依赖
  引进交付面，通知链能否工作从此取决于总线进程存活。
- **上游补丁 + 运行期能力探测**：把 `#if HAVE_QTDBUS` 的广播改成
  「`sessionBus().isConnected()` 时 send，否则发本地信号」——无平台宏、对上游可提交
  （kcachegrind 同款守卫范式）。代价：维护补丁，且「总线上报」语义边界需与上游确认。

## 7. 反模式

1. **用数据库状态或返回值判定通知链正常**：merge 的写库成功与内存模型刷新是两条独立
   链路，无总线时它们静默分叉。判据必须落在内存侧（模型行数、信号计数）。
2. **给测试挂一条临时会话总线把库「救活」**：这掩盖的是构建期选型问题（产品侧仍没有
   总线），绿的是测试、不是交付物；运行期补总线只属于「产品确实要跨进程广播」这一前提
   下的替代方案。

## 8. 去重与关系

- 与 DRAFT-ktimer-26.04.0-kf6-tray-dbus-provider-selection：那条讲**双包选型**（要托盘
  协议就依赖 USE_DBUS=ON 的包、不要就选 OFF 包）；本条讲同一个开关被**平台默认自动打开**
  后、库内通知去路的静默丢失——触发机理（自动推导）与处置面（行为判据）都不同。
- 与 DRAFT-kcachegrind-26.04.0-kf6-nodbus-service-startup-abort：那条是**应用**运行期构造
  KDBusService 直接终止（显性、启动即死、运行期守卫修复）；本条是**库**构建期选型导致的
  隐性通知丢失（构建全绿、数据库已写）。方向互补。
- 与 kunifiedpush-26.04.0-dbus-less-consumer-test：那条覆盖「消费者构造期探测总线段错误」
  与 qtbase 变体选型；本条没有任何崩溃，是通知路径被换血后的静默丢弃。
- 与 DRAFT-E577-cmake-ohos-unix-guard-silent-drop / DRAFT-cmake-unix-variable-false-on-harmonyos
  （jinja2cpp）：同一根因（平台模块语义）的两个**相反后果面**——那两条是 `UNIX` 未定义/为假
  导致 `if(UNIX)` 实现被剔除；本条是 `UNIX` 为真导致能力默认被打开、而打开出来的能力在
  平台上并不存在。合起来才是「`UNIX` 语义在 OHOS 上双向失真」的完整图景。
- E622（libheif）提供了关键平台事实（`Platform/OHOS.cmake` 全文即
  `include(Platform/Linux)`）；本条把它推进到「能力默认自动推导」的后果面。

## 9. 原则挂钩

- **P-BUILD-001**（平台限制必须降级而非绕过）：无会话总线是平台固定事实（同 AF_UNIX
  EPERM 一类），应选上游已有的进程内路径，而不是反复重试或伪造总线。
- **P-ENV-001**（优先构建系统原生机制）：修复用的是上游自己的 `USE_DBUS` 选项，不动环境
  变量、不打假总线。

## 10. 关联交付

- 本草稿与 `archives/k/kpeople/6.28.0/**` 属同一交付（配方 `generate()` 注释、notes.md
  坑 1、`reports/conan-create.log` 真机日志与修复前后对照）。
- 正式 E 编号由知识库主编审核后分配。
