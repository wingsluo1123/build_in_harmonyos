# toilet 0.3.r155.3eb9d58 测试报告

> **项目**: toilet（The Other Implementation of figLET）
> **测试日期**: 2026-10-16
> **测试环境**: HarmonyOS PC（MateBook Pro HAD-W32）/ HongMeng Kernel 1.12.0 / aarch64（设备原生构建，非交叉编译）
> **测试类型**: 上游官方测试套件（make check）+ 消费者端到端测试（test_package，目标机实机执行）
> **被测包**: `toilet/0.3.r155.3eb9d58`（OHOS/aarch64，clang 15.0.4，build_type=Release）

---

## 一、测试摘要

### 1.1 上游官方测试（`make check`，conanfile.build() 内执行）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试脚本总数 | 2 | 100% |
| 实际运行 | 2 | 100% |
| 通过 (PASS) | 2 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 错误 (ERROR) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| XFAIL / XPASS | 0 / 0 | — |

automake parallel-tests 汇总：`# TOTAL: 2 / # PASS: 2 / # FAIL: 0 / # ERROR: 0 / # SKIP: 0`（`make check` 退出码 0）。

### 1.2 消费者端到端测试（`test_package`，鸿蒙 PC 目标机实机执行）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 消费者用例总数 | 3 | 100% |
| 通过 (PASS) | 3 | 100% |
| 失败 (FAIL) | 0 | 0% |

**核心功能通过率**: ✅ **100%**（上游 2/2 + 消费者 3/3）

---

## 二、测试结论

### 2.1 总体评价

✅ **适配完整**：上游官方测试原样全部通过（零上游测试修改），消费者端到端用例在鸿蒙 PC 目标机上实机跑通，
产出的 `toilet` 可执行文件 + 包内 24 个 FIGlet 字体可作为实际产品使用。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 | 构建期问题均已在配方内解决（见 notes.md 问题表），无遗留 | 🟢 |

### 2.3 可用功能清单

```
✅ 文本渲染: -f/--font 指定字体 + 多行输入（stdin / 参数）→ ASCII 艺术字
✅ 字体资产: 包内 24 个 .tlf 字体全部可加载（-d 指定字体目录）
✅ 导出格式: --html（完整 XHTML 文档）/ --irc
✅ 渲染模式与控制: -s -S -k -W -o、-w/--width、-t/--termwidth、-I infocode
✅ 过滤器: -F（flip/metal/rainbow 等，-F list 列出全部）
✅ 安装布局: bin/toilet、share/figlet/*.tlf(24)、share/man/man1/toilet.1、licenses/COPYING
```

### 2.4 已知限制

1. 编译期默认字体目录（`FONTDIR`）指向本包安装位置（`<包目录>/share/figlet`），
   这是 conan 包的常规做法（同 `archives/f/figlet/2.2.5`）：包被挪到别的路径后，
   不带 `-d` 的默认调用需要显式传 `-d <字体目录>`。属打包形态固有约束，非平台缺陷。
2. `toilet --version` 的 date 字段为空——上游 `configure.ac` 用未定义的 `$stamp` 拼日期，
   属上游自身行为，未改动。

---

## 三、测试详情

### 3.1 通过的测试（上游官方）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `test/check-source` | 遍历 `src/`、`tools/` 全部源文件，断言无制表符与行尾空格（实测 `11 files, 1147 lines, 0 errors in source code`） | ✅ PASS |
| `test/check-fonts` | 用构建出的 `toilet` 逐个加载 `fonts/` 全部字体并渲染 `Hello World`（实测 `24 fonts, 0 load errors`） | ✅ PASS |

### 3.2 通过的测试（消费者端到端，鸿蒙 PC 目标机）

| 用例 ID | 场景 | 真实输入 | 预期业务输出 | 结果 |
|---------|------|----------|--------------|------|
| HM-E2E-01 | 文本渲染端到端 | 文件内文本 `OHOS` → `toilet -f pagga --width 80`（stdin） | 3 行 pagga 字形，与黄金文件**逐字节一致**（147 字节） | ✅ PASS（exit=0） |
| HM-E2E-02 | 字体资产端到端 | 包内 `share/figlet/*.tlf` 全部 24 个字体 → `toilet -d <包目录>/share/figlet -f <font> "Hello World"` | 24/24 加载成功、输出非空、0 个加载错误 | ✅ PASS |
| HM-E2E-03 | HTML 导出端到端 | `toilet --html -f pagga "OHOS"` | 完整 XHTML（`<!DOCTYPE html` … `</div></body></html>`）+ 3 行字形 span（含 `&#9608;`），757 字节 | ✅ PASS（exit=0） |

