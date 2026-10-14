# kodi-inputstream-adaptive 21.5.16 适配笔记

## 结论

适配成功：全新 recipe（官方仓 archives/k/ 无本库先例，复用 kodi-inputstream-rtmp/21.1.2
模式）。上游 gtest 套件 58 用例全部真实执行通过（ctest manifest_tests）；
test_package 消费者测试 26 项断言全过（含 7 项本移植 OHOS 适配点新增用例）。

## 版本映射与源码身份

- 产品版本 `21.5.16` ↔ 上游 tag `21.5.16-Omega`（xbmc/inputstream.adaptive，
  tag commit `0b4dbaeffd175c4cddd32f7fd61cf81f12bda27d`）。
- 归档 `https://github.com/xbmc/inputstream.adaptive/archive/refs/tags/21.5.16-Omega.tar.gz`
  SHA256 `da61399c2aa3f1f67b4e3f293952b0fa16c90a7e1effa606f99676ff8144d25e`
  （Scout 三路实测一致；conandata gh-proxy 镜像首选 + GitHub 直连双 URL）。
- License：GPL-2.0-or-later（LICENSE.md 原文 SPDX 标识 + LICENSES/ 多许可目录，
  两者均随包安装）。

## 依赖闭包

- `pugixml/1.16`（registry；静态 PIC 归档编入模块；上游 Findpugixml 1.x 兼容）
- `rapidjson/1.1.0.1`（registry；header-only）
- `gtest/1.17.0`（registry；仅上游测试链接。上游 depends/common pin googletest
  1.14.0 未发布到 registry，且 FindGtest 门槛为 gtest>=1.10。注意 registry 上
  `gtest` 与 `googletest` 是两个包——registry 的 rapidjson/1.1.0.1 recipe 传递
  require 的是 `gtest/1.17.0`（target gtest::gtest），本配方与其对齐保持图内
  单一 gtest 包； googletest/1.15.2 在 remote 不存在（conan list 实测）
- **bento4 不用 registry 包**：registry `bento4/1.6.0-641` 是 axiomatic-systems
  官方上游，而上游 depends/common/bento4/bento4.txt pin 的是 **xbmc fork
  1.6.0-641-3-Omega**（版本族不同：fork 在官方 641 基础上带 3 个补丁，ISA 按
  fork API 编写）→ 按 E277 vendored 模式把 fork tarball 写进 conandata.yml
  （SHA256 `a9b231b63159b3a4d9e47c5328b476308852bf092ccb9ce98f7cf46a386465ce`），
  source() 抽取到 <source>/bento4，recipe-cmake 内编静态 PIC 库（ap4）
- 内置静态库：lib/mpegts、lib/webm_parser、lib/cdm（上游 CMakeLists 原样
  add_subdirectory，均 POSITION_INDEPENDENT_CODE True）
- 系统：pthread/dl（musl）；产物 DT_NEEDED 仅 libc++_shared.so + libc.so

## 构建方案（recipe-cmake 独立入口，上游源码零修改）

1. **Kodi 构建系统缺失**：上游 find_package(Kodi)/build_addon() 需要 Kodi 源树。
   仿 rtmp/21.1.2 用 recipe-cmake/CMakeLists.txt（build_script_folder），但比
   rtmp 更进一步：直接 `include(<tarball>/Helpers.cmake)` 复用 add_dir_sources /
   source_group_by_folder 宏，并原样 add_subdirectory 上游 src/ 与 lib/ 子目录
   CMakeLists——上游子目录只向 GLOBAL property 声明文件清单，本配方消费
   GlobalSourceList 建自己的 SHARED 目标，上游源文件列表零复制、零漂移。
   widevine 经上游 decrypters/CMakeLists（standalone 无 CORE_SYSTEM_NAME 走
   widevine 分支）注册的 GlobalDepsFoldersList 自动带入 lib/cdm；
   cdm_aarch64_loader 上游仅 CMAKE_SYSTEM_NAME=Linux 注册，HarmonyOS 与上游
   行为一致跳过。
2. **bento4 PIC（Scout 风险 1）**：静态 libap4.a 链入共享模块必须 PIC——上游
   FindBento4 ENABLE_INTERNAL_BENTO4 路径即显式 -fPIC。本配方以
   `CMAKE_POSITION_INDEPENDENT_CODE ON` 覆盖 ap4/mpegts/webm_parser/cdm_library
   全部静态库。include 布局：上游安装为 include/bento4/（ISA 代码
   `#include <bento4/Ap4.h>`），内编时用 staging 目录（configure 期 file(COPY)
   头文件到 build/bento4-staged/include/bento4）提供同名风格，ap4 target PUBLIC。
3. **SONAME（Scout 风险 2）**：显式 `-Wl,-soname,libinputstream.adaptive.so`
   （OHOS 平台 CMake 不发 soname；CI L5a 门禁）。产物实测：
   `readelf -d` SONAME=libinputstream.adaptive.so（相对路径），
   FLAGS=BIND_NOW，DT_NEEDED 仅 libc++_shared.so/libc.so。
4. **standalone widevine（Scout 风险 3）**：widevine（纯 C++）+ lib/cdm 编入
   模块，链接 ${CMAKE_DL_LIBS}；libwidevinecdm.so 是运行期 dlopen 可选组件，
   非构建依赖。声明与守卫与上游一致，无额外 patch。
