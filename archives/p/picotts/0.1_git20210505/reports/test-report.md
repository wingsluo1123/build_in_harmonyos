# 测试报告 — picotts 0.1_git20210505（HarmonyOS PC / OHOS aarch64）

## 1. 环境

| 项 | 值 |
|---|---|
| OS / Arch | HarmonyOS（`uname -s = HarmonyOS`，kernel 1.12.0）/ aarch64 |
| 构建三元组 | `aarch64-unknown-linux-ohos`（native，`cross_compiling=no`） |
| 编译器 | clang 15.0.4（`/data/service/hnp/bin/clang`），libc++ |
| Conan | 2.29.1（OHOS 适配版） |
| Profile | `ci/conan/profiles/ohos-aarch64`（`os=OHOS os.version=6.0 arch=armv8`） |
| 参考 | `picotts/0.1_git20210505@ohpcd/stable`，package_id `2832559a05a69c5c800f67f8a0fe6194d62b9f29` |

## 2. 层 1：上游官方测试

**上游注册用例数 = 0。** 清点证据：

- `pico/Makefile.am` 只声明 `lib_LTLIBRARIES=libttspico.la`（29 个 `lib/*.c`）、
  `bin_PROGRAMS=pico2wave`、`picolang_DATA`（12 个语音资源）与
  `libttspico_la_LIBADD=-lm`；**无 `TESTS` / `check_PROGRAMS` / `check-local` /
  `XFAIL_TESTS`**。
- 全树无 `*test*.c`、`*_test*.c`、`tests/*.sh` 或 ctest/pytest 注册文件；
  `pico/tests/` 仅一个 `data/` 目录，内含 8 个手工语料文本
  （`tests_regressions_es-ES.txt` 与 7 个 `xsampa_pico_man_*.txt`）。

`make -j1 check` 已在 `build()` 中执行，**rc=0**（零注册用例，空跑），
未删除该调用（TEST_QUALITY_SPEC §3.3）。

## 3. 层 2：test_package 消费者测试

| # | 用例 | 文件 | 断言 | 结果 |
|---|---|---|---|---|
| 1 | 库 API 端到端合成 | `test_package/picotts_engine_contract.c` | 26 | **26/26 通过** |
| 2 | 已安装 CLI 真实行为 | `test_package/cli_test.sh` | 17 | **17/17 通过** |
| | **合计** | | **43** | **43/43 通过（100%）** |

### 3.1 用例 1：库 API 端到端合成（26/26）

真实链接 `libttspico` 并调用公共 API：
`pico_initialize` → `pico_loadResource`(ta/sg) → `pico_getResourceName` →
`pico_createVoiceDefinition` → `pico_addResourceToVoiceDefinition` ×2 →
`pico_newEngine` → `pico_putTextUtf8` → `pico_getData`（循环回收 PCM）→
`pico_disposeEngine` → `pico_releaseVoiceDefinition` → `pico_unloadResource` ×2 →
`pico_terminate`。

实测输出：

```
INFO: synthesized 139008 bytes of PCM
CONTRACT: 26 assertions, 0 failed
CONTRACT-OK
```

断言覆盖：包内 `en-US_ta.bin` / `en-US_lh0_sg.bin` 可读、初始化返回 `PICO_OK`、
资源名非空、引擎句柄非空、合成 PCM 非空、采样格式为 `PICO_DATA_PCM_16BIT`、
全程数据格式稳定、16-bit 字节数为偶、资源回收各步返回 `PICO_OK`。

### 3.2 用例 2：已安装 CLI 真实行为（17/17）

对包内 `bin/pico2wave` 做真实执行 + 链接真实性校验：

- `readelf -d`：`NEEDED` 含 `libttspico.so.0`（本包产物）与 `libc.so`；
- `nm`：二进制内含 **51 个 popt 符号**——制品仓 `popt/1.19` 为静态包
  （`shared=False`），libtool 将 `libpopt.a` 静态链入，故 `NEEDED` 不含 `libpopt`；
- `--help` rc=0 且输出含 `Usage:`、`-w, --wave`、`-l, --lang` 与默认值 `en-US`；
- 缺 `--wave` → rc=1 且含 `Mandatory option: --wave=filename.wav`；
- 未知语言 `-l xx-XX` → rc=1 且含 `Unknown language: xx-XX` 并列出合法值；
- 非法选项 → rc=1 且含 `Invalid option`。

实测输出：

```
CLI-TEST: 17/17 assertions passed, 0 failed
CLI-TEST-OK
```

> 说明：新编译的消费者 ELF 在 OHOS 上先经 `binary-sign-tool -selfSign` 自签名，
> 运行时目录用可写的 `/data/storage/el2/base/cache`（libXext 1.3.7 同一模式）。

## 4. 构建与产物验证

- `conan create -pr:h/-pr:b=ohos-aarch64`：**成功**
  （`Package '2832559a05a69c5c800f67f8a0fe6194d62b9f29' created`）。
- `conan-verify`：**G0 / G1 / G2 / G3 / G4 全部 PASS** → `✅ 配方验证通过`。
- W3 本地 CI 模拟（`ci/conan/build_and_test.sh`）：`G0_RESULT=pass`、
  `L0_RESULT=pass`（L0i/L0j/L0k/L0m 全过）、`KC_RESULT=pass`、`JC_RESULT=pass`；
  L1a/L1b/L1c PASS、L5 PASS；**L4 为「patches 含危险函数」warn**
  （整文件替换型补丁载荷为 GNU `config.guess`/`config.sub` 副本，含 shell 惯用构造；
  已声明 `patch_type=portability`），按审计分级表属**非阻断**项。
- 产物：`lib/libttspico.so.0.0.0`（+ `.so.0`、`.so` 软链）、`bin/pico2wave`、
  `include/pico*.h`、`share/pico/lang/*.bin`（12 个）。
- R26：`/lib`、`/lib64`、`/usr/lib` 下无 `libttspico*` → 非系统同名库，按 Conan
  默认动态链接（`--enable-shared --disable-static`），不污染系统库。

## 5. 未运行/受限项

- 上游用例：0 个，无可运行对象（清点证据见第 2 节）。
- `pico2wave` 的**完整合成**（CLI 端到端出 WAV）未在测试中执行：其语音资源目录
  是编译期常量（`picolangdir = $(datadir)/pico/lang`，本包 `--prefix=/` 下为
  `//share/pico/lang`），上游无运行期覆盖选项，且 OHOS `/` 只读无法在测试中落到
  该路径。TTS 引擎功能本身已由用例 1 用显式目录完整验证。
- 本地 W3 需两项环境规避（与本包内容无关）：① 本 worktree 的 `origin/main`
  落后 HEAD 5199 个提交，JC6 会误判整仓 2485 个包为「本 PR 变更」，故以
  `JUNK_PR_DIFF`（CI `checkout-pr` 同语义）传入只含本包的 diff；② 本机
  `github.com` 主站超时，由 W3 内置镜像预下载改写为 `file://` 构建（退出时已还原
  官方 URL）。

## 6. 结论

适配后测试用例 **43/43（100%）通过**；上游 0 用例已如实清点并附证据；
`conan-verify` G0–G4 全绿。达到路径 A「测试用例完整且全部通过」的要求。
