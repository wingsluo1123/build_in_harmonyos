## PR 信息

- **三方库名称**：uefitool
- **上游版本**：`0.28.0-a73`（上游 tag `A73` → commit `29796629`；tarball `2400878 B`，sha256 `81d9944d75e27d4afbc8559d9ba913552552006fd21ce9cadf357a4a0f58e59507e`）。★ 版本号读法见下：`0.28.0` 是上游 **old_engine** 分支的版本号，`a73` 对应 **new_engine** 分支的快照 tag `A73`（`version.h` 里写 `"NE alpha 73"`），**必须取 tag `A73`**，取 `0.28.0` 那个 release 会拿到完全不同的代码树
- **上游仓库地址**：https://github.com/LongSoft/UEFITool
- **适配路径**：**路径 C（高难度挑战）** —— 另按平台要求在本 PR 内附带 `knowledge/drafts/` 下的 4 条路径 B 草稿，选题与全量池查重结论见 `notes.md` §8
- **使用知识库**：有命中，共 **4 条**（`E077` / `E074` / `E063` / `E439`），逐条命中说明见下

### 使用知识库 · 命中说明

> 说明方式：本包的适配在**配方设计阶段**就按知识库条目的判据把三处平台风险**提前规避**了
> （而不是"踩到坑之后再回头找条目"）。下表注明每条是"预防性采用"还是"由症状定位"，
> 不把预防写成事故。

| 条目 | 判据关键词 | 本次采用的具体位置 |
|------|-----------|-------------------|
| **E077** `post-install-script` | `operation not permitted`、`RPATH`、`RUNPATH`、`permission denied.*ELF`、`.note.ohos.ident` | **预防性采用，并在真机上实测确认。** E077 指出"修改 RPATH/RUNPATH 会使 ELF 的签名段失效 ⇒ 内核拒绝加载"。本包**不产出任何第三方 `.so`**（brotli / LZMA / zlib / Tiano / bstrlib / SHA-1·256·512·SM3 全部以源码内联，见 `notes.md` §1.3），产物 `NEEDED` 只剩平台自带的 `libc++_shared.so` 与 `libc.so`（真机 `readelf -d` 实测 **2 条**）⇒ 没有任何"要靠 RPATH 才找得到"的库，RPATH 本无意义；直接在 `generate()` 里 `CMAKE_SKIP_RPATH=ON` + `CMAKE_SKIP_INSTALL_RPATH=ON`，从源头取消 install 期的 relink 动作。**真机实测**：两个产物的 `RPATH`/`RUNPATH` 条目数均为 **0**，而 `.note.ohos.ident` 与 `.codesign` 段**都还在**，且二进制能正常执行（`-v` → `NE alpha 73 (Oct  4 2026)`、rc=0）。同仓 `archives/q/qdl/2.7` 是"踩到后处置"的实例（meson install 把 `DT_RUNPATH` 整段改写成 `XXXX…`、`.dynamic` 少 16 字节 ⇒ rc=126），本包按同一机制提前规避 |
| **E074** `env-var-override` | `make -j`、`parallel`、`FIFO`、`jobserver`、`Permission denied`、`concurrent build`、`GNU make` | **预防性采用。** `/storage/Users/**` 走 HMDFS，GNU make 的 jobserver fifo 建不出来（`mkfifo … Operation not permitted`），症状是并行子任务集体 `Error 1` 且日志里**一行编译器诊断都没有**（极易误判成代码错误）。配方在 `build()` 内固定 `self.conf.define("tools.build:jobs", 1)`（必须在 `CMake(self)` 之前） |
| **E063** `add-cflags-disable-werror` | `-Werror`、`warning to error`、`clang`、`CFLAGS`、`Makefile` | **预防性核对（对应 P007）。** 本包**零补丁、不改任何编译 flag**，所以必须反过来确认"构建变绿不是因为做了 CFLAGS 级绕过"。真机 `conan create` 的完整日志中 `warning` 行数为 **0**（原文见下「验证结果」）⇒ 上游源码在 OHOS 的 clang 15 + libc++ 上**本身零告警**，不需要任何 `-Werror` 豁免。若下游加严，按 P007 也只能精准到具体 warning 类别，而不是关掉全局 `-Werror` |
| **E439** | 子模块可选组件误设为 `REQUIRED`、依赖膨胀 | **相关但需区分的条目。** E439 的层面是 **conan 配方依赖**（不要把非必需模块写进 `requirements`），而本包的障碍在**更下一层**：上游根 `CMakeLists.txt` 用无条件的 `ADD_SUBDIRECTORY(UEFITool)` 把 Qt6 GUI 耦合进整棵构建树，而 `UEFITool/CMakeLists.txt` 第 9 行是 `FIND_PACKAGE(Qt6 REQUIRED COMPONENTS Widgets)` ⇒ 在没有 Qt6 的 OHOS PC 上**连零 Qt 依赖的两个 CLI 都到不了编译**。处置也不同（E439 改配方，本包新增适配侧构建入口）。本 PR 的路径 B 草稿已把 E439 登记为 `similar_to`，供审核判别 |

