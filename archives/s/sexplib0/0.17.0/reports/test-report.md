# 测试报告 — sexplib0 0.17.0

- 日期: 2026-10-14（规则 4 修复版）
- 方式: W3 本地 CI（finish step [5/10]，ci/conan/build_and_test.sh）
- 结果: **通过**（本地 W3 同源 CI exit 0；上游测试 7/7 用例、40/40 断言真实执行通过；test_package 20/20）

## conan create（干净源码构建）
- 配方: `dune build -p sexplib0 @install`（库本体零修改）
- 配方（本轮新增）: `dune runtest` —— **上游 7 个用例在 build() 内真实执行**
- conan-verify G0–G4 + L2/L4/L5 全部 PASS（profile ohos-aarch64-device）
- test_package 两个消费者用例在 OHOS worker 原生编译并真实执行，全部通过

## 上游测试（R51）——真实执行结果
- 清点: `test/sexplib0_test.ml` 7 个 expect 用例、40 条 `[%expect]` 期望断言
- 实测: **7/7 用例、40/40 断言通过**（`ALL UPSTREAM TESTS PASSED (7 cases, 40 checks)`）
- 实现说明（框架移植）: 上游测试栈（base v0.17 需 OCaml≥5.1；expect_test_helpers_core
  依赖 core/ppx_jane 未发布；Sexplib.Conv_error 属完整 sexplib 包）在公开环境不可构建，
  故以 portability 补丁把测试框架移植为独立运行器：
  - **7 个用例的输入字符串与全部 40 条期望输出逐字保留**（未增删改任何用例）；
  - 替换项：Parsexp 输入解析（用例输入均为简单 atom/list）、Base.Or_error 的
    `(Ok ...)`/`(Error (Of_sexp_error ...))` 渲染、Base.Result.t_of_sexp、
    `Sexplib.Conv_error`→`Sexp_conv_error`、`[@@deriving sexp_of]`→手写打印函数、
    `[%expect]`→白空格归一化比较；
  - 被测代码 100% 为包内 sexplib0 本体。
- 详见 test_package/MANIFEST.yml 申报表与 notes.md「上游测试的真实执行」一节。

## test_package 覆盖（消费者级，鸿蒙特有测试 ≥1）
1. 产物断言: sexplib0.cma/.cmxa/.cmxs/.a、sexplib0.cmi、
   sexplib0__Sexp.cmi、sexplib0__Sexp_conv.cmi、META（8/8 存在）
2. 字节码编译: `ocamlc -I <pkg>/lib/ocaml/sexplib0 sexplib0.cma test_sexplib0.ml`
3. 原生编译+运行 test_sexplib0.ml：15 断言（Sexp 构造/打印、equal/compare、
   Sexp_conv int/string/bool/list 双向转换、Sexpable、Sexp.message）
4. 原生编译+运行 test_ohos_e2e.ml（鸿蒙特有测试）：真实文件 I/O 5 断言
   → "ALL OHOS E2E PASSED"

## 门禁
- L0/L1/L1e/L2/L5：见本地 CI 日志与 .ci-result.json
