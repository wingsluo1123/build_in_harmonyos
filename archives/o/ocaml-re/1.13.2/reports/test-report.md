# 测试报告 — ocaml-re (re) 1.13.2

- 日期: 2026-10-12
- 方式: W3 本地 CI（finish step [5/10]，ci/conan/build_and_test.sh）
- 结果: **全部通过（1/1，100%；.ci-result.json exit_code=0）**

## conan create（干净源码构建）
- 配方: dune `-p re @install`（源码未修改，无补丁）
- conan-verify G0–G4 + L2/L4/L5 全部 PASS（2026-10-12，profile ohos-aarch64-device）
- test_package 两个消费者用例在 OHOS worker 原生编译并真实执行，全部通过

## test_package 覆盖（消费者级，鸿蒙特有测试 ≥1）
1. 产物断言: re.cma/.cmxa/.cmxs/.a、re.cmi、META 及 4 个子库归档
   (emacs/glob/pcre/str 的 .cmxa)（10/10 存在）
2. 字节码编译: `ocamlc -I <pkg>/lib/ocaml/re re.cma test_re.ml`（compile-only）
3. 原生编译+运行 test_re.ml：9 断言 — Perl 日期分组提取、Glob 通配
   接受/拒绝、Posix 锚定类接受/拒绝、split、replace_string、
   Str.string_match 兼容层接受/拒绝 → "ALL TESTS PASSED"
4. 原生编译+运行 test_ohos_e2e.ml（鸿蒙特有测试）：真实文件 I/O —
   写入 key=value 报告文件、逐行正则解析与聚合（3 行 / 6 位数字）、
   结果文件写出并读回校验 → "ALL OHOS E2E PASSED"

## 上游测试（R51）— 129/129 真实执行通过
- 清点: lib_test/expect = 129 个 `let%expect_test` 用例（21 个 test_*.ml）；
  lib_test/str = ounit2 套件；lib_test/fort_unit = ounit2 兼容层
- **执行结果（OHOS 设备真实执行，2026-10-15）**:
  - `inline_test_runner_re_tests.exe inline-test-runner re_tests -list-test-names` →
    枚举 129 项；`-verbose` 逐例执行输出 129 行、进程 rc=0
  - `dune runtest lib_test` rc=0；lib_test 下 0 个 `.corrected`（期望零偏离）
  - lib_test/str（ounit2）: `Ran: 18 tests in: 0.13 seconds.` + `OK`（18/18）
- 执行环境说明: 上游测试框架（ppx_expect / base / ppx_inline_test / ounit2 等
  20+ 包）不在制品仓发布（ppx_expect→ppxlib 制品仓依赖环），故由官方源码在
  本地验证环境构建完整框架链后执行；**测试源码与期望值零修改**，仅 2 处
  构建配置适配（inline_tests 用 native 模式——js 后端需 js_of_ocaml；显式开启
  implicit_transitive_deps）。完整构建与运行日志随本地验证材料归档。
- 适配回归仍由 test_package 消费者用例覆盖（10 产物断言 + 9 API 断言 + 3 步
  e2e 流程，OHOS 真实执行）

## 门禁
- L0/L1/L1e/L2/L5：见本地 CI 日志与 .ci-result.json
