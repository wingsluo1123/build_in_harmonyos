# vbindiff 3.0-beta5 adaptation notes

## 1. Source and build system

C++ curses application built with Autotools. The release archive already contains
`configure` and `Makefile.in`, so the recipe does not regenerate Autotools files and
declares no autotools tool requirement.

Version strings are deliberately different in two places and both are kept as they are:

- Conan reference, branch and task version: `3.0-beta5` (hyphen), matching the upstream
  archive file name `vbindiff_3.0-beta5.orig.tar.gz`.
- Upstream `Makefile.in` line 584: `PACKAGE_VERSION='3.0_beta5'` (underscore), which is
  what the built binary prints (`VBinDiff 3.0_beta5`). Consumer assertion A2 asserts the
  underscore form on purpose; it is not a mismatch of this port.

The recipe applies one HMDFS-specific repair before configure: `config.status` temp-dir
dance (`umask 077 && mktemp -d "./confXXXXXX"`) is replaced by a plain `mkdir` of a
private `conf$$-$RANDOM`, because Toybox `mktemp -d` under `umask 077` on HMDFS produces a
directory the following `echo 'BEGIN {' >"$ac_tmp/subs1.awk"` write cannot use.
`configure`, `install-sh`, `missing` and `depcomp` are chmod'ed executable after
extraction, because tar extraction on HMDFS does not always keep the exec bit.

## 2. Source provenance decision (documented judgement, not a silent choice)

The upstream host declares `Content-Encoding: gzip` on an already-gzipped `.tar.gz`.
The Conan download stack transparently decodes it, so the payload it hashes is the
*decoded* tar, while `conandata.yml` carries the *file-face* hash of the gzip member.
The first real `conan create` failed exactly there:
`Provided f04da97de993…, Computed b38ea2e0dfdb…`.

Measured carriers for the archive bytes:

| Carrier | Result |
|---|---|
| `curl` without Accept-Encoding | 128406 bytes, sha256 `f04da97de993caf8b068dcb57f9de5a4e7e9641dc6c47f79b60b8138259133b8`, magic `1f8b` |
| Conan's own `FileDownloader` (real download layer) | 128406 bytes, same sha256, magic `1f8b`, `MATCH_DECLARED=True` |
| Upstream cjmweb payload vs Ubuntu pool `.orig` payload | byte-identical; both gunzip to `b38ea2e0dfdb6929c021a182cb8b6c332b6300e97115f7088c4451c94878bc1b` |

Resolution kept: the Ubuntu pool `.orig` URL, which returns the gzip member unchanged, so
the file-face hash in `conandata.yml` is the value conan actually stores and no
"decoded-face" hash has to be recorded. This is the mechanism already documented by
`DRAFT-E690-content-encoding-x-gzip-conan-decode-two-faced-sha256` and
`E718-opt-3.19-dead-upstream-pool-four-source-pf7`; nothing new was invented here.
The alternative (upstream URL plus the E690 urllib fallback in `source()`) was rejected
because that fallback path cannot be validated without a build, and this round runs no
build. The remaining judgement is left open for W4: the Ubuntu pool URL is validated by
the real download layer, while the official upstream homepage URL would be preferred if
the recipe carried the decode-face remedy.

PF7 source-classifier check was run against the repo's own function, not inferred:
`_pf7_classify("https://archive.ubuntu.com/ubuntu/pool/universe/v/vbindiff/vbindiff_3.0-beta5.orig.tar.gz")`
returns `None`, and the upstream homepage URL also returns `None`, so neither URL is
classified as a mirror or Debian downstream repackage by the current gate.

`conandata.yml` holds the URL and sha256 in plain scalar form. The live archive files were
scanned for local-URI sources, mirror-host backup copies, stale patch-reject files and an
extra `filename:` key in the sources map: none are present, only the genuine upstream
archive name `vbindiff_3.0-beta5.orig.tar.gz` in the official pool URL.

## 3. Tests (upstream inventory counted before writing any number, per R51)

Counted from the extracted stable tag `vbindiff_3.0-beta5` in the conan source folder:

- Registration patterns counted: `TEST_CASE(`, `test:`/`check:` recipe bodies,
  `add_test(`, `ASSERT_`, `t_test`, `runtest`, `check_PROGRAMS`, `TESTS =`, `XTESTS`,
  `noinst_PROGRAMS`, `.PHONY: check`, `AM_TESTS`-style variables and the shell-level
  `case`/`expect` harness markers — 14 patterns total, every one of them **0**.
