# ocamlbuild 0.16.1 适配笔记

## 编译环境
- 构建系统: makefile（GNU Make + configure.make 生成 Makefile.config / ocamlbuild_config.ml）
- 编译日期: 2026-10-04
- 编译器: OCaml 4.14.1（registry `ocaml/4.14.1.1.4`）+ OHOS clang 15.0.4
- 平台: OHOS/aarch64（HarmonyOS PC）
- 状态: built

## 软件说明
ocamlbuild 是 OCaml 生态的通用构建系统（内置 OCaml 项目构建规则），opam 生态
大量包（topkg 等）以其为构建后端。上游构建完全自举：configure.make 通过
`ocamlc -where`/Makefile.config 取工具链信息，Makefile 用 ocamlc/ocamlopt/
ocamldep/ocamllex 构建字节码与原生两套工具，并自带 toplevel 测试套件。

## 依赖版本
- ocaml/4.14.1.1.4（制品仓，armv8/OHOS/Release）
- findlib/1.9.8（制品仓；提供 ocamlfind，上游 with-test 依赖，也是下游常用运行时工具）

## 编译步骤
1. `make -f configure.make all OCAMLBUILD_PREFIX=<pkg> OCAMLBUILD_BINDIR=<pkg>/bin
   OCAMLBUILD_LIBDIR=<pkg>/lib/ocaml OCAMLBUILD_MANDIR=<pkg>/man
   OCAML_NATIVE=true OCAML_NATIVE_TOOLS=true`
2. `make all`（byte + native + man）
3. 上游测试（R51）：`make test-internal`、`make test-findlibonly`、`make test-external`
4. `make install CHECK_IF_PREINSTALLED=false DESTDIR=<staging>` → 复制到包

## 遇到的问题与解决方案

registry ocaml 包是在 CI worker 上构建并发布的，其烘焙工具链与真机环境存在多处
不一致；加上 OHOS 对 ELF 签名的强制校验与 findlib 包的打包缺口，本次适配在
**不改上游源码** 的前提下，通过 conanfile 内的私有 shim 目录逐项修复：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `as: inaccessible or not found` | registry ocaml 包 Config.asm 为裸 `as`，OHOS 无 GNU as | shim `as` → `<OHOS clang> -c`（clang 集成汇编器支持 GAS aarch64） |
| 2 | `/data/service/hnp/bin/clang: inaccessible or not found`（链接/C 编译/-output-obj） | 烘焙 C 编译器为 CI worker 绝对路径 | `ocamlc`/`ocamlopt` shim 追加 `-cc <clang>`（R33：路径取自 conan conf） |
| 3 | cmxs 链接报 `undefined symbol: main/caml_call_gc` | 加 `-cc` 后 OCaml 丢失 cmxs 的 `-shared` | `ocamlopt` shim 检测 `-shared` 时追加 `-ccopt -shared` |
| 4 | 新构建字节码直接执行失败（shebang 指向构建期缓存路径） | ocaml 包烘焙 runtime 路径 | `ocamlc` shim 追加 `-use-runtime <真实 ocamlrun>`；`ocaml` 顶层用 `ocamlrun` 启动（安装的 `ocaml` 启动器自身 shebang 悬空） |
| 5 | 新链接 ELF 执行 EPERM（如 `myocamlbuild`、`ocamlbuild.native`） | lld 生成的 `.codesign` 对部分二进制不被 OHOS 接受 | `ocamlopt` shim 对链接产物重新签名（`binary-sign-tool -selfSign 1`，先移除旧 `.codesign`；SDK 内工具） |
| 6 | `ocamlmklib` 直连烘焙死路径（无 `-cc` 选项、`-ocamlc`/`CC` 均无效） | ocamlmklib 直接执行 Config 编译器路径 | 真机缺该路径时，在 shim 安装字符串补丁副本（死路径→`clang`+空格，shell 从 PATH 解析），补丁后重签名；CI 机器路径存在时跳过 |
| 7 | findlib 测试组 `Cannot find file topfind` | registry findlib 包未安装 `topfind` 脚本 | shim 提供最小 topfind（`#load findlib.cma` + `#load findlib_top.cma`），并 `-I` 进顶层加载路径 |
| 8 | `ocamlfind` 配置指向构建期缓存 + `ld.conf` 缺失 | findlib 包烘焙 destdir/path/ldconf | shim 生成修正版 `ocamlfind.conf` + `ld.conf`，并设置 `OCAMLPATH` |
| 9 | `make man` 的 `options_man.byte` 执行失败 | 同 #4（shebang） | 由 #4 的 `-use-runtime` 一并修复 |

## 上游测试（R51，真机实测）

| 组 | 结果 | 说明 |
|----|------|------|
| testsuite/internal.ml | **44/44 PASS** | 核心规则、插件编译、cmxs、C stub、依赖/卫生、错误码等 |
| testsuite/findlibonly.ml | **3/3 PASS** | ocamlfind 集成（threads/archive/predicate/tools flags） |
| testsuite/external.ml | 0 通过 / **3 SKIPPED**（RC=0） | 上游 requirement guard：camlp4、camlp4.macro、menhir 包在制品仓不可用（上游第 4 个用例 Camlp4NativePlugin 已被注释） |
| 合计 | discovered=50 / passed=47 / skipped=3 / failed=0 | |

## 源码修改
无补丁（patches_applied 为空；上游源码零修改）。全部适配在 conanfile 的
build-time shim 与 findlib 配置中完成。

## 验证结果
- `conan-verify ocamlbuild 0.16.1 --profile ohos-aarch64-device`：**G0–G4 全 PASS**
- W3 本地 CI（`zsh ci/conan/build_and_test.sh archives/o/ocamlbuild/0.16.1`）：
  **L0/L1/L1e/L2/L4/L5 全 PASS，1/1 包，pass rate 100%**
- 上游测试 47/50 通过、3 SKIPPED（缺 camlp4/camlp4.macro/menhir）、0 失败；
  test_package 18 断言通过（native+bytecode 工程构建运行 + findlib e2e）
- 详见 `reports/test-report.md`

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ocamlbuild` / `bin/ocamlbuild.native` | 原生工具（已签名，设备可直接执行） |
| `bin/ocamlbuild.byte` | 字节码工具（shebang 已修复为真实 ocamlrun） |
| `lib/ocaml/ocamlbuild/` | META、signatures、ocamlbuildlib.cma/.cmxa/.a、cmi/cmx 等 |
| `man/man1/ocamlbuild.1` | 手册页 |

## 发现与知识
- ✅ registry ocaml 包的「烘焙 CI 工具链」缺陷族（as/C 编译器/cmxs shared/字节码
  shebang）在下游包（本包、xmlm）中反复出现，可通过统一 shim 方案修复
- ✅ OHOS 对 ELF `.codesign` 的强制校验：部分 lld 链接产物需用 `binary-sign-tool
  -selfSign 1` 重新签名才能执行；补丁/改写二进制会使签名失效
- ✅ `ocamlmklib` 无 `-cc`/`-ocamlc`/`CC` 覆盖途径，需字符串补丁 + 重签名
- ✅ findlib 1.9.8 包缺 `topfind` 脚本且 conf 烘焙缓存路径，下游需自备最小 topfind 与修正 conf

---
**编译结束**: 2026-10-04
**最终状态**: built
---

**编译结束**: 2026-10-06 12:10
**最终状态**: built