5. **gtest（Scout 风险 4）**：registry gtest/1.17.0（>= 上游 FindGtest 门槛
   1.10）替代上游 pin 的 googletest 1.14.0。
6. **链接闭包显式化**：全部依赖走 CMake target 显式链接（ap4/pugixml::pugixml/
   rapidjson::rapidjson/mpegts/webm_parser/cdm_library），无 lld 隐式闭包依赖；
   产物仅剩 libc/libc++ 系统运行时 NEEDED，test_package dlopen(RTLD_NOW) 全
   闭包加载成功为运行期实证。

## 上游测试（L1，真实执行）

- 入口：src/test/CMakeLists.txt → add_test(NAME manifest_tests COMMAND
  inputstream.adaptive_test <src>/src/test/manifests)；生产源码以
  `#ifdef INPUTSTREAM_TEST_BUILD` 把 Kodi 头路由到 src/test/KodiStubs.h 桩
  （`#include "test/KodiStubs.h"` 经 -I<src> 解析），不需要 Kodi 宿主；
  kodi/tools/StringUtils.h 等纯工具头走 vendored kodi-dev-kit 真实头
  （test 目标 -I kodi-dev-kit）。
- 本配方 build() 内 `ctest -V --test-dir <build>` 真实执行：
  **[==========] 58 tests from 5 test suites ran. [ PASSED ] 58 tests.**
  （TestDASHTree 30 / TestHLSTree 16 / TestSmoothTree 3 / TestUtils 9，本地
  fixtures 离线）。失败非零退出即构建失败（真门禁，非装饰性）。
- 注意：测试源列表（44 单元）≠ 模块源列表（src/ 全树），不可复用模块目标；
  gtest 包 CMakeDeps 名为 gtest（find_package(gtest CONFIG REQUIRED)，target
  gtest::gtest；TestMain.cpp 自带 main，不链 gtest_main）。

## test_package 设计（26 项断言，全过）

- Part 1（6）：链接产物调 ADDONCREATOR 导出 ADDON_GetTypeVersion/MinVersion，
  断言 inputstream=3.3.0/3.3.0、general=1.0.5/1.0.4、main=2.0.2/2.0.0
  （vendored kodi-dev-kit 21.3-Omega 头真实编入）。
- Part 2（13）：dlopen(相对 DT_SONAME) + dlsym ADDON_Create，以最小 Kodi 宿主
  桩走稳定 C ABI 全流程：ADDON_Create 实例化真实 CMyAddon（CAddonBase）；
  create_instance(ADDON_INSTANCE_INPUTSTREAM) 构造真实 CInputStreamAdaptive
  并布线 open/close/get_capabilities；GetCapabilities 精确断言上游掩码
  IDEMUX|IPOSTIME|IDISPLAYTIME|SEEK|PAUSE|ICHAPTER=0x5F；无会话
  get_time/get_total_time 返回 0（上游 null-session 守卫）；
  destroy_instance/destroy/dlclose 无崩溃收尾。C ABI 结构体按 kodi-dev-kit
  c-api 逐字转写 + static_assert 布局守卫（31 指针 inputstream 函数表等）。
- Part 3（7，**本移植 OHOS 适配点强制新增用例**）：
  1. dlclose 后按相对 SONAME 重开成功；
  2. dladdr(符号地址) 命中设备上真实 libinputstream.adaptive 文件
     （运行期映射实证）；
  3. RTLD_NOLOAD 按相对 SONAME 命中已加载模块（SONAME 注册实证，与 CI L5a
     互补）；
  4. OHOS musl dlopen(RTLD_NOW) 全闭包解析成功（E004 BIND_NOW 语义 + lcmaps
     dlopen 作用域教训的运行期验证：模块未定义符号仅自身 DT_NEEDED 闭包解析，
     模块自含静态 PIC 依赖）；
  5-7. musl libc 语义（生产代码路径依赖）：timegm（oscompat _mkgmtime 替代）
  2024-01-02T03:04:05Z→1704164645、gmtime(0) 逆变换、strcasecmp、
  snprintf+PRIu64。
  本移植无源码 patch（构建入口改写在 recipe-cmake），故 OHOS 差异面 =
  SONAME/链接闭包/musl libc 三类，Part 3 逐一覆盖。

## 遗留风险

- Kodi 宿主端到端播放（真实 DASH/HLS 网络流、CDM 解密路径）未覆盖（设备无
  Kodi 宿主）；上游 58 用例覆盖 manifest 解析/段逻辑，test_package 覆盖加载、
  ABI 工厂与实例生命周期；真实流会话需宿主侧验证。
- widevine CDM 路径编入但设备无 libwidevinecdm.so：运行期 dlopen 可选失败路径，
  与上游 Linux 行为一致；若宿主环境有安全标签（E212 hmmac）限制 dlopen 用户
  路径 .so，属部署面问题而非本包缺陷。
- registry rapidjson/1.1.0.1 recipe 自带 gtest/1.17.0 传递依赖（其上游测试
  用），使本包图内多一个构建期包；无产物影响（rapidjson header-only，gtest 不
  进模块）。
