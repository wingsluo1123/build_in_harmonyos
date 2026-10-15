# spot 2.15.1 — OHOS PC 适配说明

## 产物

- 共享库（单文件无版本形态）：`libspot.so`、`libbddx.so`、`libspotgen.so`、`libspotltsmin.so` + 对应 `lib/*.pc`
- 头文件：`include/spot/`（含 `spot/ltsmin/`）
- 命令行工具（16 个，`bin/`）：autcross / autfilt / dstar2tgba / genaut / genltl / ltl2tgba / ltlcross / ltldo / ltlfilt / ltlf2dfa / ltlgrind / ltlmix / ltlsynt / ltlfsynt / randaut / randltl

## 构建方式

`conan create`（autotools）：

- `--disable-python`（关闭 SWIG 绑定）；ltsmin 接口按环境自动探测
- `--build/--host=aarch64-unknown-linux-musl`（OHOS 目标）
- 补丁 `0001-unversioned-shared-libs.patch`：hmdfs 禁符号链接 → 四个可安装库追加 libtool `-avoid-version`
- OHOS 真机拒绝直接 execve `#!` 脚本（EACCES）：configure 经 shell 显式解释执行（`sh configure`）；上游测试框架 `make check` 按目录适配——tests/ 经 `/bin/sh ./run` 前置解释器（上游 `LOG_COMPILER=./run` 本身是 #! 脚本；上游 `run` 内部对 `.test` 本就用 `sh -x`）、buddy/src 无 ./run 直执真身 ELF（全局覆盖 LOG_COMPILER 会给该目录拼出 `sh ./run bddtest` → 127，实测踩坑）
- 上游用例复现两遍法（`reports/run-upstream-tests.sh`）：第一遍 `make check TESTS=` 仅构建（编译全部 check_PROGRAMS，不跑用例）；随后把 libtool 包装脚本原地替换为 `.libs/` 真身 ELF（幂等，已是 ELF 的跳过），并导出**绝对路径**的 `LD_LIBRARY_PATH` 覆盖全树 `.libs` 目录（测试 cwd 为各自子目录，相对条目会解析失败 → musl `Error loading shared library` / `Error relocating` 洪泛，实测踩坑）；第二遍为证据轮
- 运行期脚本 spawn 垫片（`reports/spot-shexec-shim.c`，复现脚本构建并 `LD_PRELOAD`）：ltlcross* 用例运行期用 heredoc 生成 `fake` 翻译器脚本（chmod +x）再由 ltlcross/ltldo 经 `posix_spawnp` 直执——脚本构建期不存在、无法预转换，且 OHOS `sh -c ./script` 亦 126（无 ENOEXEC 回退）；垫片拦截 `posix_spawn(p)`，`#!` 目标（含 PATH 解析）改写为 `/bin/sh <script> <args…>`、ELF 透传（正常平台脚本执行语义的等价物，上游测试零改动；微测：无垫片 rc=2 / 加垫片 rc=1 恰为用例期望码）
- sanity/style.test 的 GNU grep 语义对齐（环境侧，测试零改动）：设备默认 grep 为 toybox 0.8.12——UTF-8 感知且无视 LC_ALL=C，对 `<< "〈"` 等多字节字形按单字符命中、对上游原始树误报（style.test 源码注释已预告"grep 实现无视 LC_ALL=C"的情形）；复现脚本把设备自带 GNU grep（`/data/service/hnp/bin/grep` 3.12）封装为私有 `grep`（5 行 execv 包装，hen 目录不可整目录前置）后仅将该目录前置 PATH（`SPOT_GNU_GREP` 可覆盖来源）——LC_ALL=C 下按字节语义零误报（对照实测：多字节不命中 rc=1 / `"c"` 命中 rc=0 / toybox 两者均 rc=0）
- 补丁 `0002-autoconf-mktemp-fallback.patch`：hmdfs 拒写 config.status 的 mktemp 临时目录（EACCES）→ 三级 configure（顶层/buddy/ltdl）的 mktemp 分支改为立即失败，走 autoconf 自带 mkdir 回退分支（真机 `sh ./config.status` rc=0 实证）
- 环境：`SHELL=/bin/sh`、可写 `TMPDIR`（save_script 覆盖 profile 钉死的缺失 bash）
- `package()` 对包内全部 ELF 统一重签（E077 流程：去 `.codesign` → `binary-sign-tool -selfSign` → 恢复权限位）

## 验证

- 上游 `make check`：真机全量执行（实测：214 项 188 通过 / 0 失败 / 26 项按上游环境守卫跳过；复现脚本 `reports/run-upstream-tests.sh`，记录 `reports/upstream-test-run.md`）
- `conan create`（含 test_package）：真机 rc=0（2026-10-04 10:25:58，完整重建零错误）；test_package 12/12 具名用例全过（两个执行器各 6/6；末行 `(test package): TEST SUMMARY: 6/6 passed`）
- test_package 12 项具名用例（探针 6 + 执行器 6：cpp_api_probe / CLI 版本 / CLI 转换 / CLI 等价过滤 / ELF AArch64 / 代码签名）

## 已知限制

- python/SWIG 绑定未启用（`--disable-python`）
- ltsmin 接口在无 ltsmin 环境自动关闭
