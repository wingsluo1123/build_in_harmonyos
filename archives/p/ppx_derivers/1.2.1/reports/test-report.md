# 测试报告 — ppx_derivers 1.2.1

- 日期: 2026-10-11
- 方式: W3 本地 CI（finish step [5/10]，ci/conan/build_and_test.sh）
- 结果: **全部通过（1/1，100%；.ci-result.json exit_code=0）**

## conan create（干净源码构建）
- 配方: dune `-p ppx_derivers @install`（源码未修改，无补丁）
- conan-verify G0–G4 + L2/L4/L5 全部 PASS（2026-10-11，profile ohos-aarch64-device）
- test_package 两个消费者用例在 OHOS worker 原生编译并真实执行，全部通过

## test_package 覆盖（消费者级，鸿蒙特有测试 ≥1）
1. 产物断言: ppx_derivers.{cma,cmxa,cmxs,a,cmi} + META（6/6 存在）
2. 字节码编译: `ocamlc -I <pkg>/lib/ocaml/ppx_derivers -c test_pd.ml`
3. 原生编译+运行 test_pd.ml：4 断言（注册后 lookup 命中、
   derivers() 包含条目、未知 lookup 返回 None、重复注册抛异常
   ——后两项为负例控制）→ "ALL TESTS PASSED"
4. 原生编译+运行 test_ohos_e2e.ml（鸿蒙特有测试）：真实文件 I/O —
   注册 deriver、注册表内容序列化到文件、读回并复核注册/查询
   → "ALL OHOS E2E PASSED"（3 断言）

## 上游测试（R51）
- 清点: v1.2.1 tarball 无 test/ 目录（仅 src/、pkg/pkg.ml 与 dune 元数据）→ N=0
- 适配回归由 test_package 消费者用例覆盖（7 断言，OHOS 真实执行）

## 门禁
- L0/L1/L1e/L2/L5：见本地 CI 日志与 .ci-result.json
