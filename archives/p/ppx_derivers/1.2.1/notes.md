# ppx_derivers 1.2.1 适配笔记

## 编译环境
- 构建系统: dune 3.17.0（registry 工具链）
- 编译日期: 2026-10-11
- 编译器: OCaml 4.14.1（registry `ocaml/4.14.1.1.2`）+ dune/3.17.0
- 平台: OHOS/aarch64（HarmonyOS PC）
- 状态: built

## 软件说明
ppx_derivers 是 ppx_deriving / ppx_type_conv 共用的[@@deriving]注册表，
是 ppxlib 的依赖之一。

## 语言预检说明（R47）
lang-preflight 判定 `detected_language=c`（顶层 Makefile 命中，构建系统 make）
——与任务语言 cpp 属兼容族，通过（与 camlp-streams/ounit/menhir 等纯 OCaml 包
同一先例）。源码主体为 OCaml（.ml/.mli），工具扩展名表不含 .ml 的说明见
language_evidence 字段。

## 编译步骤
1. 依赖（W0，制品仓预编译包）：`ocaml/4.14.1.1.2`、`dune/3.17.0`
2. `dune build -p ppx_derivers @install`（源码未修改；dune-project 为
   `(lang dune 1.0)`，dune 3.17 正常接受）
3. package()：从 `_build/install/default/lib/ppx_derivers/` 解引用软链拷贝
   实文件到 `lib/ocaml/ppx_derivers/`，校验无悬空软链/空文件
4. test_package 消费者用例（原生编译+真机运行）：4 断言（含两项负例：未知
   lookup 返回 None、重复注册抛异常）+ OHOS 文件 I/O e2e 3 断言

## 上游测试（R51）
上游 v1.2.1 无测试目录（tarball 仅 src/（含 dune 构建文件）、pkg/pkg.ml 与 ppx_derivers.opam），N=0，
以 tarball 清点为证据。适配回归由 test_package 消费者用例覆盖（OHOS 真实执行）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | dune 原生编译经 `as --debug-prefix-map` 失败（设备无 GNU binutils） | OCaml 原生汇编调用 `as`；本机 LLVM clang 不认 GNU as 的该选项 | 本地 `as` shim 将其转译为 `-fdebug-prefix-map=`（个人设备工具，不入归档；CI 侧 GNU as 原生支持该选项） |
| 2 | dune @install 全为指向 _build 的相对软链 | dune 安装树设计 + HMDFS 软链限制 | package() 解引用拷贝实文件 |

## 源码修改
无补丁（patches_applied 为空）。

## 依赖版本
- ocaml/4.14.1.1.2（制品仓）
- dune/3.17.0（制品仓）

## 依赖发布检查（W0）
`conan download ocaml/4.14.1.1.2 -r=ohpcd` / `conan download dune/3.17.0 -r=ohpcd`
均返回 revision（已发布）。

## 验证结果
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS（2026-10-11，profile ohos-aarch64-device）
- 本地 CI 门禁（ci/conan/build_and_test.sh，与平台同源）: L0/L1(含 test_package 执行)/
  L1e(破坏性反向验证)/L2(skip，纯库无 bin)/L4/L5 全部 pass，1/1 100%
- .ci-result.json: exit_code=0（W3 本地 CI 模拟通过）
- test_package: 全部断言通过（unit 4 + OHOS e2e 3 = 7）

## 交付物
- packaging/ppx_derivers-1.2.1-ohos-aarch64.tar.gz（本地打包物证，不入仓）
- conan 包: ppx_derivers/1.2.1@ohpcd/stable（本地 conan 缓存）

**编译结束**: 2026-10-11
**最终状态**: built
---

**编译结束**: 2026-10-11 21:55
**最终状态**: built