- `Makefile.in` only carries automake's generic rules: line 777 `check-am: all-am`,
  line 778 `check: check-am`, line 863 `installcheck-am:`. There is no test program, no
  test data file and no test registration. `make check` therefore succeeds trivially and
  proves the entry point runs, not that cases passed.

Five-dimension ledger. The same-value claim is limited to the three archive files that
actually enter the PR: this `notes.md`, `manifest.yaml` and `test_package/MANIFEST.yml`; the
three were read back against each other on 2026-10-13 and agree on `0 / 0 / 0` upstream and
`7 designed / 7 executed / 7 passed / 0 failed` consumer. `reports/test-report.md` is
deliberately excluded from that claim: it lives under the gitignored `reports/` path
(`.gitignore` line 96, confirmed by `git check-ignore -v`), so a reviewer cannot verify it
from the delivered surface; it is maintained only as a local working ledger and now carries
the same 2026-10-13 19:10:33 readings. No equal-value claim is made here about a PR body that
does not exist yet — when one is drafted, its two test tables must be transcribed from the
ledger below and re-checked against those same three files at that tip:

| Dimension | Value | Basis |
|---|---|---|
| `N_static` upstream statically declared cases | 0 | 14 registration patterns all 0, count above |
| `N_registered` build-system registered cases | 0 | `check: check-am` only, no `TESTS` variable |
| `N_executed` actually executed | 0 | `RUN: make check -j1` really executed (2026-10-13 15:33, `reports/conan-create.log` line 192 of the 16841B r16 log) and returned trivially: 0 cases registered upstream |
| not executed / skipped, classified | 0 declared upstream ⇒ 0 attributable to skips | no upstream suite exists; the denominator was not shrunk |
| `N_consumer` designed consumer assertions | 7 | `test_package/test_vbindiff.sh` A1–A7, each backed by `record $?` |
| `N_consumer` executed | 7 passed / 0 failed | 2026-10-13 19:10:33 real device, `== consumer assertions: passed=7 failed=0 ==`, script exits on the failed counter (`VERIFY_RC=0`) |

`test_package/test_vbindiff.sh` runs the packaged `vbindiff` binary itself and asserts
behavior, not file presence: A1 `-V` exits 0; A2 prints the built `VBinDiff 3.0_beta5`;
A3 `--help` exits 0 and prints the `FILE1 [FILE2]` usage; A4 `-L` exits 0 and prints the
GPL notice; A5 an unknown option exits 1 and prints usage; A6 no operands exits 0 and
prints usage; A7 unreadable operands exit non-zero and non-zero-but-not-124 with non-empty
stderr. `MANIFEST.yml` records `assertion_count: 7` for the same script.

`upstream_test_in_build: true` with `upstream_check_command: "make check"` describes what
`build()` invokes (`autotools.make(target="check", args=["-j1"])`), while the upstream
case count stays 0. The recipe is therefore honest on both sides: it does execute the
upstream check entry point, and it does not claim cases.

## 4. Validation state (what is proven, what is not)

Proven on the real HarmonyOS aarch64 device (window `QDR-1009-E01`):

- Source layer: the URL/sha256 pair above survived a real `conan download` through the
  Conan download stack (`source()` and `Uncompressing … to .` both succeeded in the
  2026-10-12 20:48 create). The earlier sha256 failure signature is eliminated.
- Dependency layer: `ncurses/6.6#3dcfd3b6d759300e8997800cefe8c61f:21b17f8b2bc0e9511e276e3d57a23893067cefe5`
  resolved from the published package and was consumed as the configure `CPPFLAGS`/`LIBS`
  values in the observed command line.
- Build/package layer (2026-10-13 15:33:23–15:34:05, 42 s, `VERIFY_RC=2`): configure,
  `make -j1`, `make check -j1` and `make install` all executed; `Created package revision
  a455d3abbd7f30b1fdfe109703f86f11` (package id `5451db01063ffef70a6f03c02395d1808faeb5e5`);
  the packaged binary is `ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)` and was
  executed on the device printing `VBinDiff 3.0_beta5` with rc 0.
- Consumer layer (2026-10-13 19:10:21–19:10:33, `VERIFY_RC=0`): after the one-line runner
  fix, the same `conan-verify` entry point reported `Verdict: PASS` with G0/G1/G2/G3/G4/L2/
  L4/L5 all green, and the packaged binary ran 7/7 consumer assertions (failed=0). This run
  reused the cached package, so its log does not contain the compile/`make check` lines —
  those are in the 16841B r16 log cited above.

Not proven, and explicitly not claimed:

