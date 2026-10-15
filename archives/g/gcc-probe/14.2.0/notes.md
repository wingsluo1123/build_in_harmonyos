# gcc-probe（前置 GCC 14 包）探针笔记 · 路径 C / 路线 (ii)

> 本文件是配方目录下的 `notes.md`，记录**探针轮的实测事实与整改**，供后续
> 交付（finish / W4 / PR 正文补充说明）取数。所有数字都带出处；**没有出处的
> 数字不要写进来**。

## 1. 起跑脚本两处硬前置（2026-10-03 主理裁定，缺一条不起跑）

1. **日志截断必须在 `gate.sh` 通过之后**：
   起跑脚本原先第一句就是 `: > "$LOG"`，随后才跑 `gate.sh 8000`。第 7 轮首次
   起跑被内存门槛挡下时，这句**把上一轮（r6）的 54MB 构建日志整份覆盖**，
   导致「五个症状全份日志 0 次」这类计数失去原文支撑。现改为：先把
   `gate.sh` 输出收进变量判定，**通过之后**才 `rm -f` 与 `: > "$LOG"`。
2. **截断之前必须先备份上一轮日志**：
   `cp -p "$LOG" "$LOG.prev-<时间戳>"`（`[ -s "$LOG" ]` 才复制），脚本会打印
   `LOG_BACKUP=<路径>`。两处合起来保证：门槛不过 ⇒ 上一轮日志原封不动；
   门槛通过 ⇒ 上一轮日志有副本可回查。

**r6 日志损失的幸存证据**（原文已失，出处如下）：
- `gcc-probe-r3-summary.txt` 四行：`START 2026-10-03 08:15:31 / END 09:39:38 / RC=1 / WALLCLOCK=5047s`；
- 五闸原文与分段时刻：见登记表 `odb-2.4.0` 行 note（2026-10-03）与链主终报；
- r6 已装树完好（见第 3 节读数）。

## 2. 已验证的根因链（每条都带实测读数）

| # | 症状（首条真实错误） | 根因（实测） | 修法 | 复验读数 |
|---|---|---|---|---|
| 1 | `ld: cannot find crti.o`（r1/r2） | `libgcc_s.so` 链接由 `$(CC)` 驱动，配方只钉了 `CC_FOR_TARGET` | 两条 make 行补 `CC=`/`CXX=` | 同目录 `make -n`：改 `CC` 链接命令变、改 `GCC_FOR_TARGET` 不变；包装器与手补 `-B` 均 rc=0 |
| 2 | `configure: error: C++ preprocessor "/lib/cpp" fails sanity check` | 顶层 `RAW_CXX_TARGET_EXPORTS` 在 configure 规则 shell 内重新 `export CXX=$(RAW_CXX_FOR_TARGET)`，压过命令行；`RAW_CXX_FOR_TARGET` 是裸 `xgcc`、缺 `-isystem <sysroot>/usr/lib/<triplet>` | make 行补 `RAW_CXX_FOR_TARGET=<包装器 + 原始 flags>` | 四候选实测：原样 rc=1（`bits/alltypes.h` 缺）、加多arch `-isystem` rc=0、包装器 rc=0、`-c` 也 rc=0 |
| 3 | `os_defines.h: missing binary operator before token "("` | 选中 `config/os/gnu-linux`，其 `#if __GLIBC_PREREQ(2,15)` 依赖 glibc；OHOS `features.h`(905B) 无此宏 | （已由 #4 取代）加 `#define __GLIBC_PREREQ(major, minor) 0` shim | A/B：未打补丁 `-E` rc=1（同错），打上 rc=0 |
| 4 | `ctype_base.h: '_ISupper' was not declared` | 同族第 2 条：`os/gnu-linux/ctype_base.h` 用 glibc 位掩码；OHOS include 全树 `_ISupper` 0 命中 | **族级**：`configure.host` 加 `linux-ohos*) os_include_dir="os/generic"`（上游本就有 `linux-musl*)` 同支） | 三变体实编译：gnu-linux rc=1（生产同错）/ **generic rc=0** / bionic rc=1(`_U` 未声明)；`R3GATE4` 读 `S["OS_INC_SRCDIR"]="config/os/generic"` + ctype conftest rc=0 |
| 5 | `make: *** No rule to make target 'install-plugin'` | 顶层 Makefile 无该目标（`grep -c "^install-plugin"` = 0）；目标在 `gcc/Makefile`（`3832: install: install-plugin`、`3915: install-plugin: …`） | `package()` 改两步：顶层 install 三目标 + `make -C gcc install-plugin`，并加 `R3PLUGIN` 安装面自检 | r6 目录真跑 `make -C gcc install-plugin DESTDIR=<pkg>` rc=0 |

