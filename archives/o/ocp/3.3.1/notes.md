# ocp 3.3.1 适配笔记（HarmonyOS PC / aarch64）

- 软件：ocp（Open Cubic Player）3.3.1
- 上游仓库：https://github.com/mywave82/opencubicplayer
- 源码：`https://github.com/mywave82/opencubicplayer/releases/download/v3.3.1/ocp-3.3.1.tar.gz`
  （sha256 `975a615ad4ef98c4ee03df7238db51199df976e9f9147d73fc971163d57e6a10`，8547765 字节）
- 构建系统：autotools（`configure` + 递归 Makefile）
- 目标平台：HarmonyOS PC，`aarch64-unknown-linux-ohos`，SDK clang 15（libc++ / musl）
- 适配状态：**成功**（`conan create` 全绿，消费者测试 1/1，上游测试 9/9 可运行用例通过）
- 归档：`archives/o/ocp/3.3.1/`

## 1. 依赖清单

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.6 | 必需：UI 基于 curses，`configure` 无它直接中止 |
| zlib | 1.3.2 | 压缩层（对齐 libpng/flac 的 zlib 需求） |
| bzip2 | 1.0.8.2 | bzip2 抽象文件系统层 |
| mad | 0.16.4 | MP3 解码 |
| libogg | 1.3.6 | `override=True`：libvorbis 需要 1.3.6、flac 需要 1.3.5，统一为单一 ogg 运行时 |
| libvorbis | 1.3.7 | Ogg Vorbis 解码 |
| flac | 1.5.0 | FLAC 解码 |
| libpng | 1.6.58.3 | 图形/封面支持 |
| libjpeg-turbo | 3.2.0 | JPEG 解码 |
| game-music-emu | 0.6.5 | 芯片音乐（VGM/SPC 等） |
| alsa-lib | 1.2.16.1 | 音频输出后端 |
| libdiscid | 0.6.5 | CD 识别 |
| cjson | 1.7.19 | 配置/元数据 JSON |
| ancient | 2.3.0 | 解压远古压缩格式（本包 `.pc` 需归一化，见 §4.6） |
| xa（tool_requires） | 2.4.1 | libsidplayfp（playsid）汇编 6502 代码所需 |

依赖二进制预检（W0）：14 个 `requires` + 1 个 `tool_requires` **全部在制品仓可下载**
（`conan download <pkg> -r=ohpcd --only-recipe` 逐个核查，`OK=11 MISS=0` 二进制核查亦通过）。

## 2. 配置与构建参数

```bash
conan create . --build=missing -pr:h ohos-aarch64 -pr:b default
```

- `--host=aarch64-unknown-linux-ohos`：**显式**传入。目的不是绕过交叉编译检测，而是让配方在
  非 HarmonyOS 宿主（CI worker 跑 x86_64 Linux）上也能得到正确的目标三元组——build 三元组由
  `config.guess` 从宿主机器推断。这是上游文档化的交叉编译工作流，与 R1/E007 禁止的
  “用 `--build`/`--host` 伪造结果”不同（见 §9）。
- `--with-x11=no --without-info --without-desktop_file_install
  --without-update-mime-database --without-update-desktop-database`：HarmonyOS PC 无 X11
  与桌面集成。
- **in-source 构建**（`folders.build = "."`）：ocp 的 `configure` 以**相对路径**校验仓库内
  vendored 解码子模块（`playtimidity/timidity-git`、`playqoa/qoa-git` 等），Conan 默认的
  out-of-tree 构建目录会让这些校验失败。
- `make -j1`（R9：Makefile 类配方单并发）。
- `compiler.cppstd` / `compiler.libcxx` 在 `configure()` 中 `rm_safe` 移除（见 §4.3）。

## 3. 补丁清单（`conandata.yml`）

| 补丁 | 内容 | 类型 |
|------|------|------|
| `0001-autotools-ohos-triplet.patch` | 教会仓库自带 `config.guess`/`config.sub` 识别 `aarch64-unknown-linux-ohos`（含 `*:HarmonyOS:*:*`）。不打则 configure 报 “cannot guess build type”（知识条目 **E007**） | portability |
| `0002-configure-ohos-config-status-tmpdir.patch` | 强制 `configure` 走 `mkdir` 回退路径，绕过 `mktemp -d` 快路径（HarmonyOS 上 `mktemp -d` 产出 `drwx--S---` 目录，组不可写 → `subs1.awk: Permission denied`） | portability |
| `0003-ocp-tests-writable-scratch-dir.patch` | 让内置测试程序把 scratch 数据写到构建树内的相对目录 `ocp-test-data/`，替代硬编码 `/tmp/`（HarmonyOS `/tmp` 只读，知识条目 **E002**） | portability |

补丁均为最小可复现改动，不含平台宏（R8）；`0003` 只涉及测试程序，不影响发布产物。

## 4. 遇到的问题与解决