- **The green above is a local, out-of-repo carrier green.**
  本地 G2/W3 以仓库外 profile 内容副本通过；官方默认管线（仓库 `ci/conan/profiles/ohos-aarch64`
  的 /data/service/hnp 路径本机与 worker 均存疑）仍红，待 #15461 合入后在最终 tip 重跑重绑。
  Copy: sha256 `67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e`, 2757B,
  byte-identical to the #15461 head `1f9ac70298a59d6bb5c6722558262121b46f4ecc` content
  (cross-checked against E03 `fw-15461-verify/profiles/ohos-aarch64.B`, E07
  `profiles/ohos-aarch64.B` and PR01 `f15461/ohos-aarch64`); installed only under this
  window's own `CONAN_HOME/profiles/`, never in `ci/`. The in-tree profile is untouched at
  sha256 `7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793`.
  The create command line recorded verbatim is
  `conan create … -pr:h=ohos-aarch64-15461B -pr:b=ohos-aarch64-15461B --build=missing --user=ohpcd --channel=stable`,
  i.e. name resolution through the official CLI `--profile` switch, no framework file written.
- A profile fix does not fix the whole runtime: the runner shell used by `test()` is chosen
  by the recipe, not by the profile (see section 5), so W3 is **not** "fully green because
  the framework was fixed", and this archive is still not presented as submittable.
- `finish` was not run and `result.json` was not generated: `ohc-run.py finish` has no
  `--profile` switch, so it would resolve the in-tree dead-path profile; running it would
  either fail against the official pipeline or require a second, out-of-scope build.
  `status` therefore stays `pending`, not `built`/`published`.

Root cause of the create failure is framework-side, measured and recorded:

1. The framework profile `ci/conan/profiles/ohos-aarch64` (the exact profile this build
   used) sets `[buildenv] CONFIG_SHELL=/data/service/hnp/bin/bash`, `SHELL=` to the same
   directory, and `[conf] tools.build:compiler_executables={...: /data/service/hnp/bin/clang…}`.
2. On the current device `/data/service/hnp/bin` does not exist: `test -d` false,
   `clang` absent, `bash` absent (measured). The working interpreters and compilers live
   under `~/.harmonybrew/bin` (bash 5.3.9_1) and `~/usr/local/bin`.
3. Conan exports the profile `[buildenv]` into the build environment; autoconf `configure`
   then re-execs itself through `$CONFIG_SHELL` (the `exec $CONFIG_SHELL $as_opts
   "$as_myself"` branch near the top of the generated configure, line 160 in this package's
   configure). With a non-existent `CONFIG_SHELL` the exec fails, giving shell exit 127 —
   before any compiler is ever invoked.
4. So two layers are blocked, not one: the `SHELL` layer (this failure) and the `CC`
   layer (the profile's clang path does not exist either, already shown by the framework
   A/B experiment in E03). The documented device workaround
   `env -u CONFIG_SHELL SHELL=/bin/sh` only clears the `SHELL` layer, which is why it was
   deliberately **not** half-applied to the recipe: a recipe edit has to ship together
   with a new HEAD and one real-device validation, and this round starts no build.
5. The framework fix is commit `1f9ac70298a59d6bb5c6722558262121b46f4ecc`
   ("Draft: fix(ci): support HarmonyBrew OHOS profile paths"), which parameterizes those
   paths. It is **not** in this worktree (worktree HEAD `dfaf229038bc3b7a5dbd051bc4ebdca8a814bbd7`
   on `feat/vbindiff-3.0-beta5`, `AHEAD=2` = this window's own two archive commits), and as
   measured by the coordinator it is still `state=open`, `merged=null` with no CI verdict.
6. Carrier adjudication is not this window's to invent. The 15:00 dispatch authorized using
   the E05/E07-proven out-of-repo profile *content copy* through the official `--profile`
   switch for exactly one create, and required the attribution text above verbatim in
   notes/manifest/report; the 19:00 dispatch then authorized one regular recipe-side runner
   fix plus one self-verification. Neither authorizes calling this the official W3.

## 5. Known limitations and open items

- `test_package/conanfile.py` runner shell — **fixed in this round, with the before/after
  readings**:
  - before (2026-10-13 15:33 create): `shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")`.
    `CONFIG_SHELL` is empty in Conan's own process environment during `test()` (measured:
    `echo CONFIG_SHELL=` → empty; the profile `[buildenv]` reaches the *build* env files, and
    `test()` here passes `env="conanrun"`, which does not carry it), so the fallback path was
    used and the run died with `/system/bin/sh: /data/service/hnp/bin/bash: inaccessible or
    not found` → `Error 127` at `test()` line 34 (verbatim in the 16841B r16 create log).
  - after (2026-10-13 19:10 verify, `VERIFY_RC=0`): the fallback is now the always-present
    system shell `/bin/sh` (`os.environ.get("CONFIG_SHELL") or default_shell`), still
    honouring a profile-provided `CONFIG_SHELL` when one exists. Device proof: `/bin/sh` and
    `/system/bin/sh` are the same root-owned 306288B ELF present on PATH-independent absolute
    paths, `sh -n test_vbindiff.sh` → rc 0 (no bash-only syntax: the two `((` hits are
    `$((PASS + 1))`/`$((FAILED + 1))` POSIX arithmetic substitution, not the `(( ))` command
    form), so the assertions run unmodified and still decide the exit code.
  - scope of the change: one recipe-local line, no `ci/`, no `scripts/`, no repo profile,
    no framework file. Honest caveat for W4: 168 `test_package/conanfile.py` files in this
    repository encode the same `/data/service/hnp/bin/bash` path (grep count, read-only), so
    this deviation from the house convention is deliberate and must be reviewed as such —
    #15461 alone does not change those files, and this window does not touch them.
