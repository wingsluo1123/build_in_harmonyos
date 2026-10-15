# DRAFT-zerolang-0.3.4-pie-mandatory-exec-refusal-for-et-exec

> HarmonyOS PIE-mandatory 拒绝对 ET_EXEC/非 PIE 镜像 exec，修复切换产 PIE 后端或对链接命令打 `-pie` 补丁，并依 noexec 挂载语义选择可执行产物 cwd

## 问题特征（真实日志片段/标记）

- 真机 preflight test_package 阶段 `zero run` 反复返回 rc=127：
  - `zero --version` 通过、`init/import/check` 通过，唯独端到端 `zero run` 失败
  - 真机日志明确输出 `zero run: Permission denied`（execv EACCES→子进程 `_exit(127)`→rc=127）
- build() 内 5 个 native C smoke 全部通过：
  `HMBS_UPSTREAM_TEST_RESULT={"status": "passed", ..., "discovered": 5, "executed": 5, "passed": 5, ...}`
- 现象与快速排除对应关系：
  - 迁移 cwd 到 conan-home 可执行挂载后仍 `Permission denied` → 排除单纯 noexec 挂载
  - 注入 `ZERO_LLVM_CLANG`（clang 默认 PIE/ET_DYN）后仍 `Permission denied` → 排除工具链选择
- 本地实证：direct 产物 `readelf Type=EXEC`（341B）且全程不调用 cc；`--backend llvm`+`-pie` 产物 `Type=DYN`（PIE，35K）并运行输出 "hello"
- 环境上下文：`HMBS_PLATFORM_CAPABILITIES{"tmpdir": ".../preflight/clients/.../runtime/zerolang-0.3.4/tmp"}`（HMBS 注入的 scratch tmpdir）、`HMBS_CMAKE=/data/service/hnp/bin/cmake`、`HMBS_PYTHON3=/storage/Users/currentUser/usr/local/bin/python3`

## 根因

HarmonyOS（类 Android 的 Linux 内核）实行 **PIE-mandatory**：内核拒绝 exec 非 PIE/ET_EXEC 镜像，execve 返回 **EACCES**。

zerolang `zero run` 的**默认 direct 后端根本不经过 clang**：它用 `emit_elf_aarch64.c`/`emit_elf64.c` 的 `z_elf_write_executable64` **直接写**一个静态、绝对寻址的 **ET_EXEC** 镜像（e_type=2、base_addr=0x400000、单 RX PT_LOAD、无 interpreter）。OHOS 拒绝 exec 这种非 PIE 镜像，返回 EACCES，子进程 `_exit(127)`。

前置 3 轮打的 `-no-pie`→`-pie` 补丁恰好打在 **clang 链接路径**（`link_direct_object_executable`/`z_llvm_link_executable`）上，而 direct 后端不走这条路径——这就是只打 PIE 补丁永远无效的原因。必须先甄别可执行产物实际由哪条后端/路径产出，再决定修复方向。

## 修复方案（rec）（编号步骤，含具体文件与命令）

1. **甄别后端**：确认 `zero run` 产物实际走 direct-ELF（无 cc 调用、Type=EXEC）还是 LLVM 链接路径。
2. **conanfile.py 新增 `_patch_no_pie()`**：在 `build()` 开头（make 之前）把 `llvm_toolchain.c` 与 `main.c` 两处 `" -no-pie"` 改写为 `" -pie"`，使 `--backend llvm` 的 clang 链接产物为 PIE/ET_DYN（该补丁必须保留）。
3. **test_package/test.sh**：`zero run` → `zero run --backend llvm`，让 hello-world 走 clang 链接的 PIE 路径，绕开被 OHOS 拒的 direct 静态 ET_EXEC；2/2 断言不变（编译同一 hello-world 源、check 过、run 输出 "hello"），属后端选择的端口适配，非删除断言/静默跳过。
4. **test_package/conanfile.py**：`ZERO_LLVM_CLANG` 解析对齐 `_cc()`（conf→PATH cc→clang）并 `import shutil`，保证真机上 LLVM 后端能定位 clang。
5. **可执行 cwd 选择（辅助/兜底）**：consumer 工作目录从 noexec scratch（如 HMBS 注入 tmpdir）移到可执行挂载（如 `conan-home/p/b/<pkg_id>/test_package_run/`，与 5 个 smoke 成功的 conan cache 同棵可执行子树）；`access(X_OK)` 看不穿 noexec，须以 `execve` 的 EACCES 为准。

真机验证：`zero run --backend llvm` 输出 hello（2/2 断言）+ 5 上游 smoke 5/5 全绿，门禁通过。

## 禁止策略

- **禁止** 把 non-PIE 执行镜像 EACCES 误判为 noexec 挂载或工具链问题，仅迁移 cwd/换 clang 却保留错误的 ET_EXEC 字节码。
- **禁止** 打着 "-no-pie→-pie" 补丁却只命中 clang 链接路径、对 direct 后端无效后仍判通过。
- **禁止** 删除/静默跳过 `zero run` 断言或把 2/2 改少来掩盖 EACCES；后端选择属合法端口适配，不得归零证据。
- **禁止** 零证据放行：上游存在测试时必须真实发现并执行（5 smoke 5/5），`HMBS_UPSTREAM_TEST_RESULT` 保留真实值。

## 与相近条目的边界（查重）

- 本条目与既有多轮修复经验（Conan `basic_layout` 导入位置、`get()` `strip_root`、`package()` `keep_path` 双 bin 嵌套、镜像下载、`test_package` 消费者 PATH/`[shell_getcwd]`）**只共享环境/证据关键词**（`HMBS_UPSTREAM_TEST_RESULT`、`readonly_tmp`/tmpdir 等），属"相邻但不相同"，无逐条等同覆盖。
- `[DRAFT-ccrtp-1.0.0-demo-as-upstream-regression]` 类似之处在 `HMBS_UPSTREAM_TEST_RESULT` 证据口径与 no_tests/0 拒绝，但 ccrtp 主题是 upstream 测试大盘点，与 PIE/ET_EXEC 内核拒绝**不相邻**，不做并条目。
- 本条目是**生态通类**而非纯库特化：OHOS PIE-mandatory 语义对任何产非 PIE 可执行镜像的构建/运行链路适用。

## 适用判断

- 适用：在 HarmonyOS 上产出并 exec 非 PIE(ET_EXEC) 可执行产物且 `execve` 报 EACCES/rc=127 的任何构建或工具链路（直接 emit ELF 的后端、`-no-pie` 链接、依赖可执行 cwd 的 consumer）。
- 通用启发：先甄别产物实际后端再打 `-pie` 补丁或切换产 PIE 后端；结合 noexec 挂载语义选择可执行产物 cwd；以 `readelf Type=EXEC→DYN` 作为通过判据。
