# spot 2.15.1 — 上游全量 `make check` 真机复现记录

- 设备：OHOS PC 真机（沙箱身份，`/storage/Users/currentUser`），任务卡 **10869**（@evol）
- 源码树：conan 构建根 `~/tmp/ch/home-smartdns/p/b/spotf571336f559c4/b/`（`spot/`、`tests/`、`buddy/` 所在）；构建目录为其中 `build-release/`
- 复现脚本：`reports/run-upstream-tests.sh`（8912 B，md5 `ab4fe5738eb24a7e77c1e5691dd4b075`；设备副本 md5 逐位一致）
- 执行命令（真机）：
  ```sh
  cd ~/bih && bash archives/s/spot/2.15.1/reports/run-upstream-tests.sh \
    ~/tmp/ch/home-smartdns/p/b/spotf571336f559c4/b/build-release 4
  ```
- 驱动日志：`reports/upstream-test.out`（本轮）；上一轮 `reports/upstream-test.v5.out`（留证，见「轮次记录」）

## 方法（两遍法 + 五层环境适配，全部环境侧，上游测试零改动）

1. **构建轮（Pass A）**：`make check TESTS=` 仅构建——编译全部 `check_PROGRAMS` 与辅助物，不执行用例；同时补跑 `buddy/src` 构建。
2. **包装替换 + 库路径接线**：把各测试条目的 libtool 包装脚本原地替换为 `.libs/` 真身 ELF（`cp -f .libs/<name> <name>`，幂等：已是 ELF 的跳过）；导出**绝对路径**的 `LD_LIBRARY_PATH` 覆盖全树 `.libs` 目录（`find` 一次性收集，实测 33 个）——测试 cwd 为各自子目录，相对条目会解析失败（musl `Error loading shared library` / `Error relocating` 洪泛）。
3. **`LOG_COMPILER` 按目录**：`tests/` 的 `*.test` 经 `/bin/sh ./run` 前置解释器驱动（上游 `run` 为 `#!` 脚本，OHOS 拒直接 execve）；`buddy/src` 无 `./run`，保持直执真身 ELF——全局覆盖会给该目录拼出 `sh ./run bddtest` → 127 且 `check-recursive` 中止。
4. **运行期 spawn 垫片**：脚本自动构建 `reports/spot-shexec-shim.c` 并以 `LD_PRELOAD` 注入——拦截 `posix_spawn(p)`，`#!` 目标（含 PATH 解析）改写为 `/bin/sh <script> <args…>`、ELF 透传。上游 ltlcross* 用例运行期用 heredoc 生成 `fake` 翻译器脚本再直执，构建期不存在、无法预转换（微测：无垫片 rc=2 `Permission denied` / 加垫片 rc=1，恰为用例期望码）。
5. **工具链语义（GNU grep）**：设备默认 grep 为 toybox 0.8.12（UTF-8 感知且无视 `LC_ALL=C`），会使上游 `tests/sanity/style.test` 对多字节字形误报；脚本自动探测（style.test 同款探针 `grep --color=auto -n --version`，GNU rc0 / toybox rc2）并将设备自带 GNU grep（`/data/service/hnp/bin/grep` 3.12）封装为私有 `grep` 后仅前置该目录（不整目录前置 hnp）。

> 证据轮 = 上述接线完成后真实执行 `make check`（tests/ 与 buddy/src 两棵树），判定标准与用例清单全部上游原样。

## 结果

### tests/（core + sanity + ltsmin）

证据轮（`tests/`）结果汇总：

```
# TOTAL: 213
# PASS:  187
# SKIP:  26
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
```

- 结构：core（196 项）178 通过 + 18 环境守卫跳过；sanity（9 项）9 通过；ltsmin（8 项）全部按上游环境检测跳过。

### buddy/src

- `bddtest` 1 项通过（驱动日志行 `[run-upstream-tests] buddy/src check rc=0`）。

### 汇总

- **上游 214 项：188 通过 / 0 失败 / 26 跳过**（188/214，跳过项全部为上游环境守卫）
- 驱动日志尾行：`[run-upstream-tests] tests check -j4 rc=0`
- 26 项跳过全部为**上游环境守卫**（见下），非测试失败；计入分母会与上游“条件跳过”语义不符。

## 跳过分类（26 项，全部上游环境守卫）

core（18 项）：

| 类别 | 项 | 上游守卫原因 |
|---|---|---|
| 内核接口 | `full.test` | 需要可写 `/dev/full`（设备无） |
| 排版工具链 | `latex`、`dot2tex` | 需要 latexmk 全套 |
| 特权检测 | `ltlcross5` | 需要 root 运行检测器 |
| 外部工具 | `ltldo2`（LTL2BA）、`ltl3ba`、`ltl3dra`、`ltl2dstar`×4、`autcross` | 上游检测外部翻译器缺失即跳过 |
| lbtt | `ltl2neverclaim-lbtt`、`spotlbtt` | `need_lbtt`（TESTS_ENVIRONMENT 守卫） |
| python | `ltlcross4`、`ltlsynt2` | 需 python 绑定（`--disable-python`） |
| SAT 后端 | `satmin3` | 需 picosat/glucose |
| 工具 | `syfco` | 需外部工具 |

ltsmin（8 项）：`tests/ltsmin/*` 在上游检测到无 ltsmin 环境时即跳过（本构建 `ltsmin` 接口自动探测关闭）。

## 轮次记录

- **轮 5**（垫片就绪、但使用设备默认 grep）：除 `style.test` 外全部已绿；`style.test` 被 toybox 多字节误报钉死（`print.cc` / `compsusp.cc` 两处字形行，该轮其后中止）。误报即上述两处诊断行，逐次 log 不再入仓。
- **轮 6**（本记录，GNU grep arming 注入）：上游 214 项 188 通过 / 0 失败 / 26 跳过（全部为上游环境守卫）；`style.test` 全过、两处多字节字形零误报；驱动日志尾行 `tests check -j4 rc=0`，完整结果见「结果」节汇总。
- 知识沉淀：`knowledge/drafts/` 三条草稿（libtool 包装 exec、posix_spawn 垫片、toybox grep 语义），随 MR 提交。

## 证据文件

| 文件 | 内容 |
|---|---|
| `reports/upstream-test.out` | 本轮驱动日志（首行=GNU grep arming 回显；含垫片就绪、两棵树 rc 行） |
| `reports/upstream-test.v5.out` | 轮 5 驱动日志（含风格误报轮的全部其他结果） |
| `reports/conan-verify-report.md` | 官方门禁 G0–G4 Verdict PASS |

结果数据（原 `*.log` 证据按 PR 文件规范移除，结论并入本报告）：

- `tests/`：`# TOTAL: 213 / # PASS: 187 / # SKIP: 26 / # FAIL: 0 / # ERROR: 0`（核心 178 过 + 18 守卫跳过；sanity 9 过；ltsmin 8 跳过）
- `buddy/src`：`bddtest` 1/1 通过
- 垫片相关 4 例：ltlcross6 / ltlcrossce / ltlcrossce2 / ltlcrossgrind 全 PASS
- `conan create`：test_package 12/12=6+6（结论见 `reports/conan-verify-report.md`）
- 轮 5 `style.test` toybox 误报：两处字形诊断行（见「轮次记录」）
- 自补 L2 冒烟：16 CLI 工具 16/16 + 包内 ELF `.codesign` 签名 20/20
