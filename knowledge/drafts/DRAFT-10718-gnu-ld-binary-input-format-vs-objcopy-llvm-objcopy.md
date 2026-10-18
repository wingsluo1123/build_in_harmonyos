# DRAFT-10718：`ld -r --format=binary` 只有 GNU ld 实现 —— worker 上 `$(LD)` 是 ld.lld 时必须改用 objcopy

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-15
> Source: slurm-wlm 25.11.4 HarmonyOS PC 适配（`archives/s/slurm-wlm/25.11.4`）
> 对应：`knowledge/drafts/DRAFT-10718-gnu-ld-binary-input-format-vs-objcopy-llvm-objcopy.kv`
> 相关：DRAFT-E007（config.sub 不认新 OS）、DRAFT-11327（fork EAGAIN 环境性间歇失败）

## 现象

同一份配方、同一份 profile：设备上 `conan create` 全绿，平台 CI 上直接红在
`src/plugins/certgen/script`：

```text
curr_dir=.../src/plugins/certgen/script; cd .../src/plugins/certgen/script; \
  ld.lld -r -o ".../certgen.sh.bino" -z noexecstack --format=binary "certgen.sh.txt"; cd $curr_dir
ld.lld: error: target emulation unknown: -m or at least one .o file required
llvm-objcopy --rename-section .data=.rodata,alloc,load,readonly,data,contents "certgen.sh.bino"
llvm-objcopy: error: 'certgen.sh.bino': No such file or directory
make[5]: *** [Makefile:858: certgen.sh.bino] Error 1
```

CI 的失败诊断只会写「编译失败（make/gcc）」，看不出这和配方代码有什么关系。

## 根因

上游 `make_ref.include` 用 **linker 的二进制输入格式**把脚本内嵌成可重定位对象：

```makefile
%.bino: %.txt
	$(AM_V_GEN)curr_dir=$(shell pwd); cd $(abs_srcdir); $(LD) -r -o "$(abs_builddir)/$*.bino" -z noexecstack --format=binary "$(notdir $<)"; cd $$curr_dir
	$(AM_V_at)@OBJCOPY@ --rename-section .data=.rodata,alloc,load,readonly,data,contents "$*.bino"
```

`--format=binary`（等价于 `-b binary`）是 **GNU ld 的输入格式**，llvm 的 linker `ld.lld`
不实现它：lld 拿不到“输入是裸二进制”的语义，也找不到输出格式/输入对象，于是报
`target emulation unknown: -m or at least one .o file required`；紧随其后的 `objcopy`
步骤再报 `'xxx.bino': No such file or directory`。make 的报错行只落在 `%.bino` 规则上，
**错误信息完全不指向“这个 ld 不是 GNU ld”**。

### 为什么“本机绿、CI 红”

profile 只把 `/data/service/hnp/bin` 前置进 PATH，而**这个目录里的 `ld`/`objcopy` 指向谁，
取决于构建机上装了哪些 hnp 包**：

| 构建机 | `which ld` | `which objcopy` | `--format=binary` |
|--------|-----------|-----------------|-------------------|
| 适配设备（额外装了 `binutils.org` 2.45） | GNU ld 2.45 | GNU objcopy | 可用 → 本地全绿 |
| 平台 CI worker（只有 ohos-sdk llvm 工具链） | `ld.lld` | `llvm-objcopy` | 报 target emulation unknown |

即：**同一份配方在同一 profile 下，构建机工具链构成不同 → 一个能过、一个过不了。**
这是确定性差异，不是“环境偶发”（区别于 DRAFT-11327 的 fork EAGAIN）。

### 影响面被放大

slurm 的这条规则定义在 `make_ref.include` 里，被 automake **内联进 13 个 `Makefile.in`**：
certgen/script、sacct、sacctmgr、sackd、scontrol、scrontab、scrun、sinfo、slurmctld、
slurmd/slurmd、slurmrestd、sprio、squeue。CI 只是在字母序最靠前的 `certgen` 上被卡住，
后面那 12 个同样会失败。

## 正确做法（推荐：用 objcopy 的二进制输入模式）

把“两步（ld 生成 + objcopy 改名）”换成“一步 objcopy”，符号完全等价：

