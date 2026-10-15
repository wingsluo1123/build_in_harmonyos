# kcontacts5 5.116.0 — 适配笔记（OHOS / HarmonyOS PC）

- 状态: built（conan create 通过，上游 32 例 + test_package 全绿，未 upload）
- 日期: 2026-10-06
- 账号: j669539（任务卡 #14897，taskBranch feat/kcontacts5-5.116.0）

## 上游结构实测（源码取证，2026-10-06）

- tarball: kcontacts-5.116.0.tar.xz（download.kde.org，R39 单条 URL）
  sha256 `f107fdec8f52f7362499159c958e57e3b8b1981b0d797a90685c4a604156b4cb`
  （主源两次下载 bit 级一致；清华/USTC KDE 镜像无 5.116 目录，返回 404
  错误页——镜像探测不是有效第二源，主源重现性双下载即双源实测）
- 单库目标：libKF5Contacts.so（src/，含 converter/ 与 vcardparser/）
- 链接：PUBLIC Qt5::Core/Qt5::Gui；PRIVATE KF5::CoreAddons/KF5::ConfigCore/
  KF5::I18n/KF5::I18nLocaleData/KF5::Codecs；Qt5::Quick 仅为顶层
  find_package 列出的普通组件，src/ 无任何链接点（tests/ 的
  qmlintegrationtest 才用，且有 `if (TARGET Qt5::Quick)` 守卫）
- 测试（autotests/，BUILD_TESTING=ON 才进构建）：
  - kcontacts-testroundtrip（add_executable + add_test，qrc 内嵌 17 张
    vCard 参考数据）
  - 29 个 ecm_add_tests 目标（NAME_PREFIX kcontacts-）
  - kcontacts-addressformattest（QTEST_GUILESS_MAIN，含 KCountry 数据
    校验）、kcontacts-picturetest（QTEST_MAIN，QImage/Painter）
  - vcardtool_benchmark：上游注释明示"compiled, but not run automatically
    with ctest"——不计入 ctest 用例
  - **合计 32 个 ctest 用例**
- tests/（非 autotests）：testread/testwrite 上游自标 "FIXME: Build
  fails"（手工转换器程序，无 ctest 注册）；qmlintegrationtest 是手工 QML
  demo（非测试）；testread2 无 ctest 注册。整目录经 patches/0001 排除
  （上游本来就构建不过，非 OHOS 差异）

## OHOS 适配要点（沿用 KF5 链先例）

1. **Qt Quick 降级为 OPTIONAL_COMPONENTS**（patches/0001）：库本身不链
   Quick，顶层 find_package 的 Quick 组件是 tests/ QML demo 的遗留；
   5.15.2.2 线无 Quick 供给，降级后库+全量 autotests 照常构建。
2. **CMAKE_SYSTEM_NAME=Linux 双覆盖**：tc.variables + tc.cache_variables
   双写（OHOS 适配版 toolchain 用 cache 条目映射 HarmonyOS，会覆盖
   variables——双保险）。ECMAddTests 只在非交叉构建时注册 ctest，Linux
   平台强制恢复 UNIX 语境（链级惯例，kcoreaddons5 起）。
3. **KF5 底座四件套**：kcoreaddons5/ki18n5/kconfig5/kcodecs5 全走
   cmake_find_mode=none + 手写 conan_cmakedeps_paths.cmake 遍历注入
   lib/cmake（E429 模式，kjobwidgets5 先例）；
   find_package(KF5 COMPONENTS ...) 经 ECM FindKF5 转发模块解析。
4. **qt5-qtbase/5.15.2.2 force=True**：kcoreaddons5 钉 5.15.2，混图被
   conan 拒（E429）；.2 为 DBus 超集二进制，ABI 兼容，整图归一。
5. **iso-codes 测试数据部署**：KCountry 系函数（addresstest 的
   countryToISO/ISOtoCountry、addressformattest 的 repository 校验）经
   QStandardPaths::GenericDataLocation 找 iso-codes JSON + 翻译目录；
   kcontacts 测试**未开** QStandardPaths test mode（与 ki18n5 自己的测试
   不同），XDG_DATA_HOME 即数据根。从 ki18n5 传递依赖的 iso-codes 包
   部署到 <build>/test-home/.local/share/。