> 附带参考：**P013**（平台限制必须降级而非绕过）—— 剥离 Qt6 GUI 子目录、把交付面收敛到两个零 Qt 依赖的 CLI，属于"按平台能力裁剪交付面"而非"绕过平台限制"；**P007**（`-Werror` 禁用应精准到具体 warning 类别）—— 见上表 E063 条目。

### 知识库未覆盖的缺口（本 PR 附带 4 条路径 B 草稿）

对候选主题做了**全量池硬查重**（`knowledge/doc/` 541 条 + `knowledge/drafts/` 3853 个文件，
共 4394 个文件），四条主题均**零命中或仅低命中**，故在本 PR 内附带草稿：

| # | 草稿主题 | 查重锚点 | 命中 | 判别点 |
|---|---|---|---|---|
| 1 | Qt6 GUI 子目录被无条件耦合进根工程，连带阻断零 Qt 依赖的 CLI | `ADD_SUBDIRECTORY+Qt6` / `FIND_PACKAGE+Qt6` | 3 / 38 | `DRAFT-kf6-top-level-component-negotiation` 讲的是 `find_package` 的 optional components 协商；本条是**上游 CMakeLists 的 ADD_SUBDIRECTORY 无条件耦合**，已登记 `similar_to` |
| 2 | `guids.csv` 只进 GUI 的 Qt 资源 + 按 CWD 查找 + 三重静默降级 | `guids.csv` / `initGuidDatabase` / `guiddatabase` / `qrc+alias` | **0 / 0 / 0 / 0** | 全零命中 |
| 3 | `uefiextract <img> guids` 在 GUID 库为空时打印用法并 `rc=1` —— 收集函数按 `text` 字段筛选（普通文件该字段恒空）+ 该分支缺终结 `return` | `print_usage` / `guidDatabaseFromTreeRecursive` / `fall-through` / `U_INVALID_PARAMETER` | **0 / 0 / 0 / 0** | 全零命中；**由真机第 28 条消费者用例实测触发**，有/无 Volume Top File 互为对照 |
| 4 | 同一包内多个 CLI 的退出码契约不对称 ⇒ 消费者测试不能套同一模板 | `UEFIExtract` / `UEFIFind` | **0 / 0** | 全零命中 |

**已否决的候选**（记录以免重复尝试，详见 `notes.md` §8）：曾疑为缺口的
「`.manifest` 塞进 `ADD_EXECUTABLE` 在非 MSVC 平台会失败」经**最小复现实测证伪**
（cmake 4.3.4 + clang + Ninja：configure 成功，且 `app.manifest` 被 CMake 识别为
`MANIFESTS` 目标属性写进 `build.ninja`，既非报错也非静默忽略）；真机 Linux 语义下的
行为无法在主机上验证，故**不写条目**。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游**没有**测试套件 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | 唯一的 `fuzzing/ffsparser_fuzzer.cpp` 是 libFuzzer 入口（`LLVMFuzzerTestOneInput`），不是可执行测试套件，且不带种子语料 |
| **合计** | **0** | **口径 = CMake `add_test` / meson `test()` 注册条目数** |

> 源码级审计（tag `A73` tarball）：全树 `meson.build` 里 `test(` 出现 **0** 次；
> 全树 `enable_testing()` / `add_test(` 出现 **0** 次；无 `tests/` 或 `test/` 目录。
> 审计过程逐条记在 `test_package/MANIFEST.yml` 的 `upstream_test_audit`。
> **本 PR 不伪造上游通过率**，故下方「上游测试用例通过率」如实写 N/A。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 上游单元/集成测试 | 0 | 不变 | 上游无测试套件可执行（见上表） |
| 构建自检（适配侧新增） | **3** | +3 | `cmake/CMakeLists.txt` 注册的 3 条 ctest 用例，只断言两个 CLI 自身的退出码（`uefiextract -v` / `uefifind -v` / `uefiextract` 无参数并置 `WILL_FAIL`）。作用见下「补全测试用例说明」。**不计入上游测试数**，在 `MANIFEST.yml` 里单列为 `build_selftests` |
| 鸿蒙特有测试 | 0 | 不变 | 本包产物无平台特有 API 依赖（两个 CLI 是纯文件解析），无需专门覆盖 |
| 消费者测试（Conan test_package） | **28** | +28 | `test_package/test.sh`，三层 28 条检查（A. CLI 契约 17 条 / B. 真实解析 8 条 / C. `guids.csv` 生效性 3 条） |
| **合计** | **30** | **+30** | |

