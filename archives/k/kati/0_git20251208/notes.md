# kati 0_git20251208 适配笔记(notes.md)

任务:开源鸿蒙PC专项积分赛 · kati 0_git20251208(contrib-7754)|分支 feat/kati-0_git20251208|路径 A(基础适配)+ 路径 B 素材见下

## 一、上游与版本锚定

- 上游:google/kati(GitHub),无 tag 发布;版本 0_git20251208 的打包日
  (2025-12-08)前最后一个提交为 ec1814e15fd4(2025-12-02),conandata 以
  完整 SHA codeload archive 锚定(官方源,R39)
- sha256 双源核验 ✅(2026-10-08):短 SHA 与完整 SHA 的 codeload tarball
  字节一致,`9b4249fbdf967d22a928160a91299917ede9a3f62b0abbeddd08197f3e1f9c35`
- ⚠ 待核:任务页 sourceUrl 若指向其他提交,以平台为准重锚(尚未核对,
  认领后未取得 sourceUrl)

## 二、构建(W0:零外部依赖)

- Makefile.ckati 纯 C++17(26 个 src/*.cc),`make all` = ckati + 3 个单测二进制
- version.cc:tarball 无 .git → KATI_GIT_DIR 为空 → KATI_VERSION="unknown"
  (Makefile.ckati:104-113 逻辑已核),无需处理
- **KATI_CXXFLAGS 覆盖**:上游含 `-march=native`,OHOS aarch64 clang 对其
  支持不可靠 → 命令行整体覆盖为 `-O2 -g0 -W -Wall -MMD -MP -DNOLOG`
  (保留上游 -MMD -MP;`-std=c++17` 由上游规则自带,不经 CXXFLAGS)
- `-lrt -lpthread`:上游 ifeq(Linux) 加,musl OK
- Rust 重写(src-rs/rkati)、Go harness(run_test.go)、benches 均不在默认
  构建路径,配方忽略

## 三、测试(上游无 Go → 忠实移植差分 harness)

上游测试 = ① 3 个 C++ 单测(find_test/ninja_test/strutil_test,自带框架,
确定性,build() 内硬失败);② testcase/ 296 个 .mk **差分用例**(GNU make
与 ckati 各跑一遍,归一化比对 stdout + 产出文件名,`# TODO` 口径 xfail)。

- **0001 补丁(find_test 平台可移植性,真机第 1 轮实证)**:find_test
  夹具在同级目录建 top/a(文件)与 top/A(目录),整个测试假设文件系统
  大小写敏感;OHOS 平台 FS 大小写不敏感 → 夹具无法成立、native find 与
  模拟器结果必异(真机 2026-10-08 实证,ninja_test/strutil_test 全过)。
  补丁在 FindUnitTests 开头运行时探测(mkdir P + touch p 后 stat 判
  S_ISDIR):大小写不敏感 → 打印 SKIP 并 exit 0(显式标记,不计通过);
  大小写敏感 FS 行为零变化(探针目录即刻清除,ext4 容器回归验证)。仅
  测试代码,库与 find emulator 零改动。MANIFEST/PR 披露口径:真机
  find_test=SKIP(平台 FS 限制),非通过。

- **tests/run_testcases.py**:run_test.go 的 Python 逐行移植(非 ninja/
  非 rkati 路径)——同调用参数(`make [-s] [tc] SHELL=...` /
  `ckati --use_find_emulator [-s] SHELL=... [tc]`)、同归一化正则链
  (normalizeMakeLog/normalizeKati 全套)、同文件清单忽略规则、同 check
  语义(xfail 反向断言)、同 "make 侧含 FAIL 即 harness 报错"
- SHELL 参数化:上游写死 /bin/bash,OHOS 无此路径 → 由 CONFIG_SHELL 注入
- tests/xfail.txt:平台性失败显式钉住(逐条原因),**已按 2026-10-08 真机
  第 1 轮证据回填、并按 2026-10-09 第 2 轮 gate-PATH 取证解钉 4 项**
  (76 整文件 + 5 tc,见五之真机小节);禁止空泛豁免。
  格式 `<name>[ testN...] <原因...>`:裸文件名=整文件钉住;尾部 `testN`
  记号(精确匹配 test\d*)=tc 级钉住,用于部分败文件(整钉会使其通过 tc
  变 XPASS 使 rc=1)——harness 对上游 run_test.go 的可移植性扩展,语义与
  # TODO 一样严格(xfail 而输出一致=XPASS=失败)。
  归一化扩展(NOISE_CWD,双侧生效):OHOS 上 bash 5.3 的 getcwd 回退噪声
  (`shell-init:/chdir: error retrieving current directory: ...`)行数随
  子 shell 环境翻动(实证翻动 find_command.mk[test1]),零 make-vs-kati
  语义信息 → 归一化剥离,与上游剥离 Entering/Leaving directory 同类;
  getcwd 正常的平台(上游 CI、musl 容器)上为 no-op
- **tests/ 经配方 `exports = "tests/*"` 进真机构建树**,差分调用显式传
  `--xfail-file`(回填后生效)与 `--workdir`(构建树下,真机 /tmp 只读——
  ivar EROFS 先例);python3 发现顺序 PYTHON → PATH → 设备已知路径
  (/storage/Users/currentUser/usr/local/bin/python3, 3.12.9)
- submake 注入:上游 symlink 进沙箱;真机文件系统若不支持 symlink 则
  回退为沙箱内拷贝(语义等价,run_testcases.py 已带 fallback)
- 未覆盖:--ninja 变体(OHOS 无 ninja)、*.sh 用例(Go harness 的
  runKatiInScript 路径)、rkati 对比(Rust)——均如实写入 MANIFEST

## 四、test_package(消费者视角)

真实把 ckati 当构建解释器用:pattern rule + 自动变量 + 函数求值产出真实
文件并逐字节断言;二次增量运行不得重执行 recipe(kati 的 regen 检测是它
存在的意义);缺失先决条件的错误面断言。

## 五、Windows 预验证(非真机)

- Makefile.ckati 逻辑、version.cc 回退、harness 语义:源码级核对 ✅
- runner 语义与正则:与 run_test.go 逐行对照 ✅(预验证又修出三处偏差,见下)
- **Alpine 3.20(musl)Docker 容器预验证 ✅(2026-10-08,不代表真机)**:
  - `make all`(KATI_CXXFLAGS 覆盖去 -march=native)编译通过,4 个二进制齐全
  - 3 个 C++ 单测(find_test/ninja_test/strutil_test)全过
  - 差分套件:**total=355 pass=316 fail=15 xfail=24 xpass=0**
- 预验证暴露并修正的三处 harness 移植偏差(均已对齐 run_test.go):
  1. `normalize()` 漏了 circularRE 前置抽取(run_test.go:131-143,
     "Circular … dropped." 行先抽取置顶再比对)→ circular_dep 转绿
  2. 沙箱布局:上游是 `out/<name>/{make,kati}` **兄弟目录**(绝对路径类
     用例 curdir_var/realpath 依赖共享父目录)
  3. 每 .mk 文件一个沙箱对、testN **顺序共用同一目录**、先跑完全部
     make 侧再全部 kati 侧(run_test.go:442-486)→ order_only2 的
     MAKE-SIDE-FAIL 与 makefile_list 的 touch 顺序效应转绿/正确 xfail

### 差分失败归因(15 例,musl 容器实测;真机 make 版本不同分布会变)

| 类别 | 用例 | 根因 |
|---|---|---|
| kati 追加变量首空格语义 ×7 | cond_syntax、ifeq_without_parens、var_append、target_specific_var_append、makefile_list×3 | 对空变量 `+=` 后 kati 保留前导空格(`echo  PASS` 双空格),GNU make 剥离 |
| make 版本措辞 ×2 | test_version、err_word_non_numeric | kati 自称 MAKE_VERSION=4.2.1(main.cc:64)、沿用 4.2.1 的 word() 报错文案;容器 make 4.4.1,上游 CI 的 Ubuntu make 4.2.1 可对齐 |
| find emulator ×6 | find_command×5、escaped_wildcard[test2] | kati find emulator 与容器新版 coreutils find 的行为差异 |

- 结论:失败均为确定性、可归因的 make 版本/语义差异,非构建或移植错误。
  xfail.txt 仍留空——**按 MateBook 真机首跑的实测分布回填**(真机 make
  版本若为 4.2.1,措辞类两条预期转绿;首空格语义类与 find emulator 类
  预期仍需钉住,以实测为准)

### 真机第 1 轮(诊断轮,2026-10-08,MateBook 实测;非 Windows 推断)

环境:GNU make 4.4.1、bash 5.3.0(1)-musl、python3 3.12.9。差分套件
total=355 pass=241 fail=90 xfail=24 xpass=0;3 个 C++ 单测中
ninja_test/strutil_test 通过,find_test 因平台 FS 大小写不敏感失败
(→ 0001 补丁,见三)。90 例失败经全量 diff 取证逐簇归因为 7 类:

1. **错误前缀大小写 ×65**(纯 `Makefile:`→`makefile:`):OHOS FS 大小写
   不敏感,kati 的 FindFirstMakefie(main.cc:335-347)经 Exists("makefile")
   命中沙箱大写 "Makefile" 后以小写名报错;GNU make 以打开名报错。
   其中 2 例另有语义差:var_visibility_prefix_invalid_file_one(kati 与
   make 选中的变量/行不同)、var_visibility_prefix_implicit_define
   (make 静默空输出,kati 单侧报 visibility 错误)——原因改按实记。
2. **+= 前导空格 ×4**:cond_syntax、ifeq_without_parens、
   target_specific_var_append、var_append(与 musl 归因一致,平台无关)。
3. **getcwd 回退噪声 ×7+翻动**:bash 5.3 on OHOS 在子 shell 初始化时输出
   `shell-init:/chdir: error retrieving current directory: getcwd: ...`,
   行数随环境翻动。fail_ignore_error 家族 4 例的 diff 纯粹是 Error 行与
   噪声行的相对顺序 → **不钉,改为双侧归一化剥离**(NOISE_CWD,见三),
   归一化后预期转绿;find_command_sorted(噪声 vs kati 侧空行)与
   shellstatus 3 例(前缀差叠加噪声行数差)仍钉;find_command.mk[test1]
   的 run 间翻动(首跑 pass、验证跑 fail)即源于此噪声 → 归一化后转确定性。
4. **$(MAKEFILE_LIST) 小写名 ×3**:makefile_list[test1-3] 输出 `makefile`
   (kati 选中的小写名,FS 制品)+ 前导空格双因素。
5. **find emulator vs 真 find ×6**:escaped_wildcard[test2](展开结果
   `echo foo` vs `echo `)、find_command[test2-5](错误措辞 cd: xxx vs
   绝对路径、Symbolic link loop 行间空行等,均为确定性差异)。
6. **make 版本措辞 ×1**:test_version(真机 make 4.4.1 vs kati 自称 4.2.1;
   musl 轮的 err_word_non_numeric 真机上同为措辞类,归此)。
7. **测试夹具 FS 依赖 ×1**:find_test(见三,0001 补丁 SKIP)。

xfail 回填口径(自洽性约束:任何归一化/钉住组合下 xpass 必须=0):
- 移除草案中的 fail_ignore_error、fail_subshell_in_recipe、ignore_error、
  silent_ignore_error(归一化后输出一致,钉住会 XPASS);
- 首版 77 整文件 + 8 tc;**第 2 轮 gate-PATH 取证后解钉 4 项**(见下节),
  终版 76 整文件 + 5 tc(escaped_wildcard test2、find_command test2、
  makefile_list test1-3)。

### 真机第 2 轮(复验轮,2026-10-09,MateBook;交接 SHA 37bcc9eeb 未过门禁)

conan create 三次失败全部取证定位(报告 kati-r2-evidence/ROUND2-REPORT.md),
修复经真机确证跑 ×2 逐字一致(EXIT=0)后交回 Windows 出新 SHA:

1. **conandata patches 映射形式静默不应用**:本仓 Conan 2.x 的
   apply_conandata_patches 按列表读取 patches 键;37bcc9ee 的带键映射
   (`"0001-...": {...}`)迭代不出任何条目且不报错 → find_test 无补丁裸奔
   崩溃(Find emulator cannot handle 'find top/A/b')。修复=列表条目式
   (`- patch_file: ...`,与 libmtp D1 教训同族:条目必须 dict、外层是列表)。
2. **exports 不落构建树**:`exports = "tests/*"` 只进配方缓存;改
   `exports_sources = "tests/*"` + export_conandata_patches 补丁文件随源导出。
3. **workdir 深度破坏夹具契约**:上游布局约定 `<source root>/out/<name>/
   {make,kati}`,用例以 `../../../testcase/tools/` 相对深度引用夹具;
   build_folder/kati-diff 深度错位 → find_command.mk[test1] 走偏。修复=
   workdir = source_folder/out(严格对齐上游 run_test.go 布局)。
4. **解钉 4 项**:gate PATH(conanbuild,/data/service/hnp/bin 先于 /usr/bin,
   双侧解析到同一 GNU findutils)下逐 tc 归一化对比矩阵:find_command
   test1/3/5 与 find_command_sorted 双侧 EQUAL——第 1 轮证据 diff 是归一化
   前抓取,彼时误判为语义差。**保留 find_command.mk[test2]**:真残差
   (make 侧 bash getcwd 回退路径前缀 `/data/service/hnpcd: xxx:` vs kati
   模拟器纯 `cd: xxx:`,NOISE_CWD 正则不覆盖该行)。
   确证:total=355 pass=249 fail=0 xfail=106 xpass=0,×2 逐字一致。

教训沉淀:①conandata patches 外层键形式错误是**静默**失败面(无 Apply 行
即未打补丁);②exports vs exports_sources 语义分野(缓存 vs 构建树);
③沙箱相对深度是夹具契约的一部分,workdir 不可随意挪;④钉单证据必须以
归一化后的最终输出为准,归一化前抓的 diff 会混入噪声伪影。

### 真机第 3 轮(2026-10-09,SHA 494ced945;止于 test_package 缺陷)

第 2 轮 4 项修复**全部实证通过**:补丁 Apply 行出现、tests 落构建树、
workdir=out 布局、差分 **total=355 pass=249 fail=0 xfail=106 xpass=0**
(与 r3 预期逐字一致)、find_test=SKIP(照录非通过)、ninja/strutil=pass、
解钉 4 项零 XPASS。

create 整体 rc=1,唯一根因=**test_package/test.sh 既有设计缺陷首次暴露**
(该脚本自原始提交起从未被执行到;平台无关——GNU make 4.4.1 同病,双侧
对照留证 testpackage-defect/):

1. [1/3] `$(OUT)` 直接依赖 `$(SRC)`,目标图没有任何目标引用 message.mid
   → 模式规则永不实例化,"pattern rule did not produce message.mid" 必假。
2. [2/3] 注释假设"kati no-op 不打印 Nothing to be done 横幅"与实测相反
   (run1 全 @ 前缀静默 0 行,run2 反打 1 行横幅),旧"log 行数不增"断言必假。

修复(仅 test_package/test.sh,断言最终形态 Windows 定夺):
1. `$(OUT)` 改依赖 `$(subst .in,.mid,$(SRC)) rule.stamp`,.in→.mid→.txt
   依赖链成立,模式规则实例化;
2. [2/3] 改**直接计量 recipe 执行次数**:每个 recipe 向 recipe-runs.log
   追加标记行,no-op 重跑后行数必须仍为 3——regen 检测的直接断言,与
   横幅措辞解耦;同步改写两处错误注释。

**修复版已在 musl 容器以真实 ckati 端到端预验证:3/3 ALL TESTS PASSED
rc=0**(含 [3/3] 错误面 grep——该断言此前同样从未实测)。

教训:**消费者测试脚本必须在交接前真实端到端执行过**——test.sh 两缺陷在
Windows 阶段跑一次容器 e2e 即可源头拦截;断言注释中的环境行为假设(横幅
有无等)同样必须实测,不得按想当然落进断言。

## 六、路径 B 素材(知识库 0 命中,真机验证后沉淀)

1. **构建工具自举 + 参考实现差分**:构建工具类(make/构建器)在无 Go/
   专属 harness 的平台上,以"参考实现差分"做全量回归的方法论
   (参考实现 = GNU make 本就存在于构建机,零额外依赖)
2. **Go harness 的 Python 移植模式**:同正则/同语义移植的可审计性
   (逐行对照表),泛化其他 Go-harness 测试套件(kati 不是唯一)
3. 真机阶段补:musl 下 ckati 差分套件的失败分布与归因

## 七、遗留与风险

- 真机第 1/2/3 轮均已完成归因(见五三节真机小节):差分套件已在真机实证
  **fail=0/xfail=106/xpass=0**(pass=249);第 3 轮唯一遗留=test_package
  test.sh 既有缺陷(已修复并容器 e2e 预验证)。**第 4 轮待做**:新 SHA 下
  MateBook 全量复验(conan create/test → finish → G2 → 审计),预期
  create 全链 rc=0、find_test=SKIP、差分 249/0/106/0、test_package 3/3,
  以实测为准——任何偏离按取证回报,不得沿用旧结论
- 任务页 sourceUrl 未核对(见一)
- conandata sha256 已双源核验(见一,2026-10-08)
---

**编译结束**: 2026-10-10 15:57
**最终状态**: built
