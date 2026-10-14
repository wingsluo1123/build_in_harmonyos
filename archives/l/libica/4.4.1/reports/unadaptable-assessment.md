# libica 4.4.1 — 不可适配性评估报告（含完整复现证据）

- **三方库名称**：libica
- **上游版本**：4.4.1
- **上游仓库**：https://github.com/opencryptoki/libica
- **目标平台**：OpenHarmony PC / aarch64（DAYU200 · RK3568，6.0.0.47）
- **结论**：**在 aarch64 上不可适配**（结构性、非轮次不足）
- **本次复核方式**：2026-10-04 按主管派单**从零复核**，不沿用此前结论；下述每一条均为本次新跑出的原始输出。

---

## 1. 一句话结论

libica 是 **IBM Z（s390x）大型机专用硬件密码库**。它的全部功能实现都以
① s390 通用寄存器内联汇编、② s390 专用内核头 `<asm/zcrypt.h>`、
③ 大型机密码卡设备 `/dev/zcrypt` 为载体。**上游不提供任何架构中立或软件后端**，
因此不存在"让它在 aarch64 上真正工作"的适配路径；任何能编译出 `.so` 的做法都只能是
把库掏空的假适配（必然导致 rule4 测试 0/N、rule12 无端到端）。

---

## 2. 复核方法与关键进展（本次比此前更严格）

此前的结论停在 `configure` 阶段（`config.sub` 不认 `aarch64-unknown-linux-ohos`），
严格说那只证明了**工具链/autotools 版本落后**，不足以证明**源码**不可适配。

本次复核**主动绕过了这一层噪声**：先打补丁让 `config.sub` / `config.guess` 接受
`aarch64-unknown-linux-ohos` 三元组（`sh config.sub aarch64-unknown-linux-ohos` → `CONFIG_SUB_OK`），
使 `configure` **成功返回 0**，从而把失败点推进到**真正的源码编译**。

```
configure exit=0
checking host system type... aarch64-unknown-linux-ohos
```

这样得到的证据才是**针对 libica 源码本身**的，而非针对我本机 autotools 的。

---

## 3. 原始证据（本次实测输出）

### 3.1 configure 顺利通过后，`make -j4` 的真实失败

```
=== make -j4 : THE BLOCKER ===
make exit=2
--- fatal errors ---
71:.../src/include/s390_ecc.h:19:10: fatal error: 'asm/zcrypt.h' file not found
81:.../src/include/s390_rsa.h:18:10: fatal error: 'asm/zcrypt.h' file not found
--- top error signatures ---
     22 error: invalid output constraint '+a' in asm
      8 error: invalid output constraint '+d' in asm
      4 error: invalid input constraint 'a' in asm
      2 error: invalid output constraint '=d' in asm
      2 error: 'asm/zcrypt.h' file not found
      1 error: use of undeclared identifier 'program_invocation_name'
--- .o produced ---
count: 2
--- total errors ---
39
```

**整个库只编译出 2 个目标文件，共 39 处 error。** 三类架构级失败如下：

| # | 失败点 | 文件 | 实测 | 性质 |
|---|---|---|---|---|
| 1 | s390 内核 UAPI 头 | `src/include/s390_ecc.h:19`、`s390_rsa.h:18` | `fatal error: 'asm/zcrypt.h' file not found`（**2 处**） | s390 专属内核头，aarch64 内核树中不存在 |
| 2 | s390 寄存器类内联汇编 | `src/include/s390_crypto.h`（被 `s390_crypto.c`/`ica_api.c`/`icainfo.c`/`init.c` 等包含） | **36 处** `invalid output/input constraint '+a'/'+d'/'=d'/'a' in asm` | `+a`/`+d` 是 s390 通用寄存器类；aarch64 用 `x`/`w` 类，无对应物 |
| 3 | 架构专用汇编写死寄存器 | `src/mp.S` | aarch64 clang 汇编该文件共 **51 处 error**（其中 2 处为 `unrecognized instruction mnemonic`，其余为寄存器/指令操作数不匹配）；**宿主 x86_64 原生 gcc 汇编同一文件同样失败**（`bad register name '%r1'`、`'%f4'`） | 由 `src/mp.pl` + `src/perlasm/s390x.pm` 生成（perlasm 下**唯一**后端） |

**计数闭合说明（第 1、2 类，合计 39）**：签名严格加总 `36 + 2 + 1 = 39` ——
36 处 asm 约束错误（第 2 类）、2 处 `asm/zcrypt.h`（第 1 类）、
以及 1 处 `use of undeclared identifier 'program_invocation_name'`
（autotools 生成的探测代码引用 glibc 专有符号，OHOS musl 无此符号，
属**平台 libc 差异**，与上述架构绑定无关，故单列、不混入分类）。

