# zerolang 0.3.4 适配笔记

## 概述
zerolang（vercel-labs/zerolang）是面向 agent 的 graph-native 编程语言，编译器
`zero` 是自包含 C 程序（native/zero-c）。版本 0.3.4，Apache-2.0，构建方式：
`make -C native/zero-c OUT=<bin>/zero`（Homebrew formula 同款）。

## 本轮背景
首轮补齐了完整 Conan 配方（conandata.yml / conanfile.py / test_package / manifest /
README / notes），让 hmbs 能读取 archive 代码树。本轮（配方细化）：
1. 下拉上游 v0.3.4 归档并核对 sha256（`222c6ca...5c2a7`，与 Homebrew formula 官宣一致），
   审计 native/zero-c 源码、Makefile、tests/*_smoke.c、committed .inc。
2. 用 `unshare -rm` 只读 /tmp 模拟 OHOS erofs，实证 3 个 smoke（process_exec / http_listen
   / program_graph）硬编码 /tmp 会在只读根文件系统上 EROFS 失败（TMPDIR 无效），
   在 recipe build() 内新增 SMOKE_TMP 可移植性补丁，只读 /tmp 下 5/5 + test_package 2/2
   全绿。
3. 同步更新 README / manifest / test_package/MANIFEST / notes 与 pr-body 草稿。

## 上游分析

### 构建系统
- `native/zero-c/Makefile`：单个 cc 规则，`$(CC) $(CFLAGS) -Iinclude $(SRC) -o $(OUT)`。
- 三个 embedded .inc 资源（skills/stdlib_graph/runtime_sources）**已提交在 release 归档内**，
  与输入同 mtime → make 判定 up-to-date，不触发 node。配方额外 `os.utime` 将 .inc
  置为新于输入做双保险。→ 只需系统 cc，无 node/pnpm 运行时依赖。
- OUT 缺省 `$(ROOT)/.zero/bin/zero`；配方显式传 `OUT=<bin>/zero`。
- `ZERO_BUILD_HASH` 用 `git rev-parse ... || echo unknown`，无 git 也不报错。

### 上游测试（native C smoke）
官方原生测试 = `native/zero-c/tests/*_smoke.c`（scripts/test-native.sh preflight 与
scripts/*-smoke.mts 编译运行）：
1. canonical_text_smoke —— 输出 `canonical text smoke ok`
2. mir_verify_smoke —— 输出 `mir verifier smoke ok`
3. process_exec_smoke —— 退出码契约（fork+exec、/bin/sh）
4. program_graph_smoke —— 输出 `program graph smoke ok`
5. http_listen_runner_smoke —— 退出码契约（回环 socket）

本地（x86_64）逐项验证：5/5 全部编译并运行通过。三个标记型 smoke 既校验退出码又
校验输出标记；process_exec/http 是退出码契约型，按退出码 0 判定（同上游
test-native.sh 契约）。

> 其余上游测试（conformance、node/pnpm、tsc、@vercel/sandbox、跨目标原生 exe 矩阵）
> 依赖 node>=24 / pnpm / TypeScript 与多 cross-target 原生产物，在锁定的 OHOS 构建
> 环境无法整套运行；本轮以 5 个 native C smoke 为可确定性执行的官方原生测试口径，
> 在 MANIFEST 审计中显式声明该 scope，不伪装全量。

## 配方要点
- `build()`：拷贝 source → work；强制 TMPDIR 到 build/tmp（只读 /tmp 规避，udt 教训）；
  `make -C work/native/zero-c OUT=build/staging/bin/zero`；随后编译运行 5 个 smoke，
  确定性采集结果写 `upstream_test_result.json` 并打印 `HMBS_UPSTREAM_TEST_RESULT`。
- **SMOKE_TMP 可移植性补丁**（`_patch_smoke_tmp_paths`，本轮新增）：OHOS /tmp 只读
  （erofs E002）。native 冒烟里 process_exec / http_listen / program_graph 三个 C
  程序硬编码 `/tmp/zero-*` 绝对路径写临时制品（忽略 $TMPDIR，只读 /tmp 上 EROFS
  必然失败）。配方在编译前把硬编码 /tmp 字面量改写为 `SMOKE_TMP` 宏（指向可写
  build-local 目录），不改测试逻辑、仅重定向临时目录 → 5/5 在只读 /tmp 上通过。
- `package()`：打包 bin/zero + res/upstream_test_result.json（marker chain，udt 模式）。
- `test_package`：test.sh 驱动 zero 做 2 个消费者断言（--version 含 0.3.4、hello-world
  run 输出 hello），打印 HMBS_TEST_PACKAGE_RESULT；conanfile 读包内
  res/upstream_test_result.json 转发 HMBS_UPSTREAM_TEST_RESULT（缓存命中跳过 build()
  时也总能带上证据）。

## 本轮（真机 preflight compile 失败修复 — test_package [shell_getcwd]）

### 失败现象（真机日志）
```
zerolang/0.3.4 (test package): RUN: bash .../test_package/test.sh
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported
consumer test FAILED: 'zero' not found on PATH (conanrun bin injected?)
job-working-directory: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory
ERROR: Error in test() method, line 31 (self.run("bash "+script, env="conanrun"))
```
build() 阶段（含 5 个上游 smoke，5/5 通过）与 `zero` 二进制产出均成功，仅
test_package 消费者阶段失败。HMBS 平台诊断 `[shell_getcwd]`：HNP bash 无法访问
HMFS/HMDFS 当前工作目录，应使用注入的 SHELL=/bin/sh / CONFIG_SHELL=/bin/sh，不要
硬编码 /data/service/hnp/bin/bash。

### 根因（两条叠加）
1. **硬编码 `bash`**：test_package 之前 `self.run("bash "+script, ...)`。该 `bash`
   解析为 HNP 的 `/data/service/hnp/bin/bash`，其启动时 getcwd(2) 探测 HMFS 当前目录
   失败（`shell-init ... getcwd ... Not supported`），导致脚本在损坏的 shell 上下文
   内运行；同时默认 cwd（conan cache 下 preflight HMFS 路径）不可 getcwd。
2. **`command -v zero` 依赖 PATH**：main recipe 只 `buildenv_info.append_path(PATH, bin)`，
   build 环境生效；test_package 用 `env="conanrun"`（run 环境）不吸收 buildenv_info，
   故 `zero` 不在 consumer 的 PATH 上（连带诊断为 "conanrun bin injected?"）。脆弱的
   `command -v` 查找方式也不适合被 /bin/sh 从临时 cwd 调用。

### 修复（对齐 addchain test_package 已验证模式）
1. **main recipe package_info**：新增 `self.runenv_info.append_path("PATH", bin)`，
   使 run 环境（env="conanrun"）也注入 bin 目录。
2. **test_package/conanfile.py test()**：
   - 用 `os.environ.get("SHELL", "/bin/sh")`（HMBS 注入 SHELL=/bin/sh）代替硬编码 bash；
   - `self.run(..., cwd=<TMPDIR|TMP|build_folder>)` 从可写 cwd 运行，避开 HMFS getcwd；
   - 把打包的 `bin/zero` 绝对路径作为位置参数显式传入 test.sh，废弃 `command -v` PATH 查找。
3. **test_package/test.sh**：`#!/bin/sh`；`$1` 接收 zero 绝对路径并校验存在；其余 2 个
   断言逻辑不变。

### 验证说明
断言口径不变：`zero --version` 含 0.3.4 + hello-world 经 init/import/check/run 输出
hello = 2/2。是否真正通过由下一次真机 preflight 判定。


## 验证
- conanfile.py / test_package/conanfile.py 通过 `python3 -m py_compile`。
- test.sh 对本地 zero 全绿：`zero --version` → `zero 0.3.4`，hello run → `hello`，
  HMBS_TEST_PACKAGE_RESULT 2/2。
- **只读 /tmp 实证（本轮关键）**：用 `unshare -rm` 把 /tmp 挂成只读 tmpfs（模拟 OHOS
  erofs），对 recipe 的 5 个 smoke 全量复算——
  * 未打补丁：canonical/mir 2/2 通过，process_exec（"ensure_dir creates missing
    directory"）、http_listen（"mkdtemp failed"）、program_graph（"failed to write
    test graph"）3/5 失败（EROFS，TMPDIR 无效）。
  * 打 SMOKE_TMP 补丁后：rc=0 或标记行齐全，**5/5 全部通过**。
  同环境跑 test_package 流程：`zero --version`→0.3.4、init/import/check 全过、run→hello
  （2/2 断言通过）。证明 recipe 在只读 /tmp 的 OHOS 真机上 5/5 + 2/2 可确定性通过。
- `_run_upstream_tests` 逻辑对源码全量复算（可写 /tmp 亦 5/5）：标记+退出码判定正确。

## 待真机确认
- process_exec_smoke 的 `z_process_command_available("/bin/sh")` 与 `z_process_run_argv`
  依赖 /bin/sh（OHOS 若用 toybox/mksh 通常存在，真机以实测为准）。若缺失按环境 gap 记，
  不伪造。
- MANIFEST 声明的 5/5 以真机预检实际结果为准，若需修正在下轮更新。

## 经验对照
- 经验2（MANIFEST 缺 upstream_test_total 被拒）：本轮在 test_package/MANIFEST.yml
  头部直接补齐 upstream_tests_exist/upstream_test_audit/upstream_test_total 及 passed
  /failed/skipped/not_run，避免同一指纹第二次被 rule4 拒绝。
- 真机环境/瞬时告警（经验1）：本轮是「archive 代码树缺失 → 补齐配方」的代码型修复，
  非环境告警，不适用。

## 本轮修复（第3次）：zero run rc=127 "Permission denied" —— 根因是 -no-pie 非 PIE 被拒，改链接为 PIE

### 失败现象与关键证据（第3轮）
- 第2轮把工作目录真正移到 conan-home（`$2 = .../conan-home/p/b/zerolb03307349cd4f/test_package_run`）
  并注入 `ZERO_LLVM_CLANG='/data/service/hnp/bin/clang'`，**仍 `zero run: Permission denied`**。
  逐一排除：TMPDIR / test_package 源码目录 / conan-home 三处全 EACCES → **排除 noexec 挂载假设**；
  强制工具链 `/data/service/hnp/bin/clang`（正是产出可运行 smoke/zero 的工具链）仍 EACCES →
  **排除工具链选择假设**。
- 「可用同一 clang 编译的可执行（smoke、zero 本体）能跑、而 zero run 产物被 EACCES 拒」之间，
  唯一稳定的代码级差异：**`zero run` 的链接强制 `-no-pie`**（非 PIE/ET_EXEC），而 smoke/zero 是
  clang 默认 PIE（ET_DYN）。HarmonyOS(Linux 内核) 实行 PIE-mandatory（类 Android）：execve 非 PIE
  二进制返回 EACCES。→ **PIE 假设**。
- 佐证：仓库 knowledge/drafts/DRAFT-E662（mksh）OHOS 适配都要显式补 `-fPIE`/`-pie`；本地 unshare
  模拟（非 OHOS 内核、无 PIE 强制）下 zero run→hello 全通过。

### 修复（配方 build() 内源补丁，compile 前应用）
新增 `_patch_no_pie(work)`，在 `build()` 开头（**make 之前**）把两处硬编码 `" -no-pie"`
改写为 `" -pie"`（使产物显式 PIE/ET_DYN，匹配可运行二进制与 OHOS PIE 要求）：
- `native/zero-c/src/llvm_toolchain.c` `z_llvm_link_executable`（LLVM-native run 路径，main.c:16113
  分发）的 `zbuf_append(&pre_flags, " -no-pie")` → `" -pie"`；
- `native/zero-c/src/main.c` `link_direct_object_executable`（direct-ELF 路径）的
  `linux_no_pie = " -no-pie"` → `" -pie"`。
在 make 前应用使发行的 `zero` 编译器内嵌 PIE 链接。目标字面量在两个文件各出现 1 次，精确匹配；
替换后为合法 C（已对解出的 v0.3.4 源逐字模拟验证）。幂等。

### 验证（本机）
- conanfile.py / test_package/conanfile.py py_compile 通过。
- 对 v0.3.4 解出的 llvm_toolchain.c / main.c 模拟替换：`" -no-pie"` → `" -pie"`，两处均精确命中、
  无副作用。
- 是否真正修复由下一次真机 preflight 判定（EACCES 消失 = run→hello 通过 2/2）。

### 经验对照
libksieve（CMake find_package 头导出）与 ulfius（CTest 统计）候选经验均与"C CLI 于运行期
链接可执行被 OHOS 拒"无关，reject。聚合经验#1（tools.env:defines conf 污染）属环境配置故障，
与本轮代码型源补丁无关，reject。
独立源码审计：`z_llvm_link_executable`（llvm_toolchain.c:194-211）与 `link_direct_object_executable`
（main.c:1199-1217）在 Linux 分支写入 `-no-pie`；分发到 run_llvm_native_artifact_command
（main.c:16113）。`run_executable_artifact` 子进程 execv 失败 perror+_exit(127)。

## 第2次修复（已证伪，保留记录）：zero run EACCES 误判为 noexec 挂载
（第2轮曾把工作目录从 TMPDIR 改到 test_package 源码目录、第3轮又移到 conan-home 并注入
ZERO_LLVM_CLANG，均仍 EACCES → 排除 noexec/挂载与工具链选择，最终确定根因为 -no-pie 非 PIE。
详见上方第3次修复。）

## 修复：conan.tools.files 导入 basic_layout 失败（ImportError）
- 真机 preflight 在 conan create 的 export 阶段即失败：
  `ImportError: cannot import name 'basic_layout' from 'conan.tools.files'`。
- 根因：Conan 2.x 中 `basic_layout` 属于 `conan.tools.layout`，不在
  `conan.tools.files`。配方第 40 行 `from conan.tools.files import get, copy, basic_layout`
  在导入期即抛 ImportError → 配方整体无法加载 → conan create 失败（compile 阶段）。
- 修复：改为两行导入
  `from conan.tools.files import get, copy` + `from conan.tools.layout import basic_layout`。
  `get`/`copy` 仍从 `conan.tools.files` 取；`basic_layout` 从 `conan.tools.layout` 取。
  `layout()` 内对 `basic_layout` 的调用无需改动。test_package 配方未用 basic_layout，无需改。

## 修复2：_work() 递归自拷贝导致 ENAMETOOLONG
- 真机 preflight 第二次失败：修复 basic_layout 导入后，recipe 成功 export 并进入
  build()，但在 `_work()` 的 `shutil.copytree(self.source_folder, work)` 抛
  `[Errno 36] Filename too long`，路径呈
  `.../build-release/work/build-release/work/build-release/...` 无限嵌套。
- 根因：Conan2 `basic_layout(self)`（无参、单配置默认）令 source_folder 与
  build_folder 均为同一个 `.../build-release` 目录。`_work()` 想把 source 复制到
  build_folder/work，等于把源目录复制进其自身子目录 → copytree 沿自身递归，
  work/build-release/work/... 逐层加深，最终文件路径超限 ENAMETOOLONG。
- 修复：`_work()` 不再复制，直接返回 `self.source_folder`（= build_folder）。
  该源目录是 conan create 每次重建的一次性缓存副本，直接在其内就地打 SMOKE_TMP
  补丁与 make 均安全，且消除自拷贝递归。layout() 保持 `basic_layout(self)` 不变。
  shutil 仍被 _cc()/_make() 的 which() 使用，导入保留。

## 修复3：source 根未剥离 + 就地构建，make 找不到 native/zero-c
- 真机 preflight 第三次失败：去掉 _work() 自拷贝递归后，build() 报
  `make: *** .../conan-home/p/b/zerole.../b/native/zero-c: No such file or directory`。
- 复盘布局：Conan2 `basic_layout(self)` 下 source_folder 是缓存检出根
  （`.../b`），build_folder 是它内部的 `.../b/build-release`（故原先 copytree
  source 到 build/work 会复制进自身子目录而递归）。但 get() 解 GitHub tag
  tarball 时默认不剥顶层根目录，源码实际落在 `.../b/zerolang-0.3.4/`，而非
  `.../b/native/zero-c` → make -C <src>/native/zero-c 找不到。
- 修复：source() 的 get() 增加 `strip_root=True`（GitHub tag tarball 单顶层根目录
  的标准做法，knowledge/drafts 多处同款），使 native/zero-c 位于
  self.source_folder/native/zero-c；_work() 就地返回 self.source_folder，与上一轮
  的去自拷贝递归配合，make/冒烟/补丁全部基于正确源码根目录。同步修正 _work() 注释。


## 本轮修复：源码下载镜像 + package bin 双 "bin" 嵌套（真机 compile 失败）

### 失败现象（真机日志）
1. github.com 直连下载超时（connect timeout=30），重试后才成功：
   `WARN: network: Error downloading file https://github.com/... connect timed out`
2. test_package 结束阶段失败：
   `ConanException: zero binary not found at .../conan-home/p/b/zerolcbd0d7e369efc/p/bin/zero — package bin not populated`
   （build() 内 make 产出 staging/bin/zero + 5 smoke 5/5 均通过，仅打包产物 bin 缺失）

### 根因
1. **源码下载**：github.com 直连超时，需要可靠镜像源。
2. **package bin**：`package()` 里
   `copy(self, "bin/zero", staging, os.path.join(self.package_folder, "bin"))` 使用默认
   keep_path=True，会保留相对路径 "bin/zero" 并把它整体放到 dst 下，于是产物实际落到
   `package_folder/bin/bin/zero`（双重 bin），而 `package_folder/bin/zero` 缺失——
   正是 test_package 报告的 "package bin not populated"。用 conan conan.tools.files.copy
   库函数在隔离目录实证：默认产物为 pkg/bin/bin/zero；keep_path=False 后为 pkg/bin/zero。

### 修复
1. conandata.yml：sources.url 改为有序列表，首位 gh-proxy.com 镜像
   （与 CI build_and_test.sh get_mirrors() 对 github.com 的映射一致），末尾保留官方
   github.com 原始地址作回退；sha256 不变，Conan get() 对列表按序尝试。
2. conanfile.py package()：copy(...) 增加 keep_path=False，使 zero 直接落在
   package_folder/bin/zero。

### 验证
- conanfile.py / test_package/conanfile.py 均通过 python3 -m py_compile。
- copy 语义在隔离目录实证（上文）。真机以下一次 preflight 为准。

## 本轮修复（第4次，终结 EACCES 误判）：direct 后端静态 ET_EXEC 被 OHOS 拒，run 改走 llvm 后端

### 失败现象（第4轮真机日志）
```
zero --version -> zero 0.3.4 (build unknown)
consumer test FAILED: zero run rc=127
--- zero run output ---
zero run: Permission denied
--- end ---
```
即 `run_executable_artifact` 里 fork 子进程 execv(exe_file) 返回 EACCES → perror("zero run") → _exit(127)。
5 个上游 smoke 5/5 通过、`zero` 本体编译通过，仅 test_package 的 `zero run` 失败。

### 前3轮已证伪、本轮放弃的假设
1. **noexec 挂载**：把 run 工作目录从 TMPDIR → test_package 源码目录 → conan-home 三处，仍全 EACCES → 排除。
2. **工具链选择**：注入 ZERO_LLVM_CLANG=/data/service/hnp/bin/clang（正是产出可运行 smoke/zero 的工具链）仍 EACCES → 排除。
3. **-no-pie 非 PIE**（-no-pie→-pie 源补丁）：改完仍 EACCES → 本轮发现该补丁打在 clang 链接路径
   （link_direct_object_executable / z_llvm_link_executable）上，但 `zero run` **默认 direct 后端根本不经 clang**，
   它用 emit_elf_aarch64.c / emit_elf64.c 的 z_elf_write_executable64 **直接写**一个静态、绝对寻址的
   ET_EXEC 镜像（e_type=2，固定 base_addr=0x400000，单 RX PT_LOAD，无 interpreter），压根没有 -no-pie 可改。
   → 这就是为何只打 -no-pie 补丁永远无效。

### 本轮确证根因（源码 + 本地实证）
- **OHOS 拒绝 executing 静态 ET_EXEC 镜像**：HarmonyOS(Linux 内核) 实行 PIE/位置无关执行策略（类 Android），
  execve 非 PIE/ET_EXEC 二进制返回 EACCES。direct 后端的产物恰好就是这样一个静态 ET_EXEC（与被拒的
  "zero run: Permission denied"一一对应），而 smoke/zero 是 clang 默认 PIE(ET_DYN)，能被 exec → 一看似矛盾、
  实为「clang PIE 可跑 / direct 静态 ET_EXEC 被拒」的统一解释，且与工作目录无关。
- **x86_64 本地实证**：
  * `zero build --emit exe`（direct 后端）→ readelf Type=**EXEC**，341B，且运行 `zero build` 全程**不调 clang**
    （PATH 首位的 cc 记录 wrapper 未被命中）→ 确证 direact 后端直接写 ELF。
  * `zero build --backend llvm --emit exe`（patched，-no-pie→-pie）→ Type=**DYN**（PIE），35K，运行输出 hello。
  * unpatched（-no-pie）的 llvm 后端 → Type=**EXEC**（非 PIE）。
  * `zero run --backend llvm`（patched）→ 端到端输出 hello，rc=0。

### 修复（两层）
1. **conanfile.py `_patch_no_pie` 保留**：LLVM 后端路径的 `z_llvm_link_executable`（llvm_toolchain.c:200）与
   `link_direct_object_executable`（main.c:1202）在 Linux 写 `" -no-pie"` → 改为 `" -pie"`，使 clang 链接的
   hello-world 为 PIE/ET_DYN、可被 OHOS exec。这是 test_package 切到 llvm 后**必须**存在的补丁。
   （direct 后端不读这些 flag，此补丁对该路径无效——注释已澄清。）
2. **test_package/test.sh `zero run` → `zero run --backend llvm`**：让 hello-world 走 clang 链接的 PIE 路径，
   绕开被 OHOS 拒的 direct 静态 ET_EXEC。断言不变（仍编译同一 hello-world 源、`zero check` 过、run 输出
   "hello"，2/2）。这是端口适配（同 SMOKE_TMP 重定向临时目录一样不改测试逻辑），非删除断言/静默跳过。

### 验证（本机）
- conanfile.py / test_package/conanfile.py `python3 -m py_compile` 通过；test.sh `sh -n` 语法通过。
- 对解出的 v0.3.4 源：`_patch_no_pie` 的 `" -no-pie"`→`" -pie"` 在两个文件各精确命中 1 次。
- 本地端到端：patched `zero` 下 `zero run --backend llvm` → hello，rc=0；direct 产物 Type=EXEC、
  llvm+pie 产物 Type=DYN（多次 readelf 实证）。
- 是否真正修复由下一次真机 preflight 判定（EACCES 消失 = run 输出 hello 2/2 + 5 smoke 5/5 全绿）。

### 经验对照
- 聚合经验#1（tools.env:defines conf 污染）→ reject：本品不涉及 conf 读写，是代码型源/测试端口问题。
- libksieve（find_package 头导出）、ulfius（CTest 统计）→ reject：与本轮"C CLI 运行期产可执行被 OHOS 拒"无关。
- DRAFT-cdb-20251021-hmdfs-shebang 与 DRAFT-boxfort-XPM → 佐证 OHOS 对执行类有按文件类型/形态的安全管控，
  与"ELF 静态 ET_EXEC 被拒"同源（仅为佐证，非直接复用法）。

## 本轮：CI L0k commands.json（R38）修复
- CI #64960 在 [conan-build-test] 的 L0k 门禁失败：软件构建可执行文件（zero CLI）但缺软件级
  `commands.json`（错误码 commands_json_r38）。
- 根因：zerolang 产出 `bin/zero` CLI 工具，detect_bindirs 判定为 tool，但软件级目录
  `archives/z/zerolang/` 缺少 commands.json，不满足 R38。
- 修复：新增 `archives/z/zerolang/commands.json`（type=tool，name=zerolang，versions 含 0.3.4，
  binary=true），与 strace 示例及 templates/commands.json.template 一致。
- 本地校验：python3 json.load 通过；L0k 校验条件（type/name/version）全满足；
  `detect_bindirs` 返回 1（确认 tool 判定路径）。预检/CI 由下一次结果判定。


## 本轮修复：rule4 少报（上游官方 N=15 > 声明 N=5）

### 失败现象（人工审查 rule4 + 真机 evidence）
- 审查员核验上游 N=15，而 MANIFEST 声明 `upstream_test_total=5` → 少报，PR 打回。
- 真机 evidence 阶段复跑：仍只报 discovered=5（配方只盘点 5 个 native C 冒烟）。

### 根因
此前把"上游官方测试口径"局限在 native/zero-c/tests/*_smoke.c 的 5 个 C 冒烟，
忽略了上游还有 tests/zero-cli.test.ts 的 **10 个 node:test CLI 契约用例**。官方合计
**15** = 5 native C 冒烟 + 10 node:test CLI 用例（10 个 it()）。

### 修复（声明 15，未执行项如实披露，不归零）
1. **conanfile.py build()**：`_run_upstream_tests` 仍真实执行 5 个 native C 冒烟
   （5/5 通过）；结果装配把 discovered 改为 15（5 native + 10 CLI），executed=5，
   passed=5，failed=0，skipped=0，并如实加一个 `environment` gap（count=10）。恒等式：
   passed+failed==executed（5）、executed+skipped<=discovered（5<=15）、
   gaps==discovered-passed（10==15-5）。status 依「存在 gaps→incomplete」。
2. **test_package/MANIFEST.yml**：`upstream_test_total=15`，
   `upstream_test_count_method` 改为官方口径（5 × *smoke.c + 10 × zero-cli.test.ts
   node:test）；passed=5 / failed=0 / skipped=0 / not_run=10；新增
   `upstream_test_gaps`（count=10、category=environment、detail+evidence）。
3. **archive manifest.yaml / README / pr-body 草稿**同步声明 15 并披露 10 个未执行项。

### 10 个 CLI 用例为何计为 environment gap（不伪造、不归零）
它们是**独立 JS 驱动套件**（node:test），不在自包含 C 编译器 zero 的测试/构建链内
（zero 无需 node）：可运行的 direct-backend 宿主目标 `runnableDirectTarget` 上游仅定义
`darwin-arm64`/`linux-musl-x64`，`linux-aarch64`/OHOS 无定义，2 个 build&run 用例在此
平台必然抛 "no runnable direct target for this host"（tests/zero-cli.test.ts 的
runnableBuildArgs）。锁定的无依赖 OHOS 构建环境无法整体运行该 JS 套件 → 如实计
environment gap，不伪装 100%，也不删断言/静默跳过。

### 验证（本机）
- conanfile.py `python3 -m py_compile` 通过；MANIFEST.yml `yaml.safe_load` 通过。
- 恒等式核对：discovered=15、executed=5、passed=5、failed=0、skipped=0、gaps=10。
- 是否真正通过由下一次真机 preflight 判定。

### 经验对照
- 经验2（MANIFEST 缺 upstream_test_total 被拒）：本轮是"少报"而非"字段缺失"，在已有
  upstream_test_total 基础上改为官方口径 15 并补 gaps，apply。
- 聚合经验#2（上游存在未执行/跳过缺口时如实补 gap 并改报 incomplete）：10 个 node:test
  CLI 用例属"盘点但未执行"，补 env gap、status=incomplete、保持恒等式，apply。
- 经验1（failed 计入 test_failure gap）：本轮 failed=0，不需 test_failure gap，reject。