> 计数口径：消费者用例的 28 条均为**运行时**断言，逐条自带且仅带一条断言
> （`pass()`/`fail()` 计数器，无循环包裹），使通过率分母无歧义；运行时以日志末尾
> `--- uefitool consumer: 28 checks run, N failed ---` 为准。检查点清单见 `notes.md` §4。
> 构建自检 3 条与消费者 28 条**分开计数、不混用**。

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] 是，存在对上游测试用例的修改
- [x] **否，未修改上游任何测试用例**

> 上游**没有测试套件**，因此不存在"修改上游测试"这件事。
> 且本包 **`patches_applied` 为空 —— 上游源码零改动**：唯一的构建侧改动是
> **新增**一个适配侧文件 `cmake/CMakeLists.txt`（由 `conanfile.py` 的
> `export_sources()` 随包带出，**不在上游源码树里**，故不构成 patch）。
> 这也意味着本包不存在"补丁数与补丁文件同步"这一类问题。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是，上游无测试用例，适配后补全了测试**
- [ ] 否，上游已有测试用例覆盖

> 上游零测试，所以本包的**全部功能证据**都来自适配后补的两层用例。补全分两层，
> 定位不同：

**第一层：构建自检（3 条，`cmake/CMakeLists.txt` → ctest）**

上游零测试的直接后果是：`ctest` 会因为"找不到任何测试"返回非 0，`conan create`
随之失败，而日志里只有一句 `No tests were found` —— 这既不是有效证据，也不是
可诊断的失败原因。故注册 3 条**只依赖两个 CLI 自身退出码**的冒烟用例：

| 用例 | 命令 | 期望 |
|---|---|---|
| `uefitool-cli-version-extract` | `uefiextract -v` | 退出码 0 |
| `uefitool-cli-version-find` | `uefifind -v` | 退出码 0 |
| `uefitool-cli-usage-extract` | `uefiextract`（无参数） | 退出码 1（`WILL_FAIL` 反转） |

这三条让 `ctest` 成为一条真实、确定、与机器负载无关的证据链，并要求
`conan create` 日志中留下 `ctest` 痕迹（CI 的 L1c 读取该痕迹）。

**第二层：消费者用例（28 条，`test_package/test.sh`）**

这个包是**纯工具包**（没有库、没有公共头），"消费者"只能是拿到
`bin/uefiextract` / `bin/uefifind` 两个可执行文件的人。三层设计：

- **A 层 · CLI 契约（17 条）**：`-v` / `--help` / 无参数 / 缺文件的退出码。
  **期望值全部取自上游 `main()` 的字面返回**，不是臆断的：`uefiextract` 无参数
  返回 **1**、`uefifind` 无参数返回 **0**（上游在这件事上**刻意不对称**，本用例
  把两边各自钉住，等于把"确实读过 `main()`"变成可验证的）；镜像打不开都返回
  `U_FILE_OPEN = 5`。用法文本断言覆盖两个工具的真实子模式
  （`imagefile all` / `unpack` / `dump` / `report` / `guids` / `-m MODE_1`；
  `header | body | all` / `list | count` / `patternsfile`）。
- **B 层 · 真实解析（8 条）**：上游零语料，故用**纯标准库**手搓一张 4096 字节的
  最小合法 FFS2 固件卷（FFSv2 卷头 + `calculateChecksum16` + `BlockMap` 终止项；
  一个 FREEFORM 文件 + 一个 RAW 段，段体含 4 字节魔数与 32 字节 ASCII 标记），
  然后让两个工具真的走一遍 **镜像 → 卷 → 文件 → 段**：报告生成、报告里出现探测
  文件 GUID、`body count` / `body list` 命中魔数并报出 GUID、查不存在的模式得
  `U_ITEM_NOT_FOUND(8)`、`dump` 落出非空目录树。固定装置字节级细节见 `notes.md` §4.2。
- **C 层 · `guids.csv` 生效性（3 条）**：★ 本包最有分量的证据链，做**双向**验证。
  上游把 GUID→可读名映射表（12042 行）**只**打进 GUI 的 Qt 资源
  （`UEFITool/uefitool.qrc`），`INSTALL()` 里没有它；而 `UEFIExtract` 在 `main()`
  **首行**就 `initGuidDatabase("guids.csv")`（相对路径 ⇒ 按 CWD 解析），读失败时
  `guiddatabase.cpp` **静默**返回空名表 ⇒ 退出码不变、报告照样生成，只有可读名
  悄悄退化成裸 GUID 串。故断言：
  ① 无 `guids.csv` 时卷名必须是裸格式 `8C8CE578-8A3D-4F1C-9935-896185C32DD3`；
  ② 把随包安装的那份放进 CWD 后重跑，同一个卷必须变成 `EfiFirmwareFileSystem2Guid`；
  ③ `uefiextract <img> guids` 必须产出非空的 `<img>.guids.csv`。
  第 ② 条**同时证明** `package()` 把 `guids.csv` 装到 `share/uefitool/` 是**必要且
  有效**的，而不是"多装了个文件"。

