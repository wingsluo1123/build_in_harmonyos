# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_92456880.md`

---

## 背景

- **软件名称**: mar
- **版本**: 0.5
- **构建日期**: 2026-10-04
- **构建系统**: makefile（上游两级手写 Makefile，无 configure；骨架里的构建系统字段还是 BUILD_SYSTEM 占位，是自动采集失效，见「自动化补全」）
- **上游仓库**: https://critical.ch/distfiles/mar-0.5-src.tar.gz（FreeBSD ports `archivers/mar` 使用的 distfiles，302 到 distcache.FreeBSD.org；原站 www.emantic.co.uk 已下线）
- **适配路径**: 路径 B（知识库扩展）：基础适配 + 3 个移植补丁 + 知识草稿 E14735-draft-1370，同一个 PR（骨架里的“路径 A（基础适配，无补丁）”是自动采集失效）
- **补丁数量**: 3
- **编译依赖**:
无
- **最终状态**: 本地验证成功（built）；PR 在本报告提交之后创建，远端 CI 与机器人检视结果以 PR 页面为准

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 构建系统被误判为 autotools（`init_build.py:78-86` 只看 URL，默认 autotools），conanfile/test_package 模板「不可用」，manifest 留下 software、BUILD_SYSTEM 两处花括号占位，需手工改；.work 与 .orig 是硬链接，需手工断开 |
| build | 编译构建 | 成功 | 构建系统: makefile。库与 CLI 一次编过；`-static` 重链后经 qemu 实跑才发现每条真实命令都报 `Unknown option` |
| conan-verify | 配方验证 | 通过（G1/G2/G3 PASS） | 先直接跑 `conan create` 迭代：消费者用例里我对 `mar_tokey` 越界返回值的假设错了一次（返回 `MAR_NOMATCH` 而不是 0），修正后通过 |
| finish | 归档收尾 | W3 通过，整体 RC=1 | W3 本地 CI：L0/KC/JC/L1a–L1e/L4/L5 通过，L2 skip。RC=1 来自旧框架项（G0 的 `./configure` 不存在、gen_summary 异常）；finish 里的 refresh-patch 还把手写的 manifest 字段覆盖成模板（见「SKILL 设计改进」） |
| submit | PR提交+AI检视+CI | 本报告提交时尚未执行 | 走 fork 旁路手工建 PR（`submit` 硬编码 `git push origin`）；AI Review: — |

### 失败与问题

- **1**: 根因=plain char 在 OHOS aarch64 上无符号，`mar_main_c.c` 的 `main()` 与 `mar_run()` 各有一个 `char ch` 接收 `mar_getopt()` 的 int 返回值，选项扫描结束的 EOF 变成 255，每条真实命令（`-h` 除外）报 `Unknown option` 并退出 1，解决方案=两处改 `int ch`（补丁 0003）。只改一处是半修复：只改 `main()` 则数据已写入仍退出 1，只改 `mar_run()` 则什么都不写（五种构建的实测表在知识草稿里）
- **2**: 根因=2004 年的 C++ 流封装对依赖基类成员 `rdbuf`/`setg`/`sputc` 不加限定，clang+libc++ 两阶段名字查找拒绝，上游 `make check` 与任何包含安装头文件的 C++ 消费者都编不过，解决方案=补丁 0001/0002 共 9 处加 `base_type::`
- **3**: 根因=上游 `make install` 的头文件清单漏掉 `mar_string_c.h`（`mar_key_cpp.h` 包含它），12 个 C++ 头里 8 个装完无法包含，且不创建 `$(MANDIR)/man1`，解决方案=不用上游 install，`package()` 安装 17 个头文件，并对每个已安装头文件只用包内 `include/` 做编译检查
- **4**: 根因=x86_64 运行器缺 `/lib/ld-musl-aarch64.so.1`，动态链接的 OHOS 产物起不来，解决方案=`bin/mar` 以 `-static-pie -Wl,-z,relro,-z,now` 链接（先例 tal、cutmp3、ctpv），build() 与 test_package 实跑的就是交付产物本身
- **5**: 根因=`finish` 的 `refresh_patch.py` 把 manifest 的 `patch_classification` 重写成 `type: auto / platform_only: True / guard: 'pending'`，并删掉该键之后的所有内容（`knowledge_gained` 整段丢失），解决方案=`git checkout` 恢复手写版本（详见建议 1）
- **6**: 根因=W3 的 L2 烟测只试 `--version`/`--help`，`mar` 只有短选项 `-h`，解决方案=记为 skip（脚本标注非阻塞），未改配方

### 知识图谱使用情况