> **第 3 类与第 1、2 类的关系**：`mp.S` 是**独立编译单元**，其 51 处错误
> **不在** `make` 那 39 处 error 的直方图内 —— 两者属不同编译阶段的计数，**不可相加**。
> `mp.S` 的完整原始输出见 `raw-build-failure.txt` 的 **SECTION B** 与
> `raw-logs/ica_mps_aarch64.log`。
> 它证明的是：这三类失败分别发生在**内核头**、**内联汇编宏**、**独立汇编单元**三个层面，
> 三者都需要各自独立的架构级移植工作，而非单点修补。

### 3.2 无任何可移植/软件后端

```
$ ls src/*.c | xargs -n1 basename | grep '^s390_'
s390_crypto.c  s390_drbg.c  s390_drbg_sha512.c  s390_ecc.c
s390_prng.c    s390_rsa.c   s390_sha.c
（共 7 个 s390_ 前缀实现文件；另有 ica_api.c / init.c / rng.c / fips.c
  / icastats*.c / test_vec.c 等与具体架构无关的胶水/工具文件）
```

> **证据强度说明**：以上输出由 `ls`/`grep` 等**标准命令**直接产生，
> 复核者可在上游源码树中执行 `ls src/s390_*.c | wc -l`（→ 7）自行核对，
> 不依赖任何未入库脚本。本报告 §6.2 列出的辅助脚本仅用于**编排完整构建流程**，
> 不用于产生本节这类可直接复算的计数。

- `configure.ac` 仅有 `--enable-fips` / `--enable-debug` / `--enable-sanitizer`，
  **没有任何架构开关、没有 `--disable-hw`、没有软件后端选项**。
- 全仓 `grep '__aarch64__|__x86_64__|--disable-hw|software backend'` → **0 命中**。
- OpenSSL 在其中**不是密码学后端**，只被用于 BN/EC 参数编解码与 FIPS 自检
  （`openssl/bn.h`、`ec.h`、`param_build.h` 等）；真正的运算全部落到 CPACF 指令 / CEX 卡。
- `-DNO_CPACF`（libica-cex 构建）**不是软件后端**：它只是把 CPACF 指令换成 CEX 密码卡，
  **仍然需要大型机硬件**。

> **最容易误判的一处**：`src/ica_api.c:383` 注释写着
> *"the software fallback will still work without an adapter handle"*。
> 该 "software fallback" 指的是**换用另一种 s390 机制**（CPACF 指令代替 CEX 卡），
> **不是**可移植的软件实现 —— 其能力探测本身就靠执行 s390 指令
> （`s390_kmc`/`s390_kimd`/`s390_ppno`/`s390_kma`/`s390_kdsa`/`s390_pcc`）。
> 若据此认为"有软件兜底，可以适配"，是**误读上游注释**。

### 3.3 上游测试用例无法在 aarch64 上执行（rule4 硬约束）

```
=== test dir: can ANY test run without s390 hw? ===
total test .c: 48
count WITHOUT hw refs: 5   (fips_test.c, get_functionlist_test.c,
                            get_version_test.c, mp_test.c, rsa_key_check_test.c)
```

**这 5 个"看起来不碰硬件"的用例同样不可用**，因为它们的断言全部依赖 libica 自身符号：

| 测试文件 | 调用 `ica_*` 符号次数 | 为何仍不可用 |
|---|---|---|
| `fips_test.c` | 42 | 需 libica 完成构建；库本体编不出来 |
| `get_functionlist_test.c` | 16 | 同上 |
| `get_version_test.c` | 9 | 同上 |
| `mp_test.c` | **103** | 直接测试 `mp.S` 的 `ica_mp_mul512`/`ica_mp_sq512` —— 正是无法汇编的 s390 汇编 |
| `rsa_key_check_test.c` | 7 | 同上 |

另 43/48 个用例直接引用 `ica_open_adapter` / CPACF / CEX 能力位。
**因此可执行用例数 N 恒为 0** —— 而 rule4 明确规定"0/N 一律不通过，无任何借口"。

### 3.4 上游与发行版侧旁证

上游 `.travis.yml` 中的 job 定义（**逐行原样引用，行号为实测**；
注意 `- name:` 与其下的 `arch:` 是**不同缩进的两行**，不是同一行）：

