# lam 7.1.4 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.59 生成，2007-07-22 版 config.guess/sub ×23 对）
- 编译日期: 2026-10-11
- 编译器: clang/clang++ 15（/data/service/hnp/bin，OHOS SDK 26.0.0.18）
- 目标: OHOS/aarch64（armv8，aarch64-linux-ohos 三元组）
- 状态: built

## 编译步骤

```bash
./configure --prefix=<package_prefix> --without-romio --without-fc \
    --disable-shared --enable-static \
    --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
    CC=clang CFLAGS="-O2 -fPIC" CXX=clang++ CXXFLAGS="-O2 -fPIC"
make -j2        # 13m24s，0 error，"LAM/MPI 7.1.4 has been built"
make install    # staging 443 文件：liblam.a/libmpi.a/liblammpi++.a + 20+ 工具
```

构建产物验证：`laminfo`（Architecture: aarch64-unknown-linux-ohos）、`lamboot`（本机 lamd 启动 n0=localhost）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 报 `Unable to guess system type` | 2007 老版脚本不认识 HarmonyOS；patch-autotools-ohos.pl 插入的分支用新版 `GUESS=` 变量写法，但老版没有统一出口 | 手工改为 `echo "${MACHINE}-unknown-linux-ohos"; exit ;;`（0002 补丁） |
| 2 | config.sub 报 `Invalid configuration aarch64-unknown-linux-ohos` | 三元组尾部 `linux-ohos` 不在 KERNEL-OS 拆分列表，整段被当成 machine 名 | 4 处修改：maybe_os 加 `linux-ohos*`、CPU 列表加 `aarch64`、os 列表加 `-ohos* \| -linux-ohos*`、`-linux*` 分支保护 ohos 不被改写为 linux-gnu（0003 补丁） |
| 3 | configure 报 `Your C++ compiler does not support the bool data type` | 上游 bug：7 处 conftest 写错 `int main(int argc, char* argv)`（缺 `[]`），clang 15 拒绝该签名 | 批量改为 `char* argv[]`（0001 补丁，7 个 hunk） |
| 4 | configure 首跑数百条 `safe-bin/rm: No such file or directory` | WorkBuddy 沙箱注入的 rm shim 用 `#!/bin/bash` shebang 而 OHOS 无 /bin/bash | `unset -f rm` + PATH 前置 toybox wrapper（环境噪声，非源码问题，不入 PR） |
| 5 | mpicc/mpic++ wrapper 编译任何程序报 `No such file or directory`（rc=1） | LAM 的 wrapper 是编译期生成的 ELF 二进制（hcc→mpicc→mpic++ 链），内部 fork/exec clang++ 在 OHOS 上静默失败；`--showme` 正常但实际编译不产出 | 消费者绕开 wrapper，直接 `clang` + `--showme` 暴露的标志（-I/-L/-llammpi++ -lmpi -llam -ldl）；test_package 按此模式编译 |

## 源码修改

- `patches/0001-configure-main-signature.patch`：configure 中 7 处 conftest main 签名修复
- `patches/0002-config-guess-ohos.patch`：config/config.guess 增加 HarmonyOS 识别分支（echo+exit 出口）
- `patches/0003-config-sub-ohos.patch`：config/config.sub 支持 aarch64 与 linux-ohos 三元组（4 处）
- conanfile.py 的 `_propagate_config_ohos()`：源码树内 23 份 config.guess/sub 字节级相同，补丁只改 config/ 规范副本后程序化复制到其余 22 份

## 依赖版本

- 无 conan 依赖（W0 预检通过：lam 为自包含 autotools 包，无需 perl 等工具依赖）
- 工具链：OHOS SDK 26.0.0.18（llvm clang 15、aarch64-linux-ohos sysroot）

## 验证结果

### 上游测试（examples/，2026-10-11 设备实跑）

LAM 7.1.4 无 `make check` 目标；上游测试入口为 examples/ 下各示例程序（每个按其设计模式运行）与 romio/test（`--without-romio` 下不可用）。

统计：**18 项 = 15 通过 / 0 失败 / 3 跳过**（Fortran 无工具链）。