---

## 验证结果

> ⚠️ **本节数据以真机 `conan create` 与本地 CI 模拟的实际输出为准，逐个回填；
> 未执行的行明确标注，不预填。**
> 采集环境：鸿蒙 PC 真机 OpenHarmony 6.0 / aarch64 / clang 15 / libc++ / 原生构建，
> 仓库 `~/runner002/build_in_harmonyos`。

- 编译状态：✅ **通过** —— `conan create` 退出码 **0**；完整日志 356 行（`$HOME/uefitool-create-final.log`），其中 `error:` / `fatal error:` / `Error N while executing` / `ERROR` 命中数 **0**，`warning:` 命中数 **0**
  - 本 PR 提交的配方 `uefitool/0.28.0-a73#bb0813fe038ff0ccc7b1525eb894a2e4` 是**改动过注释后重跑**的一版；改动前的 `#a75862c9…` 也跑过一遍，两次的 `package_id`、package revision 与**两个二进制的 sha256 完全相同**（注释修订只发生在文字层，产物零变化）。两次原始输出见 `notes.md` §7.1 与 §7.8
- **上游测试用例通过率：N/A** —— 上游**没有**测试套件（`upstream_test_total = 0`，审计见 `test_package/MANIFEST.yml`）。本 PR 不伪造上游通过率
- 构建自检通过率：✅ **3/3（100%）** —— `cmake --build … --target test` 输出 `100% tests passed, 0 tests failed out of 3`（`Total Test time (real) = 0.12 sec`）：`1/3 uefitool-cli-version-extract`、`2/3 uefitool-cli-version-find`、`3/3 uefitool-cli-usage-extract` 全 Passed
- **新增测试用例通过率**：✅ **28/28（100%）** —— 真机 `bash test.sh <pkg>/share/uefitool/guids.csv` 输出 `--- uefitool consumer: 28 checks run, 0 failed ---` 与 `ALL CHECKS PASSED (28/28)`；脚本末尾的 `EXPECTED_CHECKS=28` 计数自校验未触发 `Bail out`
- 编译器：clang 15（OHOS 6.0 / aarch64 / libc++ / **原生构建**）
- 构建系统：CMake（上游 `CMAKE_MINIMUM_REQUIRED(VERSION 3.22)`），本包用
  `CMakeToolchain` + 适配侧 `cmake/CMakeLists.txt`（`build_script_folder="cmake"`）
- 配置选项：`CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`、
  `CMAKE_SKIP_RPATH=ON`、`CMAKE_SKIP_INSTALL_RPATH=ON`、
  `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`，以及 `tools.build:jobs=1`
  （逐项理由见 `notes.md` §2.3 与 §3 决策表）
- 本地 CI 模拟：✅ **通过** —— `JUNK_PR_DIFF=… CI_PACKAGES="archives/u/uefitool/0.28.0-a73" CI_BRANCH=feat/uefitool-0.28.0-a73 zsh ci/conan/build_and_test.sh` ⇒ 退出码 **0**、`Pass rate: 100.0% (1/1)`（`Total 1 / Success 1 / Failed 0`）。逐闸口：`G0_RESULT=pass`（含 `[ok] G0e: Root directory whitelist passed`）、`KC_RESULT=pass`（`KC_ERRORS=0`）、`JC_RESULT=pass`（`JC_ERRORS=0`）、`L0_RESULT=pass: all checks passed`、`L1_RESULT=pass: upstream tests + test_package executed`（含 `[ok] L1e: Negative test confirmed — test genuinely depends on uefitool`）、`L2_RESULT=pass: uefiextract --version OK, uefifind --version OK`、`L4_RESULT=pass: no patches`、`L5_RESULT=pass: bin/ has content`
  - ⚠️ **非阻塞的本机环境现象（已定位到根因，不影响任何结论）**：CI 脚本的「Pre-download」预热步骤是 Python 代码（`subprocess.run(['curl', …])`），日志里会出现 **12 行** `[fail] [Errno 2] No such file or directory: 'curl'`。**这 12 行最容易被误读成"机器上没装 curl"，实测并非如此**，此处把证据摆全，以免复审时误判：
    - `/usr/bin/curl` **确实存在**：`-rwxr-xr-x … 4173016 bytes`，`aarch64-linux-ohos` 的 ELF，`curl 8.8.0-DEV / libcurl 8.8.0-DEV`；`sh` 侧 `command -v curl` → `/usr/bin/curl`、`[ -x /usr/bin/curl ]` → `yes`，机器上一切基于 shell 的下载都正常
    - 但**同一个文件在 Python 里完全不可见**：`os.stat('/usr/bin/curl')` 抛 `PermissionError: [Errno 13] Permission denied` ⇒ 连带 `os.path.exists` / `os.path.isfile` / `os.access(…, X_OK)` **全部为 `False`**，`shutil.which('curl')` 返回 `None`；`subprocess.run(['/usr/bin/curl', …])` 抛 `PermissionError`，用裸名 `'curl'` 则抛 `FileNotFoundError`（与 CI 日志逐字一致）
    - 根因是**进程域，不是文件权限**：真机 `python3` 位于 `/storage/Users/currentUser/usr/local/bin/python3`（**用户可写目录**），而平台**从用户可写目录启动的可执行文件会切入受限进程域、读不到 `/usr/bin`**；`sh` 是宿主交互 shell，不在该域，故 shell 侧一切正常。属平台安全模型特性，与本包的配方、源码、产物**完全无关**
    - 次数可算：`conandata.yml` 有 3 条 URL，第 1 条（`github.com`）被 `get_mirror_list()` 展开成 2 个镜像、后两条各 1 个，再乘每镜像 3 次重试 ⇒ **恰好 12 次**
    - 脚本随后打印 `[step] Pre-download: conandata.yml 已还原为官方 URL`，源码改由 **conan 自身**的下载器取得，`conan create` 与全部闸口仍然 pass —— 这也正是 `conandata.yml` 必须带"官方源 + 镜像兜底"列表的用处所在

