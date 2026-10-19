# sigutils 0.3.0 适配笔记（HarmonyOS PC, aarch64）

- 任务：contrib-10624（平台任务名 sigutils）
- 上游：https://github.com/BatchDrake/sigutils，tag v0.3.0
- 源码包：https://github.com/BatchDrake/sigutils/archive/refs/tags/v0.3.0.tar.gz
  - 实测 sha256=f39686bf78d7773f6e0305c27d7b5db7950b96dd40f89eefb307331daf49b0e9
    （codeload 下载后本地计算；`archive/refs/tags` 与 codeload 为同一字节流）
- License：LGPL-3.0-or-later（源码头声明 LGPL v3）
- 构建系统：cmake（bare cmake + OHOS NDK ohos.toolchain.cmake + Ninja，
  mgard/1.6.0 已合入骨架）
- 依赖（全部已在制品仓归档，W0 已核）：
  - libsndfile/1.2.2（REQUIRED，pkg_check_modules sndfile>=1.0.2；
    配方默认 fPIC=True 静态，可链入 libsigutils.so）
  - fftw3f/3.3.10（REQUIRED，pkg_check_modules fftw3f>=3.0；配方默认共享 .so）
  - volk>=1.0 可选：制品仓无 volk 包，上游 VOLK_FOUND=0 自动禁用
    （HAVE_VOLK 不定义），无需引入
- 适配路径：路径 A（基础适配）

## 上游源码审计

- 纯 C（project LANGUAGES C），add_library(sigutils SHARED) 只构建共享库，
  VERSION 0.3.0 / SOVERSION 1；安装头到 include/sigutils/sigutils{,/specific}
  与 include/sigutils/util；自带 sigutils.pc（Cflags -I${includedir}/sigutils
  -I${includedir}/sigutils/util -D_SU_SINGLE_PRECISION，Libs -lsigutils -lm）。
- `_SU_SINGLE_PRECISION` 决定 SUFLOAT=float，属 ABI 契约：消费者编译也必须
  带（package_info.defines 已声明，test_package 编译行同款）。
- CMakeLists 顶部 `include(CodeAnalysis)`（cmake/modules/CodeAnalysis.cmake
  在 tarball 内，FindCppCheck 缺失时软降级），不阻断。
- `-D__FILENAME__='"$(subst ...)"'` 为 make 语法 hack。~~Ninja 下作为字面量
  传入编译器，可编译（上游在 Ninja 用户下正常构建）~~
  **勘误（2026-10-16 真机第 1 轮实证，推翻上面括号内预判）**：CMake Ninja
  生成器把该串原样写入 build.ninja 的 FLAGS，ninja 解析即失败
  （`ninja: error: build.ninja:56: bad $-escape (literal $ must be written
  as $$)`），与 ninja 版本无关——$(subst ...) 是 make 函数语法，仅 make 能
  展开；Makefiles 生成器受 E074 阻断、事后 sed 改 build.ninja 违反 R6。
  处置=patches/0001-cmake-filename-ninja.patch（portability）：Ninja 生成器
  下跳过该 hack，走 sigutils/log.h:73-75 自带 `__FILENAME__="(no file)"`
  回退（仅日志域名失去文件名区分，外观性）；非 Ninja 生成器行为与上游
  逐字一致。补丁在 pristine tarball 上 git apply 验证过，结果与手工
  patched 树逐字节一致（sha256 657b02a3…）。
- cmake_minimum_required(VERSION 3.5.1) ≥ 3.5，设备 cmake 4.1.2 兼容，
  无需 CMAKE_POLICY_VERSION_MINIMUM。

## 上游测试清点（sutest，18 个注册测试）

| 模块 | 测试 | 数 |
|------|------|----|
| ncqo | su_test_ncqo | 1 |
| filt | su_test_butterworth_lpf | 1 |
| agc | su_test_agc_transient / _steady_rising / _steady_falling | 3 |
| pll | su_test_pll | 1 |
| costas/clock | su_test_costas_lock / _bpsk / _qpsk / _qpsk_noisy / su_test_clock_recovery / _noisy | 6 |
| detect | su_test_channel_detector_qpsk / _qpsk_noisy / _real_capture | 3 |
| specttuner | su_test_specttuner_two_tones | 1 |
| mat | su_test_mat_file_regular / _streaming | 2 |
| 合计 | | 18 |

