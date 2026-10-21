# portio 0.6.2 适配笔记

## 编译环境

- 目标平台：OpenHarmony / HarmonyOS PC（aarch64，`os=OHOS os.version=6.0`，clang 15）
- 构建系统：上游 `setuptools`（`setup.py build_ext`，PEP 517 后端同为 setuptools）
- 解释器：`python/3.12.9`（conan 包，提供 `Python.h` + `libpython3.12.so`）
- 编译日期：2026-10-17
- 状态：`built`（conan create + test_package 全绿；未 upload）

## 上游测试入口清点（R51 第一步）

`portio` tag `0.6.2`（commit `6345900824196a20bbaf209d2d22dc28fad0df49`）全量文件仅 **10 个**：

```
MANIFEST.in  Makefile  README.rst  build_dist.sh  conf.py
portio.c  portio.c.in  pyproject.toml  setup.py  toggle.py
```

- 无 `tests/` / `test/` 目录；无 `test_*.py` / `*_test.py`
- `pyproject.toml` 无 `[tool.pytest]`、`setup.py` 无 `test_suite`、`Makefile` 仅 Sphinx 文档目标
- `grep -rn "pytest|unittest|def test_"` 于全部源码 = 0 命中

**结论：上游 0.6.2 没有自动化测试入口（0 个用例）。** 唯一可执行样例是
`toggle.py`（README “Usage example” 即 include 该文件）。因此：

- 上游测试统计：用例总数 0 / 通过 0 / 失败 0 / 跳过 0（无入口，非“未运行”）
- 上游样例 `toggle.py` 已真实执行（两条路径，见下）
- test_package 的 10 个用例**单独统计**，不计入上游用例

## 编译步骤

```bash
# 1) 依赖解析（conan）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd

# 2) 实际构建命令（配方 build() 内，setuptools 入口）
export PYTHONHOME=<python包>            # conan python/3.12.9
export PYTHONPATH=<setuptools解包目录>   # pinned setuptools-84.0.0 wheel
export LD_LIBRARY_PATH=<python包>/lib
export C_INCLUDE_PATH=<python包>/include/python3.12
export CC=/data/service/hnp/bin/clang
export CFLAGS="-fPIC -O2"
export LDSHARED="$CC -shared -fuse-ld=bfd -L<python包>/lib -lpython3.12"
export LDFLAGS="-fuse-ld=bfd -L<python包>/lib -lpython3.12"
"<python包>/bin/python3.12" setup.py build_ext --inplace
```

产物：`portio.cpython-312-aarch64-linux-ohos.so`（EXT_SUFFIX 取目标解释器
`sysconfig`，与设备 python3 一致）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 未适配源码在 aarch64 上**编译“成功”**（20 条 `implicit-function-declaration` 告警），链接也不报错；`import portio` 报 `ImportError: Error relocating …: outl_p: symbol not found` | OHOS aarch64 sysroot 里 `<sys/io.h>` 存在，但 `bits/io.h` 为空文件（无 `outb/inb/ioperm` 声明）；共享库默认允许未定义符号，故障延后到 dlopen（musl BIND_NOW） | 补丁 `0001-portio.c.patch`：按 `__i386__/__x86_64__` 选择实现；非 x86 下 18 个 I/O 入口 `return pio_unsupported(name)`（`PyErr_Format(portio.error, "outb: port I/O is not available on this architecture (aarch64): ...")`），`ioperm/iopl` 返回 `ENOSYS` |
| 2 | 首版适配用“先 return 再让旧代码成死代码”的写法，仍留 36 条隐式声明告警，依赖 `-O2` 死代码消除 | 不可达代码仍参与语义检查 | 改成编译期 `#if PORTIO_HAS_PORT_IO … #else return pio_unsupported(...) #endif`，非 x86 完全不编译 x86 调用：**0 告警 / 0 错误 / 0 个 x86 未定义符号** |
| 3 | `pio_unsupported` 隐式声明导致 19 个 `incompatible integer to pointer conversion` 错误 | 辅助函数原先放在方法表前（定义在使用之后） | 把 `static PyObject *Error;` + `pio_unsupported()` 提前到 include 段之后 |
| 4 | `python setup.py build_ext` 找不到 `Python.h` | conan python 的 `sysconfig INCLUDEPY` 在本环境解析为 `//include/python3.12`（无效路径） | 显式 `C_INCLUDE_PATH=<python包>/include/python3.12` |
| 5 | `import portio` 报 `Permission denied`（.so 已生成） | E077：OHOS 加载未签名 ELF 被拒 | build() 内 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool … -selfSign 1` + `chmod 755`；package() 复制后**重新签名** |
| 6 | `setuptools` 不可用 | conan python/3.12.9 不自带 setuptools | 构建期按 pinned sha256（`51a5259…`）从 PyPI 下载 `setuptools-84.0.0-py3-none-any.whl` 并解包到 build 目录（与仓库内 gpgmepy 2.0.0 配方同一固定件） |

## 源码修改

`patches/0001-portio.c.patch`（portability，+130/-2 行；不含 `__OHOS__` 平台宏）：

1. include 段：`#include <errno.h>`；`#if defined(__i386__) || defined(__x86_64__)` 时保留
   `<sys/io.h>` 并置 `PORTIO_HAS_PORT_IO 1`，否则置 0。