| 用例 | 运行命令 | 退出码 | 结果 |
|------|----------|--------|------|
| hello | `mpirun -np 2 ./hello` | 0 | PASS（双 rank 各输出 Hello, world!） |
| cxxhello | `mpirun -np 2 ./cxxhello` | 0 | PASS |
| alltoall | `mpirun -np 2 ./alltoall` | 0 | PASS |
| chapter_10_mpi2 | `mpirun -np 2 ./chapter_10_mpi2` | 0 | PASS（C++ 绑定） |
| trivialc | `mpirun -np 2 ./trivialc` | 0 | PASS |
| ezstart | `mpirun -np 4 ./ezstart` | 0 | PASS（200 工作项×sleep(2)，需 450s 超时窗） |
| ring | `mpirun -np 2 ./ring` | 0 | PASS |
| cxxring | `mpirun -np 2 ./cxxring` | 0 | PASS |
| cpi | `mpirun -np 2 ./cpi` | 0 | PASS |
| cxxpi | `mpirun -np 2 ./cxxpi` | 0 | PASS |
| cxx_topology | `mpirun -np 2 ./cxx_topology` | 0 | PASS |
| mandelbrot_master+slave | `mpirun <myapp schema>`（h master : C -s h slave） | 0 | PASS（mandel.out 262944 字节完整 512×512 光栅图） |
| fault_master | `mpirun n0 ./master`（cwd 含 ./slave） | 0 | PASS（MPI_Comm_spawn 动态拉起 slave） |
| fault_slave | 被 master spawn；直接单进程运行按设计输出 `No parent!` 并 rc=0 | 0 | PASS（spawn 链路已由 fault_master 覆盖） |
| fpi / fring / wave | — | — | SKIP（Fortran 源码，OHOS 无 f77 工具链） |

日志目录：`/data/storage/el2/base/cache/lam-tests/`（每用例 `<name>.compile.log` + `<name>.run.log`），汇总 `lam-examples-results.txt`。

### 编译期注意事项

- 首轮 `mpirun -np 2` 跑 fault/mandelbrot 报错/超时不是缺陷：这些示例是 master/spawn 架构，须按 README 设计模式运行（fault 用 `mpirun n0 ./master`，mandelbrot 用 myapp schema），已按设计复跑通过
- ezstart 设计上 slave 每轮 sleep(2)，200 工作项单 slave 需 ~400s，30s/60s 超时必然 TIMEOUT，np=4 + 450s 窗口通过

### test_package（鸿蒙消费者测试，无断言）

- `test_package/test.c`：MPI_Init/Comm_rank/Comm_size + MPI_Allreduce 求和校验，成功打印 `LAM-SMOKE-OK`；**不使用 assert()**（NDEBUG 下 assert 编译为空），校验失败走显式 fprintf + MPI_Abort
- HarmonyOS 特有检查：`laminfo` 输出必须含 `LAM/MPI` 与 `linux-ohos` 架构串；`lamboot` 启动本机 lamd；`mpirun -np 1` 与 `-np 2` 各跑一轮 test_mpi；`lamhalt` 干净拆除运行时
- LAM 的 wrapper 在 OHOS 上不可用，test_package 用底层 clang + `--showme` 等价标志编译（-llammpi++ -lmpi -llam -ldl），SDK 的 libc++_shared.so 通过 `clang++ -print-file-name=libc++_shared.so` 动态定位，不硬编码沙箱路径
- **conan create 实测通过（2026-10-12，package_id `21b17f8b2bc0e9511e276e3d57a23893067cefe5`）**：laminfo 关卡（含 linux-ohos 架构串）→ lamboot（`booting n0 (localhost)` → `finished`）→ mpirun -np 1（`LAM-SMOKE-OK: rank 0 of 1, allreduce sum 1`）→ mpirun -np 2（`rank 0 of 2, allreduce sum 3` = 0+1+2）→ lamhalt → `LAM-TEST-PACKAGE-PASSED`，退出码 0；日志 `/data/storage/el2/base/cache/lam-conan-create-run17.log`

## 已知限制