### 4.1 `configure` 无法识别 HarmonyOS 三元组（E007）
`uname -s` 在 HarmonyOS 上返回 `HarmonyOS`，仓库自带（2024 版）`config.guess` 不认识；同时
`config.sub` 的内核列表里也没有 `linux-ohos`。→ 补丁 0001。
> ⚠️ SKILL 脚本 `scripts/patch-autotools-ohos.pl` §2.3 报 `[skip] linux-ohos already present`
> 是**自满足假阳性**：内核列表实际未添加（`linux-uclibc*` 模式在 2024 版 `config.sub` 中已改为
> `linux-uclibc* | linux-mlibc* )`，不匹配），且其校验段用非锚定 `grep` 误判成功。
> 本次手工修正了 `config.sub` 并生成补丁 0001（已作为 SKILL_FEEDBACK 上报）。

### 4.2 `config.status` 生成阶段 `subs1.awk: Permission denied`
HarmonyOS 的 `mktemp -d` 创建目录权限为 `drwx--S---`（组不可写），`configure` 的快路径在临时
目录里放置 `subs1.awk` 后无法让子 shell 读取/执行。→ 补丁 0002（最小改动，令其走 `mkdir`
回退路径）。

### 4.3 `playopl` 用 C 编译器编 C 源却带 C++ 标志
`playopl/Makefile` 的 `adplug_adlibemu.o: adplug-git/src/adlibemu.c` 规则使用
`$(CC) $(LIBADPLUG_CXXFLAGS) $^ -o $@ -c`，于是 clang 收到 `-std=c++14 … -std=c++17` 且目标
是 `.c` → `error: invalid argument '-std=c++17' not allowed with 'C'`。
→ 配方在 `configure()` 中 `rm_safe("compiler.cppstd")` / `rm_safe("compiler.libcxx")`，避免
C++ 专属标志泄漏进 C 编译；各子目录 Makefile 自己会请求所需标准（adplug 用 C++14），
HarmonyOS 工具链默认 `gnu++17` + libc++。

### 4.4 vendored 子模块缺失
纯 tag 归档（codeload）不含子模块，`configure` 硬失败。→ 改用 **release 资产**
`ocp-3.3.1.tar.gz`，其自带 `playtimidity/timidity-git`（465 个文件）等解码子模块。

### 4.5 部分 Makefile 规则不带任何 `-I` / `-L`
`filesel/Makefile` 等有 `$(CC) $< -o $@ -c` 这类规则，依赖系统默认头文件/库搜索路径
（桌面 Linux 上成立，HarmonyOS 不成立）。→ 配方 `generate()` 里把依赖的 `includedirs` /
`libdirs` 同时注入 `CPPFLAGS`/`LDFLAGS`（供 `AC_CHECK_LIB` 等探测）与 `CPATH` /
`LIBRARY_PATH`（供编译/链接全局生效）。

### 4.6 依赖自带 `.pc` 的失效/错误前缀
- `ancient/2.3.0` 的 `libancient.pc` 声明 `prefix=/` → `-I//include`，`<ancient/ancient.hpp>`
  找不到；
- `cjson/1.7.19` 的 `.pc` 里 `includedir` 是**绝对路径**且指向已消失的构建暂存目录。
→ 配方把依赖 `.pc` 归一化后**暂存**一份到 `<generators>/ohos-pkgconfig`，并把该目录放在
`PKG_CONFIG_PATH` 首位（依赖自带的 `.pc` 目录不入 `PKG_CONFIG_PATH`），避免陈旧前缀抢先。

### 4.7 依赖版本冲突
`libvorbis/1.3.7` 需要 `libogg/1.3.6`、`flac/1.5.0` 需要 `libogg/1.3.5` → 配方内
`self.requires("libogg/1.3.6", override=True)` 统一；`zlib` 对齐 libpng/flac 需要的 `1.3.2`。

### 4.8 内置测试写死 `/tmp`（E002）
`filesel/adbmeta-test.c:23`、`filesel/dirdb-test.c:22` 定义
`CFDATAHOMEDIR_OVERRIDE "/tmp/"`，另有 20 处 `/tmp/CPARCMETA.DAT` 字面量。HarmonyOS 挂载
`/tmp` 为只读 → `open(/tmp/...): Read-only file system`，`adbmeta-test` rc=255、
`dirdb-test` SIGSEGV。**被测代码本身无问题**（同样的 `dirdb.c`/`adbmeta.c` 在可写目录下正常）
→ 补丁 0003 把 scratch 位置改为构建树内的相对目录。

## 5. 上游测试结果

上游**没有** `make check` / `ctest`，测试是 10 个独立测试程序。实跑结果：

- **9/9 可运行用例全部通过（100%）**：`adbmeta-test`、`dirdb-test`、
  `filesystem-bzip2-test`、`filesystem-filehandle-cache-test`、`filesystem-gzip-test`、
  `filesystem-tar-test`、`filesystem-textfile-test`、`compat-test`、`utf-16-test`