被测对象来源：`test_package/conanfile.py` 从 `self.dependencies["toilet"].cpp_info` 解析
二进制与字体目录绝对路径，传入脚本并复核「被测二进制位于被测包目录内」后才执行；
不使用源码树产物、系统同名程序或旧包缓存。

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无（`test_e2e.sh` 刻意不做 `can_run()` 静默跳过：本平台 build==host，
消费者用例必须真实执行，无法运行时宁可失败也不放过）。

---

## 四、关键问题分析

### 问题 1: `configure` 报 `cannot guess build type; you must specify one`

**现象**：
```
configure: error: cannot guess build type; you must specify one
（config.guess 内部：can't create .../cgXXXXXX/dummy.c: Permission denied）
```

**根因**：本机 `config.guess`(2024-07-27) 不识别 HarmonyOS/HongMeng 内核，且在 HMDFS 上
`mkdtemp` 后写入 `dummy.c` 被拒（权限按组位判定）；conan 仅在 build profile ≠ host profile 时
才自动注入三元组，本任务两侧同为 `ohos` profile，故必须由配方显式给出。

**解决方案**：`AutotoolsToolchain.configure_args` 显式传
`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（build == host →
跳过 config.guess 且保持本机原生编译、运行期探测不被跳过）。

### 问题 2: `config.status` 在 HMDFS 上报 `could not setup config files machinery`

**现象**：
```
config.status[762]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根因**：`config.status` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，HMDFS 下该目录
实际为 `drwx--S---`(2700)；当前 uid(20020082) 并非文件属主、访问权由 `file_manager` 组位判定，
`chmod 770` 实测无效 → 写入 EACCES。

**解决方案**：在 `build()` 内把**生成后**的 `configure` 里两处 `umask 077` 改写为 `umask 022`
（该两行来自 autoconf 的 config.status 模板，不在源码树内，无法做成源码补丁；
同 `archives/l/libcaca/0.99.beta20.1` 的处理），并对替换次数做契约断言。

### 问题 3: 运行期 `error: could not load font pagga`

**现象**：安装后的 `toilet` 不带 `-d` 时找不到包内字体（二进制内烤死 `//share/figlet`）。

**根因**：conan 惯例是 `--prefix=/` + `make install DESTDIR=<包目录>`，于是
`src/Makefile.am` 的 `-DFONTDIR="$(datadir)/figlet"` 展开为 `/share/figlet`；
上游没有提供任何覆盖点（`src/main.c`: `cx->dir = FONTDIR;`，无 configure 选项/环境变量）。

**解决方案**：`patches/0001-src-Makefile.am.patch` 把该写法改为可覆盖的
`FONTDIR ?= $(datadir)/figlet`（默认行为与上游完全一致），配方在 `make` 命令行传
`FONTDIR=<包目录>/share/figlet`（同 `archives/f/figlet/2.2.5` 的既有做法）。

### 问题 4: 上游测试在默认 conan 布局下假失败

**现象**：`make check` 报 `grep: ../src/main.c: No such file or directory`、
`error: could not load font *.tlf`（2/2 FAIL）。

**根因**：`test/check-source`、`test/check-fonts` 按**源码树相对路径**取 `../src`、`../fonts`，
只在 `srcdir == builddir` 时成立；`basic_layout` 默认把构建目录放到 `build-release/` 子目录（VPATH 构建）。

**解决方案**：源码内构建（`basic_layout(self, src_folder=".")` + `self.folders.build = "."`），
两个上游测试**原样**通过、零上游测试修改。

---

## 五、测试环境

```
被测包        : toilet/0.3.r155.3eb9d58
上游源码      : cacalabs/toilet 提交 3eb9d58037afb0a1baec6dca82caa045fb2217c0（master tip，r155）
源码 sha256   : a16b3a6217852d4ec5e9fa94c5600b900710d652910ac041bf1c5c61524a03d4
构建方式      : conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
                --build=missing --build=toilet/*   （退出码 0）
构建依赖      : libcaca/0.99.beta20.1（prebuilt，传递 ncurses/6.4、zlib/1.3.1 静态）、automake/1.18（tool_requires，prebuilt）
设备/系统     : HarmonyOS PC（HAD-W32）/ HongMeng Kernel 1.12.0 / aarch64
编译器        : clang 15.0.4（/data/service/hnp/bin/clang）
包内产物      : bin/toilet（1,284,608 B）、share/figlet/*.tlf（24）、share/man/man1/toilet.1、licenses/COPYING
```

原始日志与 E2E 证据（本地留档，不进 PR）：
`~/tmp/toilet-evidence/conan-create-w3.log`、`~/tmp/toilet-evidence/test-logs/`、
`~/tmp/toilet-e2e-<pid>/`（`out-01.txt`/`expected-01.txt`/`out-03.html`）。

---

*报告生成时间: 2026-10-16*