- G0 raised `已知风险 E490 未在配方中处理` ("Autotools helper scripts … restore-known-autotools-script-modes")
  as a warning, yet G0 still PASSed and the real create/install executed `configure`,
  `install-sh` and `missing` successfully through the recipe's `_ensure_executable_helpers`.
  Recorded as a W4-facing discrepancy, not silently "fixed" by editing the checker.
- `configure` was invoked without `--build/--host` triplets in the observed command line
  (only prefix-style args plus `CPPFLAGS`/`LIBS`), which is what the Autotools toolchain
  contributed. Whether a cross triplet is required is an open question that can only be
  answered once the profile blocker is lifted, and must not be guessed into the recipe now.
- The upstream tarball registers no test suite, so upstream coverage cannot exceed the
  automake `check` entry point; the substantive coverage is the 7 consumer assertions in
  `test_package/test_vbindiff.sh`. Their execution state is date-separated and neither half
  is an inference:
  - designed but **unexecuted** at the two earlier creates — the 2026-10-12 20:48 create died
    in `build()` at `autotools.configure` (`ConanException: Error 127`, no binary produced),
    and the 2026-10-13 15:33 create produced the ELF but died in `test()` on the profile
    shell (`/system/bin/sh: /data/service/hnp/bin/bash: inaccessible or not found` →
    `Error 127`, `test()` line 34);
  - **executed 7/7 with failed=0** on the real HarmonyOS aarch64 device at 2026-10-13
    19:10:33, `VERIFY_RC=0`, the exit code taken from the failed-assertion counter
    (`reports/conan-create.log`, 6788B sha256
    `8b243b50610166c03859c25eb94bc19ce4186b91f7683b88ddcb22812df2a858`, line 99
    `RUN: /bin/sh …/test_vbindiff.sh …/bin/vbindiff` and line 148
    `== consumer assertions: passed=7 failed=0 ==`).
  Both the upstream 0-case finding and the consumer 7/7 reading must stay visible in the two
  PR-body test tables. The 19:10:33 reading is a local-carrier result, not an
  official-pipeline pass (section 4).
- The `patches` map in `conandata.yml` is empty while `apply_conandata_patches(self)` is
  still called, as the verifier requires.

## 最终状态

`status: built`（本地 CI 于显式 profile 覆盖输入下通过，W3 `exit_code: 0`；与 `manifest.yaml`
第 3 行 `status: built` 取同一状态词）／官方默认管线仍红／未过独立审计不发布。
(a) 该绿取自显式/私有 profile 覆盖输入 sha256
`67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e`（来源 #15461 head
`1f9ac70298a59d6bb5c6722558262121b46f4ecc`）；仓库跟踪 profile 未被本窗修改、验证 view 不入库不推送。
(b) 仓内跟踪 profile `ci/conan/profiles/ohos-aarch64` sha256
`7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793` 的官方默认管线在本机仍红
（其 `/data/service/hnp/bin/{clang,clang++,bash}` 实测 ENOENT），worker 侧未证 ⇒ 平台 CI 面 UNKNOWN
（未验证推断），待框架面结论；本窗不作任何“官方默认管线绿”表述。

Real-device create produced a runnable OHOS aarch64 ELF (package revision `a455d3abbd`) and
the consumer layer now executes 7/7 with the exit code decided by the assertions
(`VERIFY_RC=0`, Verdict PASS on the local carrier). This is **not** presented as an official
W3 pass and **not** a submittable state: `finish` has no `--profile` entry point, no
`result.json` exists, and the upstream case count is honestly 0 (the `check` entry point runs
but the tarball registers nothing). The single legal next action belongs to the coordinator:
either rebind on the final tip after #15461 merges, or explicitly authorize the
`finish`-path carrier question — this window requests no framework change.

