# 测试报告 — cinaps 0.15.1

- 日期: 2026-10-12
- 方式: W3 本地 CI（finish step [5/10]，ci/conan/build_and_test.sh）
- 结果: conan-verify G0–G4 + L2/L4/L5 全部 PASS；conan create 冒烟（含 test_package 真机执行）rc=0 全部断言通过；W3 本地 CI 待依赖 ocaml-re/1.13.2 发布后执行（R36）

## conan create（干净源码构建）
- 配方: dune `-p cinaps @install`（源码未修改，无补丁）
- conan-verify G0–G4 + L2/L4/L5 全部 PASS（2026-10-12，profile ohos-aarch64-device）
- test_package 消费者用例在 OHOS worker 真实执行打包后的 cinaps 二进制

## test_package 覆盖（消费者级，鸿蒙特有测试 ≥1）
1. 产物断言: bin/cinaps、lib/cinaps/META、runtime/cinaps_runtime.cma/.cmxa（4/4）
2. `cinaps --help` 正常运行并输出选项表
3. staged 生成 + 编译：`cinaps -staged staged_in.ml in_sync.ml`
   （in_sync.ml 为上游 test_staged.ml 原文），staged 驱动对打包的
   cinaps.runtime 子库 + unix 原生编译链接成功
4. in-sync 运行：求值驱动 exit 0（无修正文件产生）
5. 负例（鸿蒙特有测试）：期望块被破坏的 out_of_sync.ml 经 staged 编译运行后
   非零退出，且 out_of_sync.ml.cinaps-corrected 被生成并含再生的 "toto"
   —— 证明工具真实求值并比对，而非复制文件

## 上游测试（R51）
- 清点: test/dune runtest 规则（test_staged.ml + ppx_jane 预处理的
  test_staged_gen + `%{bin:cinaps} -staged` 生成步骤）
- 实测: test_staged_gen 依赖 `(pps ppx_jane)`，即下游 ppxlib 生态
  （依赖期循环）→ 上游 runtest 在本环境不可运行（记录 0 运行）；
  上游 test_staged.ml 与 -staged 调用形式已原样复现到 test_package
- 详见 test_package/MANIFEST.yml

## 门禁
- L0/L1/L1e/L2/L5：见本地 CI 日志与 .ci-result.json