- **引用知识条目**: 最近邻是 E6401-draft-1687 与 DRAFT-cyrus-sasl-digestmd5（同一个 getopt 返回值存进 char 的缺陷，出现在上游测试台里）；同家族的还有 E419、DRAFT-8543、DRAFT-E713、DRAFT-kevlar、wise-2.4.1（getc/fgetc 存进 char）；DRAFT-maq（依赖基类 `this->` 限定，同一诊断）、DRAFT-delaunay（安装清单漏装被引用头）。后两者已覆盖本次的问题 2、3，未重复立条
- **新增知识草稿**: 1 条 E14735-draft-1370，定位为 E6401 的补充条目（`draft-review` 判 `create`，但它只比正式条目，最近正式条目 E402 0.15、E419 0.12，看不到草稿库里的 E6401；W4 审计指出后才补全披露）。与 E6401 同根因，差异是随包交付的 CLI 症状、两遍扫描的半修复状态、测试设计后果和编译期护栏，建议主编 merge-into E6401
- **引擎命中情况**: `engine` 对 char/getopt/tautological 报错命中 E419（Phase B 0）；草稿目录条数两处口径不一致（骨架报 2975，finish 报 2782）
- **测试统计**: 上游 `mar_test` 8 个，8 通过、0 失败、0 跳过；test_package 鸿蒙特有消费者用例 2 个、断言 98 条，全部通过（骨架自动统计的 0 是采集时机早于测试，未刷新）
- **未覆盖的错误模式**:
  1. 随包交付的 CLI 里，有效选项被报 `Unknown option` 并退出 1、`-h` 正常、库级测试全绿：这个形态的症状签名此前没有条目（E6401 覆盖的是测试台形态，症状是 usage + `Invalid parameter`），连同“选项表两遍扫描→两个接收变量→半修复状态”的实测，由 E14735-draft-1370 补上。
  2. 框架行为而非知识条目：`refresh-patch` 覆盖人工维护的 manifest 字段（建议 1），不属于 E-entry。

### AI 检视结果

- **检视阶段到达**: —（PR 尚未创建）
- **变更摘要评估**: 尚无（PR 在本报告提交之后创建）
- **检视意见数量**: 尚无
- **检视意见处理**: 尚无；PR 建好后如有意见，按「合理的修改、不合理的回复理由」处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（L0j/L0k/L0m、KC1–KC5、JC1–JC6、conan create、L1a/L1b/L1c、L1e 破坏性反向验证、L4、L5 通过；L2 skip）
- **远程 CI (PR 校验)**: 未运行（PR 建好后触发 `/rebuild`）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 3（① finish 的 G0 clean-verify：`./configure` 不存在，exit 127；② finish 末尾 KNOWLEDGE CONSOLIDATION 提示；③ feedback 的 14 处占位符）。上面时间线只自动记录 submit 阶段事件，所以显示 0
- **重试次数**: `conan create` 2 次（第一次是我写的消费者断言有误）+ 强制重建 1 次；`conan-verify` 1 次；`finish` 1 次（W3 一次通过）
- **关键瓶颈**: ① 定位 `Unknown option` 的根因，并用五种构建（上游原样、`-fsigned-char`、两处都改、只改 `main()`、只改 `mar_run()`）实测半修复状态；② `finish` 的 refresh-patch 覆盖手写 manifest，需要恢复；③ 动态产物在 x86 运行器上起不来，需要选 static-pie 并验证 ELF 属性
- **耗时较长的步骤**: 源码 sha256 四源核对（两次直接下载、FreeBSD distinfo、Wayback 快照）；C++ 头文件闭包检查；负向对照实验。make 构建本身一次通过

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-04T19:29:47 | skeleton_created | result_partial |
| 2026-10-04T19:29:47 | lang_checked | detected=cpp 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. `scripts/ohc/refresh_patch.py:524-549`：`finish` [1/10] 每次都把 manifest 的 `patch_classification` 重写成 `type: auto / platform_only: True / guard: 'pending'`，并用 `re.sub(r'\npatch_classification:.*', '', content, flags=re.DOTALL)` 删掉该键之后的全部内容。本次实测：手写的补丁分类被还原为 `platform_only: True`（三个补丁都不含平台宏，是普通移植补丁），排在它后面的 `knowledge_gained` 整段丢失。建议：只为 manifest 里还没有的补丁追加条目、已有条目原样保留；正则限定到下一个顶层键而不是文件末尾；`platform_only` 不要默认 True，可由补丁内容里是否出现 `__OHOS__` 静态判定。
2. `scripts/ohc/clean_verify.py:69, 160-182`：G0 无条件执行 `./configure`。只有 Makefile 的项目 exit 127，`is_expected` 只认 `replace_in_file`，于是发 HANDOFF 并让 `finish` 总 RC=1，而 W3 其实已通过。建议先判断 `./configure` 是否存在，不存在就按 make 项目直接构建或标记“不适用”，不要发失败 HANDOFF。
3. `ci/conan/build_and_test.sh:1676-1702`：L2 烟测只试 `--version`/`--help`，对只有短选项的 CLI（本包只有 `-h`）一律 skip，等于该门禁对这类包无效。建议同时探测 `-h`、`-V`，或读 `commands.json` 里声明的探针命令。
4. `ci/conan/build_and_test.sh:1172`：预下载备份目录 `.build-cache` 默认放在仓库根，且不在 `.gitignore` 里，W3 之后留下未跟踪目录，手工 `git add` 很容易带进 PR。建议默认放 `${TMPDIR}`，或加入 `.gitignore`。