- sutest 为 src/main.c 的测试主程序（SU_TEST_ENTRY 注册表源码审计 18 项），
  上游未注册 CTest add_test；配方直接运行构建树 sutest，runner 以进程
  退出码判定（`return !result`，18 项全过才 0）。
- **如实披露**：su_test_channel_detector_real_capture 在
  SU_CHANNEL_DETECTOR_SAMPLE_CAPTURE（gqrx 采样文件，tarball 不含）缺失时
  打印 "skipping test..." 并按上游源码语义返回通过——沿用上游设计，
  非本配方造假（与 tarsnap 网络用例 SKIP 同类口径）。
- matfile 两项测试向 cwd 写 regular.mat → sutest 运行目录设为构建树
  testrun/（可写），不污染源码目录。

## 配方关键决策（mgard/1.6.0 已合入骨架，逐条对应）

1. bare cmake + 自发现 ohos.toolchain.cmake（OHOS_NDK_HOME 或
   /data/service/hnp/ohos-sdk.org/*/native/build/cmake），绕开
   conan_toolchain 的 "System is unknown HarmonyOS"（ML-0035）；Ninja
   生成器 + `-j$(nproc)`（E074 jobserver fifo EPERM 只影响 make）。
2. 依赖经 generate() 写 sndfile.pc / fftw3f.pc shim（指向制品仓包，
   Libs 按包内 .so/.a 实存选择），PKG_CONFIG_PATH=shim 目录，
   PKG_CONFIG_EXECUTABLE=/data/service/hnp/bin/pkg-config（0.29.2）。
3. CMAKE_PROJECT_TOP_LEVEL_INCLUDES 预载 ohos-find-deps.cmake：
   CMAKE_FIND_ROOT_PATH_MODE_*=BOTH —— ohos.toolchain.cmake 用普通
   set() 设 ONLY，命令行 -D 压不住（mgard 真机第 3 轮实测，brotli
   先例），否则 FindPkgConfig 的 find_library 复查丢 -L。
4. E077：构建树 libsigutils.so 与 sutest 未签名运行报 Operation not
   permitted → 运行前 llvm-objcopy 剥 .codesign + binary-sign-tool
   -selfSign 重签；package() 对安装的 .so 同样重签（ML-0043）。
5. llvm-ranlib 显式注入 CMAKE_RANLIB（SDK native/llvm/bin 缺失，
   mgard 真机第 6 轮实测 Error 127）。
6. package_info 按上游 sigutils.pc 口径：includedirs
   include/sigutils 与 include/sigutils/util、defines _SU_SINGLE_PRECISION、
   libs sigutils、system_libs m、pkg_config_name sigutils。
7. test_package 不用 CMake（dcap/2.47.14 实证 device cmake 缺 HarmonyOS
   平台文件），直接 CC 编译链接 libsigutils.so，消费者断言 6 项（见下）；
   链接时加 -Wl,-rpath（安装包 lib + fftw3f 共享库目录）+ conanrun 的
   LD_LIBRARY_PATH 双保险（OHOS musl 的 ELF 解析可能忽略
   LD_LIBRARY_PATH，audiowmark 先例）。

## test_package 消费者断言（6 项，全部离线确定性）

1. ABI 握手：sigutils_abi_version() == SIGUTILS_ABI_VERSION(=1)，且
   sigutils_abi_check(1) 正常返回（不匹配会 abort）。
2. su_lib_init() 成功且 sigutils_api_version() 精确等于 "0.3.0"。
3. NCQO 常量振荡器：freq 0 / phase 0 → 64 次 read_i==±1e-4 内等于 1、
   read_q==0（上游 src/tests/ncqo.c 末块同款断言；freq 单位
   omega=PI*fnor 已按 sampling.h SU_NORM2ANG_FREQ 核实）。
4. NCQO 单位音调：fnor=1（omega=π）512 次 read_i 交替 ±1，
   mean≈0、峰峰值≈2（上游 ncqo.c 首块同款）。
5. Butterworth 低通（5 阶 fc=0.25，截止 ω=π/4）通带选择性：fnor=0.125
   复数音调经滤波后尾部 256 点实部 RMS ≈ 0.707（解析 |H(0.3927)|=0.9997），
   断言 0.6–0.75。
6. 同滤波器阻带选择性：fnor=1.5（ω=4.7124，混叠到 1.5708）尾部 RMS
   ≈ 0.0086（解析 |H|=0.0122），断言 < 0.1。
   两项联合抓住全零 stub 与直通 stub；阈值来自上游系数公式的解析
   响应（su_dcof_bwlp/su_ccof_bwlp/su_sf_bwlp 复算验证）。

## Windows 阶段已做 / 未做

已做（Windows，2026-10-16）：
- tarball 下载（codeload）+ sha256 本地计算；CMakeLists/tests/头/pc 模板
  逐项审计（本文全部数字均出自源码，非推断）；
- 配方与 test_package 全套编写；conanfile.py / test_package conanfile.py
  py_compile 语法检查；
- 依赖核查：libsndfile/1.2.2（fPIC=True 静态默认）、fftw3f/3.3.10（共享
  默认）均已在制品仓归档；
- 第 1 轮真机失败修复：patches/0001-cmake-filename-ninja.patch（pristine
  tarball git apply --check 通过、结果逐字节比对一致），conandata/manifest/
  conanfile/notes 同步登记。

未做（留 MateBook，勿在 Windows 代验）：
- L0j：`conan download sigutils/0.3.0`（预期不存在）；
- 依赖 R35：`conan download libsndfile/1.2.2`、`conan download fftw3f/3.3.10`
  二进制可用性核验；
- `conan create` + `conan test` 全流程（aarch64 OHOS 真机构建 + sutest 18 项
  + 消费者 6 断言）；
- `ohc-run.py finish sigutils 0.3.0 built`（写 .ci-result.json，禁手改）；
- W4 审计（pre_pr_audit.py generate → 独立审计子任务 → report，P0/P1 清零）。

## 真机验证记录

### 第 1 轮（2026-10-16，SHA 42242ca7c443acb9c3e2dcb940672db353aa7faa）——构建失败

- 通过：交接核对（分支指针一致、diff-tree 仅 9 文件）、L0j（RC=1，
  与不存在包对照实验同报错）、R35（libsndfile/1.2.2 fPIC=True 静态、
  fftw3f/3.3.10 shared=True 均可取得）；
- configure 阶段全部正面证据：sndfile.pc/fftw3f.pc shim 被
  pkg_check_modules 命中（Found 1.2.2 / 3.3.10）、volk 自动禁用、
  CppCheck 软降级、FIND_ROOT_PATH_MODE BOTH 预载生效；
- **失败**：Ninja 生成 `ninja: error: build.ninja:56: bad $-escape`
  ——根因与处置见上方勘误（0001 补丁）；
- sutest 18 项与消费者 6 断言均未运行，不计通过；finish/W4 未执行。
- 环境注记：设备默认 profile 缺 os.version，真机构建必须用
  ci/conan/profiles/ohos-aarch64（finish 内部 conan_verify 自动携带）。

### 第 2 轮（2026-10-16，SHA 7fe03969073d26900282c4c611c6d736b47311ac）——构建通过，sutest 未过

- 通过：交接核对（fast-forward 至新 SHA，diff-tree 恰 5 文件）、L0j、R35、
  0001 补丁 Apply（build.ninja 'subst' 计数=0，第 1 轮根因消除）、
  configure 全绿、libsigutils.so 与 sutest 产出并签名可运行；
- **失败**：sutest 18 项中 t0/t4/t12/t13 四项断言失败 + t15
  specttuner 满核空转 ≥18 分钟被取证终止（详见下方根因定位）；
  消费者 6 断言、finish、W4 未到达/未执行。
- 同轮主动整改（isa-l 2.32.0 真机第 1 轮审计同类项）：conandata.yml 删
  gh-proxy.com 镜像行仅留官方 URL（R39/PF7）；test_package conanfile 的
  /tmp 硬编码回退改显式失败（R10）。

## 第 2 轮失败的根因定位（Windows 本地实证，2026-10-16）

方法：在 Windows x86 (MinGW gcc 14.2) 以本地编写的最小 FFTW/sndfile
shim 复现构建并运行完整 sutest；再用真 FFTW 3.3.5 (x86_64 DLL) 复测；
另做双精度（不加 -D_SU_SINGLE_PRECISION）对照构建。真机上 4 项失败 + 1
挂死在 x86 float / x86 double / 有无 -ffast-math 下逐字复现，与编译器
浮点标志、精度、平台均无关——全部为上游 sutest 自身缺陷（上游 CI
cmake.yml 只构建、从不运行 sutest，缺陷因此从未暴露）：

1. **t0 ncqo（两处叠加）**：
   - 库缺陷：`su_ncqo_read_i/q` 先返回上一步缓存的 cos/sin 再推进相位，
     而 `su_ncqo_set_phase` 只改 phi 不刷新缓存 → set_phase 后第一次
     read 返回旧相位的陈旧值（实测 step3 mean=±1/N=7.63e-6、pp=1.0，
     恰为陈旧 ±1 单样本贡献）。库内无其他 set_phase 调用方（pll 用
     inc_phase，另一函数），修复爆炸半径为零。
   - 容差缺陷：断言用 SUFLOAT_THRESHOLD=1e-15，而单精度下
     sin(pi_f)=-8.74e-8（float 的 π 不精确），全周期采样正弦均值
     下限即 |sin(pi_f)|/2≈4.4e-8，双精度构建实测也仅 6.1e-17——
     1e-15 在 float 下数学不可达。1e-15 系双精度时代语义残留。
2. **t4 agc_steady_falling（测试笔误）**：check_peak 检查的是 `input`
   而非 AGC 输出 `output`。input 由 `0.2*floor(5-5p/N)`（整型除法）生成，
   前 1/5 段振幅=1.0（实测窗内 peak=1.00586），永远越出期望带
   [0.63,0.77]；对照 t3（rising）把 AGC 输出原地写回 buffer 再检查所以
   能过。修复改为检查 output（实测 output peak=0.70265 落带内）。
3. **t12/t13 channel_detector（测试遗漏参数）**：params 用
   sigutils_channel_detector_params_INITIALIZER（mode=SPECTRUM）且未设
   mode，而 exec_fft 的 SPECTRUM 分支只算频谱图、从不调用
   perform_discovery/find_channels（detect.c exec_fft L972-990）→ 信道
   列表恒为空（实测 channels=0，PSD 本身正常：峰 bin205=12512Hz 与载波
   吻合）。补 `params.mode = SU_CHANNEL_DETECTOR_MODE_DISCOVERY` 后实测
   检出信道 fc=12502Hz、snr=48.9dB、valid=1，lookup 命中。
4. **t15 specttuner 真机挂死（FFTW_MEASURE 规划病态，结构性证据）**：
   detect.c 全部用 FFTW_ESTIMATE（t12/t13 真机瞬时完成），specttuner.c
   8 处 plan 全用 FFTW_MEASURE（t15 挂死且一个 Append 都未输出——卡点在
   su_specttuner_new/open_channel 的规划阶段）。x86 真 FFTW 下 MEASURE
   规划 0.146s 正常、t15 全程 3.5ms，判定为 OHOS aarch64 fftw3f/3.3.10
   构建上的规划器病态（该构建设备侧取得，本配方无法修改其构建）。
   处置=0004 补丁 MEASURE→ESTIMATE（与 detect.c 既有选择一致，规划质量
   对本用例正确性无影响）；待真机第 3 轮复核确认。

补丁（均针对 pristine tarball 生成、git apply 验证）：
- 0002-ncqo-setphase-cache-refresh.patch：set_phase 刷新 cos/sin 缓存
  （库修复，库内唯一调用方即测试）；
- 0003-sutest-single-precision-fixes.patch：ncqo 容差 1e-15→1e-6f（附
  单精度下限注释；step1 的精确断言保留原样）、agc t4 input→output、
  detect t12/t13 mode=DISCOVERY（仅测试文件）；
- 0004-specttuner-fftw-estimate.patch：specttuner.c 8 处 MEASURE→ESTIMATE。

本地验证（Windows x86，真 FFTW 3.3.5 + 最小 sndfile shim）：pristine
tarball + 3 补丁 git apply → 全套构建 → sutest **18 项 0 失败，退出码 0**
（t14 无采样文件按上游语义自跳过计通过）。文件级自检：apply --check +
apply 后全绿。双精度对照构建亦无回归（仅诊断用，非交付配置）。

## 预期风险

- t15 挂死根因为 MEASURE 规划病态系结构性推断（ESTIMATE/MEASURE 对照 +
  x86 真 FFTW 正常），真机第 3 轮以"t15 完成 + 无 Append 前不再空转"
  复核；若仍挂死，下一嫌疑为设备 FFTW 构建的规划器线程/时钟问题，
  届时在真机上用 `FFTW_MEASURE` 单独探针定位；
- 设备上 pkg-config 版本 0.29.2 对 shim 的 Requires 字段无要求（shim 不写
  Requires），FindPkgConfig 复查依赖 CMAKE_FIND_ROOT_PATH_MODE 放宽片段
  （既有真机实证）。


## 第 3 轮真机结果（SHA bdc79054bd）与本轮整改

真机第 3 轮（2026-10-17 报告）：交接核对、L0j 查重（E477 反控逐字
一致，未发布）、conan create 前段（4 补丁全 Apply、configure 命中、
主包构建安装签名成功）全部通过；**上游 sutest 18/18 全过、退出码 0**
——第 2 轮全部失败项真机实证修复：t0/t4/t12/t13 转绿，t15 specttuner
由挂死变毫秒级完成（构建内 2.456 ms、复跑 2.437 ms，Append 输出 60+
行），0004 的 MEASURE→ESTIMATE 假设成立。

唯一阻断为消费者测试编译：`block.h:26: 'util.h' file not found`。
根因在 test_package/conanfile.py 的手写 direct-CC 编译命令，缺两层
include（缺陷历史性地被第 1/2 轮的 sutest 失败挡住从未到达，与 3 个
补丁无关；主配方 package_info() 两层 includedirs 正确，无需改动）：
1. -I<inc>/sigutils/util——上游 sigutils.pc Cflags 本就两层，命令漏传；
2. -I<fftw3f 包>/include——公共头 types.h #include <fftw3.h>，上游 .pc
   无 Requires 行（常规系统靠 /usr/include 兜底），conan 常规消费者经
   依赖图传播 cpp_info 获得，手写编译必须显式收集。

真机修复探针（r3-fixprobe，不改仓库）补齐两层 -I 后 test.c 编译 RC=0、
6 断言全 ok、RUN_RC=0——修复方向已真机实证。

本轮整改（仅 test_package/conanfile.py）：build() include 集合改为
sigutils 两层（主层缺失或 util 层缺失均 fail-closed）+ 显式收集
fftw3f 的 cpp_info includedirs（组件级一并收集，含包内探测兜底与
fftw3.h 存在性终检）；libsndfile 公共头无引用，不加入。按复验规则，
该改动影响构建/门禁 → 新 SHA 交 MateBook 全量重走 conan create +
finish + W4 审计。

## 第 4 轮真机结果（SHA 70351d3ca8）与 manifest 同步

真机第 4 轮（2026-10-17）全部门禁通过：conan create（含 --build
强制源码重建，4 补丁全 Apply、configure 命中、39 目标构建打包）
RC=0；上游 sutest 18/18、失败 0、跳过 0、退出码 0（首跑与重建后
两轮一致；样本文件在位，t14 未触发自跳过）；消费者测试编译 INC
三层实测（sigutils 两层 + fftw3f 传递层）、6 断言全 ok；finish W3
门禁全绿（.ci-result.json 工具生成，W3 的 gh-proxy 回写按 PF7 备份
还原不采纳）；W4 独立审计 verdict=pass、P0=0、P1=0（P2×3、P3×3
不阻塞）。

本轮（2026-10-17）按审计 P2 建议同步 manifest 陈旧文案，仅 2 文件：
- manifest.yaml upstream_tests.notes：删除"通过数待真机预检 evidence
  回填"，回填实测 18/18（失败 0、跳过 0、退出码 0）；自跳过描述改为
  条件式（本轮样本在位未触发）；
- test_package/MANIFEST.yml 对应注释行同口径更新。
conanfile.py requirements() 顺序风格项（P2）不采纳，纯风格不值得一轮
SHA 迁移。按复验规则，manifest 非默认纯文档 → 新 SHA 交 MateBook
第 5 轮全量重验（create 重建 + sutest + 消费者 + finish + W4）。