族级修法生效证据（r6 全份日志计数）：`missing binary operator`=0、`_ISupper` 编译错=0、
`/lib/cpp`=0、`bits/alltypes.h` 编译错=0、`cannot find crti.o`=0。
（⚠ 该日志已被第 7 轮首次起跑覆盖，计数原文见登记表 note，标「以链主终报读数为准」。）

## 3. r6 已装树读数（2026-10-03 10:2x 只读复核）

- 插件头目录：`<pkg>/lib/gcc/aarch64-linux-ohos/14.2.0/plugin/include`
  - `.h` 计数 = **475**；关键头 `gcc-plugin.h` ✓、`plugin-version.h` ✓
  - 由 `install-gcc`（顶层 Makefile:4782 → `gcc/Makefile` `install` → `install-plugin`）装出
- bin 面：`aarch64-linux-ohos-gcc/g++/c++`、`gcc-14.2.0`、`gcc-ar/nm/ranlib`、`c++` 等，`bin/gcc`=1、`bin/g++`=1
- 该轮失败点：`package()` 第 1308 行 `install-plugin`（#5），**其前所有阶段已过**：
  selftest 09:29:20、torture 子集 09:29:53–09:34:49（未触发 10% 阈值）、install 09:34:49 起、09:39:38 红。

## 4. 交付时要注意（给 finish / W4）

- `package()` 里 `R3PLUGIN` 是安装面硬闸：`headers=0` 或缺 `gcc-plugin.h` 即 `R3PLUGIN_FAIL` 中止，
  终报必须带 `R3PLUGIN include=… headers=N gcc_plugin_h=True` 原文。
- 五闸读数（`R3VARIANT/R3GATE1/R3GATE2/R3OSDEF/R3GATE3/R3GATE4`）与 `R3HOSTCC` 必须进终报原文。
- `--enable-shared` 与 `--enable-plugin` 是路线 (ii) 的硬需求，⛔ 不许回退到已发布 gcc-14 的
  `--disable-shared`/`--disable-plugin`/`--enable-languages=c`。

## 5. 与仓内 `archives/g/gcc-14/14.2.0` 的差异（W4 / 审查必问）

两包同源（GNU GCC 14.2.0，`https://ftp.gnu.org/gnu/gcc/gcc-14.2.0/gcc-14.2.0.tar.xz`，
sha256 见本目录 `conandata.yml`），但**configure 开关与安装面不同**：

| 维度 | `archives/g/gcc-14/14.2.0`（仓内已发布） | 本包 `archives/g/gcc-probe/14.2.0` |
|---|---|---|
| 关键开关 | `--disable-plugin --disable-shared --enable-languages=c`（纯 C 前端） | `--enable-plugin` + `--enable-shared`，多语言 |
| 插件头 `plugin/include` | **不安装** | **安装**：r6 实测 `.h` 计数 **475**、`gcc-plugin.h` ✓、`plugin-version.h` ✓；`package()` 内 `R3PLUGIN` 硬闸，`headers=0` 或缺 `gcc-plugin.h` 即 `R3PLUGIN_FAIL` 中止 |
| 下游用途 | 独立 C 编译器 | `odb/2.4.0` 的 `tool_requires` |
| CI 超时条目 | `gcc-14/14.2.0 14400` | `gcc-probe/14.2.0 8640`（r8 实测 `WALLCLOCK=4316s` @ `-j4`，2026-10-03；取 2× 余量给慢速 CI worker） |

**为什么 odb 必须要带 plugin 的 GCC**：上游 `m4/gcc-plugin.m4` 对非 GNU 编译器直接
`AC_MSG_ERROR`；`odb/odb.cxx` 亦以 `-fplugin=` 注入 driver。仓内 5 个 GCC 家族包
（`gcc 9.5.0.1` / `gcc-14 14.2.0` / `gcc-snapshot` / `gcc-ada` / `gcc-c-fortran`）
**全为 c 前端 + `--disable-plugin` + `--disable-shared`**，制品仓亦无任何已发布 GCC
工具链 ⇒ 本包是 `odb/2.4.0` 的必要前置（登记表 `依赖边 = odb/2.4.0@desc#-`）。

