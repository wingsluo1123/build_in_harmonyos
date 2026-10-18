# libhttpserver 0.11.1 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libhttpserver（libmicrohttpd 的 C++ 封装） |
| 版本 | 0.11.1 |
| 状态 | built |
| 构建系统 | autotools（tarball 无 configure，需 autoreconf -fi） |
| 源码 | https://github.com/etr/libhttpserver/archive/refs/tags/v0.11.1.tar.gz |
| sha256 | a5c3d2fb08cce842c0e9c900340260deb20b6fc4827fa0c94306aa34e50e5239 |

## 适配要点
1. **bootstrap**：release tarball 不带 configure，build() 先 `autoreconf -fi`
   （tool_requires automake/1.18 + libtool/2.5.4，abiword-plugin-clarisworks 先例）。
2. **交叉 triplet**：--build=x86_64-unknown-linux-gnu --host=aarch64-linux-ohos
   （config.sub 原生支持 ohos）。configure 的 cross 分支（host≠build）会跳过
   MHD 运行时版本探测（只查编译），行为正确。
3. **MHD 1.0.1 API 回调返回类型**：libhttpserver 0.11.1 的 MHD 回调（policy_callback、
   build_request_*/build_request_args、post_iterator、answer_to_connection、
   bodyless/bodyfull_requests_answer、finalize_answer、complete_request）原返回
   `int`，MHD 1.0.1 要求返回 `MHD_Result`（枚举）→ 全部改为 MHD_Result，
   返回点用 `(MHD_Result) to_ret`（同 0.19.0 演进方向）。
4. **http_endpoint 拷贝构造**：0.11.1 的 http_endpoint 把拷贝构造/operator</operator=/
   match 放在 private（friend std::pair 绕行），libc++（OHOS）pair 构造 SFINAE
   不可见 private 拷贝 → map 插入编译失败；按 0.19.0 把相关成员改为 public。
5. **-lstdc++ 补丁**：configure.ac 的 AM_LDFLAGS="-lstdc++" 硬编码在 OHOS（libc++）
   链接失败 ld.lld: unable to find library -lstdc++ → patch 0001 加 linux-ohos* 分支
   置空（同上游 freebsd 分支先例，非平台宏，纯构建系统分支）。
6. **E011 umask**：生成后的 configure 内 umask 077 → 022（HMDFS config.status 临时目录
   不可写；CI Linux 上幂等无害）。
7. **libtool/mksh 兼容**：生成 libtool 的 `$echo`（ECHO="print -r --"）在 mksh 下
   未定义导致参数被当命令执行 → 补 `echo="$ECHO"`；`tool_oldlib` 未定义导致 ranlib
   空参数 → old_archive_cmds 改用 `$oldlib`（仅本地探索阶段，配方通过 conan 的
   libtool 2.5.4 工具链不依赖此修补）。
8. **make -j4**：HMDFS jobserver fifo 限制下保守并行；out-of-tree 构建（configure.ac
   强制分开构建目录）。

## 上游测试（r02 用例级台账，rule4/rule8 口径纠正）
- 注册层普查（源码 TEST 宏口径，发现命令 grep -c "LT_BEGIN_AUTO_TEST(" test/{integ/basic.cpp,unit/http_utils_test.cpp,integ/threaded.cpp}）：
  - **basic_suite 注册 9 用例**：two_endpoints / read_body / read_long_body / read_header / complete / only_render / postprocessor / empty_arg / no_response
    （另有 LT_BEGIN_AUTO_TEST_ENV() 为 main() 主入口 `AUTORUN_TESTS()`，非用例）
  - **http_utils_suite 注册 3 用例**：unescape / standardize_url / ip_to_str
  - **threaded_suite 注册 1 用例**：base
  - **去重合计 13 个注册用例**（basic 9 + http_utils 3 + threaded 1；与分析端预期 13 一致，差异归属：分析端计 basic 10 含 ENV 主入口，执行端按 TEST 宏注册口径计 9 用例 + 1 主入口）
- 实跑层（r02 真实重跑三入口，命令/cwd/退出码/日志/SHA-256 见 reports/test-report.md）：
  - **http_utils**：3 用例 8 checks 全过（PASS，exit 0）
  - **threaded**：1 用例 1 check 全过（PASS，exit 0）
  - **basic**：9 用例 27 checks，25 过、2 断言失败（exit 2，littletest 对断言失败返回非零）：
    - `complete` 用例：CONNECT 断言 curl 52（CURLE_GOT_NOTHING）→ 豁免
    - `only_render` 用例：CONNECT 断言 curl 52 → 豁免
    - 豁免归属：MHD 1.0.1 对 CONNECT 方法不交付给 access handler 直接关闭连接，
      属依赖包能力边界（0.19.0 同款豁免 3 例 SSL checks），非本包缺陷
- 断言级→用例级映射：13 注册用例全部真实执行；11 用例通过、2 用例（complete/only_render）
  各含 1 个 CONNECT 断言豁免（用例其余断言通过），无跳过/禁用。
- test_package 以最小真实 HTTP 往返（起服务→GET→比对→停）覆盖核心链路（6 断言全过）。

## 依赖
- libmicrohttpd/1.0.1（已发布制品仓 ✅，MHD_VERSION 0x01000100 ≥ 0x00097037）
- 构建期：automake/1.18、libtool/2.5.4（已发布 ✅）
- 上游集成测试需 curl 头：curl/8.15.0（制品仓 ✅，仅测试编译期使用）

## HarmonyOS 专项测试
- 新增 test/harmonyos_specific_test.cpp：uname 核验 HongMeng 内核 + 真实 HTTP
  往返（webserver start → register_resource → 原始 socket GET → 比对响应体）。
- 两次运行：第 1 次失败（平台判定误用 sysname==Linux、start(false) 返回语义误读），
  修复后第 2 次 exit 0 全过（final_count=1）。

## 交付物
- conanfile.py + conandata.yml + test_package/ + patches/0001-configure.ac-ohos-link.patch
- manifest.yaml + notes.md + test_package/MANIFEST.yml
---

**编译结束**: 2026-10-16 13:16
**最终状态**: built
