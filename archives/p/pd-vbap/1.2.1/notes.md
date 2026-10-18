# pd-vbap 1.2.1 适配笔记

## 编译环境
- 构建系统: Makefile（pd-lib-builder 0.6.0，上游随源码 vendored 的 `Makefile.pdlibbuilder`）
- 编译日期: 2026-10-01
- 编译器: clang 15 —— `/data/service/hnp/bin/clang`（OHOS SDK 自带，经 `tools.build:compiler_executables` 传入）
- 目标三元组: `aarch64-unknown-linux-ohos`（`make` 内 `target.triplet` 实测）
- 状态: published

## 编译步骤

```bash
# 头集来自 puredata 包（含 Pd 内部头 s_stuff.h / m_pd.h / g_canvas.h …）
make -j1 CC="<clang from tools.build:compiler_executables>" \
         PDINCLUDEDIR="<puredata package>/include/pd"
# 产物：vbap.pd_linux / rvbap.pd_linux / define_loudspeakers.pd_linux
```

- `make check`：上游**无该目标**（上游测试是 Pd 补丁，见 `test_package/MANIFEST.yml` 与下文"验证结果"）。
- 零补丁适配：不改上游任何源文件、不生成 `.patch`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Makefile.pdlibbuilder:764: *** Command "cc -dumpmachine" did not return a target triplet…` | OHOS 无 `cc`/`gcc`；builder 默认 `CC = $(PLATFORM)-cc`（`Makefile.pdlibbuilder:388/392`），干净环境下 `CC=cc` 直接硬失败 | 显式传 `CC=<profile 里的 clang>`；配方从 `tools.build:compiler_executables` 取值（R33，不裸用 `${CC}`） |
| 2 | `vbap.c:14:10: fatal error: 's_stuff.h' file not found` | `libpd/0.16.1` 包只装 `include/libpd`，不含 Pd 内部头 `s_stuff.h` | `PDINCLUDEDIR` 指向 **`puredata/0.54.1` 包的 `include/pd`**（`package_folder`，该包 `cpp_info.includedirs` 为空） |
| 3 | `get()` 解包报 `BadZipFile: File is not a zip file` | 源码 URL 末段是 tag 名（无扩展名），conan 按文件名选择解包器 | `get(…, filename="v1.2.1.tar.gz")` 显式给出格式提示 |
| 4 | `ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list` | 本仓 conan 基线不支持 `:c` 子键读法 | 按仓内既有写法读整个 dict：`self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c")` |
| 5 | 消费者测试 `Error relocating …/vbap.pd_linux: pd_error: symbol not found`（musl） | 外部对象需 Pd 引擎符号（`pd_error`/`gensym`/`class_new`）；musl 下**已 dlopen 的库不进后续 dlopen 的全局符号域** | 运行步注入 `LD_PRELOAD=libpd.so`（等价 pd 二进制的 `-rdynamic`）；**仅运行步**，绝不进编译/链接环境 |
| 6 | 上游用例 `unittests/*-unittest.pd` 直接运行即报 `couldn't create: testtools/unit-test-frame` | 上游补丁靠 `loadbang` 例化 `testtools/unit-test-frame` 驱动，而该帧**上游仓 / Pd 发行版 / 本包均未分发**（`puredata` 与 `libpd` 包内均无 `testtools/`） | 适配层在 `test_package/upstream_pd_tests/testtools/` 补齐该帧（仅提供补丁连接的 4 进 4 出 + `UNTEST:` 回显 + 延时退出，无断言逻辑），上游补丁本体不改一字 |

## 源码修改

无（零补丁）。上游 `Makefile` / `*.c` / `*.h` 未改动。

## 依赖版本

- `puredata/0.54.1`：编译期头集（`include/pd`）+ 运行上游补丁的 Pd 宿主（`bin/pd`），`package_type=application`，需用 `package_folder` 取路径
- `libpd/0.16.1`：仅 `test_package` 使用（提供 Pd 引擎作为插件宿主）。
  该依赖已发布到制品仓（2026-10-01 实测 `conan download libpd/0.16.1 -r=ohpcd` 取回
  recipe `42fa20a58368b96f98351155f29f0353` 与 OHOS/clang 15 二进制，RC=0；2026-10-04 复核
  `conan install --requires=puredata/0.54.1 --requires=libpd/0.16.1 --build=never` 亦为
  "Already installed"，即两者均可直接取用预编译包），CI 直接取预编译包，不再以
  `--build=missing` 从源码构建该依赖。本 PR 不携带该依赖的适配内容（保持单包原子性），仅在此登记该依赖关系。
- 编译期工具链：无（不依赖 autotools/libtool）

## 验证结果

```bash
conan create . -pr:h=$PWD/ci/conan/profiles/ohos-aarch64 -pr:b=$PWD/ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
# → G2 PASS / G3 PASS（无系统同名库冲突）/ G4 PASS / L2 PASS / L4 PASS / L5 PASS
# → test_package: 消费者断言 18/18 + 上游补丁 3/3  RESULT: PASS
# 产物：NEEDED=libc.so，RUNPATH=$ORIGIN（自包含，无额外运行时依赖）
```

