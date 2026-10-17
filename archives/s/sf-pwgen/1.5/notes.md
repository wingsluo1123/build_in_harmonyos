# sf-pwgen 1.5 适配笔记

## 编译环境

- 构建系统: makefile（上游 `Makefile` 仅服务 macOS：`clang -fobjc-arc -framework Foundation/CoreFoundation/SecurityFoundation`；OHOS 产物改用单文件 `cc` 直编，见下）
- 编译日期: 2026-10-16
- 编译器: OHOS SDK clang 15（`tools.build:compiler_executables.c`，R33）
- 目标: ohos-aarch64（`ci/conan/profiles/ohos-aarch64`）
- 状态: built（待真机 `conan create` 通过后由 HMBS 统一提交；R29 不伪造 published）
- 申请人: momimgya / 队伍：干

## 上游源码

- 仓库：https://github.com/anders/pwgen（macOS password generator，Objective-C）
- 版本：tag `1.5`（commit `1212ca43967f49a8ef4deed9164a6558a321bcdc`）
- 归档：https://github.com/anders/pwgen/archive/refs/tags/1.5.tar.gz
- sha256：`e1f1d575638f216c82c2d1e9b52181d1d43fd05e7169db1d6f9f5d8a2247b475`（直链实测）
- 内容：17 个文件（`.gitignore/.travis.yml/Makefile/README.md/SFPasswordAssistant.h/VERSIONS.md/sf-pwgen.m/sf-pwgen-test/*(空占位 XCTest)/sf-pwgen.xcodeproj/*`）

## 为什么必须新增可移植后端（平台事实）

`sf-pwgen.m` 首部即 `#import <Foundation/Foundation.h>` + `#import "SFPasswordAssistant.h"`，全程调用 SecurityFoundation 口令助手 API（`SFPWAPolicyCopyDefault / SFPWAContextCreateWithDefaults / SFPWAContextLoadDictionaries / SFPWAPasswordSuggest`），`Makefile` 硬链三个 framework：

```
LIBS=-framework Foundation -framework CoreFoundation -framework SecurityFoundation
```

这三个 framework 只存在于 Apple 平台，OHOS/Linux 上既无头文件也无实现，属平台事实不可编译，不是靠补几行宏能解决的。因此本次不做“宏开关式修补”，而是新增纯 C99 后端文件复刻 CLI 契约，macOS 原文件原样保留、不参与 OHOS 产物。

## 编译步骤