```makefile
%.bino: %.txt
	$(AM_V_GEN)curr_dir=$(shell pwd); cd $(abs_srcdir); @OBJCOPY@ -I binary -O elf64-littleaarch64 -B aarch64 --rename-section .data=.rodata,alloc,load,readonly,data,contents "$(notdir $<)" "$(abs_builddir)/$*.bino"; cd $$curr_dir
```

- `-I binary` 与 `-O elf64-littleaarch64`（OHOS PC = aarch64）在 **GNU objcopy 与
  llvm-objcopy 上都实现**，`-B aarch64` 给出二进制输入的架构；
- 生成的符号与 GNU ld 版**逐符号一致**：`_binary_<name>_start` / `_end` / `_size`；
- `--rename-section` 合并进同一步，省掉“生成后再改名”，也避免中间文件不存在时的二次报错；
- 没有链接器参与 → 与 `$(LD)` 是 GNU ld 还是 lld **彻底无关**。

**必须改两处**：源头 `make_ref.include`，以及 automake 已经内联好的每个 `Makefile.in`。
OHOS 主机上没有 automake/aclocal/libtoolize（这正是本包必须用 release tarball 的原因），
`configure` 只用 `Makefile.in` 生成 `Makefile` —— 只改 `.am`/源头不会生效。

## 备选做法（让 `$(LD)` 指到 GNU ld）

`configure` 传 `LD=<gnu-ld>`，或把带 GNU ld 的 binutils 目录前置到 PATH。
代价：要求**构建机确实装了 binutils**（worker 上未必有，本方案在 CI 上不可靠），
而且这是“绕过差异”而不是“消除差异”。

## 验证

```sh
# 1) 复现：把 lld 当 ld 用（与 CI 报错原文一致）
ld.lld -r -o x.bino -z noexecstack --format=binary certgen.sh.txt
# → ld.lld: error: target emulation unknown: -m or at least one .o file required

# 2) 等价替换：两套 objcopy 都应成功，且符号一致
for oc in objcopy llvm-objcopy; do
  $oc -I binary -O elf64-littleaarch64 -B aarch64 \
      --rename-section .data=.rodata,alloc,load,readonly,data,contents \
      certgen.sh.txt "$oc.bino"
  nm "$oc.bino" | sort
done
# → _binary_certgen_sh_txt_end / _binary_certgen_sh_txt_size / _binary_certgen_sh_txt_start

# 3) 与旧产物（GNU ld 版）对照
nm <build>/src/plugins/certgen/script/certgen.sh.bino | sort    # 应逐行相同

# 4) 规则真的不再用 $(LD)
grep -rn -- "--format=binary" <build>/**/Makefile    # 期望 0 命中
```

slurm 25.11.4 实测：

- 补丁后 13 个 `Makefile.in` 的规则全部改写（`grep -c format=binary` → 0）；
- 设备侧旧构建树里用 `OBJCOPY=llvm-objcopy`（与 worker 相同的 `llvm-objcopy`）重跑
  `certgen.sh.bino`/`keygen.sh.bino`/`help.bino` 全部产出，`nm` 符号与 GNU ld 版一致，
  `sacct` 用这些对象正常链接。

## 反例（禁止）

```makefile
$(LD) -r -o "$@.bino" -z noexecstack --format=binary "$(notdir $<)"   # 仅 GNU ld 可用
```

## 通用化建议

1. 看到构建系统里出现 `--format=binary` / `-b binary` / `ld -r`，先确认这条路径在
   **LLVM 工具链**下是否可用；不确定时直接换成 `objcopy -I binary`。
2. “本机绿、CI 红”的编译/链接类失败，第一步先对齐工具链解析结果：
   `which -a ld objcopy ar ranlib`，以及生成的 Makefile 里的 `LD = ` / `OBJCOPY = ` 两行。
3. 一个规则被 automake 内联进 N 个 `Makefile.in` 时，改动要**源头 + 全部内联副本**同时做
   （无 automake 可重生成），否则修了第一个目标、第二个目标还会再炸一次。
4. 内嵌二进制资源的 objcopy 目标名按平台写死是合理的（OHOS PC 固定
   `-O elf64-littleaarch64 -B aarch64`），符号命名规则 GNU/LLVM 一致，消费侧无需改动。