## 6. 归档来源与实测基线

- 本配方由探测目录归档迁移：`~/tmp/uc2/odb-2.4.0/gcc-probe/`（A 机），
  迁入件 = `conanfile.py` + `conandata.yml` + `notes.md` + `files/{ohos.h,prepare_ohos_sources.py}` +
  `test_package/{conanfile.py,test_gcc.c,MANIFEST.yml}`；**未迁** 10 份 `conanfile.py.bak-*`
  历史备份与 conan 生成的 `test_package/{conanbuild,conanrun,deactivate_conan*}.sh`
  （`.gitignore` L215-217 已忽略）、r8 产物 `test_package/gcc_test_program` 与空 `metadata/`。
- **包名保持 `gcc-probe`**：r8 全系于该名（起跑脚本 `gcc-probe-r3-run.sh`
  md5 `ad236c1c6119dbb42480910f4217cbb4`、build 目录 `p/b/gcc-pd40a35364926f`），
  改名需连动 `conanfile.name` + odb 的 `tool_requires` + 全部日志锚点；`AGENTS §8`
  只约束版本 / 归档目录 / 分支三者一致，未约束包名语义。
- **r8 实测基线（决定超时条目）**：`START_EPOCH=1791028790 (2026-10-03 19:59:50)` /
  `END_EPOCH=1791033106 (21:11:46)` / `RC=0` / `WALLCLOCK=4316s` /
  `OUTCOME=完整跑完（conan create rc=0，含 install/test_package）` / `jobs=4`（r7 OOM 后降档）。
- ⚠ `test_package/MANIFEST.yml` 首行 `package: gcc-14/14.2.0` 是**随 gcc-14 配方克隆
  留下的原样**（本目录按"只迁配方实质"原样迁移，未改写）；仓内无任何门禁读取该字段
  （`scripts/*.py`、`ci/scripts/*.sh` 全量 grep 仅 `gen-test-packages.py` /
  `sync-recipes.py` 两处提及 MANIFEST，均不读 `package:`）。

## 7. 归档门禁整改记录（2026-10-06）

- **W2 `conan-verify` G1 要求 `apply_conandata_patches` 调用**（判据在
  `scripts/ohc/conan_verify.py` G1 `checks` 清单第 8 项，字面匹配）：
  r8 的 `conanfile.py`（57661B / md5 `631217789635e392ffca2168d9176ec2`）无该调用
  ⇒ G1 红「conanfile.py 缺少: 补丁应用调用」。
- **本配方确实无补丁**（`patches/` 缺，r8 未用补丁即跑通），故该调用是**有日志的 no-op**：
  conan 2.29.1 实读 `~/.local/lib/python3.14/site-packages/conan/tools/files/patches.py:82-88`
  —— `conan_data.get('patches')` 为 `None` 时打印
  `apply_conandata_patches(): No patches defined in conandata` 并 `return`，
  **不改变 r8 已验证的构建行为**。
- 改动面（仅 2 处，`python3 -m py_compile` rc=0）：`conan.tools.files` import 增
  `apply_conandata_patches` 一行；`build()` 首部增 4 行（注释 3 + 调用 1）。
  `conanfile.py` 57661B → 57952B，md5 `631217789635e392ffca2168d9176ec2` →
  `451e90b67e7e1c64e803c6751bd8834c`；改前原件备份在
  `~/tmp/uc2/gcc-probe-14.2.0/recipe-src-backup/`（A 机）。
- **`ohc-run.py build` 一条红（2026-10-06 00:45 实测，未改处置范围）**：
  `EXIT_REASON=init_build_failed / EXIT_CODE=2 / STEP_FAILED=Step1` ——
  `gcc-probe` 不在 `scripts/software-registry.yaml`，`init-build` 走 `search_url`
  拿到的是 Savannah/xs4all 的**臆造同名 URL**，未生成 `.build-context-*`。
  依据 `经验库 12.50①`（「配方文件全量就位后**不要跑完整 build 一条龙**，直接
  `ohc-run.py conan-verify`（其 create 不触发 init）」）与
  `经验文档/反馈/pending/2026-10-02-finish-Step9-conan-init-force覆盖手写配方-两条链独立复现.md`
  跳过 `build`、改走 `conan-verify`（其 G2 才是真 `conan create`）。

