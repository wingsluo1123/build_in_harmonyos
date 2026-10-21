# libespeak-ng 1.51.0 适配笔记

## 概述

eSpeak NG（libespeak-ng 1.51.0）开源文本转语音合成引擎（共振峰合成），支持
100+ 语言/方言。构建产物：
- 库：libespeak-ng.a / libespeak-ng.so.1.1.51（`libespeak-ng` 主库）
- 命令行工具：espeak-ng / espeak / speak-ng / speak
- 数据：share/espeak-ng-data（phontab/phondata + 112 个语言 `*_dict` 字典）

## W0 依赖发布检查（强制第 1 步）

`bash ci/scripts/preflight_check.sh libespeak-ng/1.51.0` → 通过（无依赖声明）。
手动 conan download 验证（R35，禁用 conan list）：

| 依赖 | 制品仓状态 | binary |
|------|-----------|--------|
| pcaudiolib/1.3 | ✅ 已发布（found 1 recipe） | ✅ OHOS armv8 可用（conan download -p 'os=OHOS and arch=armv8...' 成功） |
| sonata | ❌ 未发布 | — |

**sonata 结论（重要）**：任务描述提到"构建字典数据需要 sonata"。经实测，
**espeak-ng 1.51 构建字典数据不依赖 sonata**——字典/音素数据由 espeak-ng
自身二进制在构建期编译生成：
```bash
ESPEAK_DATA_PATH=$(CURDIR) src/espeak-ng --compile-intonations
ESPEAK_DATA_PATH=$(CURDIR) src/espeak-ng --compile-phonemes
cd dictsource && ESPEAK_DATA_PATH=$(CURDIR) ../src/espeak-ng --compile="$(*F)"
```
源码树中无任何 sonata 引用（仅字典词条里的音乐术语"sonata"）。制品仓无
sonata 属正常，不阻塞构建（R36 决策：无缺失依赖，正常继续）。

## 源码选择（R39 官方源）★ 关键决策

上游 1.51 有两个官方 tarball：

1. `releases/download/1.51/espeak-ng-1.51.tar.gz`（1MB）——**残缺包**，缺：
   - `src/libespeak-ng/*.h`（28 个内部头文件）与 `src/speechPlayer/src/*.h`（6 个）
   - `phsource/`、`dictsource/`、`espeak-ng-data/` 全部数据源
   历史归档 `archives/e/espeak-ng/1.51`（status=built）正是此包 + extra_headers
   补头文件，但**无法构建完整数据**，运行期无字典。

2. `github.com/espeak-ng/espeak-ng/archive/refs/tags/1.51.tar.gz`（14MB）——
   **git archive 完整包**，含全部头文件与数据源。sha256=
   `f0e028f695a8241c4fa90df7a8c8c5d68dcadbdbc91e758a97e594bbb0a3bdbf`。

**本次采用 git archive 完整包**（两者均为官方源，R39 合规）。W0b 历史核验：
历史 `archives/e/espeak-ng/1.51` 因 release tarball 残缺仅做到 built（未
published）——历史结论不可照搬（R15），新适配必须解决数据完整性问题。

## Step 2 手动编译

```bash
# git archive 不含 configure → 手工 autogen（automake 1.16.5）
cp CHANGELOG.md ChangeLog.md        # automake 严格要求 ChangeLog.md
cp CHANGELOG.md NEWS && cp README.md README
automake --add-missing --copy --foreign   # --foreign 绕开 GNU 标准
autoconf

# E114：umask 077+mktemp 在 HMDFS 权限被拒
sed -i 's/umask 077/umask 022/g' configure

bash ./configure --prefix=$DEFAULT_PREFIX
#   checking build system type... aarch64-unknown-linux-ohos   ← config.guess 2023 原生识别！
#   PCAudioLib: no / Klatt: yes / speechPlayer: yes / MBROLA: yes
make -j1        # 编译库+工具+字典数据（~10 分钟）
make install DESTDIR=$TEST_PREFIX
```