## 6. Residue created by the real test run (disclosed, not committed)

- `test_vbindiff.sh` creates its scratch directory **relative to the current working
  directory**, so the 2026-10-13 19:10 run left `test_package/vbindiff-test-output/`
  (12 files: `*.out`/`*.err` captures for A1–A7) inside the recipe tree. It was untracked
  and never staged; this window moved it out to `~/tmp/uc2/QDR-1009-E01/r17-test-output/`
  (reversible move, no delete) so the commit surface stays clean.
- Open item for whoever owns the runner-shell decision: if this archive advances, the
  scratch path should be redirected to a temp dir (e.g. `mktemp -d`) instead of `$PWD`,
  otherwise every worker run drops untracked files in the archive tree. Not changed in
  this round because it needs its own paired real-device verification, and this window is
  limited to exactly one build per dispatch.
## r20 (2026-10-15 14:40) 第 2 次官方 finish 尝试读数

- 输入 tip：`3cd0a41c7fdfeded4c20e421272034dd7d5612d9`（`build()` 已按 E386 家族改
  为 `env -u CONFIG_SHELL SHELL=/bin/sh` 手工调用 configure，目录参数照抄上一次构建
  生成的 `conanbuild.conf` 六项，无 `--host/--build`）。
- 命令：`sh ~/tmp/uc2/QDR-1009-E01/build-slot.QDR-1009-E01.sh --wait 3600 --mem 8000 -- python3 scripts/ohc-run.py finish vbindiff 3.0-beta5 built`
  （`CONAN_HOME=~/tmp/ch/home-QDR-1009-E01-vbindiff`，`jobs=2`/`MAKEFLAGS=-j2`，
  profile = 官方默认 `ci/conan/profiles/ohos-aarch64`）。
- 退出码：`FINISH_RC=2`（Step5 `w3_local_ci_failed`，resumable），14:40:43 → 14:41:54。
- junk_check：本地 `pr.diff`（8 个本包路径）→ `检查模式: prdiff (8 个文件)`、
  `JC_RESULT=pass`、`JUNKCHECK_RC=0`（r19 的 full 模式 8+8 他包命中不再适用本包面）。
- G2 `conan create`：**真实进入编译路径**——新 build 目录
  `p/b/vbindf492b1008eaa9`，日志无 `Already installed!` 缓存命中。
- 第一条真实错误：`configure: error: C++ compiler cannot create executables`
  （前一行 `checking whether the C++ compiler works... no`），随后
  `ERROR: vbindiff/3.0-beta5: Error in build() method, line 124` /
  `ConanException: Error 77 while executing`。
- shell 路由本身生效：configure 在 `/bin/sh` 下跑到编译器探测并输出正常 autoconf
  检查序列（此前 profile 的 `CONFIG_SHELL` 指向不存在的路径，configure 无法 re-exec）。
- 归因读数（只读，14:34:55，`~/tmp/uc2/QDR-1009-E01/r20-preflight.txt`）：官方 profile 的
  `tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp':
  '/data/service/hnp/bin/clang++'}` 与 `[buildenv] CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash`
  在本设备均为 ENOENT（`ls: /data/service/hnp/bin: No such file or directory`；
  `/data/service/hnp` 是 `drwx--x--x root root`，可遍历，故非权限假象）。
  本机可工作的编译器是 `~/.harmonybrew/bin/clang++`（15.0.4，
  Target: aarch64-unknown-linux-ohos）。
- 结论：本包配方侧的 shell 路由缺口已闭合；剩余阻塞在框架 profile 的编译器路径本身，
  属 `ci/conan/profiles/ohos-aarch64` 写权限范围——本轮未申请、未修改该文件。
  本轮不建 PR、不提审、不 push，也不起第 3 次同类构建（R43）。
- 终态对齐：`manifest.yaml` 的 `status` 由 finish 本轮写入的 `built` 改为 `failed`
  （与真实终态一致）；`.build-closed`/`.conan-verified`/`.handoff.json` 是 finish 自身
  写入的标记，原样保留，`.ci-result.json`/`result.json`/`TASK_CARD.md` 仍缺失（未达成）。

## r21 (2026-10-16 18:16) 真机 conan create 读数（15461-B 设备回退 profile 输入）