```bash
# 1) 同步上游 main 并切分支（稀疏检出：含 ??/CR 异常文件名的 gama 补丁在 Windows 无法落地，故仅检出 SKILL/docs/templates/.gitcode/knowledge/ci/archives/s）
git fetch upstream main
git checkout -B feat/sf-pwgen-1.5

# 2) 配方构建（conanfile.py build() 实际执行的单命令，CC 取自 Conan conf，R33）
"<conan conf tools.build:compiler_executables.c>" -O2 -Wall -Wextra -std=c99 \
  -o sf-pwgen sf-pwgen-portable.c

# 3) 真机验证（由 HMBS 后台执行，本轮不手动跑 conan）
# conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

产物：`bin/sf-pwgen`（单可执行文件）、`licenses/README.md`、`licenses/VERSIONS.md`（上游无 LICENSE 文件，以此溯源）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `.m` 在 OHOS 上无法编译 | macOS 专属 Foundation/SecurityFoundation 私有 API，无跨平台实现 | 新增 `sf-pwgen-portable.c`（纯 C99，复刻 1.5 全部 CLI 契约），配方只编该文件；macOS 原文件保留 |
| 2 | 熵源需要跨平台且无偏 | `rand()%n` 有模偏；`arc4random` 非 POSIX | `/dev/urandom` + 拒绝采样（`rng_range`），`fopen` 失败时回退到 time/pid 种子 PRNG，保证沙箱内仍可运行 |
| 3 | memorable 长度语义需与 1.5 一致 | 上游 1.5 明确“偏短要警告”（VERSIONS.md），词拼接天然不等长 | 词数随请求长度增长（上限 8 词）：默认 12 通常无警告，128 必然偏短告警，警告文案与上游一致，可执行断言覆盖 |
| 4 | 语言选项兼容性 | 上游从 policy 读语言列表；可移植后端无 policy 文件 | 内建接受 `en, de, es, fr, it, nl, pt, jp`（与上游 README 一致），非法语言打印同格式 warning，不改变退出码 |
| 5 | 零依赖如何过 R36/W0 | 无 requires 即无“依赖未发布”风险 | 保持零 requires（仅 libc），W0 预检为空依赖，直接通过 |
| 6 | Windows 检出 main 失败 | `archives/g/gama/2.29/patches/0002-dataparser-ungated.patch??` 文件名含 CR，在 Windows 非法 | 稀疏检出（`SKILL.md docs templates .gitcode knowledge ci archives/s`），只取本任务所需子树；不碰该文件 |

## 源码修改

唯一补丁 `patches/0001-ohos-portable-backend.patch`（新增文件 `sf-pwgen-portable.c`，约 300 行，`type: portability`）：

- CLI：`-a memorable|random|letters|alphanumeric|numbers`（默认 memorable）、`-c`（默认 5，<1 按 1）、`-l`（默认 12，钳制 8..128，置位偏短警告）、`-L`（合法 8 语言接受/非法警告）、`-v`（打印 `sf-pwgen 1.5`）、`-h`（打印用法；与上游一致返回非零）、未知算法报错 `error: unknown algorithm.` 并打印用法
- 字符集固定：letters 52 / alphanumeric 62 / numbers 10 / random 88（含 26 个 ASCII 符号）/ memorable 小写词表 64 词连字符拼接
- 熵源：`/dev/urandom` 拒绝采样；`getopt_long` 来自 musl `getopt.h`，无需 `_GNU_SOURCE`
- 无任何平台宏（R8/PF5），对 Linux 同样可用；macOS 原文件零改动

## 依赖版本

| 依赖 | 版本 | 类型 | 制品仓状态 |
|------|------|------|-----------|
|（无）| — | 零 requires（仅 OHOS musl libc + `/dev/urandom`）| 无需 W0 制品仓预检 |

## 上游测试清点（R51 三步法）

**计数口径（唯一口径，贯穿 MANIFEST.yml / notes.md / 测试日志 / PR 两张表）：按「独立检查项数量」计数** —— 每项可单独判定成败、单独打印 `ok:`/`FAIL:`。

### 第一步：清点上游原始测试

审计对象 `pwgen-1.5.tar.gz`（sha256 见上，tag `1.5`）：

- 无 `tests/` 或 `test/` 目录
- `Makefile` 目标仅 `all/format/clean`，**无 `check` / `test` 目标**
- 唯一“测试”是 `sf-pwgen-test/sf_pwgen_test.m` 的空占位 XCTest（`testExample` 无断言、`testPerformanceExample` 测空 block；2019-04-13 为修复 Travis CI 加的占位工程），随 Xcode 工程存在，不可构建、不可在 OHOS 运行
- 无 gtest / criterion / check / CUnit 等 C 测试框架绑定

**上游有效测试用例数 = 0**（单元测试 0 / 集成测试 0 / 其他 0）。

### 第二步：可运行环境实际运行

上游无有效测试可运行（0 项）。适配后补全的 14 项（功能 9 + 鸿蒙特有 5）由 `test_package/test.sh`（`can_run()` 为真时）与 `ohos_abi_check.py`（产物静态检查，任何主机可跑）在真机实跑，证据以预检日志的 `HMBS_*_RESULT` 标记为准（本轮为工作树准备轮，标记计数待真机 evidence 轮回填，见 PR 草稿）。

### 第三步：适配后测试清单（14 项独立检查项）

功能补全 9 项（`test_package/test.sh`，上游 0 测试 → 新增）：

| 项 | 命令 | 断言 |
|----|------|------|
| F1 | `sf-pwgen`（无参） | rc=0，恰好 5 行、每行非空 |
| F2 | `sf-pwgen -v` | rc=0，stdout 为 `sf-pwgen 1.5` |
| F3 | `sf-pwgen -h` | 输出含 `Available options`（与上游一致返回非零） |
| F4 | `sf-pwgen -a letters -l 12 -c 3` | 3 行、每行恰好 12 个 `[A-Za-z]` |
| F5 | `sf-pwgen -a alphanumeric -l 16 -c 2` | 2 行、每行恰好 16 个 `[A-Za-z0-9]` |
| F6 | `sf-pwgen -a numbers -l 10 -c 2` | 2 行、每行恰好 10 个 `[0-9]` |
| F7 | `sf-pwgen -a random -l 12 -c 2` | 2 行、每行恰好 12 个非空格可打印字符 |
| F8 | `sf-pwgen -a memorable -l 12 -c 3` | 3 行、每行非空且仅含 `[a-z-]` |
| F9 | `sf-pwgen -a bogus` | rc 非零且 stderr 含 `error: unknown algorithm.` |

鸿蒙特有 5 项（rule12，N=5 ≥ 1）：

| 项 | 位置 | 针对的鸿蒙适配点 | 断言 |
|----|------|-----------------|------|
| A1 | `ohos_abi_check.py` | 目标架构 | ELF64 小端且 `e_machine == EM_AARCH64(183)` |
| A2 | 同上 | 工具链/sysroot | `.interp == /lib/ld-musl-aarch64.so.1`（glibc 产物会是 `ld-linux-aarch64.so.1`） |
| A3 | 同上 | 零依赖/无 framework 残留 | `DT_NEEDED` 含 `libc.so` 且无 `libcrypto/libssl`（本包零 requires，静态检查固化无 framework 链接） |
| H1 | `test.sh` | 内核熵源 | 连续两次 `-a random -l 16` 输出必须不同（`cmp` 判定），否则 CSPRNG 未被正确播种 |
| H2 | `test.sh` | 1.5 偏短警告语义 | `-a memorable -l 128 -c 1` rc=0、1 行且 stderr 含 `shorter than the requested length`（8 词上限必然偏短，确定性触发） |

反向验证（CI L1e 口径）：把 bindir 换成空目录后 `test.sh` 立即 `ABORT: <dir>/sf-pwgen missing or not executable`，`passedCount:0` 并退出码 1 —— 测试真实依赖被测包，非空壳（R34）。

## 验证结果

- 本轮为工作树准备轮：配方、补丁、测试套件已就绪，未提交（`git status` 应仅显示未跟踪的新文件）。
- 真机 `conan create` 与 `HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT` 标记计数待 HMBS 后台预检回填；PR 草稿中测试数字一律写“待真机实测”，不猜测。
- 证伪预案（真机轮执行）：① 检查测试输出/参照非空；② 必要时把二进制换成 `exit 1` 桩重跑，确认 harness 能抓失败；③ 区分“通过”与“静默跳过”（`can_run()` 为假时 runtime 用例跳过但 ABI 层仍执行，不计为通过）。

## 注意事项 / 已知限制

- **memorable 口令长度是近似值**：与上游一致，词拼接无法精确等于请求长度；超长请求会打印偏短警告，这是 1.5 的设计语义（H2 已断言），不是缺陷。
- **语言选项为 CLI 兼容接受**：可移植后端内建英文词表，`-L de/es/fr/it/nl/pt/jp` 接受但不切换词表（上游 README 已注明该功能损坏会产出乱码）；非法语言打印 warning，与上游格式一致。
- **`commands.json` 的 `binary` 为 `false`**：按 ARCHIVE-SPEC「适配中为 false，发布后改为 true」。本轮未 push/upload；release 流水线上传后改为 `true`。
- **Windows 稀疏检出**：本机仅检出任务所需子树；`archives/g/gama` 的异常文件名文件不影响本配方，CI（Linux）全量检出不受影响。

## 知识沉淀（W5）

使用的既有知识：

- **R8/PF5**（补丁禁平台宏）—— 本补丁为新增可移植文件，零平台宏
- **R33**（编译器取自 Conan conf）—— `self.conf.get("tools.build:compiler_executables:c")`
- **R34/PF3**（测试必须实质执行被测包）—— 全部 14 项均调用 `bin/sf-pwgen` 或检查其 ELF
- **R32**（`os in ("Linux", "OHOS")`）—— `validate()` 遵循
- 先例配方：`archives/s/secpwgen/1.3`（同为口令生成器 CLI 的 `test.sh + ohos_abi_check.py` 双层结构、`can_run()` 门控、`HMBS_*_RESULT` 标记口径）

新增草稿：本轮不新增知识条目（macOS-framework 不可移植属一次性平台事实，已在 notes 讲清；若评审认为可移植后端值得沉淀，后续轮按 `graph add --draft` 补）。

---

**编译结束**: 2026-10-16
**最终状态**: built（待真机预检）