```yaml
# .travis.yml
 8:        - name: "linux-s390x-gcc"
 9:          os: linux
10:          arch: s390x
13:        - name: "linux-s390x-clang"
14:          os: linux
15:          arch: s390x
18:        - name: "linux-s390x-sanitizer"
19:          os: linux
20:          arch: s390x
```

- 上游 CI **3/3 job 全部 `arch: s390x`**（`.travis.yml` 第 10/15/20 行），amd64/arm64 为 0。
- `README.md` 首行自述：*"Linux on z Systems crypto library"*。
- Ubuntu `libica4` 二进制包 `Architecture` **仅 s390x**。
- 设备侧：DAYU200 为 RK3568，**无 zcrypt 总线、无 CEX 密码卡**，
  `#define DEFAULT3_CRYPT_DEVICE "/dev/zcrypt"`（`src/ica_api.c:51`）在设备上无对应设备节点。

---

## 4. 为什么"打个补丁让它编译过"是错误答案

可以预见的"强行适配"做法与其后果：

| 做法 | 后果 | 判定 |
|---|---|---|
| 删掉 `mp.S` | 缺失 `ica_mp_mul512`/`ica_mp_sq512` 符号，链接失败；改 stub 则 RSA/ECC 全部失效 | 假适配 |
| 替换 s390 内联汇编为软件实现 | 等于**重写整个密码库**（非"适配"），且已超出该库边界 | 不是适配 |
| 保留空壳 API 让测试"通过" | 密码运算返回错误结果，测试用例无从真实执行 | 违反 rule4 |
| 用 OpenSSL 顶替底层 | 那就不再是 libica；且上游无此构建路径 | 不是适配 |

**结论**：不存在把 libica 真正跑在 aarch64 上的路径。

---

## 5. 对赛事规则的直接冲突

| 规则 | 要求 | libica 现状 |
|---|---|---|
| rule4 | 真实执行上游测试，通过率 N/N，0/N 一律不通过 | 可执行用例 **0/48**，N 恒为 0 |
| rule12 | 鸿蒙特有测试需**完整消费者端到端用例** | 库唯一功能是调用 s390 硬件，设备上无任何可执行端到端流程 |
| rule7 | CI 必须通过 | 构建失败（整库 39 处 error + `mp.S` 51 处 error，均架构级），CI 必然红 |

---

## 6. 复现方式

### 6.1 自包含复现（证据已入库，可逐字核对）

本 PR 的 `raw-build-failure.txt` 汇总了 **SECTION A**（整库 make 失败）与
**SECTION B**（`mp.S` 汇编失败）的关键输出，其中**每个数字均由命令从原始日志实时计算**得出
（`grep -c` / `find | wc -l`），不含任何硬编码常量。

**真实原始日志同时入库于 `raw-logs/`**，复核者可逐字比对、复算每一个数字：

| 原始日志 | 内容 |
|---|---|
| `raw-logs/ica_confF.log` | configure 全过程（host = aarch64-unknown-linux-ohos） |
| `raw-logs/ica_makeF.log` | 整库 `make -j4` 完整输出（39 处 error） |
| `raw-logs/ica_mps_aarch64.log` | `mp.S` 于 aarch64 clang 的完整输出（51 处 error） |
| `raw-logs/ica_mps_host.log` | `mp.S` 于宿主 x86_64 gcc 的完整输出（24 处 Error） |

例如，复核者可自行复算：

```bash
grep -c 'error:' raw-logs/ica_makeF.log          # -> 39
find <build dir> -name '*.o' | wc -l             # -> 2
grep -c 'error:' raw-logs/ica_mps_aarch64.log    # -> 51
grep -c 'Error'  raw-logs/ica_mps_host.log       # -> 24
```

> **计数口径声明（重要，避免误判"数字对不上"）**：本报告所有 `error:` 计数均为
> **按日志行计数**（`grep -c` 的语义），**不是按去重后的错误签名计数**。
> 以 `mp.S` 为例：aarch64 日志中同一条错误常跨 2 行
> （`unknown token in expression` / `invalid operand`），
> 故按行得 51，而按去重签名只有 **4 类** —— 两者口径不同，本报告一律采用**按行口径**。
> 同理 §3.1 的 `39` 亦为按行计数（其签名去重后为 6 类）。
> 复核时请使用上方给出的 `grep -c` 命令，以保证口径一致。

### 6.2 完整重跑（需要构建环境，未入库）

下列脚本位于任务机的 `/mnt/d/OHDev/work/`，属**本任务的工作脚本、未随 PR 入库**，
仅供复核者按 §6.3 的步骤自建等价流程时参考。**它们不是 PR 的交付物**，
因此本报告**不主张"任何人可直接复跑"**：