### 模板改进

1. `scripts/ohc/init_build.py:78-86` 的 `_guess_build_system(url)` 只凭 URL 子串判断、默认 autotools。mar 是只有 Makefile 的项目，被判为 autotools，于是 `init_archive.py:253` 报“conanfile.py 模板不可用（autotools）”，manifest 里留下 software、BUILD_SYSTEM 两处花括号占位和 `system: autotools`。建议解压后按源码树判定：有 `configure`/`configure.ac` → autotools，只有 `Makefile` → makefile，有 `CMakeLists.txt` → cmake，有 `meson.build` → meson。
2. `templates/conanfile-makefile.py.tmpl` 取 `tools.build:compiler_executables:ar` 取不到时回落到裸名 `llvm-ar`；本机 `hnp/bin` 下只有 clang、clang++、bash 三个软链，裸名解析不到。建议模板示例改成“取编译器真实路径同目录下的 `llvm-ar`/`llvm-ranlib`”（本包 `_llvm_tool()` 的做法，其它配方里也有同样写法）。
3. `templates/conandata.yml.tmpl` 用扁平的 `sources: {url, sha256}`，而仓库里绝大多数配方用版本键 `sources: {"<版本>": {...}}`；建议模板与现状一致，并加上 `patches:` 的版本键示例（含 `strip: 1`，`refresh-patch` 生成的补丁带 `a/`、`b/` 前缀）。
4. `templates/test_package*` 没有“CLI 往返消费者”样板。建议补一个：包内 CLI（static-pie）产出 → CMake 编译消费者读取并校验 → 消费者产出再交回 CLI 读取。tal、shfm、mar 三个包各自写了一遍。

### 自动化补全

1. `scripts/ohc/feedback.py:305, 321`：骨架在 `lang-preflight` 阶段就创建，此时补丁数为 0、构建系统是 BUILD_SYSTEM 占位、上游是“(未知)”、路径固定为“路径 A”，之后不再刷新，背景节全部失真。建议在 `finish` 结束和建 PR 时按 manifest、conandata、patches 目录重新计算背景节与测试统计。
2. `finish` 的 Step10 要求的 `reports/test-report.md` 与 `.staging-verified` 都可以在 W3 通过后由 `.ci-result.json`、`w3-local-ci.log`、`conan-create.log` 自动生成，省一次 HANDOFF 往返。
3. `refresh-patch` 生成的补丁名只是文件路径（`0001-include-mar_stream_cpp.h.patch`），建议按 `patch_description` 命名，或支持 `--name`。
4. PF9 与 PF8/R38 对新增软件首个版本互斥：本地对 `origin/main...feat/mar-0.5` 实跑 PF 闸，唯一命中项就是 PF9，路径是软件级的 `README.md`、`commands.json`、`manifest.yaml`，而 PF8/R38 又要求 CLI 包必须有 `commands.json`。建议在 `preflight.py` 里给 `archives/<字母>/<软件>/{README.md,manifest.yaml,commands.json}` 加白名单，而不是让每个新软件的首个版本都 `--no-preflight`。

### 知识图谱覆盖

1. 已新增草稿 E14735-draft-1370，作为 E6401 的补充：随包交付的 CLI 的症状（有效选项被报 `Unknown option`、`-h` 正常）、两遍扫描的两处接收变量与两种半修复状态、对测试设计的后果（必须驱动有效调用并执行交付二进制）。建议 merge-into E6401。另外 `draft-review` 只比对正式条目，建议让它同时比对 `knowledge/drafts/`，否则同根因草稿一律显示 `create`。
2. plain char / EOF 家族现在至少有 7 份分散的条目（E419、E6401、DRAFT-8543、DRAFT-E713、DRAFT-kevlar、DRAFT-cyrus-sasl-digestmd5、wise-2.4.1 等），机制相同、症状不同（死循环、输入读不完、usage 报错、`Unknown option`）。建议主编把它们合并成一个正式条目的多个症状变体，并在 `error_signature` 里同时收录编译期告警文本和各运行期症状，免得继续各自为政。
3. 依赖基类的两阶段名字查找（DRAFT-maq）目前只有一份草稿，而 `std::basic_streambuf`/`basic_istream` 的 `setg`、`rdbuf`、`sputc` 是同一诊断最常见的来源；建议在 DRAFT-maq 的 `match_keywords` 里补上这几个名字。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 2AC5
- **生成时间**: 2026-10-04 19:29:47
- **PR 编号**: —
- **Git Commit**: 1262b4ac24
