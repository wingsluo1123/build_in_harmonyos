# xdemorse 3.6.7 编译笔记（HarmonyOS PC / aarch64）

## 这是什么

**业余无线电工具**：X/GTK+ 的 **Morse（CW）解码器** —— 从声卡取音频，经 **Goertzel 音调
检测**得到 mark/space 流，解码成文本；带瀑布图（整数 FFT）与 Yaesu FT847/FT857、
Elecraft K2/K3 的 CAT 支持。上游：`www.qsl.net/5b4az` 的 Morse 工具集。

## 上游构建形态（实测 `configure.ac`）

| 事实 | 处理 |
|---|---|
| autotools，且 **`configure` 已随包生成** | 无需 autoreconf，直接 configure+make ✓ |
| `pkg_modules="gtk+-3.0 >= 3.22.0"`（`PKG_CHECK_MODULES`） | 依赖 `gtk/3.24.43`；需 `PkgConfigDeps` 生成 `.pc` ✗否则 configure 失败 |
| `AC_CHECK_LIB([asound], [snd_pcm_open])` | 依赖 `alsa-lib/1.2.16.1` |
| `AM_GNU_GETTEXT_VERSION([0.19.8])` | **硬前置**，而本仓没有 gettext ⇒ configure 传 `--disable-nls` |
| `AC_CHECK_HEADERS([… perseus-sdr.h …])` | 可选头，无则自动降级 ✓ |

## 依赖

| 用途 | 包 | 说明 |
|---|---|---|
| GUI | `gtk/3.24.43` | GTK3（已发布 ✓） |
| 音频 | `alsa-lib/1.2.16.1` | ALSA（已发布 ✓） |

## 上游测试申报（R51 三步法）

- **清点（①）**：上游**没有可自动运行的测试套件**（tarball 里没有 `tests/` 或 `make check`
  目标；Debian 侧对该包也只跑 `superficial` 级 autopkgtest）⇒ **N = 0**。
- **实跑（②）**：上游没有可跑的用例（N=0，见①）；**程序运行验证**在本平台不可行，但给的是
  **代码级、可复核**的原因 —— 上游 `src/main.c` **第 48 行先 `gtk_init(&argc, &argv)`**，
  到**第 51 行**才 `getopt(argc, argv, "hv")` 解析 `-h/-v` ⇒ **任何命令行选项都需要显示环境**，
  连 `-v` 都到不了 ✗（不是"没试"）。已把它落成 `test_package/smoke.sh` 里的**真跑尝试**：
  按 rule4 区分「无显示 ⇒ **环境性 SKIP**（打印观测输出；**SKIP ≠ PASS**，不冒充通过 ✓）」与
  「非显示原因失败 ⇒ **FAIL**（不掩盖 ✓）」。
- **回填（③）**：如实登记 —— 上游测试 **0**（无 `tests/`；`TESTS`/`check_PROGRAMS`/`check-local`
  在各 `Makefile.am` 命中 0 ⇒ **无 `make check` 钩子**；`configure.ac` 无 `AC_CONFIG_TESTDIR`，
  逐项可复核 ✓）；程序运行验证 **结构性不可行**（代码级原因见②）⇒ 记**环境性 SKIP**、
  **不宣称运行期可用** ✓；补偿验证见 `test_package`（产物齐备 + 动态依赖可解析 + 真跑尝试 +
  OHOS 自签 + 许可证）。

## 已知限制（如实）

- 需要显示服务与音频输入才可运行 ⇒ 本平台不可运行，交付为「可构建/产物完整/已签名」；
- i18n（NLS）关闭（本仓无 gettext），故不装翻译；如需启用需先补 gettext 工具链；
- CAT 能力只针对 Yaesu FT847/FT857 与 Elecraft K2/K3（上游限制，与平台无关）。

## 四处**实际动手**的移植点（都在本机实测）

1. **`config.guess` 太老** ⇒ `configure: error: cannot guess build type; you must specify one` ✗
   ⇒ 按仓内 autotools 约定显式给 **musl** 三元组 `--build=aarch64-unknown-linux-musl` ✓。
2. **`config.status` 的临时 helper 无法执行**：这份老 autoconf 用**相对路径**造临时目录
   （`tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\``，第 589 行），随后**执行**其中的
   `subs1.awk`。而构建目录在 **hmdfs** 上 —— **hmdfs 忽略 chmod** ✗ ⇒
   `./config.status: line 618: ./confX1wMpm/subs1.awk: Permission denied` +
   `config.status: error: could not setup config files machinery`。
   （注意 TMPDIR 在此**无效**：老 config.status 不看它。）修法：在 `source()` 里把 `configure`
   里那一行改成 **ext2 绝对路径**（`/data/storage/el2/base/cache/confXXXXXX`）✓。
3. **上游只 `AC_CHECK_LIB([asound], …)`，不取 pkg-config 的 Cflags/Libs** ✗ ⇒
   ① 编译期 `src/sound.h:18:10: fatal error: 'alsa/asoundlib.h' file not found`；
   ② 链接期一串 `undefined symbol: snd_mixer_selem_id_set_index / snd_mixer_find_selem`
   （连到了 **sysroot 里的 stub libasound**，而不是 conan 制品）。
   修法：用仓内既有写法 `tc.extra_cflags`/`tc.extra_ldflags` 显式加 `-I`/`-L`
   （AutotoolsToolchain **没有** `include_paths` 属性 ✗，加了会 AttributeError）。
4. **NLS**：上游 `AM_GNU_GETTEXT` 是硬前置，而本仓无完整 gettext ⇒ `--disable-nls` ✓。

## 本地实测（2026-10-17）

| 项 | 结果 |
|---|---|
| `conan create`（含 test_package） | **EXIT=0** ✓ |
| 产物 | `bin/xdemorse`（**已 E318 自签** ✓，`signed 1 ELF(s)`） |
| 消费测试 | 可执行产物 `bin/xdemorse` ✓ / 已 E318 自签 ✓ / 许可证 ✓ / 应用级验证通过 ✓ |