上游测试（R51 三步法）：
- 清点：`unittests/` 3 个 Pd 补丁（`vbap-unittest.pd` / `rvbap-unittest.pd` / `define_loudspeakers-unittest.pd`）+ 同名 `.wav` 参考信号；无 `make check`/ctest 目标。
- 运行（**已在 CI 内真实执行，3/3 通过**）：三个上游补丁以 `puredata/0.54.1` 的 `bin/pd` 为宿主逐个运行；补丁本体 verbatim（sha256 见 `test_package/upstream_pd_tests/README.md`），仅补齐上游未分发的 `testtools/unit-test-frame`。断言在 `test_package/run_upstream_pd_tests.py`：补丁载入成功 / 无 `couldn't create` / 无 `connection failed` / 宿主无 `error` / 帧回显出期望用例名。
- 鸿蒙独有测试：`test_package/consumer_e2e.c` 以 `libpd` 为宿主驱动真实 DSP —— 18/18 通过（能量守恒、最近扬声器增益集中、Pd 控制台无报错）。

实测证据（W3 本地 CI 日志 `reports/w3-local-ci.log`，`conan create` 内 test_package 段）：

```
[PASS] vbap                   upstream patch executed (marker 'UNTEST: vbap')
[PASS] rvbap                  upstream patch executed (marker 'UNTEST: rvbap-unittest')
[PASS] define_loudspeakers    upstream patch executed (marker 'UNTEST: define-loudspeaker-unittest')
upstream Pd unittests: 3/3 passed
[ok] L1a: test_package was executed by conan create
L1_RESULT=pass: test_package executed
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/pd-externals/vbap.pd_linux | 43328 B | VBAP 声像器（主对象） |
| lib/pd-externals/rvbap.pd_linux | 31040 B | 不定向声源（rvbap） |
| lib/pd-externals/define_loudspeakers.pd_linux | 31040 B | 扬声器布局定义（`ls-directions`/`ls-triplets`） |
| share/pd-vbap/*.pd | — | help 补丁、examples/、unittests/（Pd 宿主资源） |
| licenses/LICENSE.txt | 1652 B | 上游 MIT 许可 |

## 注意事项

- 本文库属 **pd-lib-builder 外部库** 一族，通用做法（检测 → `CC` + `PDINCLUDEDIR` 注入 → `libpd` 消费者测试 → 上游补丁宿主运行）已沉淀为 `knowledge/operations/pd-externals-ohos/`；同族库（zexy/iemlib/cyclone…）可直接复用。
- `.pd_linux` 是 **Pd 运行时插件**（`dlopen` 装载），不是可链接库：`cpp_info.libs` 必须为空，插件目录通过 `cpp_info.libdirs=["lib/pd-externals"]` 暴露。
- Pd 按"补丁所在目录"优先解析 class，消费者测试因此把三个产物 stage 到补丁同目录；上游补丁按 `vbap/<name>`（libdir 布局）寻址，运行器另建该目录布局。
- 手动复现（不经 conan）：按 `test_package/conanfile.py` 的 `test()` 逐条执行（编译不链接 libpd、运行步 `LD_PRELOAD`）；上游补丁复现可直接跑
  `python3 test_package/run_upstream_pd_tests.py --pd <puredata>/bin/pd --externals <pkg>/lib/pd-externals --tests test_package/upstream_pd_tests --work <可写目录>`。
  适配期间的临时 shell 脚本未随归档保留。
- OHOS 目标机 `/tmp` 只读：clang 需显式 `TMPDIR`（`test()` 已设，见 R6/§7）。

## 对话记录

### 对话 #1 [2026-10-01] 首适应配
- 完成 pd-lib-builder 外部库的 OHOS 适配（零补丁），沉淀 `knowledge/operations/pd-externals-ohos/`。
- 首次提交 CI 绿（L0/L1 通过）；人工审核指出上游测试未实际运行（rule4）与脚本规范问题。

### 对话 #2 [2026-10-03 ~ 10-04] 审核整改
- rule4 整改：补齐上游未分发的测试帧，并以 `puredata/0.54.1` 宿主真实运行三个上游补丁（3/3，见上"实测证据"），纳入 `test_package` 由 CI 每次执行。
- 依赖核验：`puredata/0.54.1` 与 `libpd/0.16.1` 均已在制品仓（`conan install --build=never` 实测，不依赖 `conan list`）。
- 脚本规范：`knowledge/operations/pd-externals-ohos/scripts/reproduce_poc.sh` 改为 `set -eu` +
  条件 `pipefail`（`#!/bin/sh` 兼容 dash），所有允许失败的命令显式消化退出码（`cmd && ok=0 || ok=$?`），
  不再整体禁用 `-e`。

---

**编译结束**: 2026-10-04 10:39
**最终状态**: published
