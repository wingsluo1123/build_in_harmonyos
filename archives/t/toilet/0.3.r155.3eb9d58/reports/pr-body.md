- **三方库名称**：toilet（The Other Implementation of figLET）
- **上游版本**：0.3（源码点 = 提交 `3eb9d58037afb0a1baec6dca82caa045fb2217c0`，master 最新提交；
  包版本串 `0.3.r155.3eb9d58` 由任务/分支给定，`r155` = 该仓库 master 提交总数 155，已用 GitHub API 逐项核实：
  仓库无任何 tag、该提交即 master tip、commits?per_page=1 的 Link rel="last" = 155）
- **上游仓库地址**：https://github.com/cacalabs/toilet
- **适配路径**：路径 A（基础适配）
- **使用知识库**：鸿蒙三方库适配技能 `openharmony-compile-agent`（v12.22）；知识条目
  E175（HMDFS 临时目录限制，本次实测修正其首选方案）、E490（Autotools helper 执行位）、
  E178/E248（设备无 automake 的自举）、E524（依赖注入须用私有 prefix / HMDFS 按组位判权）；
  本次新增草稿 **E700**（HMDFS 上 config.status 的 `umask 077` 临时目录不可写）、
  **E701**（上游测试按源码树相对路径取值时 VPATH 构建会假失败）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架 |
| 集成测试 | 2 | 来源：`test/Makefile.am` 的 `TESTS = check-source check-fonts`（automake parallel-tests 驱动），`make check` 实际执行 |
| 其他测试 | 0 | — |
| **合计** | **2** | 清点证据：`test/Makefile.am` 仅此 2 个测试脚本 + `src/`、`tools/` 无测试目录 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | — |
| 集成测试 | 2 | 不变 | `check-source`（源码卫生：11 files / 1147 lines / 0 errors）、`check-fonts`（24 fonts / 0 load errors），配方 `build()` 内运行上游 `make check`，**未改上游任何测试文件** |
| 鸿蒙特有测试 | 3 | 新增 | 消费者端到端用例，鸿蒙 PC（HAD-W32，HongMeng Kernel 1.12.0 aarch64）实机执行、3/3 PASS：<br>• **HM-E2E-01** 文本渲染端到端：真实输入文件 `OHOS` → 安装后的 `<包>/bin/toilet -f pagga --width 80`（stdin）→ 输出与黄金文件**逐字节一致**（147 B，exit=0）<br>• **HM-E2E-02** 字体资产端到端：包内 `share/figlet` 全部 24 个 `.tlf` 逐个加载并渲染 `Hello World` → 24/24 成功、0 加载错误<br>• **HM-E2E-03** HTML 导出端到端：`toilet --html -f pagga "OHOS"` → 完整 XHTML（DOCTYPE + `</div></body></html>` + 3 行字形 span，757 B，exit=0）<br>源码/入口：`test_package/test_e2e.sh`（由 `test_package/conanfile.py` 从 `self.dependencies["toilet"]` 解析被测包绝对路径后驱动）；证据：`reports/test-report.md` 第三节 3.2、`reports/audit-result.json` |
| **合计** | **5** | **+3** | 上游 2 + 鸿蒙特有 3 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：上游两个测试脚本按**源码树相对路径**取值（`../src/*.c`、`../fonts`），
> 只在 `srcdir == builddir` 时成立。配方用 `basic_layout(src_folder=".")` + `self.folders.build = "."`
> 做源码内构建（同 `archives/a/adjtimex/1.29` 先例），使它们**原样**通过；**测试文件零改动、零补丁**。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 说明：上游已有 2 个官方测试脚本并全部通过；本 PR 另外新增的是**消费者端到端用例**
> （鸿蒙特有测试 3 个，见上表），属平台特有的消费者视角验证，不计入「补全上游测试」范畴。
> 新增文件：`test_package/test_e2e.sh`、`test_package/conanfile.py`、`test_package/MANIFEST.yml`。

## 验证结果

- 编译状态：通过（`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build=toilet/*` 退出码 0；W3 本地 CI 模拟通过，`.ci-result.json` exit_code=0）
- 上游测试用例通过率：**2/2（100%）**（`make check` 实测 `# TOTAL: 2 / # PASS: 2 / # FAIL: 0 / # ERROR: 0 / # SKIP: 0`）
- 新增测试用例通过率：**3/3（100%）**（鸿蒙特有测试 3 个，鸿蒙 PC 目标机实机 PASS）

## 补充说明

**适配内容（本版本唯一补丁 1 个，另加 1 处生成物必需改写）**

