# icmake/icmbuild 驱动的上游项目在无 icmake 的 OHOS 环境下复刻编译语义

Status: DRAFT
Source: xd 5.00.03（fbb-git / Frank B. Brokken）；对照实证 bobcat 6.14.00（同作者，libraries 模式，已合并）
PR: `feat/xd-5.00.03`（【积分赛】/【知识库扩展】待定，见 §Review Checklist）

## 相关既有条目

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E2175 | musl/libc++ 与 glibc/libstdc++ 的六类差异及修复组合；其中明确写“构建系统: 任意（bobcat 为 icmake，conanfile 复刻其编译语义）”，但**不涉及 icmake/icmbuild 语义本身** | 本条专门覆盖“构建工具缺失 → 按 icmconf/CLASSES 复刻 icmbuild 语义”这一类问题的判定标志、语义清单与禁改项 |
| E359 | 自定义构建系统下把 Conan 构建上下文编译器映射到 HOSTCC/HOSTLD | E359 解决“编译器从哪来”，本条解决“源集合/对象布局/链接库/清理语义怎么复刻”；两者互补，本条 rec_description 第 (6) 项引用 E359/E2175 的编译器注入做法 |
| DRAFT-E628 | 手写 Makefile 多子工程（无构建系统）的适配五件套 | 两者都属“上游构建方式非主流”，但触发标志不同（E628 无构建文件/makefile 大小写；本条是 icmake 脚本 shebang + icmconf/CLASSES），解决方案不可复用 |

检索关键词记录：`icmake`、`icmbuild`、`icmconf`、`CLASSES`、`bobcat`、`fbb-git`、`custom-build-system`。
结果：`knowledge/graph/index.tsv` 与 `knowledge/doc/` 无 icmake/icmbuild 条目；`knowledge/drafts/` 仅
`E2175-draft-623C` 提到 icmake（且明确与构建系统无关）。→ 判定为**未覆盖**。

## Scope（何时使用）

- 上游顶层存在 icmake 脚本 `build`（首行 `#!/usr/bin/icmake -t.`）且带 `icmconf` / `CLASSES` / `INSTALL.im`；
- 目标环境（OHOS 设备/CI）没有 icmake，制品仓也没有 icmake 配方；
- 需要把上游 `./build program`（或 `libraries`）的产物（可执行文件/静态库/共享库）落进 Conan 包。

不适用：上游同时提供 autotools/CMake/meson 入口（优先用原生入口）；已经发布 icmake `tool_requires` 的场景（改用 tool_requires，见 Fallback）；构建还需要 yodl/flex/bison 等生成器的文档/man 目标（本仓不构建 man/manual）。

## Symptom（真实日志）

