# libquotient 0.8.0 鸿蒙 PC 适配笔记

上游: <https://github.com/quotient-im/libQuotient>
版本: 0.8.0（0.x 线最后一个同时支持 Qt5/Qt6 的发行版）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

构建产物：`libQuotientQt6.so.0.8.0`（Qt6 形态的 Matrix 客户端-服务器
库：连接层/同步循环、房间与事件模型、完整公共 API，头文件装入
`include/Quotient/`）。源码补丁一处（0001：QT_CONFIG(ssl) 能力守卫，
见问题 4），其余适配在 Conan/CMake 层完成：

- `BUILD_WITH_QT6=ON`：上游用该开关把库名、导出目标与 CMake 包名整体
  切换为 `QuotientQt6`（`cmake/QuotientConfig.cmake.in` →
  `QuotientQt6Config.cmake`），消费侧 `find_package(QuotientQt6)` 后链接
  裸目标 `QuotientQt6`（上游 install EXPORT 不带 NAMESPACE）。
- **E2EE 保持上游默认 OFF**：`Quotient_ENABLE_E2EE` 上游默认即 OFF，且
  平台无 libolm（Olm 撕裂轮库）制品；OFF 下免去 Olm/OpenSSL/QtSql 三组
  依赖与六个 E2EE 专属 ctest 用例，其余功能不受影响。
- `BUILD_TESTING=ON`：编译并运行上游自测套件（callcandidateseventtest、
  utiltests 两个 ctest 用例）；quotest 集成套件仅编译作构建冒烟
  （运行需真实 homeserver，上游未注册 ctest）。
- `Quotient_INSTALL_TESTS=OFF`：不把 bin/quotest 打进包（纯库交付）。

## 二、问题与处置

### 问题 1：OHOS /storage 全域禁 symlink 对版本链的杀伤

上游赋 `VERSION 0.8.0` / `SOVERSION 0.8`，构建图用
`cmake -E cmake_symlink_library` 建立 `.so.0.8 → .so` 链（Ninja 下为
rules.ninja 规则，Unix Makefiles 下为 build.make 的链接配方——本平台
CI profile 实测选定 Makefiles）。OHOS /storage 对 symlink 创建返回
EPERM（XPM 限制，普通 Linux 无此约束），且两代生成器都对「上次失败的
边」无条件重跑——重试法无效。

**处置**（lfortran 0.64.0 / kea 先例）：仅 OHOS 分支在
`cmake --build` 前调用 `_replace_symlink_rule_with_copy()`，把构建图中该
命令改写为
`python3 -c "... shutil.copyfile(sys.argv[1], f) for f in sys.argv[2: ]" ...`
逐路径实体拷贝——同时覆盖 Ninja 的 rules.ninja 与 Unix Makefiles 的
`CMakeFiles/*.dir/build.make`（平台 CI profile 实测选定 Makefiles）。
动态加载器按 DT_NEEDED 文件名字符串解析文件，不区分软链与实体；CMake
安装脚本对这些名字只做拷贝（自身不建链），安装树同样以「名字可解析」
为准。Linux/CI 构建行为不变。

### 问题 2：quotest 的 Qt6::Concurrent 依赖是 configure 硬失败点

`quotest/CMakeLists.txt` 以 `find_package(Qt6 COMPONENTS Concurrent)`
（非 REQUIRED）+ `target_link_libraries(... Qt6::Concurrent ...)` 写死
链接：Qt6Concurrent 若缺失，CMP0028 下直接 configure 失败。实测平台
`qtbase-sql-dbus/6.11.1` 与同源 qtbase 构建带 Concurrent 模块
（制品仓 asyncfuture 1.0/1.1.0 即链接 `Qt6::Concurrent` 的既有例），
无需处理；同时其自带 Qt6Test（其自测 tst_qcolor/tst_qwidget 等 7 个
目标即链接 Qt6Test 构建），满足上游 `find_package(Qt6 ... REQUIRED
Core Network Gui Test)` 的首关。

### 问题 3：Qt6Keychain 的消费链

`QuotientQt6Config.cmake` 内含
`find_dependency(Qt6Gui/Qt6Network/Qt6Keychain)`；配方把 qtkeychain 的
`lib/cmake` 目录一并注入 CMAKE_PREFIX_PATH（与 qtbase-sql-dbus 同款
处理），配方与 test_package 均显式 requires qtkeychain/0.14.2，保证
find_dependency 链完整解析。

### 问题 4：平台 qtbase 无 TLS 支持，QSslError 类型不存在

