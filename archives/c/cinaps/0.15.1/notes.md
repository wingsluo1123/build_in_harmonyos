# cinaps 0.15.1 适配笔记

## 编译环境
- 构建系统: dune 3.17.0（registry 工具链）
- 编译日期: 2026-10-12
- 编译器: OCaml 4.14.1（registry `ocaml/4.14.1.1.2`）+ dune/3.17.0
- 平台: OHOS/aarch64（HarmonyOS PC）
- 状态: built

## 软件说明
cinaps 是轻量 OCaml 元编程工具：求值 `(*$ ... *)` 注释内代码并使后续块与
输出同步（期望测试风格）。ppxlib 上游测试套件使用 cinaps 可执行文件
（cinaps stanza），因此本包是 ppxlib `dune runtest` 在 OHOS/CI 可运行的前置依赖。

## 语言预检说明（R47）
lang-preflight 判定 `detected_language=c`（顶层 Makefile 命中，构建系统 make）
——与任务语言 cpp 属兼容族，通过（与 camlp-streams/sexplib0/ocaml-re 等纯
OCaml 包同一先例）。源码主体为 OCaml（.ml/.mli）。

## 编译步骤
1. W0 依赖检查：`ocaml/4.14.1.1.2`、`dune/3.17.0`、`ocaml-re/1.13.2`（三者均为
   制品仓包；ocaml-re 为同批发布的前置依赖，随包提供 findlib `re` 与 `seq` 垫片）
2. `dune build -p cinaps @install`（源码未修改）
3. package()：从 `_build/install/default/` 解引用软链拷贝实文件——
   `bin/cinaps`（可执行工具）+ `lib/ocaml/cinaps/`（findlib META + cinaps.runtime
   子库；主 cinaps 库为 private 库，dune 不安装）
4. test_package 消费者用例（真机运行打包后的 cinaps 二进制）：
   --help、check 模式（上游 test_staged.ml 原文，同步→exit 0）、
   staged 模式回写、负例（破坏期望块→非零退出 + .corrected 生成）

## 上游测试（R51）
上游 `test/` 的 test_staged_gen 需 `(pps ppx_jane)`（下游 ppxlib 生态，依赖期
循环），本环境不可运行（记录 0 运行）；但上游 test_staged.ml 与 run 规则中
`%{bin:cinaps} -staged` 的调用形式被原样复现到 test_package 中（等价覆盖）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备原生编译经 `as --debug-prefix-map` 失败（设备无 GNU binutils） | OCaml 原生汇编调用 `as`；本机 LLVM clang 不认 GNU as 的该选项拼写 | 设备 profile 的 as 垫片转译为 `-fdebug-prefix-map=`（既有先例，不入归档） |
| 2 | 原生链接调用 `/data/service/hnp/bin/clang`（设备不存在） | ocaml 包 config 内 C 编译器路径为构建期 CI 路径 | conanbuild 环境经设备 profile `OCAMLPARAM=_,cc=ccwrap` 覆盖（既有先例） |
| 3 | dune @install 全为指向 _build 的相对软链 | dune 安装树设计 + HMDFS 软链限制 | package() 解引用拷贝实文件 |

## 源码修改
无补丁（patches_applied 为空）。

## 依赖版本
- ocaml/4.14.1.1.2（制品仓）
- dune/3.17.0（制品仓）
- ocaml-re/1.13.2（制品仓，本批新增发布；提供 findlib `re` 与 `seq` 垫片）

## 依赖发布检查（W0）
`conan download ocaml/4.14.1.1.2 -r=ohpcd`、`dune/3.17.0`、`ocaml-re/1.13.2`
均返回 revision（已发布）。

## 验证结果
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS（2026-10-12，profile ohos-aarch64-device）
- conan create 冒烟（含 test_package 真机执行）: rc=0，全部断言通过
  （4 产物断言 + --help + staged 生成/编译 + in-sync exit 0 + 负例非零退出与
   .cinaps-corrected 再生）
- finish/W3 本地 CI: 待依赖 ocaml-re/1.13.2 发布后执行（R36）

## 交付物
- packaging/cinaps-0.15.1-ohos-aarch64.tar.gz（本地打包物证，不入仓）
- conan 包: cinaps/0.15.1@ohpcd/stable（本地 conan 缓存）

**编译结束**: 2026-10-12
**最终状态**: built
---

**编译结束**: 2026-10-16 23:09
**最终状态**: built