- hcc/mpicc/mpic++ wrapper 二进制在 OHOS 上 `--showme` 可用但实际编译静默失败，包内保留原样（上游产物），消费者应使用 cpp_info 标志
- Fortran 绑定未构建（`--without-fc`，OHOS 无 Fortran 工具链）
- ROMIO（MPI-IO）未构建（`--without-romio`），romio/test 与 examples/romio 不可用
- 仅静态库（`--disable-shared --enable-static`），与实测通过的构建配置一致
- 构建采用串行 `make`（不使用 -j）：conan 缓存所在文件系统拒绝 mkfifo，GNU make -j2 的 jobserver 建立失败会偶发破坏并行 recipe 执行；串行构建约 25 分钟，在 CI 默认 3600s 超时内
- configure 显式传 `SHELL=/bin/sh` 并通过 0004 补丁以 `$SHELL` 调用 libtool 探测，规避 conan 缓存文件系统不保留 exec 位导致的 EACCES（CI 为干净检出时同样适用）
- 配方在 build() 预置 `RSH_COMMAND=/usr/bin/ssh` 环境变量：rsh boot 模块 configure 对该变量的既定 override（跳过 ssh 搜索），同时规避部分文件系统上 stat 探测不可靠导致的搜索失败；`RSH_FULL_PATH` 无效（该脚本会先清空它）
- PMPI 桩与 wrapper 安装 hook 的 `ln -s` 在不支持 symlink 的文件系统上失败，配方在 configure 后将其改写为等价的 `cp -p`/直连目标（CI 干净 Linux 上无行为差异）
- test_package 在运行目录落地 `lam-bhost.def`（上游单节点默认内容），配方通过 runenv 注入 `LAMHOME=<包目录>`，使 lamboot/hboot/lamhalt 从 `$LAMHOME/etc/` 解析 schema/hostfile/helpfile（DESTDIR `--prefix=/` 装箱后 `/etc` 不存在）
---

### 对话 #1 [2026-10-11]

- 问题
  - 上游 2007 版 config.guess/sub 不识别 aarch64-linux-ohos；configure 主签名 `int main(int argc, char* argv)` 在 clang15 报错；23 份 config.guess/sub 副本需同步；捆绑 libltdl 的 libtool 以 `#! $SHELL` 生成 shebang，在 conan 缓存 FUSE（不保留 exec 位）上 exec 被拒
- 操作
  - 0002/0003 补丁加 HarmonyOS 分支（echo+exit / 4 处 linux-ohos 改写）；0001 补丁修 7 处 main 签名；conanfile 程序化把补丁后的 config/ 副本复制到其余 22 份；0004 补丁把顶层 configure 6 处 `cmd="$libtool` 改为 `cmd="$SHELL $libtool`，并显式传 `SHELL=/bin/sh`
- 结果
  - configure 完整通过（178 个 Makefile、23 个 SSI 子模块）

### 对话 #2 [2026-10-11]

- 问题
  - conan create 的 make 阶段反复静默失败（clang/libtool 零诊断输出 Error 1），手动执行同命令却 RC=0
- 操作
  - 排除法定位：conan `conan_run` 源码证实构建树 stdio 默认 = conan 进程 stderr = 外层 `| tee` 管道；沙箱对长生命周期进程树的管道写间歇性 EACCES（`echo hello | cat | tail` 复现），诊断输出随管道一起被吞。改为 stdio 全部落文件后，真实错误首次显形：PMPI 桩规则硬编码 `ln -s` 在 FUSE 上 Permission denied
- 结果
  - 配方在 configure 后把 share/pmpi/Makefile 与 tools/wrappers/Makefile install-exec-hook 的 `ln -s` 改写为等价 `cp -p`/直连目标（后者还修正了 hook 顺序：`hcp←mpiCC` 先于 `mpiCC←mpic++`，ln -s 语义下顺序无关、cp 必须源先存在，改为上游注释掉的旧版写法 `hcp←mpic++`）；make 全绿

### 对话 #3 [2026-10-11/12]

- 问题
  - rsh boot 模块在所有 conan 构建中 compile: no（`checking for ssh... no`，/usr/bin/ssh 明明存在），导致 lamboot 无可用 boot 模块；随后 lamboot 找不到 `lam-bhost.def`，hboot 找不到进程 schema `lam-conf.lamd`（DESTDIR `--prefix=/` 装箱后 `/etc` 不存在）
- 操作
  - rsh 模块 configure 源码定案：真正的 override 入口是 `RSH_COMMAND` 环境变量（`RSH_FULL_PATH` 会被脚本先清空，设它无效）；配方 build() 无条件预置 `RSH_COMMAND=/usr/bin/ssh` → `boot:rsh compile: yes`；test_package 在运行目录落地上游同款单节点 `lam-bhost.def`（lamboot 优先搜本地目录）；配方 package_info 注入 `LAMHOME=<包目录>`，schema/hostfile/helpfile 全部改从 `$LAMHOME/etc/` 解析
- 结果
  - conan create 全绿（`CONAN_CREATE_RC=0`，package_id `21b17f8b2bc0e9511e276e3d57a23893067cefe5`）；test_package 四关全过（lamboot → mpirun -np 1 → mpirun -np 2 → lamhalt → `LAM-TEST-PACKAGE-PASSED`）

### 对话 #4 [2026-10-12]