2. 提前声明 `static PyObject *Error;`；非 x86 下提供 `pio_unsupported()`（抛
   `portio.error`，消息含入口名与架构名）。
3. 18 个 I/O 入口：`#if PORTIO_HAS_PORT_IO` 保留原实现，`#else` 显式失败。
4. `ioperm`/`iopl`：非 x86 返回 `ENOSYS`（保持上游“返回 errno”契约，示例
   `os.strerror(status)` 分支照常工作）。

未修改上游任何 Python 文件（`setup.py`/`pyproject.toml`/`toggle.py` 原样）。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|---|---|---|---|
| python | 3.12.9 | ohpcd（可消费，二进制已在缓存） | `Python.h` + `libpython3.12` |
| setuptools | 84.0.0 | PyPI wheel（pinned sha256） | 构建期 PEP 517 后端 |
| setuptools_scm | — | 未使用 | 直接跑 `setup.py build_ext` 绕过 PEP 517 元数据生成，不触发动态版本 |

## 验证结果

### 基线（未适配）——取证的失败形态

```bash
$ clang -x c -fPIC -O2 -I<python>/include/python3.12 -c portio.c   # rc=0，20 条隐式声明告警
$ llvm-readelf -sW portio…so | grep UND | grep -E 'outb|inb|ioperm'
  … UND outb / inb / outl_p / ioperm …（20 个）
$ python3.12 -c "import portio"
ImportError: Error relocating …/portio.cpython-312-aarch64-linux-ohos.so: outl_p: symbol not found   # rc=1
```

### 适配后

```bash
$ conan create . -pr:h=… -pr:b=… -r=ohpcd        # rc=0
$ llvm-readelf -sW <pkg>/…/portio…so | grep UND | grep -E 'outb|inb|ioperm'   # 0 个
$ llvm-readelf -SW <pkg>/…/portio…so | grep -c codesign                        # 1（已签名）
```

上游样例（build() 内真实执行，包内 `res/upstream_test_summary.json`）：

| 运行 | 命令 | 退出码 | 输出 | 结论 |
|---|---|---|---|---|
| import 探针 | `python3.12 -c "import portio;print(portio.__file__)"` | 0 | 打印 .so 路径 | PASS |
| `toggle.py` 原样 | `python3.12 toggle.py` | 0 | `You need to be root! Exiting.` | PASS（上游非 root 前置分支） |
| `toggle.py` getuid 桩为 root | `python3.12 -c "import os,runpy;os.getuid=lambda:0;runpy.run_path('toggle.py',run_name='__main__')"` | 0 | `ioperm: Function not implemented` | PASS（进入 API 路径，aarch64 上 ENOSYS 分支） |

test_package（独立统计，非上游用例）：**10/10 PASS**，其中鸿蒙/aarch64 特有 5 个
（见 `reports/test-report.md`）。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/python3.12/site-packages/portio.cpython-312-aarch64-linux-ohos.so` | 扩展模块（已签名，无 x86 未定义符号） |
| `res/upstream_test_summary.json` | build() 内上游样例实测结果（供 test_package 汇总上报） |

## 注意事项

- 本包在 aarch64 上**不提供真实端口 I/O**：所有 I/O 入口抛 `portio.error`，
  `ioperm/iopl` 返回 `ENOSYS`。这是平台能力缺失下的显式失败语义，而非功能可用。
- 下游若 `import portio` 后直接 `outb(...)` 而无异常处理，会在 OHOS 上失败退出；
  依赖 portio 的 x86 专用程序在 OHOS 需要另行改写。
- 设备非 root 时运行 `toggle.py` 只会走 root 前置分支，这也是上游行为。
- 构建机 inode 紧张（`/storage/Users` 可用 inode 长期接近 0），`conan create`
  可能因无法创建临时文件失败，属环境问题而非配方问题。

## 对话记录

### 对话 #2 — 2026-10-17 Pre-PR 独立审计整改（P0/P1/P2）

独立审计（上下文隔离子任务，对照 SKILL 铁律 + `.gitcode/code-style.md`/`review-memory.md`
+ L0 门禁 + PF1-PF9）共提出 1 项 P0、3 项 P1、7 项 P2。整改如下：

| 级别 | 问题 | 处理 |
|---|---|---|
| P0 | W3 的 Pre-download 把 `conandata.yml` 改写成 `gh-proxy.com` 镜像列表（R39/PF7 会直接拦），而日志仍打印"已还原为官方 URL" | 交付件恢复单条官方 URL；删除 `.ghfast-bak`/`.orig` 残留。**框架缺陷**：还原逻辑把已被污染的内容当基线（`predl_cache` 备份未生效），每次 W3 后需人工复核 |
| P1 | 补丁 `PyBuffer_Release` 缺失（6 个 `"Hs*k"` 入口在非 x86 失败路径泄漏 Py_buffer） | 补丁 `#else` 分支先 `PyBuffer_Release(&string)` 再抛错；补丁重新生成（+130/-2，含 6 处 release） |
| P1 | `manifest.yaml` 的 `patch_classification` 仍是工具占位值（`type: auto` / `platform_only: True` / `guard: pending`） | 改为 `type: portability` / `platform_only: False` / `guard: "__i386__/__x86_64__…"`，与 conandata 的 `patch_type` 一致 |
| P1 | `ci-metadata.json` 的 L1 记为"upstream tests + test_package executed"（本包上游 0 用例）——根因是配方 `reason` 文本含 `pytest/ctest` 字样被 CI grep 命中 | 配方文案去掉这些字样，复跑后 `ci-metadata` 的 L1 = `test_package executed`，日志显示 `L1c: No upstream make check/ctest in log` |
| P1 | 仓库根 `SUMMARY.md` 被 finish 在稀疏 worktree 中重写成"1 款软件"（-2603 行） | `git checkout -- SUMMARY.md` 还原；该文件不入 PR（框架文件，R/W2 只读） |
| P2 | 上游样例 as-is 断言绑定"运行者非 root" | 改为接受两种合法输出（root 检查 / ioperm 分支），与权限无关 |
| P2 | 文案称"交叉编译"，实际是 aarch64 构建机原生构建（需执行目标 python 读 EXT_SUFFIX） | docstring/description/notes 全部改为"原生执行 + 环境变量注入"，并注明 x86 构建机不适用 |
| P2 | 非 OHOS 平台缺签名工具时"告警后必失败" | 签名仅对 `os=OHOS` 强制，其它平台降级告警 |
| P2/P3 | test_package 断言硬绑定 `aarch64`；`MANIFEST.assertion_count` 语义混淆；`package_type` 的死选项 | 断言改为"消息含架构括注"；MANIFEST 增 `test_package_case_count`；`package_type` 试过 `application` 被 L0k 判为 CLI 包（要求 commands.json）→ 保留 `library`+`shared` 并在注释中说明这是 Conan 校验需要、产物不受影响 |

