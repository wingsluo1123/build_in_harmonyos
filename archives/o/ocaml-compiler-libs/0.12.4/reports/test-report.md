# 测试报告 — ocaml-compiler-libs 0.12.4

- 日期: 2026-10-11
- 方式: W3 本地 CI（finish step [5/10]，ci/conan/build_and_test.sh）
- 结果: **全部通过（1/1，100%；.ci-result.json exit_code=0）**

## conan create（干净源码构建）
- 配方: dune `-p ocaml-compiler-libs @install`（源码未修改，无补丁）
- conan-verify G0–G4 + L2/L4/L5 全部 PASS（2026-10-11，profile ohos-aarch64-device）
- test_package 两个消费者用例在 OHOS worker 原生编译并真实执行，全部通过

## test_package 覆盖（消费者级，鸿蒙特有测试 ≥1）
1. 产物断言: META、common/ocaml_common.{cma,cmxa,cmxs,a}、
   bytecomp/ocaml_bytecomp.cmxa、shadow/ocaml_shadow.cma、
   toplevel/ocaml_toplevel.cmxa（8/8 存在）
2. 字节码编译: `ocamlc -I <pkg>/lib/ocaml/ocaml-compiler-libs/common
   -I <ocaml>/lib/ocaml/compiler-libs -c test_ocl.ml`
3. 原生编译+运行 test_ocl.ml：4 断言（Pprintast 打印 42、
   Parse.implementation 解析 `let x = 1`、Longident.last、
   Location.none）→ "ALL TESTS PASSED"
4. 原生编译+运行 test_ohos_e2e.ml（鸿蒙特有测试）：真实文件 I/O —
   写入 `let answer = 42` 源文件、读回、Parse 解析、Pprintast 回印并校验
   往返文本 → "ALL OHOS E2E PASSED"（3 断言）

## 上游测试（R51）
- 清点: v0.12.4 tarball 无 test/ 目录（仅 src/ 库代码 + gen 生成器）→ N=0
- 别名模块由 gen.exe 扫描已安装 compiler-libs 自动生成，构建即验证重打包
  与 OCaml 4.14.1 的兼容性
- 适配回归由 test_package 消费者用例覆盖（7 断言，OHOS 真实执行）

## 门禁
- L0/L1/L1e/L2/L5：见本地 CI 日志与 .ci-result.json
