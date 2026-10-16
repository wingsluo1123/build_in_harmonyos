# ocaml-re (re) 1.13.2 适配笔记

## 编译环境
- 构建系统: dune 3.17.0（registry 工具链）
- 编译日期: 2026-10-12
- 编译器: OCaml 4.14.1（registry `ocaml/4.14.1.1.2`）+ dune/3.17.0
- 平台: OHOS/aarch64（HarmonyOS PC）
- 状态: built

## 软件说明
ocaml-re 是纯 OCaml 正则表达式库（Perl/Posix/Emacs/Glob/Str 语法），
是 cinaps 工具（ppxlib 上游测试依赖）的编译与运行依赖。

## 语言预检说明（R47）
lang-preflight 判定 `detected_language=c`（顶层 Makefile 命中，构建系统 make）
——与任务语言 cpp 属兼容族，通过（与 camlp-streams/sexplib0/menhir 等纯 OCaml
包同一先例）。源码主体为 OCaml（.ml/.mli）。

## 编译步骤
1. W0 依赖检查（均制品仓已有）：`ocaml/4.14.1.1.2`、`dune/3.17.0`
2. seq 兼容垫片：OCaml 4.14 已将 Seq 并入 Stdlib 且 registry findlib 无 seq 的
   META，而 re 的 dune 文件与其生成 META 均 `requires = "seq"`。build() 在私有
   site-lib（.ohc-site）生成空 seq.cma/seq.cmxa + META 供自身构建；
   package() 将同一垫片安装到包内 `lib/ocaml/seq/`，使下游（cinaps、ppxlib 测试）
   经 OCAMLPATH 透明解析 `requires = "seq"`。
3. `dune build -p re @install`（源码未修改）
4. package()：从 `_build/install/default/lib/re/` 解引用软链拷贝实文件到
   `lib/ocaml/re/`（含 emacs/glob/pcre/str 4 个子库），校验无悬空软链/空文件
5. test_package 消费者用例（原生编译+真机运行）：9 断言 + OHOS 文件 I/O e2e

## 上游测试（R51）— 129/129 + 18/18 真实执行通过
上游测试框架（ppx_expect / base / ppx_inline_test / ounit2 等 20+ 包）未在制品仓
发布（ppx_expect→ppxlib 制品仓依赖环），本次由官方源码在本地验证环境构建完整
框架链，并于 2026-10-15 在 OHOS 设备上真实执行上游套件：
- expect：`-list-test-names` 枚举 129 项；`-verbose` 逐例执行输出 129 行、rc=0；
  `dune runtest lib_test` rc=0；0 个 `.corrected`（期望零偏离）
- ounit2（lib_test/str）：18/18 通过（`Ran: 18 tests ... OK`）
测试源码与期望值零修改；仅 2 处构建配置适配（native 模式替代 native+js；
显式开启 implicit_transitive_deps）。适配回归仍由 test_package 消费者用例覆盖。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `dune build -p re` 报 `Library "seq" not found` | OCaml 4.14 将 Seq 并入 Stdlib，registry findlib 无 seq META | 包内提供空 seq 垫片（见编译步骤 2），并随包安装供下游使用 |
| 2 | 设备原生编译经 `as --debug-prefix-map` 失败（设备无 GNU binutils） | OCaml 原生汇编调用 `as`；本机 LLVM clang 不认 GNU as 的该选项拼写 | 设备 profile 的 as 垫片转译为 `-fdebug-prefix-map=`（既有先例，不入归档） |
| 3 | 原生链接调用 `/data/service/hnp/bin/clang`（设备不存在） | ocaml 包 config 内 C 编译器路径为构建期 CI 路径 | conanbuild 环境经设备 profile `OCAMLPARAM=_,cc=ccwrap` 覆盖（既有先例） |
| 4 | dune @install 全为指向 _build 的相对软链 | dune 安装树设计 + HMDFS 软链限制 | package() 解引用拷贝实文件 |

## 源码修改
无补丁（patches_applied 为空）。

## 依赖版本
- ocaml/4.14.1.1.2（制品仓）
- dune/3.17.0（制品仓）

## 依赖发布检查（W0）
`conan download ocaml/4.14.1.1.2 -r=ohpcd` / `conan download dune/3.17.0 -r=ohpcd`
均返回 revision（已发布）。

## 验证结果
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS（2026-10-12，profile ohos-aarch64-device）
- 本地 CI 门禁（ci/conan/build_and_test.sh，与平台同源）: L0/L1(含 test_package 执行)/
  L1e/L2/L4/L5 通过，1/1 100%；.ci-result.json exit_code=0
- test_package: 全部断言通过（10 产物断言 + 9 API 断言 + 3 步 e2e 流程，真机执行）

## 交付物
- packaging/ocaml-re-1.13.2-ohos-aarch64.tar.gz（本地打包物证，不入仓）
- conan 包: ocaml-re/1.13.2@ohpcd/stable（本地 conan 缓存）

**编译结束**: 2026-10-12 16:58
**最终状态**: built