## 8. 本轮门禁实测（2026-10-08）

- **G2 超时读数（两条）**：①静态：`scripts/ohc/conan_verify.py:587` =
  `rc, output = self._run(cmd, timeout=3600, cwd=str(self.pdir))`，
  `grep -n build_timeouts scripts/ohc/conan_verify.py` = 0 命中 ⇒ 本地 G2 不读
  `ci/config/build_timeouts.txt`；②行为：2026-10-06 00:53:00→01:53:02 实测
  （当时 8640 条目已在分支内）`reports/conan-create.log` 全文 7 字节 `TIMEOUT`、
  报告「conan create 失败 (RC=1)」、起止 3602s ⇒ **3600 生效、8640 对本地不生效**。
- **预热缓存正解实测（经验库 12b:170）**：与 G2 逐字同款 `conan create <archive_dir>
  -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
  手工无超时跑通：`CREATE_RC=0`、`WALLCLOCK=4375s`
  （START 2026-10-08 12:45:54 / END 2026-10-08 13:58:49），完整日志
  `reports/conan-create-full.log`；conandata 无 github.com URL ⇒ 无 E017 注入、
  手工与官方 verify 的 recipe revision 一致；成品入缓存后官方 `conan-verify`
  命中缓存 `VERIFY_RC=0`、耗时 7s。
- **测试读数（本轮 conan create 实测）**：`make -C gcc selftest` RC=0；
  torture 子集 `96/100 passed`（排序前 50 源 × -O0/-O2 两档，≤10% 失败闸内）；
  test_package 消费者 1/1（`gcc_test_program`，3 重断言 + binary-sign-tool 签名校验）。
  静态枚举：`gcc/testsuite/gcc.c-torture/execute/*.c` = **1656 源**（×2 档 = 3312
  执行口径，同 #12490 计数法）；DejaGnu 全套（gcc.dg/gcc.target 等）需
  dejagnu/expect，未纳入执行面与声明面（PR 补充说明已披露）。

## 9. 路径 B 判定（AGENTS §6.2①，2026-10-08）

**B判定 = none**（理由：无既有条目命中，本 PR 不携带知识草稿）

- 查重证据：仓内 `knowledge/`（drafts + graph index）对修复关键词
  `os_include_dir|os/generic|install-plugin|RAW_CXX_TARGET_EXPORTS|CC_FOR_TARGET`
  全量 grep **命中 0** ⇒ 未复用既有条目（非 hit）；本 PR 无
  `knowledge/drafts/` 草稿、不建 Issue ⇒ 非 create。
- 五处 R3 根因修复（§2 表）均为 GCC 构建链专有，已固化为配方内自校验闸
  （R3VARIANT / R3GATE1-4 / R3PLUGIN），随配方交付；如后续 GCC 家族包需沉淀
  为条目，由主理在 B判定列升级为 create 并补草稿（列归主理）。
- 正文口径：适配路径 = 路径 A（基础适配）、标题用【积分赛】前缀（B=none
  不用【知识库扩展】，同 appres 1.0.7 先例）。
- 附：`test_package/MANIFEST.yml` 首行 `package:` 已由迁移时克隆残留的
  `gcc-14/14.2.0` 更正为 `gcc-probe/14.2.0`（§6 原记「原样迁移」的后续整改，
  仓内无门禁读取该字段，更正只为五处口径同源）。

### 对话 #1 [2026-10-08]

- 问题: 本地 conan-verify G2 硬编码 3600s，本包实测构建 4316s，直接跑必超时红（2026-10-06 已实测一轮 TIMEOUT）
- 操作: 按经验库 12b 预热缓存正解——同命令行同 profile 手工无超时 conan create 入缓存，再跑官方 conan-verify 命中缓存
- 结果: 手工 create RC=0（4375s），官方 verify VERIFY_RC=0（7s）
---

**编译结束**: 2026-10-08 14:17
**最终状态**: built
