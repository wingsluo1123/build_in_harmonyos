# kpeople

## 软件描述
kpeople 是 KDE Frameworks 6 的联系人聚合框架：把来自不同数据源（数据源插件，随包提供
vCard 后端）的联系人统一建模为 PersonData / PersonsModel，向上提供合并/拆分求解、变更
通知、排序过滤代理模型与 Widgets/QML 视图组件。本目录为 **KF6 / Qt6 线**的适配归档；
KF5 线见姊妹目录 `archives/k/kpeople5/`。

Upstream: https://invent.kde.org/frameworks/kpeople

## 功能概述
- **统一人物模型**：`PersonsModel` 聚合各数据源的联系人，`PersonsSortFilterProxyModel` 提供排序/过滤
- **合并与拆分**：联系人合并求解（`mergeContacts` / `unmergeContacts`）与变更通知
- **数据源插件接口**：`KF6PeopleBackend`（`BasePersonsDataSource`），随包提供 vCard 后端插件
- **视图组件**：`KF6PeopleWidgets`（PersonDetailsView 等）与 QML 模块（`KF6PeopleDeclarative`，URI `org.kde.people`）

## OHOS 适配

### 构建方式
- CMake（Unix Makefiles）+ Conan 2 配方；`cmake_system_name=OHOS` 平台真名
- 四个产物：KF6People / KF6PeopleBackend / KF6PeopleWidgets / KF6PeopleDeclarative（QML）
- 上游测试：`BUILD_TESTING=ON` 注册 3 个 ctest 目标（persondatatest / personsmodeltest /
  personsproxymodeltest），测试自带 FakeContactSource 注入，无插件发现依赖

### 关键攻坚点
1. **`UNIX` 为真导致 USE_DBUS 被自动打开 → 通知静默丢失**：`Platform/OHOS.cmake` 全文是
   `include(Platform/Linux)`，上游据此把 `USE_DBUS` 默认置 ON；`HAVE_QTDBUS=1` 后合并通知改经
   `sessionBus().send()` 回环广播，而 `PersonsModel` 只监听本地信号——设备无会话总线时
   数据库已提交、内存模型不刷新的静默分叉（personsmodeltest rowCount 4 vs 3 + QFATAL 崩溃循环）。
   修复：配方显式 `USE_DBUS=OFF`（KF5 姊妹包 kpeople5 天然走进程内路径），修复后 10/10 用例全绿
2. **KF6 版本墙**：上游钉 KF_DEP_VERSION=6.28.0 / ECM 6.28.0，制品仓基线为 6.18.0 家族
   （kcontacts 链）+ ECM 6.26.0。补丁 0001 下调版本门槛并删除 `ki18n_install(po)`
   （无 Qt Linguist 工具；kcontacts 先例）
3. **HMDFS 拒符号链接**：CMake 版本化符号链接链无法建立（EPERM）。`CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`
   + 显式 `-Wl,-soname` 注入只产出单个 `libKF6People.so`，`DT_SONAME` 真实在位，
   消费者 `DT_NEEDED` 记录可重定位名（`test_ohos_soname` 执行器实测）
4. **ctest 挂死防护**：OHOS 上 QTest fatal 进入崩溃处理循环（不响应 TERM），ctest 统一
   `--timeout 300`，把挂死转换成失败

### 与 Linux 的差异
- 无会话 D-Bus 总线：库内通知走进程内信号路径（`USE_DBUS=OFF`），不做跨进程广播
- 编译期 `.so` 版本化符号链接链不存在（HMDFS 限制），以单文件 + 真实 DT_SONAME 代替

## 依赖关系
- 运行依赖：`qtbase-sql-dbus/6.11.1`（vanilla qtbase 无 FEATURE_sql，本包顶层要求 Qt6::Sql）、
  `qtdeclarative/6.11.1`、`kcoreaddons` / `kwidgetsaddons` / `ki18n` / `kitemviews` / `kcontacts` 6.18.0
- 构建依赖：`ecm/6.26.0`

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 6.28.0 | built | 2026-10-16 | 首次适配：USE_DBUS 静默丢失修复 + KF6 版本墙补丁；上游 10/10 + 消费者 10/10 真机全绿；八门禁 Verdict PASS |

## 目录

```
kpeople/
├── manifest.yaml          # 软件级元信息与适配要点
├── README.md
└── 6.28.0/
    ├── conanfile.py       # 主配方：OHOS 平台配置 + USE_DBUS=OFF + SONAME 注入
    ├── conandata.yml      # 官方源 + sha256 + 补丁声明
    ├── manifest.yaml      # 版本级编译元数据
    ├── notes.md           # 本版适配笔记（USE_DBUS 排障全链）
    ├── patches/
    │   └── 0001-CMakeLists.txt.patch
    ├── reports/           # 真机 conan create 日志与八门禁报告
    └── test_package/      # Conan L1 消费者测试（10 用例执行器）
```

## 参考资料
- 上游仓库: https://invent.kde.org/frameworks/kpeople
- 源码下载: https://download.kde.org/stable/frameworks/6.28/kpeople-6.28.0.tar.xz
- KF5 姊妹适配: archives/k/kpeople5/5.116.0/