| 类别 | 内容 | 理由 |
|---|---|---|
| 补丁 `patches/0001-src-Makefile.am.patch`（portability，无平台宏） | `src/Makefile.am` 的 `toilet_CPPFLAGS = -DFONTDIR=\"$(datadir)/figlet\"` 增加覆盖点：`FONTDIR ?= $(datadir)/figlet` + `-DFONTDIR=\"$(FONTDIR)\"` | conan 惯例用 `--prefix=/` + `make install DESTDIR=<包目录>` 安装，使 `$(datadir)` 展开为 `/share`、二进制内烤死 `//share/figlet`，运行期报 `error: could not load font pagga`；上游无任何覆盖点（`src/main.c`: `cx->dir = FONTDIR;`）。默认值与上游逐字一致、未改逻辑分支；配方在 `make` 命令行传 `FONTDIR=<包目录>/share/figlet`（同 `archives/f/figlet/2.2.5` 既有做法） |
| 生成物改写（`build()` 内，非补丁） | 把**生成后** `configure` 里 2 处 `umask 077` 改写为 `umask 022`，并对替换次数做契约断言 | HMDFS 按**组位**判目录访问权（构建 uid 20020082 非文件属主），`config.status` 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建的 2700 目录不可写且 `chmod` 是 no-op，configure 报 `could not setup config files machinery`。该两行来自 autoconf 模板、不在源码树内，无法做成源码补丁（同 `archives/l/libcaca/0.99.beta20.1`） |

**构建要点（其余均通过配方/generate() 解决，无源码改动）**

1. 源码归档为 git-archive 快照、不含 `configure`/`Makefile.in` → `build()` 先跑上游自带 `bootstrap`（aclocal→autoconf→autoheader→automake），automake 由 `tool_requires("automake/1.18")` 提供（设备 `/data/service/hnp/bin` 只有 autoconf 家族）。
2. 本机 `config.guess`(2024-07-27) 不识别 HarmonyOS 内核、且 HMDFS 下 `mkdtemp` 后写 `dummy.c` 被拒 → configure 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（build == host：跳过 config.guess 且保持本机原生编译）。conan 仅在 build/host profile 不同时才自动注入三元组，本任务两侧同为 `ohos` profile。
3. `configure.ac` 的 `PKG_CHECK_MODULES(CACA, caca >= 0.99.beta18)` 是硬检查；libcaca 配方把包拆成组件，`PkgConfigDeps` 默认生成 `libcaca-caca.pc`，configure 找不到模块 `caca` → 在 `generate()` 中把 `caca` 组件的 `pkg_config_name` 指回 `caca`（E348 同族手法）。`PKG_CONFIG_PATH` 由 `AutotoolsToolchain` 指向本配方 `generators_folder`，不碰共享 `/usr/local`（R49/PF6）。
4. 依赖：`libcaca/0.99.beta20.1`（制品仓 prebuilt，W0 双层验证通过：recipe + `conan install --build=never` 命中 binary，含传递 ncurses/6.4、zlib/1.3.1）；`automake/1.18`（tool_requires，prebuilt）。

**产物与限制**

- 产物：`bin/toilet`（1,284,608 B）、`share/figlet/*.tlf`（24）、`share/man/man1/toilet.1`、`licenses/COPYING`；软件级 `commands.json`（type=tool，`versions."0.3.r155.3eb9d58".ref = "toilet/0.3.r155.3eb9d58"`，`binary=false` 待发布后置 true）。
- 已知限制：编译期默认字体目录指向本包安装位置（`<包目录>/share/figlet`），是 conan 包常规形态（同 figlet）；包被整体挪走后不带 `-d` 的默认调用需显式 `-d <字体目录>`。`toilet --version` 的 date 字段为空为上游自身行为（`configure.ac` 用未定义的 `$stamp`），未改动。
- 独立审计（W4）：`reports/audit-result.json` verdict=**pass**，P0=0/P1=0，仅 1 项 P3（测试断言计数口径说明，非阻断）。
- 证据留档（不入 PR）：原始构建日志 `conan-create-w3.log`、上游测试日志 `test-logs/`、消费者 E2E 产物（`out-01.txt`/`expected-01.txt`/`out-03.html`）。

---

## 门禁记录（如实申报）

- **PF9 显式放行记录**：`create-pr` 的 PF9 前置闸按路径层数判定，会把本 PR 必需的三个**软件级**文件
  （`archives/t/toilet/README.md`、`archives/t/toilet/commands.json`、`archives/t/toilet/manifest.yaml`，
  由 ARCHIVE-SPEC v3.0 §2.1 强制要求）判为「缺版本目录层」。经作者向任务方申请并获**明确同意**，
  使用仓库官方入口 `scripts/gitcode_pr.py create-pr --no-preflight` 显式放行**该一条**误判；
  其余 PF 检查与门禁回执照常有效（W4：`reports/audit-result.json` verdict=pass，P0=0/P1=0；
  W3：`.ci-result.json` exit_code=0）。同形态的近期合入 PR（如 `!16028` tqftpserv）同样包含这三个软件级文件。
- **submit 自检记录**：`ohc-run.py submit` 自检要求 `packaging/*.tar.gz`，而 ARCHIVE-SPEC v3.0 已废弃
  `packaging/`（其 tar.gz 属删除项）、R19 亦禁止手动打包，故本 PR 不含该目录——与近期合入 PR 一致，
  未为通过旧自检而手工打包或伪造产物。

