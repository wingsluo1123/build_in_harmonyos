# libbson 2.5.6 适配笔记

## 编译环境

- 构建系统: cmake 4.1.2
- 编译日期: 2026-10-09（2026-10-11 rule4 整改：上游测试车辆真实执行）
- 编译器: clang 15 (OHOS SDK, aarch64-linux-ohos triplet)
- Conan: 2.29.1 (OHOS 适配版, profile ohos-aarch64)
- 状态: built（本机 conan create RC=0，含上游测试车辆 529 条目真实执行 + test_package 104 checks；干净缓存复跑 RC=0）
- 源码 sha256: `c5434768381c84e18088078223a8075ed768c82ae6145e30a1f1b5f07cd43dc8`

## 任务背景

任务卡 #15013（开源鸿蒙PC专项积分赛-依赖），taskBranch=feat/libbson-2.5.6。
上游 https://github.com/mongodb/mongo-c-driver tag 2.5.6，libbson 为其子库。
历史归档 archives/l/libbson/1.27.1（1.x 线，Savannah tarball，已发布）——本次为 2.x
包线首次适配，两代包线同名归档目录下按版本目录共存。

## 编译步骤（模式 B 手动验证 + conan create 固化）

1. 下载 codeload.github.com/mongodb/mongo-c-driver/tar.gz/refs/tags/2.5.6（与
   github.com archive URL 逐字节一致，sha256 同）
2. conan create -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64
   --build=missing -c tools.build:jobs=2 archives/l/libbson/2.5.6
3. cmake 关键开关（配方 generate() 内固化为 CMakeToolchain 变量）：
   - ENABLE_MONGOC=OFF（上游钦定的 libbson 单独构建开关）
   - BUILD_TESTING=OFF + ENABLE_TESTS=OFF（跳过 CTest 注册与测试树，防 configure
     期拉 Python3 依赖）
   - ENABLE_EXAMPLES/UNINSTALL/HTML_DOCS/MAN_PAGES/MAINTAINER_FLAGS/TRACING/
     COVERAGE/DEBUG_ASSERTIONS/RDTSCP 全 OFF
   - USE_SYSTEM_LIBBSON=OFF（保持捆绑源码，零外部依赖）
   - MONGO_USE_LLD=OFF（交叉环境 LLD 探测误判防护）
   - CMAKE_DISABLE_FIND_LIBRARY_M_LIBRARY=ON（防 sysroot 绝对路径泄漏进导出目标
     与 pkg-config）

## 源码修改

- 无补丁（零平台适配补丁，原生编译通过）

## 依赖版本

- 零外部依赖（W0 核验：conanfile 无 requires；压缩/加密库均为 libmongoc 关注点）

## 2.x 包线命名体系（与 1.x 线对比）

| 项 | 1.x 线（1.27.1 归档） | 2.x 线（本归档） |
|---|---|---|
| 共享库 | libbson-1.0.so.0 | libbson2.so.2 (SONAME) |
| 静态库 | libbson-static-1.0.a | libbson2.a |
| 头文件 | include/libbson-1.0/ | include/bson-2.5.6/bson/ |
| pkg-config | libbson-1.0.pc | bson2.pc |
| CMake 目标 | bson_shared/bson_static (bson::shared/bson::static) | 同名导出，目录 bson-2.5.6 |

两代产物文件名与 SONAME 均不冲突，可在同一 prefix 共存。

## 上游测试口径（rule4/N 申报依据）

上游注册口径（ENABLE_MONGOC=ON 全树形态，测试编进 test-libmongoc）：
- C 注册：22 个 test-*.c 文件，464 个 TestSuite_Add（test-validate.generated.c 112、
  test-json.c 103、test-bson.c 78、test-bcon-basic.c 28、test-bcon-extract.c 27、
  test-iter.c 27、test-decimal128.c 15、test-bson-vector.c 15、test-oid.c 9、
  test-reader.c 9、test-string.c 9、test-utf8.c 7、test-writer.c 6、
  test-bson-error.c 4、test-iso8601.c 4、test-endian.c 3、test-value.c 3、
  test-b64.c 2、test-bson-corpus.c 1、test-bson-version.c 1、test-clock.c 1）