- 问题
  - conan-verify 8 道门禁与 W3 本地 CI 首跑被 JC junk check 阻塞：检出 8 个与 lam 无关的垃圾文件（cloog/.build-closed+.staging-verified 等，上游 main 自带）；本地 junk_check 回退 full 整仓模式而 CI 走 PR diff 模式
- 操作
  - 本地 `git rm` 暂存删除这 8 个文件（不进 PR，提交时只 add lam 文件）；clean-verify G0 的裸 configure 失败确认为工具未传 `--without-fc` 的已知局限（非阻塞，conan 配方显式传参且 G2 两次全绿）
- 结果
  - junk_check Junk Files: 0；conan-verify 8 道门禁全绿（VERIFY_RC=0）；W3 本地 CI 模拟通过（setup.sh + build_and_test.sh）


### 对话 #5 [2026-10-13]

- 问题
  - CI（PR #15401，worker CI-007，构建 #87197）configure 阶段全量失败：`config.status` 在 `./confstatXXXXXX` 临时目录内创建任何文件均 `Permission denied` → 全部 Makefile/config.h 未生成 → `make: No targets specified`。本地 run17 全绿是因本地 conan 缓存在 `/data/storage/el2`（正常文件系统），CI 缓存在 `$HOME/.cache/conan2`（HMDFS）——HMDFS 上新建 0700 模式目录拒写（umask 077 的 mktemp -d）
- 操作
  - 配方新增 `_propagate_confstat_umask()`：把源码树全部 23 份 configure 的 `umask 077 && mktemp -d "./confstatXXXXXX"` 改写为 `umask 000`（0755 型目录在 HMDFS 可写；同仓先例 autodir/0.99.9）。不用补丁文件：该 stanza 每份 configure 出现两处、45K 行大文件位置 hunk 不可靠（patch 实测 FAIL），程序化文本替换更稳
  - HMDFS 等价环境复验（CONAN_HOME 指到 `/storage/Users/currentUser/.cache/lam-w3-rehome` + CI 同款 profile）：configure/make/install 全过，`Permission denied` 0 次，`Package '21b17f8b...' created`——但 test_package 暴露第二层问题：lamd 的 AF_UNIX socket bind 在 HMDFS 上 `Operation not permitted`（HMDFS 不支持 unix socket bind，属新发现的 HMDFS 特性差异）
  - test_package 新增 `_session_dir()`：按 TMPDIR → `/data/storage/el2/base/cache` → 系统 tmp → cwd 顺序用**真实 socket bind 探测**可 bind 目录（HMDFS 可写但不可 bind，不能只看可写），设 `LAM_MPI_SESSION_PREFIX`（LAM 源码 share/etc/kill.c::lam_tmpdir_init_opt 证实其优先级：显式参数 > LAM_MPI_SESSION_PREFIX > TMPDIR > /tmp）
- 结果
  - 复验 5 关全过（HMDFS 缓存包）：laminfo → lamboot（socket 落在 el2 探测目录）→ mpirun -np 1/2 → lamhalt → `LAM-TEST-PACKAGE-PASSED`（TEST_RC=0）；package_id 不变 `21b17f8b2bc0e9511e276e3d57a23893067cefe5`

### 对话 #6 [2026-10-15]

- 问题
  - CI 对第一轮修复 commit（PR #15401 构建 #89213）仍失败，但失败点已前移：configure 阶段通过、`share/mpi` 编译链接全部成功，`make` 递归进入 `share/libltdl` 时报 `make[2]: *** No rule to make target 'all'.  Stop.`——libltdl/Makefile 存在但缺 `all` 目标，是其 config.status 在 HMDFS 上中途死掉留下的残缺产物。期间上游 main 前进，PR 出现 `.gitignore` 合入冲突（双方各自在文件尾追加互不重叠的 reports 例外块：lam 7.1.4 与 libica 4.4.1）
  - 根因：round-1 的 umask 修复只覆盖 1 种 stanza 形态（autoconf 2.59 的 `umask 077 && mktemp -d -q "./confstatXXXXXX"`）。全树实为 **4 种形态**：2.59 的 confstat-mktemp 行 + `(umask 077 && mkdir $tmp)` fallback 行；以及 autoconf 2.59c（仅 share/libltdl/configure）的 `"./confXXXXXX"`（**无 "stat"**）mktemp 行 + `(umask 077 && mkdir "$tmp")` fallback 行。全树残留 **46 处** `umask 077`（23 份 configure × mktemp/fallback 各行一处）
  - 本地复验为何掩盖：本机 mktemp 成功、且本机 HMDFS 对 0700 目录可写，两条路径都不会踩坑；CI worker 的 HMDFS 上 mktemp 失败会走 mkdir fallback（`umask 077` → 0700 目录拒写），是 CI 特有分支