- 首轮（未打补丁 0003）为 7/10，`adbmeta-test` / `dirdb-test` 因 §4.8 失败，打补丁后转绿
- `filesel/mdb-test` **不可构建**：上游 `filesel/Makefile:441-455` 的规则只把 `mdb-test.c`
  交给链接器（`$(CC) $< -o $@`），缺 `../stuff/utf-8.c` 等对象 →
  `undefined symbol: utf8_encoded_length / utf8_encode / Console / cpiKeyHelp* / framelock`。
  属**上游测试目标自身缺陷**（补对象后会级联出下一批符号），**不做绕过式修补**，如实披露。

详细分项、计量（上游 N → 适配后 M）与证据见 `reports/test-report.md`。

## 6. 消费者测试（test_package）

`conan-init` 生成的 `test.c` 是空壳（只 `printf`），不满足 R34，已重写为**实跑交付物**：

- `fork` + `execv` 执行安装后的 `bin/ocp`，隔离且**绝对路径**的 `HOME`（构建树内临时目录，
  规避只读 `/tmp`）；
- 断言播放器自身的配置诊断（`Global ocp.ini not found`）——只有前端真正启动、加载器解析完
  全部依赖共享库并进入 `main()` 才可能出现；
- `poll()` 排空子进程输出至 EOF（不提前关管道，避免 SIGPIPE 误判），30s 宽限 + `SIGKILL` 兜底；
- 交叉编译宿主无法执行目标二进制时（`ENOEXEC`）回退为校验产物是合法 aarch64 ELF
  （`e_machine=183`），避免环境性误报失败。

## 7. 复现步骤

```bash
# 干净源码 + 配方全流程（W3）
conan create . --build=missing -pr:h ohos-aarch64 -pr:b default

# 上游测试（补丁 0003 后）
mkdir -p filesel/ocp-test-data
cd filesel && ./adbmeta-test && ./dirdb-test && ./filesystem-*-test
cd ../stuff && ./compat-test && ./utf-16-test
```

## 8. 知识图谱关联

- **E002**（`/tmp` 只读）：本次适配中两处命中——补丁 0003（上游测试 scratch）与消费者测试的
  `HOME`/`TMPDIR` 隔离。二者均在 E002 覆盖范围内，**未发现现有知识无法支撑的新共性缺口**。
- **E007**（autotools 三元组）：补丁 0001 属该条目的既有处置范式（`config.guess`/`config.sub`
  补丁，禁用 `--build`/`--host` 伪造手段）。
- 补充观察（未达新建条目门槛，记录备查）：`mktemp -d` 在 HarmonyOS 上产出
  `drwx--S---` 目录、令依赖 `mktemp` 临时目录可写性的 configure 快路径失败（补丁 0002）。

## 9. 注意事项与风险

- **不要**把 `--host=aarch64-unknown-linux-ohos` 理解为 R1/E007 所禁止的参数绕过：此处传的是
  **正确的目标三元组**，且 `config.guess`/`config.sub` 已先经补丁 0001 教会 HarmonyOS；
  `configure` 仍按正常 autotools 交叉编译流程生成 `config.h`（未跳过 `AC_RUN_IFELSE` 语义）。
- in-source 构建是本包的硬约束（子模块相对路径校验），后续上游版本若改为绝对路径校验可再评估。
- `--build=missing` 不应用于依赖缺口：本包依赖已全部发布（W0 已核查），CI 上应全部走预编译。
- HarmonyOS 目标机 `/tmp` 只读：任何在本包目录内新增的脚本/测试都不得写死 `/tmp`。

## 10. 对话记录与决策

| 决策 | 结论 | 依据 |
|------|------|------|
| 源选择 | release 资产 `ocp-3.3.1.tar.gz`（非 codeload tag 归档） | release 资产自带 vendored 子模块；tag 归档缺子模块致 configure 硬失败 |
| 构建方式 | in-source（`folders.build = "."`） | ocp `configure` 以相对路径校验子模块 |
| C++ 标志误用修法 | 配方层 `rm_safe("compiler.cppstd"/"compiler.libcxx")`，而非改上游 Makefile | 问题源于工具链标志泄漏，配方可消除；改上游 Makefile 会扩大补丁面 |
| 三元组处置 | 补丁 `config.guess`/`config.sub` + 显式 `--host` | E007 范式；显式 `--host` 为上游文档化的交叉编译工作流，保证 x86_64 CI 宿主同样可构建 |
| `mdb-test` 不可构建 | **不做**绕过式修补，仅在 notes/报告中如实披露 | 上游测试目标自身链接缺陷；补对象会级联出下一批缺失符号，属绕过而非适配 |
| 补丁 0002 形态 | 最小改动令 `configure` 走 `mkdir` 回退路径 | 保留 `mktemp` 快路径语义，避免大范围改写 `configure` |
| 定档 | **【积分赛】**（库适配为主，知识库已被 E002/E007 覆盖，无新共性缺口） | 适配全程由现有知识图谱支撑；`/tmp` 只读命中 E002、三元组命中 E007，均属既有条目覆盖范围 |
| 消费者测试 | 重写为实跑 `bin/ocp` 的实质测试 | R34/PF3：应用类包的空壳 print-only 测试不构成验证 |
---

**编译结束**: 2026-10-02 11:38
**最终状态**: published
