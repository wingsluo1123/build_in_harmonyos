# picotts

Pico TTS 是 SVOX AG 开发的轻量文本转语音（TTS）合成引擎，随 Android AOSP
以 `platform/external/svox` 发布。本仓适配的上游是 `naggety/picotts`
（`ihuguet/picotts` 的 fork），把该引擎独立化为一个可直接编译的 autotools
工程。包内产出：

- `lib/libttspico.so.0` — 语音合成引擎（29 个 `lib/*.c`）
- `bin/pico2wave` — 文本转 WAV 的命令行前端（依赖 `popt`）
- `include/pico*.h` — 公共 API 头文件（`picoapi.h` / `picoapid.h` / `picoos.h` 等）
- `share/pico/lang/*.bin` — 12 个语音资源（6 语种 × `_ta.bin` 文本分析 / `_sg.bin` 信号生成）

支持的语种：en-US、en-GB、de-DE、es-ES、fr-FR、it-IT。

## OHOS adaptation

- **不发布 configure，必须自举**：上游源树只有 `pico/configure.in` +
  `pico/Makefile.am` + `pico/autogen.sh`，因此配方以 `tool_requires` 供给
  `autoconf/2.72`、`automake/1.18`、`libtool/2.5.4`（worker 自身只有 autoconf），
  在 `build()` 中于 `pico/` 子目录内 in-source 自举并构建。
- **自举环境必须命令行内联覆盖**：`conanbuild` 会在 `self.run` 时重新注入
  `PERL`/`PERL5LIB`，指向 `perl/5.42.2`——该 perl 在真机 ABI 不兼容
  （`Perl_my_cxt_init: symbol not found`），automake/aclocal/autoconf 一律失败。
  配方在命令前显式指定 `PERL=perl` 与只含纯 Perl 模块的 `PERL5LIB`，把 XS
  扩展交回系统 perl；同时把 `TMPDIR/TMP/TEMP` 指向构建目录（OHOS `/tmp` 只读）。
- **GNU config.guess/config.sub 需补 HarmonyOS 分支（知识 E007）**：上游
  `autogen.sh` 会 `rm -f config.guess config.sub` 后由 `automake --add-missing`
  复制 automake 随附的 GNU 副本（2024-07-27 / 2024-05-27），它们不认识
  `uname -s = HarmonyOS`，configure 直接报
  `cannot guess build type; you must specify one`。配方在自举后以
  `patches/0001`、`patches/0002` 换成 OHOS 版副本，得到真实本机三元组
  `aarch64-unknown-linux-ohos`；**不使用 `--build/--host` 绕过**（那会让
  configure 误判交叉编译并跳过 `AC_RUN_IFELSE` 等运行时探测）。
  补丁中 `config.guess` 的 `__OHOS__` 出现在 LIBC 探针分支内
  （`#elif defined(__OHOS__) LIBC=ohos`），属 R8 允许的"libc 探针"例外。
- **动态链接**：`/lib`、`/lib64` 下无 `libttspico*`，本库非系统同名库，
  故按 Conan 默认构建共享库（`--enable-shared --disable-static`）。
- 源码行为未做任何功能性改动；两处补丁只作用于 autotools 自举脚本副本。

## Dependencies

- `popt/1.19` — `pico2wave` 的命令行参数解析（上游 `AC_CHECK_LIB(popt,
  poptGetContext)` + `-lpopt`），来自制品仓预编译包。
- 构建期 `autoconf/2.72`、`automake/1.18`、`libtool/2.5.4`（`tool_requires`）。

## Tests

- 上游 `pico/Makefile.am` 无 `TESTS`/`check_PROGRAMS`，`make check` 零注册
  用例（清点证据见版本目录 `notes.md` 与 `test_package/MANIFEST.yml`）。
  该目标仍被 `build()` 调用。
- 本包补全两条消费者测试：
  1. `test_package/picotts_engine_contract.c` — 真实链接 `libttspico` 并调用
     `pico_initialize`/`pico_loadResource`/`pico_getResourceName`/
     `pico_createVoiceDefinition`/`pico_addResourceToVoiceDefinition`/
     `pico_newEngine`/`pico_putTextUtf8`/`pico_getData`/`pico_disposeEngine`/
     `pico_releaseVoiceDefinition`/`pico_unloadResource`/`pico_terminate`
     完成一次端到端合成，断言 PCM 非空且为 16-bit PCM。
  2. `test_package/cli_test.sh` — 对已安装的 `bin/pico2wave` 做真实行为测试，
     并用 `readelf` 校验其 `NEEDED` 确实含本包 `libttspico.so.0`；`popt` 因
     制品仓包为静态版而静态链入，故改用 `nm` 校验二进制内含 popt 符号。

## Known limitation

`pico2wave` 的语音资源目录是**编译期常量**（`picolangdir`，由
`$(datadir)/pico/lang` 展开；本包 `--prefix=/` 下即 `/share/pico/lang`），
上游未提供运行期覆盖选项。因此从 Conan 包直接调用该 CLI 时，需把包内
`share/pico/lang` 部署到该路径，或改用库 API 并以显式目录调用
`pico_loadResource`（消费者测试即采用后者）。

## References

- 上游仓库：https://github.com/naggety/picotts
- Android AOSP 原始源：https://android.googlesource.com/platform/external/svox/
- 固定提交：`21089d223e177ba3cb7e385db8613a093dff74b5`（与 Alpine
  `community/picotts` 的 `_commit` 一致）