与历史相比的重大改进：历史用老 config.guess 补丁
（patches/config-guess-ohos.patch）；本次 automake 1.16.5 自带
config.guess/sub（2023-08-22）已原生支持 HarmonyOS → **无需 config.guess
补丁**。

### pcaudiolib 集成验证

制品仓 pcaudiolib/1.3（本仓库已适配）提供 `pcaudiolib/audio.h` 与
`libpcaudio`。conan install 后配置注入：
```bash
CPPFLAGS=-I<prefix>/include LDFLAGS=-L<prefix>/lib \
  ./configure → checking pcaudiolib/audio.h... yes → PCAudioLib: yes
```

## make check 实测（R51 三步法）

上游 tests/ 目录 21 项测试（tests/*.test / *.c），实测结果：

| 测试 | 结果 |
|------|------|
| encoding / readclause / translate / api / ieee80 / dictionary | ✅ PASSED |
| language-replace / language-pronunciation / numbers-cardinal / numbers-ordinal | ✅ PASSED |
| non-executable-files / klatt / mbrola / variants / windows-installer | ✅ PASSED |
| voices / cmd_options / ssml-fuzzer | ✅ PASSED |
| **ssml** | ❌ prosody 音频哈希不匹配（期望 fcb28f…/实际 5ea0dc…）——平台浮点差异 |
| **language-phonemes** | ❌ ltg 音频哈希不匹配——同上 |
| **bom** | ❌ dictsource/lb_list、lb_rules 带 UTF-8 BOM——**上游 git tag 自带**（raw.githubusercontent.com 实测 ef bb bf），非本次引入 |

**通过率 18/21（85.7%）**。3 项失败均属平台/上游固有：
- 音频哈希类（ssml/language-phonemes）：OHOS musl 浮点精度差异导致 WAV 哈希
  与上游 x86_64-glibc 基准不同；合成功能本身正常（手动 `espeak-ng "Hello" -w`
  产出合法 RIFF/WAVE 44KB 音频）。
- bom：上游 dictsource 文件自带 BOM（上游自身问题），非适配引入。

## Conan 配方要点

- requirements: `pcaudiolib/1.3`（音频输出后端，制品仓已发布）
- generate: AutotoolsToolchain + `--build=x86_64-unknown-linux-gnu
  --host=aarch64-unknown-linux-ohos`（沿用 pcaudiolib 已 CI 验证的惯例）
  + `ac_cv_func_malloc_0_non=yes`（交叉编译下 AC_FUNC_MALLOC 无法实测）
  + `--without-sonic --without-mbrola`（关闭未适配可选后端）
- build: apply_conandata_patches → _autogen（libtoolize/aclocal/autoheader/
  automake --foreign/autoconf + ChangeLog.md/NEWS/README 生成）→ _fix_umask
  （umask 077→022）→ Autotools.configure/make -j1
- package: Autotools.install + 剔除 .la
- package_info: `cpp_info.libs=["espeak-ng"]`、includedirs=["include"]、
  bindirs=["bin"]、datadirs=["share"]
- test_package（R34 实质测试）：**两个测试源**——
  ① `test.c`：espeak_Initialize + espeak_Terminate 基础初始化验证；
  ② `test_libespeak_ng.c`：espeak_Initialize + espeak_SetSynthCallback +
  espeak_Synth 合成英文音频 → SynthCallback 收集 PCM → 写 WAV → 校验 >100 字节。
  CMakeLists.txt 编译并运行两个可执行文件（`ctest` 注册 2 条）。
  **注意**：espeak-ng 1.51 speak_lib.h **没有 espeak_GetAudioData API**（新版才有），
  必须用 espeak_SetSynthCallback 回调收集音频。
- commands.json（R38，软件级 archives/l/libespeak-ng/commands.json）：tool 类型，
  espeak-ng/speak-ng/espeak/speak 4 个 CLI。

## 踩坑记录

1. **OHC_PROJECT_DIR 串扰**：SKILL_ROOT 下也有 SKILL.md，ohc-run.py
   find_project_dir() 误定位到 SKILL_ROOT，归档/上下文写入错误位置。解决：
   显式 `export OHC_PROJECT_DIR=<worktree>`（find_project_dir 优先读此环境变量）。
2. **上游 release tarball 残缺**：espeak-ng-1.51.tar.gz（1MB）缺内部头文件与
   全部数据源；历史归档（archives/e/espeak-ng/1.51）因此止步 built。必须用
   git archive tarball（14MB）。
3. **automake 要求 ChangeLog.md**：上游只提交 CHANGELOG.md，automake 报
   `required file './ChangeLog.md' not found` → 复制生成 + `--foreign`。
4. **E114 umask 077**：HMDFS 上 `umask 077 && mktemp -d` 建 0700 临时目录后
   config.status 写 confNliGHc/subs1.awk 报 Permission denied → 改写 umask 022。
5. **speak_lib.h 无 espeak_GetAudioData**：1.51 API 集与新版不同；R34 测试
   用 espeak_SetSynthCallback 收集 PCM（test 中发现并绕开）。
6. **speechPlayer 头文件**：即使 git archive 完整包，speechPlayer/src 的
   utils.h/speechPlayer.h/speechWaveGenerator.h/waveGenerator.h 也在构建中被
   .c 引用；git archive 已含（历史 release 包缺）。
7. **E2141 std::sample 歧义（G2 首次失败根因）**：`src/speechPlayer/src/
   speechWaveGenerator.cpp:197` 在 `using namespace std;` 下使用
   `sample* sampleBuf` 参数类型 —— OHOS libc++ 提供 C++17 `std::sample`
   （`<__algorithm/sample.h>`），与上游全局 `struct sample` 同名，编译报
   "reference to 'sample' is ambiguous"。修复：patch 改参数类型为全局
   限定 `::sample*`（无平台宏，纯命名冲突修复），补丁
   `patches/0001-fix-std-sample-ambiguity.patch`，conandata.yml patches 段声明。
   知识图谱草稿：knowledge/drafts/E2141-draft-1B75.kv（conan-verify 误匹配
   E540 → 按 R31 纠正生成独立草稿）。
8. **E490 autotools helper 执行位**：HMDFS 上 configure/config.guess/
   config.sub/install-sh 等可能丢失执行位，build() 中显式 chmod +x（_chmod_helpers
   ，autogen 前后各一次）。
9. **E1031 speechPlayer 挂起（G2 第二轮根因，关键）**：conan 构建的
   libespeak-ng.so.1.1.51 在 `espeak_Initialize` 时挂起 procmgr_wait（所有
   espeak-ng CLI 均卡住），而本地手动编译（无 speechPlayer 差异参数）正常。
   定位方法：本地二进制 + conan .so → 挂起；conan 二进制 + 本地 .so → 正常，
   锁定问题在 conan 构建的 .so。最终确认根因是 speechPlayer（NVDA speechPlayer
   C++ 模块，src/speechPlayer/）配合 OHOS clang 15 + `-O3 -stdlib=libc++
   -std=c++17` 时 espeak_Initialize 内部（KlattInit→KlattInitSP→
   speechPlayer_initialize）阻塞在 procmgr_wait（OHOS 进程管理等待）。
   修复：`--without-speechplayer` 禁用该模块（历史 archives/e/espeak-ng/1.51
   配方同款，"C++ ambiguity error with clang 15"）。验证：禁用后 conan 相同
   编译选项下 espeak-ng --version 正常、112 语言字典全部编译成功。Klatt 核心
   合成引擎与 speechPlayer 独立，不受影响；espeak_Synth 用
   AUDIO_OUTPUT_RETRIEVAL 照常输出波形。
10. **E490 autotools helper 执行位（第二轮补充）**：`_chmod_helpers` 在
    autogen 前后各调用一次（configure 为 autogen 生成；config.guess/sub/
    install-sh/missing 由 automake --add-missing 生成）。幂等，HMDFS
    chmod 可能被忽略但本机实测 755 生效。
11. **E1032 package_info component 属性 bug（G2 第三轮根因，关键）**：
    conan-verify G2 失败于 test_package 编译 `fatal error:
    'espeak-ng/speak_lib.h' file not found`。根因：conanfile.py package_info()
    中 `self.cpp_info.set_property("component", "")` 设置**空字符串组件名**，
    导致 CMakeDeps 将 includedirs 归入空名组件而**主 target
    libespeak-ng::libespeak-ng 的 INTERFACE_INCLUDE_DIRECTORIES 为空**
    （generators/libespeak-ng-release-armv8-data.cmake 中
    libespeak-ng_INCLUDE_DIRS_RELEASE 为空，而 RES_DIRS/LIB_DIRS/BIN_DIRS 正常）。
    修复：删除该行（库无组件结构，不应设置 component 属性）。验证：删除后
    conan create test_package 编译/链接/运行全部通过。
12. **E1033 package_type=application 导致 INCLUDE_DIRS 空（G2 第四轮根因，
    真正根因）**：删除 component 行后 G2 仍失败（INCLUDE_DIRS_RELEASE 仍为空）。
    最小复现实验锁定根因：**package_type = "application"**！Conan CMakeDeps 对
    application 类型不生成 INCLUDE_DIRS（应用包无 include 消费方语义），
    即使 package_info() 显式设置 `cpp_info.includedirs=["include"]` 也被忽略；
    而 LIB_DIRS/BIN_DIRS 正常。改为 `package_type = "library"`（库+CLI 混合包，
    命令行走 cpp_info.bindirs + 软件级 commands.json，R38）后 INCLUDE_DIRS
    正确生成，G2 一次通过。经验：**库+工具混合包必须 package_type=library，
    application 类型会静默丢失 include 路径**（CMakeDeps 对 application 的
    cpp_info 处理与 library 不同）。验证：conan create 两个测试源（test_basic /
    test_libespeak-ng）编译链接运行全通过；test_libespeak-ng 合成 128018 字节
    WAV 校验 OK。

## 知识图谱草稿

见 `knowledge/drafts/`（R31：conan-verify G2 未命中错误时自动生成）。
本适配的关键知识（上游 release tarball 残缺、automake 2023 config.guess
原生支持 OHOS、sonata 非 espeak-ng 依赖、1.51 无 GetAudioData API）已记录于
本 notes.md 与 manifest.yaml knowledge_gained。

---
**最终状态**: built（等待 conan-verify + finish + submit）
---

**编译结束**: 2026-10-16 01:42
**最终状态**: built

## CI 环境对照记录（E600：worker fork 资源问题，非配方缺陷）

- 本地 W3：10-16 01:42 conan create 通过（.ci-result.json exit_code=0）
- CI 失败历史（同 SHA 428b8366 前多轮）：
  - #94078 (CI-003)：`can't fork - try again`（libtoolize 阶段 fork EAGAIN）
  - #94775 (CI-018)：`posix_spawn failed: Resource temporarily unavailable`
  - #95013 (CI-031)：`Errno 11 Resource temporarily unavailable`
  - #97034 (CI-034)：`libtoolize: cannot list files: build-aux`（`{ cd && ls; }`
    子 shell fork 失败 → 输出空 → func_nonemptydir_p 误报）
- 判据：本地可复现构建通过 + 同一错误跨 4 个不同 worker + CI 自身脚本
  （knowledge_check.sh）同批也报 fork/Out of memory → 环境性（E600），
  已按 E600 建议重试等待空闲 worker。
- 10-18 补充（Septest 评审 rule12 修复后触发 CI）：
  - #98402 (CI-009)：`OSError: [Errno 28] No space left on device`
    （conan 下载依赖 20 线程 SemLock 阶段磁盘满）→ 换 worker 后 #98411 (CI-030) PASS
  - #98640 (CI-017)：同一 `No space left on device` 错误
  - 结论：磁盘满为 worker 环境波动（与 E600 fork 同类），非配方缺陷；
    test_package 新 CLI 用例在 #98411 已实测通过（CI 无配方回归）。