- 唯一动作：conan create archives/v/vbindiff/3.0-beta5 --build=missing，pr:h 与 pr:b 均指 ~/tmp/uc2/QDR-1009-E01/profiles/ohos-aarch64-15461B（未跟踪的私有影子输入，官方 profile 的 HNP 回退变体，SHA 67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e）
- 待验证 HEAD：bcb4594d74db98d9757bf67d0d5c33080215a76f，分支 feat/vbindiff-3.0-beta5，配方 conanfile.py SHA c95cf6d21234d7dcac258733bb6f4d550da556b38b6fd10ddc28cd9a4fe7dd8a
- 环境：CONAN_HOME=~/tmp/ch/home-QDR-1009-E01-vbindiff，MAKEFLAGS=-j2，tools.build:jobs=2（global.conf），cwd=worktree 根
- 门槛：gate.sh 8000 GATE_RC=0（GATE_PASS probe=clang MemAvailable=11910MB 编译器进程=0）；build-slot 快照与权威副本 diff 一致 SLOTDIFF_RC=0；槽内单任务构建
- 结果：CONAN_RC=0 SLOT_RC=0。不是缓存命中——conan 明确输出 Main binary package 5451db01063ffef70a6f03c02395d1808faeb5e5 missing / No compatible configuration found / Building from source，新构建目录 uuid vbindc93e0d602c2d8，recipe revision bc404f18b5b13e1b3bde40ab1d90bd7d，source() 实下官方 ubuntu archive tarball
- test_package 消费者测试真跑：consumer assertions passed=7 failed=0，含 -L 许可证路径、无参 usage、坏选项、缺文件时 ncurses 终端初始化失败的真实 stderr 签名
- 被测二进制内存实测：memcap-run.py --probe 峰值 4 MB（原始读数 ~/tmp/uc2/QDR-1009-E01/r21/probe.txt），已记 test_package/MANIFEST.yml max_rss_mb
- 口径边界：以上只是「15461-B 私有影子 profile 输入下官方 conan 工具真机绿」，不等于官方默认管线绿。仓内跟踪的 ci/conan/profiles/ohos-aarch64（SHA 7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793）在本设备仍指向 ENOENT 的 /data/service/hnp/bin/clang(++) 与 bash（r20 preflight 只读取证），官方 finish 的 G2/W3 因此仍红；manifest status 保持 failed，不改写。
- 本轮零 push/PR/提审/rebuild/评论/resolve；配方本体未改（E386 shell 路由已在 3cd0a41c7 提交并证明有效）。

## r22 (2026-10-17 14:14–14:18) 官方 conan-verify + 官方 W3 本地 CI 模拟真机读数

- 验证输入：根准备的显式隔离 view `~/qzy/ROOT-1017-verify-vbindiff-516ce-profile15461`，HEAD
  `516ce56ed3f4b782494daaaaf86b6668f0b66662`，分支 `codex/validation-vbindiff-516ce-profile15461`
  （验证分支不提交、不推送）。归档与源码与 tip 逐字节一致（`git diff --name-only 516ce56ed3 -- archives/v/vbindiff/3.0-beta5`
  为 0 行），配方 sha `c95cf6d21234d7dcac258733bb6f4d550da556b38b6fd10ddc28cd9a4fe7dd8a`。
- 唯一偏差文件即 `ci/conan/profiles/ohos-aarch64`，sha
  `67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e`，来源为已获授权的独立框架 15461
  （HNP 不存在时回退 `.harmonybrew` 工具链）。本窗不写 `ci/`，该 profile 不进本包任何提交。
- 全新 CONAN_HOME `~/tmp/ch/home-QDR-1009-E01-vbindiff-r22`（只拷 global.conf jobs=2 + remotes.json），
  起步 `conan list "vbindiff*"` = `There are no matching recipe references` ⇒ 排除缓存命中。
- 官方入口 1：`python3 scripts/ohc-run.py conan-verify vbindiff 3.0-beta5`（14:14:45→14:15:47）**RC=0**，
  `Verdict: PASS`，G0/G1/G2/G3 均 PASS，G4 PASS（提示"无法找到程序包 ID"），L2/L4/L5 因"无 cache 路径"跳过。
  官方工具自解析 profile：`conan_verify.py:555-559` 用 `-pr:h/-pr:b=<project_dir>/ci/conan/profiles/ohos-aarch64`
  绝对路径，本窗未额外传 profile。