```
$ command -v icmake
(icmake not installed)

$ ./build program
zsh:1: ./build: bad interpreter: /usr/bin/icmake: no such file or directory
rc=127

$ sh ./build program
./build: line 5: string: command not found
./build: line 6: syntax error near unexpected token `('
./build: line 6: `    g_logPath = getenv(LOGENV)[1],'
```

## Root Cause（机制链）

icmake 脚本语言 → 顶层 `build` 不是 shell 脚本 → 无 icmake 时 rc=127（bad interpreter）→ 误用
`sh ./build` 得到字符串/语法错误 → 真正缺失的是构建工具本身；而 icmake 未进 OHOS 依赖链
（自举型 C++ 程序，需先有 icmake 才能构建自己，官方只发源码包）→ 整族 fbb-git 项目在 CI 上无法开工。
`icmbuild` 决定的是：CLASSES 模块目录 + MAIN + Sources 的源集合、`tmp/` 对象布局、ADD_LIBRARIES 链接库、
以及 `libraries` 模式的公共头 catFile 展开（`#include "x.f"` 行内联）。

## Recommended Fix（复刻语义，不引入 icmake）

1. 解析 `CLASSES`（逐行、跳过 `//` 注释）→ 模块目录清单（bobcat: 128 类；xd: options command history alternatives selector 5 个）。
2. `program` 模式：源集合 = 顶层 `MAIN`（`icmconf` 的 `#define MAIN "main.cc"`）及顶层其余 `*.cc` + 各模块目录 `*.cc`；`libraries` 模式：各模块目录分别产出 `.a`/`.so`。
3. 每个 TU 以「自身目录 + 源码根」为包含根编译（模块内 `#include "xxx.ih"`；`main.ih` 形如 `#include "options/options.h"`、`#include "version/version.h"`）。
4. 链接按 `ADD_LIBRARIES`（fbb-git 家族多为 `bobcat`）追加 `-l<bobcat>`，保留 INSTALL.im 的 `-Wall -Werror -O2 -pthread -fdiagnostics-color=never`；`libraries` 模式还要复刻 soname（`libbobcat.so.<major>`）与静态库 `ar cr + ranlib`。
5. 复刻 `./build clean`：编译前清空对象目录（否则残留 `.o` 会与本次对象重复，链接报 duplicate symbol）。
6. 编译器/ar 来自 Conan conf（`tools.build:compiler_executables`），并按 E2175 注入 `realpath(cxx)/../lib`；`ccache` 包装（INSTALL.im 的 `CXX = ccache g++`）不迁移。
7. C++ 标准取 `max(profile cppstd, 依赖公共头要求)`：fbb-git 家族的 bobcat 公共头要求 C++20，profile 默认 17 时必须抬到 20。

## Fallback

先适配并发布 `icmake` 配方（自举：shell 引导生成首版 → 自举编译），下游 `tool_requires("icmake/<ver>")`。
优点：一次性解除整族阻塞；代价：多一个前置库任务，且需逐项验证 `icmbuild` 的 program/libraries 语义
（MULTICOMP/SPCH/USE_ALL 等开关）在 OHOS 下完整可用。

## Forbidden Approaches

- ❌ `sh ./build` / `source ./build`：icmake 脚本不是 shell 脚本，报错是二次误导。
- ❌ 只编 `main.cc`、忽略 `CLASSES`：必然 undefined symbol（模块实现整体缺失）。
- ❌ 用系统 `g++`：OHOS 只有 LLVM/Clang（P-TOOLCHAIN-001），且会产出非 OHOS ABI 产物。
- ❌ `rm -rf tmp spch` 式照搬 clean：需限定只清对象/库/头缓存目录，避免误删源码树同名内容。

## Verification

```bash
# 修复前（无 icmake，rc=127）
cd xd-5.00.03 && ./build program ; echo rc=$?

# 修复后（本 PR 的复刻驱动，OHOS 交叉编译 + 打包）
conan create archives/x/xd/5.00.03 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 期望：68/68 TU 编译通过（-Wall -Werror 零告警）→ link tmp/bin/xd → 包内 bin/xd 为
#       aarch64-linux-ohos ELF，NEEDED 含 libbobcat.so.6 / libc++_shared.so / libc.so
```

对照实证（第二例、另一模式）：`archives/b/bobcat/6.14.00` 用同一手法复刻 `libraries` 模式
（128 类 / 1051 TU，已合并并通过 CI）。

## Prevention

- 立项预检阶段先识别“非主流构建入口”：顶层脚本 shebang 指向 `/usr/bin/icmake`、存在 `icmconf`/`CLASSES` 即命中本例，可提前判定“无构建工具可用”而不是编译到一半才发现。
- 知识库/引擎命中关键词建议：`icmake`、`icmbuild`、`icmconf`、`INSTALL.im`、`CLASSES`、`fbb-git`。

## 适用范围 / 不适用范围

| 维度 | 内容 |
|---|---|
| 适用库类型 | 任何用 icmake 驱动、带 `icmconf`+`CLASSES` 的 C/C++ 项目（典型：fbb-git 家族） |
| 适用构建系统 | icmake / icmbuild（program 与 libraries 两种模式均已实证） |
| 前置条件 | 能读源码树（CLASSES/icmconf/INSTALL.im）、Conan conf 提供 OHOS clang 工具链、依赖库已适配（如 bobcat） |
| 不适用 | 上游另有 autotools/CMake/meson 入口；已能用 icmake `tool_requires`；必须构建 man/manual（需 yodl）的场景 |
| 应转用其他知识 | 编译器来源问题 → E359；musl/libc++ 编译差异 → E2175；取源/镜像与 PF7 → E718/E568 |

## References

- 上游：https://gitlab.com/fbb-git/xd （tag 5.00.03，`build`/`icmconf`/`INSTALL.im`/`CLASSES`）
- 对照实现：`archives/b/bobcat/6.14.00/conanfile.py`（libraries 模式复刻）、`archives/x/xd/5.00.03/conanfile.py`（program 模式复刻）
- 相关条目：E2175、E359、DRAFT-E628；取源相关：E718、E568
