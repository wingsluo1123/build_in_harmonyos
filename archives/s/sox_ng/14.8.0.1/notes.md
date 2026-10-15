# sox_ng 14.8.0.1 编译笔记

## 概要
- 软件：sox_ng（SoX next generation，音频格式转换库 libsox_ng + CLI 工具 sox_ng/soxi_ng/play_ng/rec_ng）
- 版本：14.8.0.1（上游官方 tag/release，非适配后缀；上游已有更新的 14.8.1）
- 源码：Codeberg 官方 release tarball（含预生成 configure/config.guess/config.sub/Makefile.in）
- 构建系统：autotools（configure + make，无需 autoreconf）
- 许可证：LGPL-2.1-or-later
- 适配路径：A（积分赛）——适配中发现知识库未覆盖的新问题类（musl tmpfile 截断），将提交路径B知识库扩展草稿（kv+md）

## 依赖情况
可消费全集（制品仓 ohpcd 已发布，binary 实测可消费，conan install --build=never 全绿）：
- zlib/1.3.1（libpng/1.6.39 与 libid3tag/0.16.3 均要求此版本）
- libogg/1.3.6
- libvorbis/1.3.7（单配方含 vorbis/vorbisenc/vorbisfile 三组件）
- libsndfile/1.2.2（自包含零依赖版，wav/pcm/aiff 后端）
- libflac/1.5.0、libmp3lame/3.100、libmad/0.15.1b、libid3tag/0.16.3
- libopus/1.6.1（codec；opus 文件读因 opusfile 缺失整链禁用）
- libpng/1.6.39（1.6.58.x 要求 zlib/1.3.2 与 libid3tag 冲突，故选 1.6.39）
- libspeexdsp/1.2.1（configure 仅探测 speexdsp 库，libspeex codec 不需要）

缺失（可选功能级，不阻塞编译）：
- libopusfile → opus 整链 using_opus=no
- libfftw3 → FFT 类效果禁用
- libwavpack → wavpack 格式禁用

## 踩坑与解决
1. **E007/E072 config.guess/sub 平台识别**：release tarball 的 config.guess（upstream 生成版）不识别 HarmonyOS（uname_system=HarmonyOS → "unable to guess system type"）。用 `perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl ./config.guess ./config.sub` 修复，Score 5/5，config.guess 输出 `aarch64-unknown-linux-ohos`。
2. **musl tmpfile() TMPDIR 7 字符截断（新问题类，路径B候选）**：8svx/gain 效果经 lsx_tmpfile()→tmpfile() 建临时文件。musl 的 tmpfile() 静态缓冲区仅 16 字节（`sizeof "/tmp/fileXXXXXX"`），TMPDIR 被截断为 7 字符：`/storage/Users/currentUser/tmp`→`/storag`，拼接出 `/storag/fileXXXXXX`，落在只读 erofs 根目录下 → open(EACCES, errno=13) → 8svx 测试 "can't open channel output file"。修复：lsx_tmpfile() 增加非 WIN32 分支，用完整 TMPDIR（fallback /tmp）mkstemp 模拟 tmpfile 语义（保留 close 删除语义）。通用问题类：影响 OHOS 上所有使用 tmpfile() 且 TMPDIR 较长的软件。验证：C 探针实证截断路径 EACCES，直接 open(TMPDIR/…) 正常。
3. **E002 /tmp 只读**：test/check.sh:52 `errs=/tmp/check$$` → `${TMPDIR:-/tmp}/check$$`（POSIX TMPDIR，未设置时回退 /tmp 保持 glibc 行为）。
4. **init-build 嵌套源码误判**：工具的嵌套源码检测把 git tag archive 的 cmake-buildsetup/ 子目录误判为源码根（基线仅 42 文件）。手动以完整源码替换 .orig/.work 并重建指纹。最终改用 release tarball 源（顶层 sox_ng-14.8.0.1/，无此问题）。
5. **test/Makefile 为 configure 替换产物**：release tarball 的 Makefile 是 maintainer（x86_64）预生成的，./configure 会重新替换变量（triplet/ALSA_LIBS 等）→ 构建副产物，按 R6 不入补丁集（曾误生成 0004-test-Makefile.patch，已剔除）。
6. **zlib 版本冲突**：libpng/1.6.58.3→zlib/1.3.2 与 libid3tag/0.16.3→zlib/1.3.1 直接冲突；两者配方均默认 full 模式（zlib 版本进 package_id），override 会破坏预编译 binary 匹配。解决：libpng 降级 1.6.39（要求 zlib/1.3.1）统一依赖图。
7. **RPATH/staging**：staging（DESTDIR+绝对 prefix）二进制的 rpath 指向构建目录/conan 缓存而非 staging 路径，需 LD_LIBRARY_PATH 运行；conan 包内 RPATH 由 conan 管理。
8. **安全弹窗（R54/E054）**：本机策略已放行，sox_ng/soxi_ng 首次运行无阻塞弹窗。
9. **HMDFS uid 映射 + umask 077 临时目录不可写（新问题类，路径B候选）**：config.status（autoconf 生成）用 `(umask 077 && mktemp -d "./confXXXXXX")` 创建安全临时目录（mode 0700）。HMDFS 上进程内核 uid 与文件属主 uid（20001006）不匹配，权限检查落到 group 分支（file_manager，mode 0700 无 group 权限）→ 向 `confXXXXXX/subs1.awk` 写入 EACCES → "could not setup config files machinery"。实证对照：tmp 挂载（uid 匹配属主）同命令 WRITE_OK；hmdfs 上普通 mkdir（umask 002 → 2731 group rwx）可写、mktemp umask 077（→2700 group 无权限）不可写。修复：configure/config.guess 共 5 处 `umask 077` → `umask 007`（保留 group 写权限、去掉 other 访问，glibc 环境无副作用；Makefile.in 的 umask 077 在 installcheck/distdir 规则，非构建路径，不 patch）。通用问题类：任何在 HMDFS 上用 umask≥070 创建目录/文件的构建工具都会触发。

