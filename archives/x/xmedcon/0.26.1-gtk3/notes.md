# xmedcon/0.26.1-gtk3 适配 notes

## 基本信息
- 上游: XMedCon 0.26.1（SourceForge `XMedCon-Source/0.26.1/xmedcon-0.26.1-gtk3.tar.gz`）
- SHA256: `4bc81e014b56873fe9a8e942f97fd0565dc891cf216f817de92647bf0285f40f`
- Conan 包版本 = 上游版本 = `0.26.1-gtk3`（上游 -gtk3 归档即 GTK3 构建线，目录/分支/配方一致）
- 许可证: GPL-2.0-or-later（CLI/GUI）+ LGPL-2.1-or-later（libmdc）
- issue: 待补（按本轮指示忽略，不在 PR 中虚构）

## W0 依赖结论
- 运行时/构建依赖: zlib（PNG/NIFTI 开启时硬性要求）、libpng >= 1.6.0、glib-2.0 >= 2.48.0、gtk+-3.0 >= 3.22.0、gdk-pixbuf-2.0 >= 2.36.0
- 仓库内均已可用: zlib/1.3.1.1、libpng/1.6.58、gtk/3.24.43（pkg_config_name=gtk+-3.0，传递携带 glib/gdk-pixbuf/pango/cairo）
- zlib/libpng 版本必须与 gtk 闭包对齐：glib/2.84.0.1 → zlib/1.3.1.1，gdk-pixbuf/2.44.6.1.1 → libpng/1.6.58；选 libpng/1.6.58.3（→zlib/1.3.2）会触发 G2 版本冲突
- 缺失依赖: 无 → 不需要拆分依赖适配
- 测试依赖: 无（上游无测试套件）
- 源码内 bundled: libs/dicom、libs/ljpg、libs/nifti、libs/tpc（随包构建，不外引）

## W1 源码/构建分析
- 经典 Autotools+libtool2.4 快照：自带 config.guess/config.sub/ltmain.sh 与生成好的 configure（仍从 autotools-dev 铺新 guess/sub 以识别 aarch64-ohos）
- 产物: `libmdc.la`（含 include_HEADERS m-*.h）、`medcon`（CLI，无显示依赖，无参数时打印 usage）、`xmedcon`（GTK3 GUI）
- 源码无 gettext/libintl 引用（区别于 xsane，无需 intl 桩）
- configure tmpdir/HMDFS 坑沿用 gtk2/xsane 同款补丁 + mktemp wrapper + umask 000

## W3 测试策略
- 上游无测试套件（无 make check 目标）→ MANIFEST.yml 豁免声明
- test_package: 消费者视角——aarch64 ELF 头断言、`medcon` usage 路径（headless 可跑）、动态链接闭包无 "shared library/symbol" 错误、`xmedcon` GUI 到达 display 初始化才失败（对齐 l3afpad 模式）

## W4 本机验证（Windows 宿主）
- `python -m py_compile` conanfile/test_package 通过；YAML 结构检查通过
- `conan graph info -pr default`：依赖图完整解析、无版本冲突（本机仅 G2 图验证，未执行完整构建——Windows 宿主交叉构建有已知假阴性知识草稿）；以真机 shadow CI 为准
- 源码 SHA256 本机下载复核一致；`git diff --check` 干净

## 下一步（真机/shadow CI 命令，待真机空闲窗口）
```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user <user> --job xmedcon-0.26.1-gtk3 \
  --package archives/x/xmedcon/0.26.1-gtk3 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/<user>/xmedcon-0.26.1-gtk3/run-conan-heavy.sh"
```
记录 job 路径、exit code、L0/L1/L2/L4/L5 结果与 test_package 输出。