| 脚本（未入库） | 作用 |
|---|---|
| `ica_verify_all.sh` | 9 项静态核验（README/架构/头文件/测试统计等） |
| `ica_final_probe.sh` | 打补丁绕过 config.sub → configure 成功 → make 失败（决定性证据） |
| `ica_mp_evidence.sh` | 单独汇编 `mp.S`（aarch64 clang 与宿主 x86_64 gcc 对照） |

> 上文 §3 引用的「9/9 通过」是**本任务在本机执行 `ica_verify_all.sh` 的结果**，
> 不等于"任何评审者都已独立验证"。复核者若需独立验证，请按 §6.3 步骤操作。

### 6.3 独立复现步骤（可照此自建）

```bash
# 1) 取上游源码
curl -LO <libica-4.4.1 tarball>   # 或 git clone https://github.com/opencryptoki/libica -b v4.4.1

# 2) 让 config.sub 认识 OHOS 三元组（否则会误报为工具链问题）
#    在 config.sub 的 kernel-os 兼容表中加入 linux-ohos*，并让 OS 白名单含 ohos*
sh config.sub aarch64-unknown-linux-ohos   # 应回显该三元组

# 3) 交叉 configure（应成功）
export CC=<ohos sdk>/native/llvm/bin/aarch64-unknown-linux-ohos-clang
export SYSROOT=<ohos sdk>/native/sysroot
./configure --host=aarch64-unknown-linux-ohos \
  CFLAGS="--sysroot=$SYSROOT -fPIC" LDFLAGS="--sysroot=$SYSROOT"
# -> checking host system type... aarch64-unknown-linux-ohos ; exit 0

# 4) 构建（必然失败）
make -j4
# -> 'asm/zcrypt.h' file not found ; 36 处 invalid output/input constraint ; 仅 2 个 .o

# 5) 单独验证 mp.S 是架构专用汇编
perl src/mp.pl /tmp/mp.S
"$CC" -c /tmp/mp.S -o /tmp/mp_ohos.o   # aarch64: 51 处 error
gcc   -c /tmp/mp.S -o /tmp/mp_host.o   # 宿主 x86_64 同样失败: bad register name '%r1'
# 注意：第 5 步依赖第 3 步 export 的 $CC；若在同一 shell 中执行即有效。
```

---

## 7. 交付说明

本分支交付一个**「失败适配记录包」**，遵循仓库既有的 `status: failed` 记录先例
（`archives/b/bltool/0.2.4`、`archives/a/abx/0.1` 等 35 个条目）：

| 文件 | 作用 |
|---|---|
| `conanfile.py` | 记录包配方；`build()` 校验记录完整性、`status: failed` 真实性、以及 manifest 引用的证据路径确实随包交付 |
| `conandata.yml` | 上游源描述（含实测 sha256） |
| `manifest.yaml` | `status: failed` + `failure.class: env_unsupported` + 测试账目 |
| `notes.md` | 适配说明（三类架构级根因、无软件后端、测试不可执行） |
| `reports/` | 评估报告、证据摘要、以及**真实原始日志**（随包交付，可逐字复算） |
| `test_package/` | **消费者端到端测试**：真实执行，且计数从包内原始日志**重新计算**后比对 |

**必须分清两个"编译状态"**（不可混淆）：

1. **记录包**（本 PR 的交付物）—— `conan create` **成功**，`test_package` 全部通过 ⇒ CI 可绿；
2. **上游 libica 本体** —— 在 aarch64 上**编译失败**（39 处 error，仅 2 个 .o）。

`test_package` 的**作用域仅限于校验记录本身**（完整性、真实性、证据一致），
**不**代表 libica 库可构建或可用 —— 它在 aarch64 上不可能构建，原因见 §3。

**为什么不提交"能编译 libica"的配方**：
删掉 `mp.S` 则缺失 `ica_mp_mul512`/`ica_mp_sq512` 符号；用软件实现替换 s390
内联汇编等于重写整个密码库；保留空壳 API 则密码运算结果错误。
以上任一路线都只能得到伪适配，并必然要求编造测试通过率 —— 违反「数字必须真实」。

### 规则适用性说明

本库为**结构性不可适配**（架构绑定，非轮次不足），无法产出"上游库编译通过 +
上游测试通过率"的路径A 交付物。若规则上仍需"编译通过"，本任务应改走
**「无法适配」通道（赛道B 储备）**，而非路径A —— 此属规则适用性问题，
需平台/主管裁决，非改代码可解决。