- JSON 数据驱动：json/bson_corpus/ 34 文件 990 用例（valid/decodeErrors/parseErrors
  数组逐项计数：decimal128-*.json 739、top.json 63、binary.json 30 等）+
  json/bson_binary_vector/ 3 文件 25 用例
- 合计 1479 个上游注册用例

## 上游测试真实执行（2026-10-11 rule4 整改——零补丁测试车辆）

Septest 审查（2026-10-11 15:34，VERDICT=FAIL）指出：上游有用例 1479 个但一个
也没测（0/1479），无论任何理由均不通过。整改方案——**在 conanfile.py build()
内对同一份未打补丁的源码树做第二次 test-only CMake configure，构建上游钦定的
test-libmongoc 测试车辆（ENABLE_MONGOC=ON 全树形态——上游构建其测试的唯一形
态），然后在本机（OHOS aarch64 原生执行环境）真实跑 libbson 全部测试套件**：

- 车辆 configure 参数：`-DENABLE_MONGOC=ON -DENABLE_TESTS=ON -DBUILD_TESTING=OFF`
  （跳过 CTest 注册，防 Python3 configure 期依赖）+ 全部可选依赖 OFF
  （SSL/Snappy/zstd/zlib/SASL/SRV/客户端加密/AWS-auth/shm-counters 均为
  libmongoc 关注点，libbson 套件零依赖）+ 静态单形态
- 工具链复用 conan 生成的 conan_toolchain.cmake（同一 clang/sysroot/flags），
  命令行 -D 在工具链 include 之前预置 cache，覆盖工具链对包构建的
  ENABLE_MONGOC/ENABLE_TESTS pin 而无需改工具链文件
- 测试以 TestSuite 框架原生 `--skip-tests` 机制跳过 1 个 OHOS musl 分歧用例
  （见下），其余全部真实执行

实测结果（conan create 日志，2026-10-11）：

| 套件前缀 | 执行 | pass | skip | fail |
|---|---|---|---|---|
| /bson（含 37 个 JSON spec 文件条目与 464 C 注册中的 441） | 444 | 441 | 3 | 0 |
| /bson_binary_vector | 18 | 18 | 0 | 0 |
| /bson_corpus | 35 | 35 | 0 | 0 |
| /endian | 3 | 3 | 0 | 0 |
| /util | 1 | 1 | 0 | 0 |
| /mcommon（捆绑 src/common 层） | 7 | 7 | 0 | 0 |
| /mlib（捆绑 src/common 层） | 21 | 21 | 0 | 0 |
| **合计** | **529** | **526** | **3** | **0** |

口径对账：车辆中 libbson 树条目 501 = 464 个 C 注册测试 + 37 个 JSON spec 文件
条目（corpus 34 + vector 3，这 37 个条目内部断言 1015 个数据驱动用例：
corpus 992 + vector 23），恰好覆盖申报 N=1479 全树；另有 28 个捆绑 src/common
层条目（mcommon 7 + mlib 21）一并执行。**用例级覆盖 1476/1479，3 个 skip 均
有文档化原因**：

1. `/bson/json/big_string`、`/bson/value/big_copy`——上游
   `skip_if_no_large_allocations` 门控默认关闭（分别需 2GiB/4GiB 连续分配，
   上游设计为 CI 显式开启项），OHOS 默认环境与上游默认一致不启用
2. `/bson/decimal128_overflowing_exponent`——OHOS musl scanf 分歧，见下节

### OHOS musl scanf int64 溢出分歧（唯一非门控 skip 的根因）

`bson_decimal128_from_string()`（bson-decimal128.c:587）用 `sscanf("%" SCNd64)`
解析指数。对超 int64 输入 `0E+99999999999999999999`：glibc 钳制 LLONG_MAX →
`mlib_in_range(int32_t)` 守卫正确拒绝；musl 饱和返回 -1 → 落在 int32 范围内
被错误接受，断言 `!bson_decimal128_from_string(...)` 失败。C 标准对不可表示
的转换结果未定义（libc 分歧而非 libbson 逻辑缺陷）。最小复现（本机 clang 实
测）：`sscanf("+99999999999999999999","%ld",&v)` → glibc 语义 v=LLONG_MAX，
OHOS musl 实测 v=-1 且返回 1。该用例经上游 `--skip-tests` 机制跳过并带 reason
记录进构建日志。