### 产物验证

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ 通过 | `conan create` rc=0；日志 356 行内 `error:` / `fatal error:` / `Error N while executing` 命中 **0**；`warning:` 命中 **0** |
| 产物存在性 | ✅ 通过 | `package(): Packaged 2 files: uefiextract, uefifind` + `Packaged 1 '.md' file: LICENSE.md` + `Packaged 1 '.csv' file: guids.csv`；安装日志逐条 `-- Installing: …/p/bin/uefiextract`、`-- Installing: …/p/bin/uefifind`；包内**无 `lib/`、无 `include/`**，与 `package_type = "application"` 一致。完整包引用 `uefitool/0.28.0-a73#bb0813fe038ff0ccc7b1525eb894a2e4:6b129b068851896169fae42d399fa922d239ce8a#eb6bed38adf631a33bb31cff0d31a1e4` |
| ELF 格式 | ✅ 通过 | `file`：`ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped`（两个产物一致）；`readelf -h`：`ELF64` / `2's complement, little endian` / `Type: DYN (Position-Independent Executable file)` / `Machine: AArch64`。`uefiextract` 1235456 B / sha256 `52dd9dce0dc6dd65f7581e11e8a82527af8ba3f5ff59cd1f7b54696932a39d91`；`uefifind` 1063424 B / sha256 `ca609260b134074f50ae2ed24147121eadba8c6cd48d3b0b74a8a65141b64653`；二者 `-v` 均为 `NE alpha 73 (Oct  4 2026)` 且 rc=0。`readelf -lW` 见 `GNU_RELRO` 段与 `GNU_STACK`（flags 为 `RW`，无 `E` ⇒ **栈不可执行/NX**） |
| 运行测试 | ✅ 通过 | 构建自检 **3/3**（`100% tests passed, 0 tests failed out of 3`）+ 消费者 **28/28**（`ALL CHECKS PASSED (28/28)`） |
| 动态依赖 | ✅ 通过 | `readelf -d`：`NEEDED` **2 条** —— `libc++_shared.so`、`libc.so`（均为平台自带；brotli / LZMA / zlib / Tiano / bstrlib / digest 全部以源码内联，本包 `lib/` 下没有任何 `.so`）；`RPATH` / `RUNPATH` 条目数均为 **0**。另 `readelf -S` 确认 `.note.ohos.ident` 与 `.codesign` 段**都在**（E077 关注点） |

### 补丁说明

**本包 `patches_applied` 为空 —— 补丁 0 个，上游源码零改动。**

让两个 CLI 能被构建的唯一改动是**新增**适配侧文件
`archives/u/uefitool/0.28.0-a73/cmake/CMakeLists.txt`（由 `conanfile.py` 的
`export_sources()` 随包带出）。它不在上游源码树里，因此不构成 patch。

**为什么需要一个额外的构建入口**（完整分析见 `notes.md` §2.1）：上游根
`CMakeLists.txt` 只有五行，其中 `ADD_SUBDIRECTORY(UEFITool)` 是**无条件**的，
而 `UEFITool/CMakeLists.txt` 第 9 行是
`FIND_PACKAGE(Qt6 REQUIRED COMPONENTS Widgets)`。OHOS PC 侧 Qt 是 qt5-qtbase
（Qt 5.15），没有 Qt6 ⇒ 直接配置上游根工程必然 `FATAL_ERROR`，而报错发生在
`ADD_SUBDIRECTORY` 展开阶段，**连零 Qt 依赖的 `UEFIExtract` / `UEFIFind` 都到不了
编译**。适配侧入口只装载这两个 CLI 子目录，并把产物名显式钉成小写
（上游只在 `IF(UNIX)` 分支里改名，本包不依赖"OHOS 下 CMake 会把 `UNIX` 判为真"
这一间接假设）。

