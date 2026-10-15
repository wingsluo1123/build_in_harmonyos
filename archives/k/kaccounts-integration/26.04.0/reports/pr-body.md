## PR 信息
- **三方库名称**：kaccounts-integration
- **上游版本**：26.04.0
- **上游仓库地址**：https://download.kde.org/stable/release-service/26.04.0/src/kaccounts-integration-26.04.0.tar.xz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游测试套件 |
| 集成测试 | 0 | - |
| 其他测试 | 0 | 跳过的测试 |
| **合计** | **0** | |

### 是否存在对上游测试用例的修改？
是，见下方补丁说明

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 通过 0/0 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 0 | - | 新增 |
| **合计** | **0** | | |

---

## 上游测试用例修改说明
上游 26.04.0 release tarball 内无 tests/ 或 autotests/ 目录（实测解压目录树确认），上游不随源码发布测试套件，无需修改任何测试用例。消费者侧新增 test_package 冒烟测试（find_package(KAccounts6) + 链接导出目标 + kaccounts_add_provider 宏 + Accounts::Manager 离线 API），R51 申报见 test_package/MANIFEST.yml。

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: cmake
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: cmake, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 0, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: qtbase/6.11.1.1, qtdeclarative/6.11.1, kcoreaddons/6.26.0, ki18n/6.26.0, kconfig/6.26.0, kcodecs/6.26.0, kcolorscheme/6.26.0, kguiaddons/6.26.0, kwidgetsaddons/6.26.0, kservice/6.26.0, karchive/6.26.0, kitemviews/6.26.0, kcmutils/6.26.0, kdbusaddons/6.18.0, kwallet/6.18.0, kio/6.26.0, libaccounts-qt/1.17, libsignon-qt/8.61, qcoro/0.13.0, openssl/3.5.6.1, zstd/1.5.7, libxml2/2.15.3, zlib/1.3.2 |

### 补丁说明
- `0001-cmake-inline-qcoro-macros.patch`: 0001-cmake-inline-qcoro-macros.patch
- `0002-kio-webdav-qcoro6-target.patch`: 0002-kio-webdav-qcoro6-target.patch
- `0003-cmake-require-qt6-xml.patch`: 0003-cmake-require-qt6-xml.patch
- `0004-lib-drop-empty-include-dirs.patch`: 0004-lib-drop-empty-include-dirs.patch
- `0005-exclude-kio-webdav-plugin.patch`: 0005-exclude-kio-webdav-plugin.patch

### 依赖
- qtbase/6.11.1.1
- qtdeclarative/6.11.1
- kcoreaddons/6.26.0
- ki18n/6.26.0
- kconfig/6.26.0
- kcodecs/6.26.0
- kcolorscheme/6.26.0
- kguiaddons/6.26.0
- kwidgetsaddons/6.26.0
- kservice/6.26.0
- karchive/6.26.0
- kitemviews/6.26.0
- kcmutils/6.26.0
- kdbusaddons/6.18.0
- kwallet/6.18.0
- kio/6.26.0
- libaccounts-qt/1.17
- libsignon-qt/8.61
- qcoro/0.13.0
- openssl/3.5.6.1
- zstd/1.5.7
- libxml2/2.15.3
- zlib/1.3.2

### 测试结论
- 总体评价: 通过
- 已知限制: kio-webdav 守护插件未构建（已发布 kio/6.26.0 包缺生成头 kdirnotify.h，kio 配方缺口另行跟踪；不影响 kaccounts-providers 对本包的消费）

### 遇到的问题与解决方案
无已知问题

### 验证命令
```
# 本地闭环 (ohos-aarch64 双 profile)
$ conan create archives/k/kaccounts-integration/26.04.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
  → configure/build/install 成功（libkaccounts6.so / kcm_kaccounts.so / kded_accounts.so / QML 插件）

# 消费者冒烟测试
  → providers listed: 0
    services listed: 0
    PASS: KAccounts6 library + AccountsQt6 chain load and respond

# W3 本地 CI 模拟
$ python3 scripts/ohc-run.py finish kaccounts-integration 26.04.0 built
  → finish_success（L0/L1/L2/JC/KC 全部 PASS）
```