- 官方入口 2：`python3 scripts/ohc-run.py finish vbindiff 3.0-beta5 built`（14:15:47→14:18:01）**RC=1**，逐步读数：
  - Step1 refresh-patch：`无法定位源码目录: orig=None, work=None` → 排除规则扫描 → `无差异，保留现有补丁`。
  - Step2 close-archive：`manifest.yaml → built`、notes.md 收尾块重写、`.build-closed` 生成。
  - Step3 G0 干净构建验证：`❌ 找不到原始 tarball`（非阻塞告警；源在 conan 下载缓存，不在 ohc 预期路径）。
  - Step4 质量验证：再次 conan-verify PASS（同 home，`Already installed` 属 Step1 前 G2 已建的复用）。
  - **Step5 W3 本地 CI 模拟（阻塞门禁）：通过** ⇒ `archives/v/vbindiff/3.0-beta5/.ci-result.json`
    `exit_code: 0`，timestamp `2026-10-17T14:17:44.332772`，`log_sha256:
    13309059b357c3822d52cee63db94d66f2d034a004c9c8e0a9b94847369b9e73`。本任务 W3 此前从未过（r20/r21 停在 create）。
  - **r23 绑定行（独立 W4 判定件 §②P1-1 要求补记；r22 段以上读数与其 head 516ce56ed3 的系属保留不动）**：
    同对未改动的官方命令于 15:41–15:45 在 view `~/qzy/QDR-1009-E01-verify-vbindiff-a1b5525537-profile15461`
    （实际最终 tip `a1b5525537`）以全新 `CONAN_HOME=~/tmp/ch/home-QDR-1009-E01-vbindiff-r23b` 机械复跑，
    `.ci-result.json` sha256 `08ecdabeb2765a43cad7288c043fea15de85399b77302cfbd0ce7ef11b3c3855`
    （`exit_code: 0`、`integrity_hash b3de1688715c3c1c`）、`log_sha256
    0af9872e757c7f31cadbf5e59ed81a3dff480341fcf8d8244b8d747815fcdb70`、任务私有 `pr.diff` sha256
    `8ae47835d146124a35d4064137c8ced8dda67ac0007078c0b32baaa706a19116`。
  - Step6 finalize-archive：RC=2，缺失 3 项（软件级 `README.md`、`packaging/`、release/debug tar.gz）+
    一致性 2 项（notes 文本含历史 "status 保持 pending" 字样与 manifest built 不一致；"notes.md 无对话记录"）。
  - Step7 W5 知识图谱：1 类问题，均为他条目字段空（E219/E253/E305 `root_cause`/`rec_approach`），doc↔kv 542 对完整、
    `graph validate 通过`。
  - Step8 SUMMARY：工具异常 `'str' object has no attribute 'append'`（框架侧 bug，非本包所改）。
  - Step9 W2 原子性：判 `ci/conan/profiles/ohos-aarch64` 为框架文件变更、要求拆分独立 PR——正是本 view 的授权偏差，
    本包 PR 不含 `ci/`，故该告警在交付面不成立。
  - Step10 submit 就绪预检：缺 `reports/test-report.md`、`packaging/`、`.staging-verified`（后两者按 AGENTS §9 属
    本地留盘不提交的工作流标记）。
- 真编译（非缓存）证据取自 `reports/w3-local-ci.log`：L108 `Exported to cache folder: …/home-QDR-1009-E01-vbindiff-r22/p/vbinded67ae2aaef3f/e`、
  L168 `Calling source()`、L173 `Building from source`、L178 build folder `vbinde17ca53417690`、
  L262/268/270 实际编译行 `~/.harmonybrew/bin/clang++ … -stdlib=libc++ -std=c++17 -c -o vbindiff.o …`、
  L282 `make install DESTDIR=… -j2`、L328 执行 `test_package/test_vbindiff.sh`、L377
  `consumer assertions: passed=7 failed=0`、L394 `L1_RESULT=pass`、L63 `Errors: 0`。
  W3 用无 user/channel 的 `vbindiff/3.0-beta5` 引用（G2 用 `@ohpcd/stable`），package id 不同，故 W3 为独立真编译。
- 资源门（本窗实测，非转述）：`gate.sh 8000` → `GATE_PASS:probe=clang MemAvailable=12059MB MemFree=1012MB
  Cached=15243MB swap余=48570MB load=20.700 PSI_full=avg10=52.14 编译器进程=0`，GATE_RC=0；
  `build-slot.QDR-1009-E01.sh --wait 3600 --mem 8000` → `SLOT_OK 14:14:43` / `SLOT_DONE:ok MemAvailable=11713MB`，
  SLOT_RC=0；与 E04 权威副本 `diff -q` → SLOTDIFF_RC=0（锁路径未改）。全窗只放本任务 1 个构建，未起第二槽，未动他人进程。
- 测试五维账本不变：`N_static=0`（上游 3.0-beta5 无自动化测试入口）、`N_registered=0`、`N_executed=0`、
  `N_consumer=7` 设计 / 7 执行 / 0 失败；`test_package/MANIFEST.yml` 的 `max_rss_mb: 600`，memcap `--probe` 峰值 4MB。