**三条理由说明这是对的做法**：① 不改上游一个字节（符合 R34），也就没有补丁计数
同步问题；② 两个 CLI 是自足的 —— 它们的目录里没有任何 `FIND_PACKAGE`，也不
`#include` 任何 Qt 头；③ 这就是"包面裁剪" —— GUI 目标在 OHOS 上既不可构建也不是
本任务需要的能力，**解析器能力 100% 保留**（解析逻辑全在 `common/` 里，GUI 只是它
的一个消费者）。

### 依赖

| 依赖 | 版本 | 角色 | 制品仓状态 |
|------|------|------|-----------|
| — | — | **无任何外部依赖** | — |

- 本包 `requirements` / `test_requires` / `tool_requires` **全为空**：
  brotli、LZMA SDK、zlib、Tiano、bstrlib、SHA-1/256/512/SM3 全部以**源码内联**在
  `common/` 下（`UEFIExtract` = 38 个 C++ + 38 个 C；`UEFIFind` = 35 个 C++ +
  38 个 C），Kaitai 生成代码已入库 ⇒ 只需"编译器 + CMake ≥ 3.22"
- 消费者测试只用环境自带的 `bash` 与 `python3`（conan 本体就跑在 Python 上）
- L0j 检查点：✅ **通过** —— 本地 CI 模拟回显 `[step] L0j: Checking version collision with registry (R37)...` → `[ok] version not in registry yet (first publish)` ⇒ 本库该版本号**首次发布**，与 registry 无冲突

### 测试结论

- **总体评价**：上游**没有测试套件**，这是本包与其它包最大的不同 —— 因此本 PR 把
  力气全部放在**自建可复现的证据链**上：固定装置用纯标准库现造（不依赖任何外部
  固件样本，无分发风险）、CLI 契约的每个期望值都能指到上游 `main()` 的具体字面
  返回、`guids.csv` 这条最容易沉默失败的能力链做**双向**断言。适配侧零补丁，
  上游源码一行未改。
- **已知限制**：
  1. **Qt6 GUI 目标不构建**。这是平台能力决定的裁剪（OHOS PC 侧 Qt 为 5.15），
     不是缺陷。若后续 OHOS 侧出现 Qt6，只需在适配侧 `cmake/CMakeLists.txt` 里
     加一行 `add_subdirectory(... UEFITool)` 即可恢复，上游无需改动。
  2. `guids.csv` 装到 `share/uefitool/` 而**不是**打进二进制。这与上游的选择
     （GUI 用 Qt 资源）不同，理由是不引入上游没有的构建期代码生成步骤；
     使用者在工作目录放一份副本/软链接即可获得可读 GUID 名（C 层第 ② 条用例
     证明该路径有效）。
  3. 上游 `fuzzing/ffsparser_fuzzer.cpp` 是 libFuzzer harness，**无种子语料**，
     且需要 libFuzzer 运行时 ⇒ 本包不构建、不执行它，也不把它计入任何测试数。
- **遇到的问题与解决方案**（全部来自真机执行，非推演）：