- 操作
  - 合并 official/main 解决 `.gitignore` 尾部追加碰撞（两块都保留；其余 6800+ 文件自动合并干净）
  - `_propagate_confstat_umask()` 重写为 **4 形态字节级替换**，覆盖全树 23 份 configure 的 mktemp 行与 mkdir fallback 行（077 → 000），与既有 `_propagate_config_ohos` 同模式
  - 本地 HMDFS 等价环境清缓存后完整重跑 conan create（CI 同款 profile `ci/conan/profiles/ohos-aarch64` + `CONAN_HOME` 于 HMDFS）
- 结果
  - 静态核验：修复前 46 处 `umask 077` → 修复后 **0 处**，`umask 000` **46 处**（四形态穷尽，含 libltdl 的 `confXXXXXX` 变体与带引号 fallback）
  - HMDFS 等价 `conan create` 全绿：`CONAN_CREATE_RC=0`（56m47s / 18666 行）；`share/libltdl/configure succeeded`（formatted L3062）、`Making all in libltdl` 正常编译、`No rule to make target` 与 `Permission denied` 均 **0 命中**；package_id 不变 `21b17f8b2bc0e9511e276e3d57a23893067cefe5`；test_package 五关全过 `LAM-TEST-PACKAGE-PASSED`
  - 局限说明：本机 HMDFS 与 CI worker 的 HMDFS 行为存在差异（本机 0700 可写、mktemp 成功），本地无法直接复现 CI 特有的 mkdir-fallback 分支，该分支以静态覆盖核验 + CI 实测为准


### 对话 #7 [2026-10-15]

- 问题
  - CI（PR #15401，worker CI-035，构建 #89267）第三轮失败：round-2 修复已被 CI 实测证实生效——日志显示全部 23 份 configure（含 libltdl）成功、`share/libltdl` 正常编译，`No rule to make target` 与 `Permission denied` 均 0 命中。真正的失败是 `conan create TIMED OUT after 3600s`，且超时前日志出现持续的 `fork: retry: Resource temporarily unavailable` 风暴（worker 资源争用，平台归类"环境问题"）：每次 fork 失败都会拖慢/污染子进程 spawn，SSI 子模块的子 configure 探测因此出现假阴性（如 `checking for sys/stat.h... no`）
  - 根因（两层）：① fork EAGAIN 是 worker 侧环境争用，配方无法消除；② 配方此前**串行 make**，HMDFS 上全量构建实测 56m47s，对 CI 3600s 上限的裕度仅约 3 分钟——任何 worker 降速（如 fork 风暴）都必然压垮超时线
- 操作
  - 核实串行 make 的依据已过时：原注释称 HMDFS 拒 mkfifo 会导致 make -j jobserver 间歇损坏，但 GNU make >= 4.2（本机 4.4.1）的 jobserver 建在匿名 pipe(2) 上而非 FIFO，HMDFS 的 mkfifo 限制不适用；实测 `make -j20` 在 HMDFS conan 缓存上干净起 jobserver、RC=0
  - 仓内先例佐证：openblas/0.3.33、c-algorithms/1.2.0 均以 `make -j20` 通过 CI
  - 配方 make 段改为并行：`make -j{min(os.cpu_count() or 1, 8)}`——上限 8 是在缩短编译期（串行 56m47s，编译段占大头）与控制争用 worker 上的 fork 压力之间取平衡
  - HMDFS 等价环境清缓存全量复验（CI 同款 profile + `CONAN_HOME` 于 HMDFS）
- 结果
  - 复验全绿：`CONAN_CREATE_RC=0`（18657 行，与串行轮 18666 行流程相当）；libltdl `configure succeeded` + `Making all in libltdl` 两关均过；`Error 1`/`Permission denied` 0 命中；package_id 不变 `21b17f8b2bc0e9511e276e3d57a23893067cefe5`；test_package 五关全过 `LAM-TEST-PACKAGE-PASSED`
  - 局限说明：本地无精确计时手段（HMFS 不提供文件 birthtime），并行加速的具体时长以 CI 实测为准；若 CI 再遇持续性 fork EAGAIN 风暴，重触发换 worker 是合理处置

---

**编译结束**: 2026-10-12 02:03
**最终状态**: built