## 上游测试（R51 三步法）
- 清点：`make check`（autotools）= src/ 格式往返测试（各格式 × 多通道/位深）+ test/check.sh（76 个回归用例，BUG-xxx/CVE-xxx 命名）
- 实际执行（release 源码真机运行）：`make check` 全部通过
  - src 格式往返：168 ok，0 fail
  - test/check.sh：76 用例 = 74 OK + 2 VOID（VOID 为脚本对超环境用例的预期跳过标记，非失败），0 FAIL
  - 总退出码 0
- 通过率：100%（0 失败）
- 日志：/storage/Users/currentUser/tmp/sox_ng-14.8.0.1.make-check-release.log

## 消费者用例（R34 + 赛事硬要求）
- test_package/test.c：模拟业务上层组件调用 sox_ng 公开 API（sox_init/sox_format_init/sox_open_input/sox_read/sox_write/sox_open_output/sox_close/sox_format_quit/sox_quit），程序内生成 440Hz 正弦 WAV（800 samples @8kHz）并完成真实 wav→wav 转换；验证编译/链接/调用运行三项通过。

## CI 修复轮（2026-10-14）
10. **codeberg 429 限流 → vendor 内置源码**：CI #89737/#90123（2 台 worker、跨 2.5h、10 次退避 22.5min 窗口）全部死于 codeberg release 端点对 CI 共享出口 IP 的持续 429。根治：官方 release tarball 解包随配方导出（vendor/，exports_sources），source() 下载失败时回退 hash-verified vendor 副本（fail closed，同构 fcft 3.3.3 tllist 先例）。commit a7e0c7d6 已推。
11. **平台 PR .diff 端点不携带二进制载荷 → vendor 文本化（本轮）**：vendor 提交（696 文件含 66 个二进制）后 CI pre-check 秒败（#90955/#90964，7.6-11.8s）：`error: missing binary patch data for <二进制文件>` + worker patch 不支持 `--fuzz=3`，机器人误诊"PR 与 main 冲突"（rebase/merge 无效：diff 内容不变则每次重建必败）。剔除 66 个二进制（58 个测试音频素材 + 7 个预建文档 PDF + src/monkey.wav）：构建/安装链均不消费——顶层 `all-am: Makefile $(MANS) $(DATA)` 不含 PDF，test/ 素材仅 `make check` 使用（上游 83 用例已在完整树上实测留档，CI 不跑 make check），monkey.wav 仅挂 EXTRA_DIST。vendor 675→609 文本文件，CHECKSUMS.sha256 重新逐条钉死（格式不变，fail closed 语义不变）。新增 0006 补丁：Makefile.in 的 `DOCPDF` 置空——automake install-data-am 恒含 install-pdf 段而 sox 给其装了真实安装体（`install-pdf: pdf`），预建 PDF 剔除后需解除对 pdf/pdfroff 的依赖；置空后 `pdf:` 无前置（等同无 PDFS 的标准 automake 形态），make install 不受影响。
12. **vendor 回退丢可执行位 → EXECUTABLES.txt（强制 vendor 路径 conan-verify 捕获，CI 必现）**：`_install_vendored_source` 用 Python `open('wb')` 逐文件写盘，不保留 tarball 的 mode 位——HMDFS 上全部落成 660，`./configure` 报 `can't execute: Permission denied`（exit 126）。CI 侧 429 下必走 vendor 回退 → 不修必挂。修复：`vendor/EXECUTABLES.txt` 由官方 tarball 权限位生成（`tar tvzf` 取用户 x 位，权威源），写盘后按清单 `chmod 0o755`，清单缺失 fail closed（与 CHECKSUMS 同语义）。
13. **vendor 顺序写盘 mtime 先后差 → automake maintainer 再生链（Error 127，第 3 轮强制 vendor 复验捕获）**：609 文件顺序写入，mtime 呈写序先后（aclocal.m4 第 15 个先落盘，configure.ac/m4/*.m4 后落盘）→ make 判 aclocal.m4 过期 → 触发 `missing aclocal-1.17`（本机/CI 均未安装 aclocal）→ `make: *** [Makefile:526: aclocal.m4] Error 127`。下载路径不犯：tar 解包把全部 mtime 统一置为发布时间（2026-05-12 14:47）。修复：`_install_vendored_source` 写盘后 `os.utime` 统一还原发布 mtime（calendar.timegm(2026-05-12 06:47:00 UTC)，与 tar 解包语义对齐）。同轮另观察到 make jobserver mkfifo 在 HMDFS 报 Operation not permitted——仅告警，make 继续，非致命。
14. **refresh-patch 原子替换清掉手工 0006 → 改动登记进编辑追踪器重生成（第 4 轮 finish 捕获）**：`refresh-patch --auto` 按编辑追踪器 `sorted(edited+added)` 顺序编号并原子替换 `patches/`（staging 只留本次生成物）——手工加的 `0006-Makefile.in-no-pdf-install.patch` 不在追踪器内被清除，致 conan `export_sources()` 报 `Patch file does not exist`，G2/W3 双挂。修复：DOCPDF 置空改动同步落到编辑追踪工作树（.work/Makefile.in）并 `track-edit add` 登记，由 refresh-patch 原生重生成；排序序下 `Makefile.in`（大写 M）列首，全套重排：0001-Makefile.in / 0002-config.guess / 0003-config.sub / 0004-configure / 0005-src-libsox_i.c / 0006-test-check.sh，conandata.yml 同步（其余 5 个补丁内容经 git diff 核验不变）。后续维护口径：补丁只经 refresh-patch 生成，手工补丁须先登记追踪器。

## 待办
- [x] conan-verify 8 道门禁
- [x] finish（W2 结构 + W3 本地 CI）
- [x] W4 pre-PR 独立审计
- [x] 路径B知识库草稿（musl tmpfile 截断 + HMDFS umask077/uid 映射，kv+md 入 knowledge/drafts/）
---

**编译结束**: 2026-10-14 14:46
**最终状态**: built