| # | 现象（原始输出） | 根因 | 处置 |
|---|---|---|---|
| 1 | 主机侧 configure 直接失败：`Could not find cmake module file: CMakeDetermineCLICompiler.cmake` / `No CMAKE_CLI_COMPILER could be found.` / `Configuring incomplete` | 适配侧 `cmake/CMakeLists.txt` 写成 `project(uefitool CLI CXX C)` —— CMake 把第 2 个位置参数起的裸词**当成语言名** | 改为 `project(uefitool LANGUAGES CXX C)` 并加注释。**在烧真机时间之前**用最小工程在本地复现并修掉（主机 cmake 4.3.4；真机 cmake 4.1.2 同样会挂） |
| 2 | 真机 `parseFileHeader: invalid header checksum D7h, should be F0h`，连锁 `invalid data checksum 1Ch, should be AAh` | fixture 生成器把 FFS **文件头**校验和也按 16 位字和算；上游要的是 **8 位补码，且求和须排除 `State`(0x17)**（`ffsparser.cpp:2187-2191`），`IntegrityCheck.File` 在 FFSv2 下是固定值 `0xAA`（`ffs.h:301`） | 新增 `ffs_header_checksum8()` 按上游口径实现（附代数化简说明），`IntegrityCheck = [0x00, 0xAA]`，并在 `build_ffs_file()` 内加自检 `assert`；本地逐字节核对得 `0x58 = F0 AA` |
| 3 | 真机 `parse: not a single Volume Top File is found, the image may be corrupted` | fixture 里没有 Volume Top File（GUID `1BA0062E-C779-4582-8566-336AE8F78F09`）。**注意**：缺 VTF 并不会让段解析失败，而是让 `ffsparser.cpp:103-109` **整遍跳过 `performSecondPass()`** —— 那道 pass 做的是 reset vector / FIT / protected range / TE image base 的**地址侧**分析，不是段解析 | fixture 追加一个 VTF（按规范放在卷内最后一个文件），并在用例文案里写清 VTF 的真实作用 |
| 4 | 消费者第 28 条失败：`uefiextract probe.fv guids` 打印用法文本并 `rc=1`，且不生成 `probe.fv.guids.csv` | **上游两处缺陷叠加**：`common/guiddatabase.cpp:124` 的收集函数按 `model->text` 而非 `model->name` 筛选（普通文件的 `text` 恒空 ⇒ 结果集恒空），且 `uefiextract_main.cpp:102-107` 的 `guids` 分支**缺终结 `return`** ⇒ 落穿到 `:216-218` 的 `print_usage(); return 1;`。对照：`report` 分支（`:109-120`）有显式 `return 1`，且报告读的是 `name`（`ffsreport.cpp:66`）—— 这正是"报告里有 GUID 名、导出文件里没有"的原因 | 该条用例改造为**双向钉住**：镜像含 VTF ⇒ `rc=0`、产出 53 B、内容 `1BA0062E-C779-4582-8566-336AE8F78F09,Volume Top File`；把 VTF 的 GUID 抹掉（库变空）⇒ `rc=1` 且不生成文件。根因与最小修复写成本 PR 附带的知识库草稿 `guids-mode-text-vs-name-emptydb-fallthrough` |
| 5 | 指令通道全断：本机 `:8000` 与"真机 hub"双双 `000` | 文档里的"真机 hub `10.29.57.12:8000`"其实是 **PC 自己**早前那张虚拟网卡的地址；校园网 DHCP 变动后 PC 变成 `10.129.64.34/16`，真机 `~/.ohget` 里写死的镜像地址已失效 | 通道确立为 **PC 侧当服务端（`0.0.0.0:8000`）+ 真机被动轮询**；`ohget.sh` 增加 `probe()` / `pick_mirror()` **多候选自动探活**（`/ping` 回 `pong` 才算活）。真机**无 SSH**（22/2222/8000/8080/5555 全关），一切下发只能走这条通道 |
| 6 | 知识库草稿「clang + libc++ 下 `-Wnullability-completeness` 刷屏（主机侧实测 119 条）」的前提**被真机证伪** | 真机 `conan create` 完整日志里 `warning:` **0 行** ⇒ 上游源码在 OHOS 的 clang 15 + libc++ 上本身零告警，主机侧 zig-libc++ 的 119 条**不能外推**到 OHOS | **撤下**该草稿（`.kv`/`.md` 已删），改把"零告警 ⇒ 本包不需要任何 `-Werror` 豁免"作为正面证据写进 `manifest.yaml` 的 `knowledge_gained` 与 E063 命中说明。宁缺勿假 |
| 7 | 真机 CI 模拟日志出现 12 行 `[fail] [Errno 2] No such file or directory: 'curl'` | **不是"没装 curl"**：`/usr/bin/curl` 存在且为 `755` 的 `aarch64-linux-ohos` ELF，`sh` 里 `command -v curl` 正常；真机 `python3` 位于**用户可写目录** `/storage/Users/currentUser/usr/local/bin/`，平台**从用户可写目录启动的进程会切入受限域、读不到 `/usr/bin`** ⇒ `os.stat('/usr/bin/curl')` 抛 `PermissionError: [Errno 13]`，`shutil.which('curl')` = `None`，`subprocess.run(['curl',…])` 抛 `FileNotFoundError` | 判定为**非阻塞**（脚本随后的 Pre-download 步骤自行降级、源码由 conan 自身下载器取得，`CI_RC=0`、全部闸口 pass），**不改任何配方与源码**；仅把根因与可复现证据写入 `notes.md` §7.6，供其它包的验证脚本参考 |

### 验证命令

