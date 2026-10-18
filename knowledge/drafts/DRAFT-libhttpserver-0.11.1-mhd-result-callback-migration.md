# DRAFT — libhttpserver 0.11.1: MHD 1.0.x 枚举回调迁移 + configure LDFLAGS 覆盖

- 来源: libhttpserver 0.11.1 适配（pc1-42 r01）
- 阶段: conan-verify G2 (conan create, ohos-aarch64) + upstream tests + W3
- 路径: Path B（知识库扩展，无等价命中、可跨库复用）

## 问题

1. 老版 C++ 包装库 / 直接使用 libmicrohttpd 回调的库（回调声明为 `int`）在
   conan 依赖变为 libmicrohttpd 1.0.x 后编译失败：
   `error: no matching function for call to 'MHD_start_daemon'` /
   `'MHD_create_post_processor'` / `'MHD_get_connection_values'`，提示
   `no known conversion from 'int (*)(...)' to 'MHD_AcceptPolicyCallback'
   (aka 'MHD_Result (*)(...)...')`。
2. autotools 库在 configure.ac 中重新赋值 `LDFLAGS=...`（例如上游在
   AC_CHECK 之后 `LDFLAGS="$LIBMICROHTTPD_LIBS $REGEX_LIBS $LD_FLAGS"`），
   把外部（conan generate / CLI）传入的 `-L<libdir>` 覆盖清空，最终链接报
   `ld.lld: error: unable to find library -lmicrohttpd`。

## 根因

1. libmicrohttpd 0.9.71+ 把回调返回类型从 `int` 改为枚举 `MHD_Result`。
   1.0.1（本任务制品）的所有回调 typedef（MHD_AcceptPolicyCallback /
   MHD_AccessHandlerCallback / MHD_KeyValueIterator / MHD_PostDataIterator
   等）返回 `MHD_Result`；旧代码回调仍签名为 `int`，C++ 严格类型下函数指针
   不兼容。
2. configure 的 `AC_SUBST(LDFLAGS)` 只在配置期读一次环境值；若 configure.ac
   内再赋值覆盖，生成的 Makefile 中 `LDFLAGS` 只剩上游自己的内容，`-L`
   丢失。

## 方案

1. 把库内所有被 MHD 接受的静态回调成员函数返回类型从 `int` 改为
   `MHD_Result`（policy_callback / build_request_* / post_iterator /
   answer_to_connection 及内部转发函数 bodyless/bodyfull_requests_answer、
   finalize_answer、complete_request），返回点显式 `(MHD_Result) to_ret`。
   头文件同步声明 + `#include <microhttpd.h>`（若此前只有前置声明）。
2. configure.ac 补丁：把上游的 LDFLAGS 赋值改为保留外部值
   `LDFLAGS="$LIBMICROHTTPD_LIBS $REGEX_LIBS $LD_FLAGS $LDFLAGS"`；
   或在配方 generate() 中把 `-L` 注入 CPPFLAGS/LDFLAGS 并加补丁保留。

## 验证

- conan-verify G2（clean source + 全部补丁 + ohos-aarch64 profile）通过，
  test_package 真实 HTTP 往返 6 断言全过。
- upstream tests：http_utils PASS、threaded PASS、basic 25/27（2 CONNECT
  豁免为依赖能力边界）。

## 适用边界

- 仅影响声明回调为 `int` 且依赖 MHD >= 0.9.71/1.0.x 的 C/C++ 库。
- configure LDFLAGS 覆盖问题适用于所有 autotools 库 + 外部 -L 注入场景。

## 反例/限制

- 平台宏禁用于补丁：-lstdc++ 分支应走 configure.ac 的 host_os 分支（同
  freebsd 处理），不得在源码里加 `__OHOS__` 判断。
- 不要为绕 -L 丢失而把 `-version-number` 等 libtool 参数塞入 make 命令行
  LDFLAGS（conan 会拆 token 导致 make 误解析）；正解是 configure 保留。

## 查重差异

- DRAFT-cgicc-3.2.19-libstdcxx-hardcode-to-libcxx：仅覆盖 -lstdc++ 链接失败，
  不覆盖 MHD_Result 回调类型迁移与 configure LDFLAGS 覆盖。
- E384：自写 configure 裸 -l 探测；DRAFT-10251：automake per-target CPPFLAGS
  空覆盖；均与 MHD_Result / AC_SUBST LDFLAGS 覆盖不构成等价命中。