- **口径边界（措辞门）**：以上是「已获授权的独立框架 15461 profile 作为显式验证输入时，官方 conan-verify 与官方 W3
  本地 CI 模拟在真机绿」，**不等于官方默认管线绿**——仓内跟踪的 `ci/conan/profiles/ohos-aarch64`
  （sha `7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793`）在本设备仍指向 ENOENT 的
  `/data/service/hnp/bin/{clang,clang++,bash}`（r20 只读取证）。验证分支未提交未推送，profile 未混入适配 PR。
- 本轮零 push、零 PR、零提审、零 rebuild、零评论、零 resolve；未领新坑；W4 不自审，改以独立审计交接。
## r23（2026-10-17 15:0x）最终 tip 复跑官方工具，取新绑定 W3 读数

- 派单裁定（job 8c3e89d6 / coord-20261017-1500-e01-vbindiff-final-head-w3-rebind，根 14:43 独立复核）：
  r22 的官方绿读数出自**测试 view**（HEAD 516ce56ed3），而交付面最终文档 HEAD 是 5289efa860877e4b267dd19835fa12b68ed41bbd；
  **旧绿不得套新头**，必须在实际最终 HEAD 上机械复跑。
- ① 发布面实核（只读，本窗实测）：worktree `~/qzy/QDR-1009-E01-vbindiff-3.0-beta5`
  分支 `feat/vbindiff-3.0-beta5`，HEAD 5289efa860；`archives/v/vbindiff/3.0-beta5` 无未提交改动，
  跟踪文件仅 7 个（conanfile.py / conandata.yml / manifest.yaml / notes.md / test_package 三件）；
  `conandata.yml` sha `59a08c0bb5ad6dacc50ddf25d9a448a1b324bb20d5ba9efb789ea9c91c704373` =
  官方标量 URL `https://archive.ubuntu.com/ubuntu/pool/universe/v/vbindiff/vbindiff_3.0-beta5.orig.tar.gz` +
  真实 sha256 `f04da97de993caf8b068dcb57f9de5a4e7e9641dc6c47f79b60b8138259133b8`，`patches: {}`；
  E017 家族残留复扫（仅本任务文件，排除目录）：无 `file://`、无 `.ghfast-bak`、无 `predl_cache`、无镜像列表形态，
  命中项均为官方 `.orig.tar.gz` 文件名自身；未跟踪项 `.build-cache/`、`test_package/vbindiff-test-output/`、`pr.diff`
  留盘不入库（AGENTS §9），故无需清理动作。
- ② 本条即"新读数一次成面"：同一提交内改 manifest.yaml 的 notes 块、test_package/MANIFEST.yml 的
  last_run/carrier_attribution 与本 notes 段，改完即为待验证的最终 tip；此后不为非阻断润色再改 HEAD。
- ③ 复跑方式（显式披露）：用官方只读准备工具 `prepare-validation-view.py` 从交付面 HEAD 建隔离验证 view
  （`git worktree add` 到 `~/qzy/` 下新目录，分支前缀 `codex/validation-`，不提交不推送），
  仅覆盖 `ci/conan/profiles/ohos-aarch64` 为已授权独立框架 15461 的 profile 内容副本（sha `67404bc17c0beae386d56bcae21d9002388e095e82210e2f8d02a886891ff19e`），
  工具同时逐文件校验归档字节与 HEAD 对象一致；随后在 view 内跑未改动的官方命令
  `python3 scripts/ohc-run.py conan-verify vbindiff 3.0-beta5` 与
  `python3 scripts/ohc-run.py finish vbindiff 3.0-beta5 built`，全新 CONAN_HOME
  `~/tmp/ch/home-QDR-1009-E01-vbindiff-r23`（排除缓存命中）。构建前过 `gate.sh 8000` 与本窗私有
  build-slot 快照（基准 2 槽/条件 3、jobs=2、锁路径 `$HOME/tmp/uc2/.build-slots` 未改，与 E04 权威副本 `diff -q` 一致），
  全窗只放本任务 1 个构建。
- 措辞门（保持）：以上绿读数含义 = 「已获授权的独立框架 15461 profile 作为显式验证输入时，官方 conan-verify 与
  官方 W3 本地 CI 模拟在真机、在实际最终 HEAD 上绿」，**不等于官方默认管线绿**；验证 view 与 profile 绝不混入适配 PR、绝不推送。
- 本轮零 push、零 PR、零提审、零 rebuild、零评论、零 import/claim；W4 不自审，改由另一 CI 角色独立审计。

---

**编译结束**: 2026-10-17 14:16
**最终状态**: built