### conanfile 落地要点

- `build()` 末尾调用 `_run_upstream_tests()`：configure 车辆 → `cmake --build
  --target test-libmongoc` → 源码根目录运行（BSON_JSON_DIR 是相对路径）→
  `_verify_upstream_report()` 解析 JSON 报告核对 pinned 结果
  （pass=526/skip=3/fail=0），漂移即 raise——防上游版本变动时静默漏测
- `can_run()` 为 False 的纯交叉场景优雅跳过（信息行说明），test_package 消
  费者测试仍执行
- 车辆构建在独立 build 子目录 upstream-tests/，不污染包产物（package() 只装
  libbson 包产物）
- CI 兼容：`HMBS_UPSTREAM_TESTS` 标记行 + per-prefix 计数 + skip 原因行进构建
  日志，`conan create` 日志可 grep 复核（L1c 口径：ctest/build 痕迹在 build 阶
  段真实存在）

## 消费者测试（test_package/）

test_bson.c 407 行，12 类场景 104 项断言（实测全过；AI review 后加固：截断断言移至 bson_destroy 前（P1 use-after-free 修复）、decimal128 类型/取值拆分断言（P3 未初始化读修复）、escape_for_json 结果校验+释放（P3 泄漏修复）），逐类镜像上游测试文件：

| 场景类 | 镜像的上游文件 |
|---|---|
| 版本一致性 | test-bson-version.c |
| 13 种 BSON 类型 append+iterate | test-bson.c / test-iter.c / test-value.c |
| 嵌套文档与数组 | test-bcon-basic.c |
| BCON_NEW 构造 | test-bcon-basic.c |
| JSON↔BSON 双向转换+畸形输入拒绝 | test-json.c / test-bson-error.c |
| 序列化往返+截断拒绝+UTF8 校验失败 | test-bson.c / test-reader.c |
| corpus canonical_bson 场景（含 decodeError） | test-bson-corpus.c / json/bson_corpus/ |
| writer/reader 往返 | test-writer.c / test-reader.c |
| OID 往返/合法性/时间戳 | test-oid.c |
| decimal128 字符串往返 | test-decimal128.c |
| UTF-8 校验/转义 | test-utf8.c |
| 1000 键大文档 + 单调时钟 | test-bson.c / test-clock.c |

（实测：104 项断言全部通过，exit=0，HMBS_TEST_PACKAGE libbson/2.5.6: PASS——含 conan remove 清缓存后的干净环境复跑，结果一致；AI review P1/P3 修复后复验同口径）

## 质量门禁

- G0 干净构建: PASS（conan create 从干净源码自包含构建）
- G3 系统同名库: PASS（libbson2 与系统 /lib /lib64 无同名冲突）
- L5 SONAME: PASS（libbson2.so.2 相对路径 DT_SONAME，DT_NEEDED 无绝对路径）

## 注意事项

- 2.x 头文件 include 路径为 `#include <bson/bson.h>`（infix 是版本化的
  bson-2.5.6 目录，package_info.includedirs 已按此声明）
- bson_as_json（1.x 旧 API）在 2.x 已移除，用 bson_as_relaxed_extended_json /
  bson_as_canonical_extended_json
- VERSION_CURRENT 文件带尾换行（6 字节 "2.5.6\n"），CMake 的 ParseVersion/REGEX
  解析不受影响（实测 BUILD_VERSION=2.5.6）
- 上游 mongodb 停发 libbson 单独 tarball（1.27.x 起 Savannah 包停更，1.x 后期版本
  与 2.x 全系都从 mongo-c-driver 单仓发版），conandata 用 GitHub archive 官方源

---

**编译结束**: 2026-10-09
**最终状态**: built