## 真机 shadow CI 迭代记录
| 轮次 | job | exit | 报错原文（关键） | 根因 | 解法 |
|---|---|---|---|---|---|
| r1 | <job-root>/xmedcon-0.26.1-gtk3-r1-20261013（设备端无官方 runner 脚本，以 mkdir 原子锁排队 + ohc-run finish 驱动） | 1 | ① build_and_test.sh heredoc `can't create temp file for here document: read-only file system`；② `L0k: CLI tool detected but commands.json missing (R38)` | ① 设备 /tmp 只读，脚本 mktemp 需要 TMPDIR；② bin/ 产物包缺软件级 commands.json | ① runner 导出 TMPDIR/TMP/TEMP=$JOB/tmp；② 补 archives/x/xmedcon/commands.json（R38） |
| r2 | 同 job，runner2.sh + 精确替换包目录（本地清单 7 文件一致） | 1 | 同报错仍在，但 L0k 已转 `[ok] commands.json valid`；probe 实测：zsh 下 `mktemp` 认 TMPDIR、**heredoc 临时文件走 TMPPREFIX（默认 /tmp/zsh*，只读）** | zsh heredoc 不读 TMPDIR | r3：runner 同时导出 `TMPPREFIX=$JOB/tmp/zsh`，probe 复验 heredoc_rc=0 |
| r3 | 同 job，runner3.sh | 1 | `JC: junk files detected (2)` → `L0_RESULT=fail: junk_check failed`，L1–L5 `blocked_by_JC`；TMPPREFIX 修复已生效（heredoc 通过） | finish 管线自生成的 `.build-closed`/`.handoff.json` 被 JC 当垃圾文件（与 xmodem "CI 自动生成物不提交"同源） | r4：锁内、W3 之前清除 `.build-closed`/`.handoff.json`/`TASK_CARD.md`/`reports/` |
| r4 | 同 job，runner4.sh | 1 | JC 仍 2 个；设备端手跑 `junk_check.sh` 定位：`archives/l/libxft/2.3.9/.staging-verified`（JC1+JC5 各计一次）——是 repo-source（libxft finish 快照）自带的残留，非本包 | repo-source 继承垃圾 | r5：锁内追加 `rm libxft/2.3.9/.staging-verified` |
| r5 | 同 job，runner5.sh | 1 | JC 仍报 `.staging-verified`；find 显示工作区已删——JC1 走 `git ls-files`，该文件被 git **索引**跟踪，rm 工作区无效 | JC 以 git 跟踪清单为准 | r6：`git rm --cached` + rm 后重跑 |
| r6 | 同 job，runner6.sh | 1 | **JC 首次放行**；L1 `conan create failed`：`get()` 报 `Cannot deduce file name from the url ...?viasf=1`；依赖 gtk/glib/cairo/gdk-pixbuf/harfbuzz 等全部从制品仓下载安装成功 | `get()` 从带 query 的 URL 推不出文件名 | r7：`get(..., filename="xmedcon-0.26.1-gtk3.tar.gz")`，已提交 |
| r7 | 同 job（复用 runner6.sh） | 1 | source() 修复生效；configure 报 `C compiler cannot create executables`——config.log 显示链接测试有 `-lgtk-3...` 但**无任何 `-L` 路径** | 手工驱动 configure 绕过了 conanbuild.sh（AutotoolsDeps 注入的 -L/CPPFLAGS 全丢） | r8：configure/make/install 前 `. conanbuild.sh`（`_source_conanbuild()`），已提交 |
| r8 | 同 job（复用 runner6.sh） | 1 | conanbuild.sh sourcing 生效（前半段 configure 全带 `-O3/-I/-L` 通过）；但 configure:16501 的 `checking whether the C compiler works` 退化为 `clang -g -O2 conftest.c -lgtk-3...` | 深挖 config.log：初始 env 完美；autoconf 2.72+ 的 `AC_PROG_CC_FOR_BUILD` 用默认 CFLAGS 且**继承目标 LIBS**，构建端可执行文件链接 `-lgtk-3` 等必挂 | r9：source conanbuild.sh 后 `unset LIBS`（AC_CHECK_LIB 按需自填），已提交 |
| r9 | 新设备 <真机IP>:<端口>（原设备 sshd 断连后切换），job <job-root>/xmedcon-0.26.1-gtk3-r1-20261013，repo 用 git archive 干净导出（设备无 git） | 1 | FOR_BUILD 探测选中 `cc`（=`~/usr/local/bin/cc`，**未签名 Permission denied**），GNU C no / C11 unsupported → `C compiler cannot create executables` | autoconf 2.72 构建端编译器探测撞上 HMDFS 未签名脚本 | r10：配方 OHOS env 显式 `CC_FOR_BUILD`/`CXX_FOR_BUILD` 指向 hnp clang，已提交 |
| r10 | 同 <真机设备> job | 1 | FOR_BUILD 用上 hnp clang（探测通过），但 ac_cv_env_LIBS 仍带 `-lgtk-3...` → works 测试又挂 | unset LIBS 未生效于 configure 初始 env | r11：改为把 `LIBS=` 作为 configure VAR=VALUE 参数显式清空（autoconf 直写 ac_cv_env），已提交 |
| r11 | 同 <真机设备> job | 1 | **configure 全过、libmdc/medcon 编译成功**；`xmedcon` GUI 链接挂：`clang: no such file or directory: ~/usr/local/lib/libtiff.so / liblzma.so` | 设备 `~/usr/local/lib` 有 Debian libtool 2.4.6 时代陈旧 `.la`（dependency_libs 全绝对路径、指向不可用 .so）；conan libtiff 包不带 .la，libtool 解析 `-ltiff` 回落到坏 .la | r12：runner 持锁期间把 `~/usr/local/lib/*.la` 隔离到 `.la-quarantine-xmedcon-r12`，构建后原样恢复（不删任何文件） |
| r12 | 同 <真机设备> job，runner12.sh | 1 | `.la` 隔离生效（libtiff/liblzma 错误消失）；新错：ld 把 `-lglib-2.0` 解析到设备 `~/usr/local/lib/libglib-2.0.a`（glib-2.88 静态库，无 pcre2，符号全缺） | 设备 usr/local/lib 还有 glib 全家 `.a` 静态库参与链接解析 | r13：隔离范围扩到 glib 全家/tiff/lzma `.a`（持锁期间搬出、结束后恢复），已部署 |
| r13 | 同 <真机设备> job，runner13.sh | 1 | **编译完整成功**（libmdc + medcon + xmedcon GUI）；test_package 真实执行，medcon 三项断言全过；GUI 断言失败：实际输出为 Gtk 小写 `cannot open display:` | 断言大小写不匹配（l3afpad 模式直接搬用大写形式） | r14：`"cannot open display" in text.lower()`，已提交 |
| r14 | 同 <真机设备> job | W3 全绿 | **全部门禁通过**：G0/JC pass、`L0 pass`、`L1 pass: test_package executed`、L1e R34 negative test confirmed、`L2 skip: medcon version`（脚本平台规则）、`L4 pass: patches clean`、`L5 pass: bin`、Pass rate 100% (1/1)；后续 finish 步骤剩 3 项交付物：reports/test-report.md、packaging/.packaged、.staging-verified | — | test-report/packaging 标记已建（均在 .gitignore，不入库）；`.staging-verified` 仅设备端创建（git 跟踪会被网站 CI JC1 判垃圾，libxft 实证） |
| r15 | 同 <真机设备> job | 1 | Step10 预检仅剩 1 项：test-report.md "需创建"——被 runner 开头的 `rm -rf reports` 清掉了 | 清理与交付物恢复顺序 | r16：runner 清理后从 job 根副本恢复 `reports/test-report.md`，`touch .staging-verified` |
| W6 submit | 本机 worktree | gate2 首次失败：本地缺 `.ci-result.json`（W3 凭证） | W3 在设备端执行，凭证留在设备 | 从设备取回 `.ci-result.json`（exit_code=0，integrity_hash 8b58525b…）与 `reports/w3-local-ci.log`（两者均 .gitignore 不入库），重跑 submit（后台） |
| W6 审计 | pre_pr_audit generate + 独立审计子任务 | 首审 fail：P1 notes.md 泄露真机 IP/端口；P2 用户名残留、未用 import | 敏感信息脱敏不彻底 | 已匿名化（`<真机IP>:<端口>`/`<user>`/`<job-root>`）、删未用 import，复审 **pass**（仅剩 1 条 P3：`autotools._configure_args` 私有属性建议性），重跑 submit |
| W6 PR | 本机 → GitCode | submit 四 Gate + 自检全过、分支 `feat/xmedcon-0.26.1-gtk3` 已推送、PR body 完整性 0 待填写；`create-pr` 两次 30s/300s 超时（GitCode API 网络不稳，list-prs 正常） | API 创建请求慢/挂起 | `gitcode_pr.py create-pr --no-preflight` 后台长窗口重试（进行中） |
| W6 CI | GitCode worker CI-034 | 首跑失败：`conan-build-test` 步骤，日志几十条 `configure: fork: retry: Resource temporarily unavailable` + `cannot find sources (source/medcon.c) in or ..` | **代码问题**（非纯环境）：CI worker PATH 无 `/data/service/hnp/bin`（GNU coreutils），configure 开头 `dirname -- /` 探测失败→`as_dirname=false`→srcdir 推导链（dirname/expr/sed）全失败→`ac_confdir` 为空→`cannot find sources ... in or ..`。真机能过只因 runner 手动加了 hnp/bin | r17 修复：① `_build_environment` 显式 `prepend_path(PATH, /data/service/hnp/bin)`（配方自包含）；② `_configure_for_ohos` configure 调用前 `srcdir=.`（绕开 dirname/expr/sed 推导，cwd 恒为源码根） |
| W6 CI 等待 | — | 待 CI 用修复后 SHA fc1c4ab0c0 重跑出结果 | 共享 CI 队列繁忙 | 已 `/rebuild`（note 194251121），监控轮询中 |
| W6 人工审查 | Septest（审查员） | VERDICT=FAIL：① rule1 PR 模板格式——`补全测试用例说明` 章节/复选框缺失；② rule6 AI 检视未覆盖最新提交（最新提交 02:38 晚于检视 13:54） | PR 正文缺「补全测试用例说明」章节；提交后未重新触发 AI 检视 | ① PR body 补 `## 补全测试用例说明`（4 项 checkbox）+ 标题加 `【积分赛】` 前缀；② 推送新提交触发 atomgit-bot 重新检视 |
| W6 CI 复跑 | GitCode worker CI-021 | **CI 校验通过**（构建 #98183：conan test_package ✅、L0 ✅、L1 ✅） | r17 修复生效 | 待人工审查复审 |

## 最终状态

- 状态：**built**（真机 shadow CI 全门禁通过：G0/JC/L0/L1/L1e/L4/L5 pass，L2 按脚本规则 skip，构建通过率 100% (1/1)）
- W4 独立审计：pass（复审，audit-result.json）
- 产物：`packaging/xmedcon-0.26.1-gtk3-ohos-aarch64.tar.gz`（bin/medcon、bin/xmedcon、bin/xmedcon-config、lib/libmdc.so.*、include、licenses、etc、share，来自真机 conan create 输出）
- 编译结束标记：本节即关闭段（progress_closed）
- PR：GitCode #16199；网站 CI 已通过（构建 #98183）；人工审查 Septest 首审 FAIL（rule1 缺「补全测试用例说明」章节、rule6 AI 检视未覆盖最新提交），已整改（补章节 + 【积分赛】前缀 + 推送触发重新检视），待复审