```sh
# 1. 真机 conan create（含构建自检 ctest + 消费者用例）—— 本文所有真机数字由它产出
cd ~/runner002/build_in_harmonyos
conan create archives/u/uefitool/0.28.0-a73 \
  -pr:h="$(pwd)/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$(pwd)/ci/conan/profiles/ohos-aarch64" \
  --build="uefitool/*"                # 强制重建本包；实测 rc=0
                                    # 完整日志：$HOME/uefitool-create-final.log（356 行）

# 2. 消费者用例可单独复跑（pkg 路径由 conan 打印，形如 …/p/share/uefitool/guids.csv）
bash archives/u/uefitool/0.28.0-a73/test_package/test.sh <pkg>/share/uefitool/guids.csv
# 期望：--- uefitool consumer: 28 checks run, 0 failed --- / ALL CHECKS PASSED (28/28)

# 3. 本地 CI 模拟（W3，pr.diff 模式；脚本是 #!/usr/bin/zsh，必须用 zsh 跑；
#    用 bash 跑会在 `${+CI_PACKAGES}` 处直接 bad substitution）
JUNK_PR_DIFF="$PWD/pr.diff" CI_PACKAGES=archives/u/uefitool/0.28.0-a73 \
  CI_BRANCH=feat/uefitool-0.28.0-a73 \
  zsh ci/conan/build_and_test.sh
```

---

## 补充说明

- **关联 Issue**：#3770（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3770）—— 路径 C 候选确认申请
  `【高难度挑战】uefitool 0.28.0-a73`
- **分支名**：`feat/uefitool-0.28.0-a73`（逐字照用平台领取任务时给出的分支名）
- **变更范围**：仅 `archives/u/uefitool/` + `knowledge/drafts/`（路径 C 的 PR 范围
  同路径 A，另带知识库草稿）。按平台要求 **PR 只带一个前缀** —— 本 PR 标题前缀为
  **`【高难度挑战】`**（逐字，方括号为标准全角 `【】`，变体符号会被关单）
- **本次变更的文件（21 个，全部为新增）**：
  - `archives/u/uefitool/0.28.0-a73/`（9 个）：`conanfile.py`、`conandata.yml`、`manifest.yaml`、
    `notes.md`、`cmake/CMakeLists.txt`、`test_package/{conanfile.py, test.sh, make_fixture.py, MANIFEST.yml}`
  - `archives/u/uefitool/0.28.0-a73/reports/pr-body.md`（本文）。★ 本文件路径被仓库
    `.gitignore` 的 `reports/` 规则（该规则原意为忽略仓库根目录下每次重新生成的质量报告）
    一并匹配到，故随提交时以 `git add -f` 显式加入 —— 与仓库内**已有的 220 个
    `*/reports/pr-body.md`** 保持一致
  - `archives/u/uefitool/`（3 个，跨版本层）：`README.md`、`manifest.yaml`、`commands.json`
  - `knowledge/drafts/`（8 个）：4 条草稿，每条 `.kv` + `.md` 成对
- **队伍名称**：北京邮电大学 uu小分队

### 关于本包的定位（供审阅时参照）

UEFITool 是 UEFI 固件镜像解析领域最常用的开源工具集。上游构建三个目标，
本包只交付其中**零 Qt 依赖**的两个：

- **`uefiextract`** —— 批量解包：把固件镜像整棵树按结构落盘成目录树，并产出
  可读文本报告（`.report.txt`）、GUID 数据库（`.guids.csv`）与完整 dump
- **`uefifind`** —— 检索：按 GUID 或十六进制 pattern 在镜像内查找，
  支持 `header` / `body` / `all` 三种范围与 `list` / `count` 两种输出
- ~~`UEFITool`（Qt6 GUI）~~ —— 因 OHOS PC 侧 Qt 为 5.15 而不构建（见「补丁说明」）

解析器覆盖面（`common/generated/` 下的专用解析器）：Intel FV/FFS 与 FIT/ACM/KEYM/ACBP、
AMI NVAR、Apple SysF、Dell DVAR、EDK2 VSS/VSS2/FTW、Insyde FDC/FDM、Phoenix FLM/EVSA、
Microsoft SLIC marker/pubkey，以及 Tiano / LZMA / Brotli 三类压缩段解压。

因此本包取 `package_type = "application"`，并按 L0k 在**软件级**目录提供
`archives/u/uefitool/commands.json`（版本目录的父目录），`cpp_info` 只设
`bindirs = ["bin"]`，显式清空 `libdirs` / `includedirs`。
同仓先例：`archives/q/qdl/2.7`、`archives/2/2048.c/1.0.3`。

### 复现性

- 源码 tarball 按 `conandata.yml` 的三源列表书写（官方源第一 + `ghfast.top` +
  `gh-proxy.com` 镜像前缀形态），三路 sha256 一致：`81d9944d…507e`
- 解包根目录 `UEFITool-A73/` 是单根目录，`strip_root=True` 可用
- 固定装置（那 4096 字节的 FFSv2 卷）由 `test_package/make_fixture.py` **纯标准库
  现场生成**，不往仓库塞任何二进制；其校验和按上游 `calculateChecksum16` 的算法
  （`(UINT16)(0x10000 - sum_of_u16_words)`）复刻，且在主机侧逐字节核对过
- 本包**零补丁** ⇒ 不存在补丁应用的可复现性问题
