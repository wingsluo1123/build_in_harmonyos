# libquotient

## 软件描述
libQuotient 是「矩阵」（Matrix）协议的 C++17/Qt 客户端库——Quaternion、NeoChat 等客户端
都在其上构建。它以面向对象方式封装 Matrix 客户端-服务器 API：连接与登录、房间状态同步、
事件解析分发、房间/成员/用户模型、文件上传下载；端到端加密（E2EE）为可选构建特性。

Upstream: https://github.com/quotient-im/libQuotient

## 功能概述
- **连接与同步**：`Connection`（homeserver/登录/同步循环）、增量同步解析（`SyncData`）
- **事件体系**：全事件类型建模（`RoomMessageEvent` 等），`loadEvent<T>()` 按 JSON 分派
- **房间模型**：房间列表、成员/已读回执/输入通知、消息历史（后台 `jobs` 体系）
- **用户与群组**：用户资料、设备列表、群组（communities）模型
- **媒体**：文件上传/下载（`Connection::uploadFile/downloadFile`）
- **可选特性**：E2EE（Olm 棘轮，需 libolm/OpenSSL）、SSO 登录、代理

## OHOS 适配

### 构建方式
- **CMake + Qt6 风味**：`BUILD_WITH_QT6=ON` 构建 `QuotientQt6` 共享库（`BUILD_SHARED_LIBS=ON`）；
  上游 `install(EXPORT)` 不设 NAMESPACE，消费侧 `find_package(QuotientQt6)` 得到裸目标 `QuotientQt6`
- **补丁 0001**：`QT_CONFIG(ssl)` 能力守卫——平台 qtbase 为无 OpenSSL 构型，`QSslError` 系 API
  不存在（编译墙）；守卫后无 TLS 构型编译通过、TLS 构型预处理结果与上游逐字一致
- **E2EE 关闭**：保持上游默认 `Quotient_ENABLE_E2EE=OFF`（平台无 libolm）；HTTP 层、事件/房间
  模型与完整公开 API 不受影响
- **上游测试随构建实跑**：`BUILD_TESTING=ON`，`build()` 内以 ctest 跑上游全部离线用例
  （非 E2EE 构建 N=2：callcandidateseventtest、utiltests）；quotest 需真实 homeserver，
  上游未注册 ctest，仅作编译冒烟且 `Quotient_INSTALL_TESTS=OFF` 不入包

### 关键攻坚点
1. **OHOS 禁 symlink（EPERM）与 SOVERSION 链**：库以 VERSION 0.8.0 / SOVERSION 0.8 构建，
   构建图的 `cmake -E cmake_symlink_library` 步骤在 OHOS 全域 EPERM（Ninja 的 rules.ninja
   或 Unix Makefiles 的 build.make，随 profile 选定生成器；两类生成器对失败边都无条件重跑、
   两遍法无效）→ 在 OHOS 分支 configure 后、build 前把该命令统一改写为逐路径实体拷贝
   （lfortran 0.64.0 先例），`.so → .so.0.8 → .so.0.8.0` 三名全部以真实文件落地，加载器
   行为不变
2. **非 SSL qtbase 的编译墙**：平台 `qtbase-sql-dbus/6.11.1` 为无 OpenSSL 构型
   （`QT_CONFIG(ssl)=off`）：`QSslError` 类型与 `ignoreSslErrors(QList<QSslError>)` 重载、
   `QNetworkAccessManager::sslErrors` 信号在头文件即被裁剪，而 libQuotient 0.8.0 无条件
   使用这些 API → 补丁 0001 以 `QT_CONFIG(ssl)` 能力守卫包住全部相关声明与实现（3 文件
   8 处），无 TLS 构型下该 API 整体不存在、TLS 构型预处理结果与上游逐字一致（能力探测，
   非平台宏；R8 合规）
3. **SOVERSION 加载名的消费链**：库实测带 DT_SONAME=`libQuotientQt6.so.0.8`——消费侧记录并
   解析的加载名即该 SOVERSION 名，故实体拷贝版的 `.so.0.8` 是运行期解析的硬前提；配合
   `CMAKE_BUILD_RPATH=$ORIGIN` 与 `-Wl,--disable-new-dtags`，运行期在同目录解析全部依赖
4. **Qt6Test / Qt6Concurrent 依赖链**：上游 configure 即硬检查 `find_package(Qt6 ... Test)`，
   quotest 链接 `Qt6::Concurrent`（CMP0028 下缺 target 直接 configure 失败）——qtbase-sql-dbus
   6.11.1 已含 Test 模块（其自身 ctest 7 目标为证）与 Concurrent（asyncfuture 先例），无需裁剪
5. **安装期重签名**：`package()` 对全部安装 ELF 依次 llvm-objcopy 去 `.codesign` +
   binary-sign-tool 自签名（CMake 安装期重写 RUNPATH 会使构建期签名失效）
6. **E132 环境前置**：build/package 的 LD_LIBRARY_PATH 前置 SDK 的 llvm/lib
   （lld 链接期间依赖其中的 libxml2.so.16）

### 与 Linux 的差异
- 版本链为实体拷贝而非符号链接（`/storage` 禁 symlink）；除此之外构建与运行行为一致
- quotest 在 Linux 上也需活的 homeserver + 账号，两平台同样不运行（上游未注册 ctest）

## 依赖关系
编译依赖：`qtbase-sql-dbus/6.11.1`（Qt6 Core/Network/Gui/Test/Concurrent）、`qtkeychain/0.14.2`
（Qt6Keychain，上游 REQUIRED）。
运行依赖：同编译依赖（同一 qtbase-sql-dbus 运行时）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.8.0 | built | 2026-10-16 | 首次适配：Qt6 共享库构建（E2EE=OFF）+ 补丁 0001（QT_CONFIG(ssl) 守卫）；OHOS 禁 symlink 以构建图规则改写（双生成器）实体拷贝落地 SOVERSION 链；上游 ctest 2/2 + 消费者 6 用例 16/16 + ELF 制品 21/21；真机八门禁 Verdict PASS |

## 目录

```
libquotient/
├── manifest.yaml          # 软件级元信息与适配要点
├── README.md
└── 0.8.0/
    ├── conanfile.py       # 主配方：Qt6 构建 + 构建图 symlink 改写（双生成器）+ 上游 ctest + 重签名
    ├── conandata.yml      # 官方源（GitHub 0.8.0 tag tarball）+ sha256 + 补丁清单
    ├── manifest.yaml      # 版本级编译元数据
    ├── notes.md           # 本版适配笔记
    ├── patches/           # 0001: QT_CONFIG(ssl) 能力守卫（非 SSL qtbase 编译墙）
    ├── reports/           # 真机 conan-verify 报告与 conan create 全量日志
    └── test_package/      # Conan L1 消费者测试（API 行为用例 + ELF 制品校验）
```

## 参考资料
- 上游仓库: https://github.com/quotient-im/libQuotient
- Matrix 协议规范: https://spec.matrix.org
- 下游客户端: Quaternion（https://github.com/quotient-im/Quaternion）、NeoChat
