# libzeep 8.4.1 — OHOS 适配笔记

## 概述
- 上游：https://github.com/mhekkel/libzeep（tag v8.4.1，官方 tarball）
- 类型：C++23 SOAP/HTTP 服务框架库（BSL-1.0），库产物（无 CLI，无需 commands.json）
- 目标：OpenHarmony PC（aarch64），clang 15.0.4 / libc++15，profile ci/conan/profiles/ohos-aarch64

## 依赖（全部偶 registry 已发布）
- openssl/3.5.8.1（CMake 侧 find_package(openssl CONFIG)）
- date/3.0.3（Howard Hinnant date lib，尝试 run_zoned_time 交叉编译必 FAILED_TO_RUN → 固定走 date 路径，提供 date::date-tz）
- fmt/11.1.3（std::format/std::println 替换）
- fast_float/8.0.1（zeem charconv 依赖，libc++15 无 float from_chars）
- CPM 依赖本地化：zeem v2.4.1（forge 官方 tarball，conandata zeem_sources 预下载 + add_subdirectory）、asio 1-36-0（conandata asio_sources 预下载 + ASIO_INCLUDE_DIR 注入）

## OHOS 适配关键点
1. **CPM 本地化**：CI/设备无法访问 github/forge git。zeem/asio 改由 conandata 额外源下载本地
   build 目录；date/Catch2/FastFloat 走 registry find_package。
2. **std::format/std::println → fmt**：libc++15 无 <format>/<print> 且 libc++.so 无 format 符号
   （llvm-nm 验证同 libcifpp）。约 15 个 libzeep 源文件 + 3 个 zeem 源文件机械替换，
   println 走 std::ostream 重载需 <fmt/ostream.h>；chrono %F 需 <fmt/chrono.h>。
3. **operator<=> 缺失**：libc++15 无 std::string/std::vector/std::map 的 <=>。el-object.cpp
   （object 三路比较：数组/对象/字符串逐项改写）、zeem node.hpp attribute（compare() 显式三路）、
   zeem xpath.cpp node_set（lexicographical_compare）。
4. **std::ranges 兼容**：_LIBCPP_ENABLE_EXPERIMENTAL 恢复 ranges 算法（libcifpp 先例，
   cpp_info.defines 导出给消费者）；std::ranges::contains（C++23 P2302）libc++15 无 → std::find。
5. **std::ranges::binary_search 误判（关键 bug）**：libc++15 实验性 ranges 的 binary_search 对
   "html"（不在空 HTML 元素表内）返回 true（最小复现 1 vs std::binary_search 0），导致 zeem
   HTML 序列化自闭合丢子节点、HTTP 登录页缺 _csrf 输入（上游 http-test 失败）。
   → zeem node.cpp is_empty_element 改 std::binary_search（同表实测正确）。
6. **<source_location> 缺失**：libc++15 无该头，zeem serialize.hpp 仅 include 未使用 → 移除。
7. **C++23 编译**：clang15 无 -std=c++23，CMake 4.1 的 cxx_std_23 自动映射 -std=c++2b（实测编译通过）。
8. **clang15 依赖类型解析缺陷**：el/object.hpp `using difference_type = T::difference_type` 需显式
   typename（glaze 先例）。
9. **P0960 聚合 construct_at 缺陷**：request.cpp lang_score 聚合 emplace 在 libc++15 construct_at
   失败 → 补显式构造函数（libcifpp 先例）。
10. **OpenSSL target**：openssl 配方 CMakeDeps 生成 openssl::openssl（et 先例）替换
    OpenSSL::SSL/OpenSSL::Crypto。
11. **date 库运行时**：MANUAL_TZ_DB 需测试运行目录提供 ./tzdata（IANA tzdata2026b，sha256 与
    date 配方 test_sources 一致）+ TZ=UTC。上游测试 el-test 依赖此环境。
12. **zeem/asio 随包安装**：libzeep 公开头文件引用 <zeem/zeem.hpp> 与 <asio.hpp>（生成的
    zeep/http/asio.hpp），zeem 头/静态库与 asio 头必须打包进 libzeep 制品并声明
    cpp_info.requires（fmt/date/openssl/fast_float）。

## 上游测试
- 全量声明 310 用例（test/*.cpp 枚举），当前配置实例化 13 个可执行（308 用例）。
- 未实例化：daemon-test（HTTP_HAS_UNIX_DAEMON=0）、rsrc_webapp-test（USE_RSRC=0）。
- ctest 13/13 通过（100%），详见 reports/test-ledger.md / reports/upstream-ctest.log。
- 最终配方 BUILD_TESTING=OFF（catch2 不进消费者依赖图，ada-url 先例），测试已在真机全量运行留证。

## 消费者用例
- test_package：zeep::uri + zeep::el JSON（公开 API smoke，随 conan create 运行）。
- ohos_test（鸿蒙专项）：URI/JSON 往返 + 本机 HTTP daemon 真实往返。
- consumer_app（消费者用例）：el 客户记录数组、http request 表单参数、stock_reply、
  业务端点 URI 解析——全部仅用公开 API。
---

**编译结束**: 2026-10-04 21:26
**最终状态**: built