整改后复验：`conan create` rc=0（10/10 用例、3/3 上游样例，日志
`/storage/Users/currentUser/Desktop/GPQworkspace/portio-0.6.2-logs/21-conan-create-final.log`），
`finish` 的 W3 全门禁通过（`reports/w3-local-ci.log`）。


### 对话 #1 — 2026-10-17 适配决策

- **语言预检（R47）**：`lang-preflight` 两次返回 `detected_language=python`（任务
  侧 `cpp` / `--lang c` 皆 exit 2）。证据表明这是分类器按文件数统计（python:3,
  bash:1, c:1）导致的误判：包主体是 403 行 C 源 `portio.c` 实现的 20 个
  CPython C-API 入口，`setup.py`/`conf.py`/`toggle.py` 分别是构建脚本、Sphinx
  配置与示例，属 R47 边界规则中“辅助脚本不算主体”；`build-systems.md §14` 亦
  明确“Python C 扩展属合法 cpp 任务”。决策：按 C 语言继续适配，并把分类器
  误判作为框架缺陷记录（未绕过 `result` 命令，未伪造字段）。
- **适配口径选择**：Debian 打包用 `ifdefs.patch` 把每个函数在缺 API 时改为
  `return NULL`（空壳桩）。本适配改为**显式失败语义**：18 个 I/O 入口抛
  `portio.error`（消息含入口名与架构），`ioperm/iopl` 返回 `ENOSYS`。理由：
  空壳 `return NULL` 不会设置异常，调用方会拿到 `SystemError`/无提示的 NULL，
  且违反 R8“禁止空壳 stub”；返回 ENOSYS 则保持上游“返回 errno”契约，示例
  `toggle.py` 的 `os.strerror(status)` 分支照常工作。
- **补丁写法复盘**：首版用“先 return 再靠死代码消除”的守卫宏，仍留 36 条
  `implicit-function-declaration` 告警且依赖 `-O2`；改为编译期
  `#if PORTIO_HAS_PORT_IO` 分支后 0 告警、0 个 x86 未定义符号。
- **上游测试**：清点确认 0 用例（无入口）；未用 test_package 冒充上游统计，
  改为在 build() 内真实执行上游唯一样例 `toggle.py` 的两条路径 + import 探针，
  并把结果写进包内 `res/upstream_test_summary.json` 供 test_package 汇总上报。
- **W3 门禁两次拦截的修复**：①L0d `stub_test_method` —— test() 原先用
  `subprocess.run`，改为 Conan 原生 `self.run` 并把结果 JSON 写到临时目录；
  ②JC 门禁 —— 首次为 `full` 模式，命中仓库 main 上**已存在**的 9 个他人归档
  运行期标记文件（cloog/kcachegrind/kics/libbfio/libdazzle/oscpack/reflex/thc），
  与 portio 无关；改用 CI 同源的 `JUNK_PR_DIFF`（prdiff 模式，只查本 PR 的 10
  个文件）后 JC_RESULT=pass、JC6 软件数=1。
---

**编译结束**: 2026-10-17 22:01
**最终状态**: built