平台 `qtbase-sql-dbus/6.11.1` 为无 OpenSSL 构型（`QT_CONFIG(ssl)` 为
off、`QT_NO_SSL` 生效）：`QSslError` 类型整体不存在（qsslerror.h 全文
包在 `#ifndef QT_NO_SSL` 内）、`QNetworkReply::ignoreSslErrors(QList<QSslError>)`
重载与 `QNetworkAccessManager::sslErrors` 信号在头文件即被预处理裁剪。
libQuotient 0.8.0 无条件使用这些 API（NetworkAccessManager 的
ignored-SSL-errors 三件套 + autotests 对 sslErrors 信号的连接），编译
期报「too many arguments」与「incomplete type 'QSslError' used in type
trait expression」（`QList<QSslError>` 成员经 qtypeinfo.h 触发 libc++
型别特性实例化）。

**处置**（补丁 0001）：以 Qt 自身的裁剪惯例 `QT_CONFIG(ssl)` 能力守卫
包住全部相关声明与实现（3 文件 8 处：`networkaccessmanager.h`/`.cpp`、
`autotests/testutils.cpp`）；无 TLS 构型下该 API 整体不存在而非编译
失败，TLS 构型下预处理结果与上游逐字一致。属能力探测型适配，无平台
宏分支（R8 合规）。语义影响：无 TLS 的 Qt 网络栈本就无法发起 HTTPS，
该守卫不改变实际可达功能面（Matrix 客户端联网需带 OpenSSL 的 Qt 构型）。

## 三、构建步骤

`conan create archives/l/libquotient/0.8.0 --version 0.8.0 -pr:h <ohos
profile> -pr:b <ohos profile>`（recipe 内等价的裸 CMake 过程：

```
cmake -G "Unix Makefiles" -DBUILD_SHARED_LIBS=ON -DBUILD_WITH_QT6=ON \
      -DBUILD_TESTING=ON -DQuotient_ENABLE_E2EE=OFF \
      -DQuotient_INSTALL_TESTS=OFF -DCMAKE_INSTALL_LIBDIR=lib \
      -DCMAKE_BUILD_RPATH='$ORIGIN' \
      -DCMAKE_EXE_LINKER_FLAGS=-Wl,--disable-new-dtags
cmake --build .
ctest --output-on-failure -R "^(callcandidateseventtest|utiltests)$"
cmake --install .
```

## 四、依赖版本

- qtbase-sql-dbus/6.11.1（Qt6 Core/Network/Gui/Widgets/Sql/DBus）
- qtkeychain/0.14.2（Qt API 密钥环，Qt6 形态）

## 五、验证结果

真机 conan-verify（`ohc-run.py conan-verify libquotient 0.8.0`，2026-10-16）：

- **G0–G4 全 PASS**（G1 配方完整性 12 项；G2 conan create；G3 R26 同名库
  隔离；G4 产物完整性）；L2/L4/L5 跳过（无 cache 路径，常态）
- **Verdict: PASS**（reports/conan-verify-report.md）

关键证据（reports/conan-create.log）：

- 上游 ctest：`100% tests passed, 0 tests failed out of 2`
  （callcandidateseventtest 0.16s、utiltests 0.05s）
- test_package 行为用例：6 用例 16 校验点
  `TEST SUMMARY: 16 assertion(s), 0 failure(s)`；消费者 ctest 1/1
- ELF 制品校验：`OK: 21 OHOS artefact checks passed`
  （14 固定结构 + 7 DT_NEEDED 裸名；含 DT_SONAME 同一性断言=libQuotientQt6.so.0.8）
- package() 重签名：`Signed 3 OHOS package ELF file(s)`

## 六、注意事项

- 上游头文件消费形态：`#include <Quotient/connection.h>`（config 包
  默认同时挂 `<prefix>/include` 与 `<prefix>/include/Quotient` 两个
  目录，扁平形式亦可）。
- 库实测带 DT_SONAME=`libQuotientQt6.so.0.8`（SOVERSION 0.8；真机
  ELF 校验断言项+输出为证）：消费侧记录并解析的加载名即该 SOVERSION 名，
  因此 /storage 禁 symlink 约束下 `.so.0.8` 必须以实体拷贝在位，否则
  运行期解析失败——版本链实体化不只是构建期绕过，更是运行期硬前提。
  运行期解析依赖 LD_LIBRARY_PATH 与 BUILD_RPATH=$ORIGIN +
  --disable-new-dtags 的同目录副本（test_package 的
  `_prepare_runtime_links` 同款机制）。
- E2EE OFF 意味着不含 Olm 加密路径；需要 E2EE 的下游应用需先引入
  libolm 制品再自行开启。

- 构建日志 `reports/conan-create.log` 依平台规则不随档（reports/ 仅随档脱敏 md）；脱敏的 `reports/conan-verify-report.md` 保留随档。