6. **msgfmt 接线**：KI18N_INSTALL(po) 的 pofiles 目标跑 msgfmt，gettext
   经 ki18n5 传递入图，GETTEXT_MSGFMT_EXECUTABLE 指到其 bin/。
   KF_SKIP_PO_PROCESSING=ON 跳过 Qt5LinguistTools 侧的 poqm 处理。
7. **ELF 重签名**：install 后 CMake 的 RPATH 重写会使 OHOS 构建期
   .codesign 失效，llvm-objcopy --remove-section .codesign +
   binary-sign-tool sign -selfSign 1 全树重签（ki18n 6.26.0.1 先例）。
8. **ECM 转发头解谜（实证）**：autotests 用安装布局前缀
   `#include "kcontacts/addressee.h"` 而源码树无 src/kcontacts/ 目录——
   ECMGenerateHeaders 对 PREFIX KContacts 的每个名字会在
   ${CMAKE_CURRENT_BINARY_DIR}/kcontacts/ 生成 build-local 小写转发头，
   KDECMakeSettings 的 CMAKE_INCLUDE_CURRENT_DIR_IN_INTERFACE 把
   build/src 放进 BUILD_INTERFACE include 路径，前缀 include 树内可解析，
   无需补丁。

## 上游测试结果（conan create 内嵌 ctest，2026-10-06 实跑）

- **100% tests passed, 0 tests failed out of 32**（第二轮实测，create2.log）
- 32 例清单（ctest 编号序）：kcontacts-testroundtrip、birthdaytest、
  addresseetest、impptest、emailtest、addresstest、geotest、keytest、
  phonenumbertest、secrecytest、soundtest、timezonetest、contactgrouptest、
  vcarddragtest、langtest、gendertest、calendarurltest、ldifconvertertest、
  relatedtest、resourcelocatorurltest、customidentifiertest、vcardlinetest、
  fieldgrouptest、importexportvcardtest、titletest、nicknametest、
  roletest、orgtest、datetimetest、clientpidmaptest、addressformattest、
  picturetest —— 全部 Passed，无一豁免
- vcardtool_benchmark：上游注释明示"compiled, but not run automatically
  with ctest"，按上游设计不计入（32 例不含它）
- KCountry 系函数（addresstest 的 countryToISO/ISOtoCountry、
  addressformattest 的 repository 校验）在 iso-codes 数据部署后真实跑通
  ——addresstest/addressformattest 均 Passed，无环境豁免
- QTEST_MAIN 系测试经 offscreen QPA 平台插件真实执行（qtbase 5.15.2.2
  自带 libqoffscreen.so）

## test_package 结果

- **test_kcontacts5: 26 passed, 0 failed**（R34 API 驱动断言全过）
- 关键断言：Addressee 字段往返（uid/givenName/familyName/note/realName/
  isEmpty/mimeType）、Email/PhoneNumber/Address 插入与集合 getter、
  VCardConverter create→parse 往返（保留 givenName/familyName）、
  ContactGroup+Data、Picture 图像数据、Geo 有效性、R53 ELF 检查
  （DT_SONAME 无版本化 + DT_RUNPATH）
- 消费者二进制在 OHOS 环境真实执行（"kcontacts5 consumer binary
  executed successfully"），非仅链接级回退

## 踩坑记录（conan create 实录）

1. **第一轮失败：iso-codes 传递依赖 package_folder=None**
   `_deploy_iso_codes_test_data` 从 `self.dependencies.get("iso-codes")`
   取到 None folder 报 TypeError。原因：iso-codes 仅经 ki18n5 传递入图，
   非直接 requires。修法：显式 `self.requires("iso-codes/4.20.1")`
   （ki18n5 同款直接依赖先例）。第二轮全绿。
2. **clang nonportable-include-path 警告（非阻断）**：autotests 用小写
   `#include "kcontacts/addressee.h"`，而 ecm_generate_headers 生成
   CamelCase 转发头目录 KContacts/——clang 大小写不敏感解析成功仅发警告。
   上游原样，无需处理。
3. **补丁 Hunk 1 首次干跑失败**：手写补丁上下文行数与真实文件不齐，
   改用 git diff 从修改后文件重新生成，干跑通过。
