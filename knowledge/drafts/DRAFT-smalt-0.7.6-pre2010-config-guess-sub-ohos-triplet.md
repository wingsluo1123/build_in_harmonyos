# pre-2010（2009 版）config.guess/config.sub 的 HarmonyOS 三元组补丁形态

新版模板在这一代脚本上会「报告成功但实际无效」，且 config.sub 只补一处会以 rc=0 静默产出畸形三元组。

Status: DRAFT
Source: smalt 0.7.6（config.guess/config.sub 头部时间戳 2009-11-20；tarball sha256 89ccdfe471edba3577b43de9ebfdaedb5cd6e26b02bf4000c554253433796b31）
PR: OpenHarmonyPCDeveloper/build_in_harmonyos #14095（远程 CI 构建 #65959 通过）
配对文件: DRAFT-smalt-0.7.6-pre2010-config-guess-sub-ohos-triplet.kv

## 相关既有条目

撞车判定检索（2026-10-01 实测执行，命令可复算）：

```text
python3 scripts/ohc-run.py engine 'config.guess: unable to guess system type ... last modified 2009-11-20'
  命中 E160（Phase B: 7）
grep -Ei 'config.guess|config.sub|unable to guess|linux-ohos|triplet' knowledge/graph/index.tsv
  命中 E007 E072 E099 E122 E149 E153 E160 E205 E245 E253 E268 E279 E387 E490
grep -RniE 'GUESS=|2009-11-20|last modified 2009|linux-gnu-ohos' knowledge/doc/
  0 命中（本草稿两个核心事实在正式知识库中均无覆盖）
```

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E007 patch-autotools-script | config.guess 无 HarmonyOS 分支导致 cannot guess build type；方案是用仓内 patch-autotools-ohos.pl 打补丁，输出标准三元组 aarch64-unknown-linux-ohos | 未区分脚本年代形态。E007 的方案与仓内 perl 工具都假设新版结构（GUESS= 变量、android-linux 分支、gnu 与 android 并列的 OS 列表），在 2009 版上全部落空 |
| E072 config.sub invalid triplet | config.sub 拒绝 ohos 三元组、unknown vendor 或 unknown OS 的校验失败 | 未指出该版 CPU 表不认识裸 aarch64（实测 aarch64 与 aarch64-unknown 均被拒，必须带 vendor 位），也未指出第二处必改点 |
| E122 add-linux-ohos-to-validation | kernel-os 校验列表缺 linux-ohos，给出针对 linux-uclibc 行的 sed 追加模板 | 该模板锚点是新版形态。2009 版写作 linux-uclibc 后接续行反斜杠，实测锚点命中数为 0，sed 静默不改；且 E122 未提及末尾 -linux 兜底分支的 sed 改写会产出 -linux-gnu-ohos |
| E160 config-guess-harmonyos-patch | 用 sed 在 case UNAME_SYSTEM 分支后插入 HarmonyOS 与 HongMeng 归一到 Linux、LIBC=musl | 该锚点在 2009 版 config.guess 中不存在（实测 grep 计数 0），命令静默无效；且其策略（把 HarmonyOS 伪装成 Linux/musl）与 E007/E205 的标准三元组策略相矛盾，本草稿按 E007/E205 口径取 aarch64-unknown-linux-ohos |
| E205 patch-script | 明确 Never use --build/--host flags as workaround，要求用 perl 补丁脚本 | 口径一致（已作为 forbid_1 收录）。增量是执行层风险：perl 脚本本身在旧版会半静默失效（3 条 warn、Score 1/5、exit 1，却仍打印 [ok] Added HarmonyOS system identification） |
| E268 patch-autotools-ohos.pl 误判 | perl 脚本 step 2.3 以全文 grep linux-ohos 判定是否已补丁，对新版（2024+）config.sub 误判跳过内核校验补丁 | 方向相反的同类问题：E268 是新版已有部分文本导致漏补；本草稿是旧版缺少全部锚点导致整体空转，且失败形态不同（旧版连 basic os 列表与 GUESS 变量都对不上） |
| E279 | patch-ng 零上下文 hunk 与 config.guess 上下文锚点问题 | 属补丁应用层，与本草稿的补丁内容形态层正交，无重叠 |
| E490 | autotools helper 脚本执行位丢失导致 configure 无法执行 | 正交问题（权限而非内容）；本次配方一并处理，不构成本草稿增量 |

结论：既有条目覆盖的是「新版脚本怎么补」。**没有任何条目覆盖 pre-2010 脚本的补丁形态差异，也没有任何条目记录「只补一处会以 rc=0 静默产出畸形三元组」**，故独立申报；相近条目已全部写入 .kv 的 similar_to。

## Scope

何时用：发行 tarball 内自带预生成 configure、且其 config.guess/config.sub 是 2010 年以前版本的 autotools 包。

判形态（下面几条都为 0 即 pre-2010 形态，此时新版模板与仓内 perl 工具会静默失效）：

```bash
head -5 config.guess                           # 看 Copyright 年份与 timestamp
grep -c 'GUESS=' config.guess                  # 0 说明旧版（分支用 echo + exit 收尾）
grep -c 'case $UNAME_SYSTEM in' config.guess   # 0 说明 E160 的 sed 锚点不存在
grep -c 'android' config.sub                   # 0 说明 perl 工具 step 2.1/2.2 锚点不存在
grep -c 'linux-uclibc*- )' config.sub          # 0 说明 E122 的 sed 锚点不存在
```

不适用：源码树无预生成 configure、需 autoreconf 自举的包（脚本由本机 automake 生成，属新版形态，按 E007/E268 处理）；已内嵌 2015 年以后新版脚本的包。

## Symptom

修复前真实日志（smalt 0.7.6，2026-10-01 实测）：

```text
$ ./config.sub aarch64-unknown-linux-ohos
Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-linux' not recognized
$ ./config.sub aarch64-linux-ohos
Invalid configuration `aarch64-linux-ohos': machine `aarch64-linux' not recognized
$ ./config.sub aarch64                      # 该版连裸 aarch64 都不认识
Invalid configuration `aarch64': machine `aarch64' not recognized
$ ./config.sub aarch64-unknown-linux-gnu    # 对照组：gnu 形态正常
aarch64-unknown-linux-gnu

$ PATH=/tmp/fakebin:$PATH sh ./config.guess  # fakebin/uname: -s HarmonyOS, -m aarch64
./config.guess: unable to guess system type

This script, last modified 2009-11-20, has failed to recognize
the operating system you are using. It is advised that you
download the most up to date version of the config scripts from
```

随后 configure 报 cannot guess build type 并在第一阶段中断。

仓内工具在同一份旧版脚本上的真实输出（注意 [ok] 与 Score 1/5 并存）：

```text
$ perl scripts/patch-autotools-ohos.pl config.guess config.sub
  [warn] Could not find __ANDROID__/LIBC=android in config.guess
  [warn] Could not find android-linux in config.sub
  [warn] Could not find linux-uclibc pattern in config.sub
Patching config.guess...
  [ok] Added HarmonyOS system identification
Patching config.sub...
Done. cg=1 sub=0 change(s).
config.guess: __OHOS__=0 HarmonyOS=1
config.sub:  ohos-linux=0 ohos*=0 linux-ohos=0
Score: 1/5
Some patches may have failed.            # exit code 1

$ PATH=/tmp/fakebin:$PATH sh ./config.guess   # 打完补丁后仍然失败
./config.guess: unable to guess system type   # exit 1
```

那条 [ok] 是**假成功**：插入的分支体是 GUESS=${MACHINE}-unknown-linux-ohos，而 2009 版脚本没有任何地方消费 GUESS 变量（旧版分支必须 echo 三元组再 exit）。

最隐蔽的一种：**只补 KERNEL-OS 白名单**（即只按 E122 的思路改一处）之后，config.sub 不再报错，而是以 rc=0 返回一个畸形三元组：

```text
$ ./config.sub aarch64-unknown-linux-ohos ; echo rc=$?
aarch64-unknown-linux-gnu-ohos
rc=0
$ ./config.sub arm-unknown-linux-ohos
arm-unknown-linux-gnu-ohos
```

没有任何错误行可 grep，configure 会正常跑完并把 host_os 记成 linux-gnu-ohos。此时 host_os 同时匹配 linux-gnu 与 ohos 两类 case 分支，平台相关判定被污染，问题通常延后到编译期或运行期才暴露。

## Root Cause

机制链一：2009 版 config.guess 的主 case 对 UNAME_MACHINE、UNAME_SYSTEM、UNAME_RELEASE、UNAME_VERSION 四变量拼串匹配，每个分支以 echo 三元组紧跟 exit 收尾，全文没有 GUESS= 变量（新版才有 GUESS 汇总后统一 echo）。所以按新版形态插入的分支只赋值不输出，脚本 fall through 到末尾失败分支并 exit 1。

机制链二：该版 config.sub 的 CPU 表不含裸 aarch64，只认带 vendor 的形式，所以三元组必须写成 aarch64-unknown-linux-ohos；写成 aarch64-linux-ohos 时 maybe_os 得不到已知 KERNEL-OS 组合，会把 aarch64-linux 整体当成 machine 名而报 not recognized。

机制链三：config.sub 有两道关卡，缺一不可。第一道是 maybe_os 的 KERNEL-OS 白名单，第二道是 OS 归一化阶段的基本系统类型白名单。只过第一道时 -linux-ohos 会落到末尾 -linux 兜底分支，该分支用 sed 把第一个 linux 换成 linux-gnu，得到 -linux-gnu-ohos，而脚本整体 exit 0，这就是静默畸形的来源。

## Recommended Fix / Workaround

按脚本形态打补丁，而不是套固定文本模板；打完必须实跑自校验。

1. config.guess：在首个 case 分支之前插入 HarmonyOS 分支，分支体按 uname -m 归一化 CPU，然后用旧版收尾形态 echo 三元组紧跟 exit（smalt 0.7.6 的 patches/0001 即此形态，+10 行）。
2. config.sub：同时改两处。maybe_os 的 KERNEL-OS 白名单加 linux-ohos*；OS 归一化的基本系统类型白名单加 -linux-ohos*（smalt 0.7.6 的 patches/0002，+2 行）。
3. 自校验（不可省）：实跑 config.sub 目标三元组，断言回显与输入一致；用假 uname（-s HarmonyOS、-m aarch64）实跑 config.guess，断言回显 aarch64-unknown-linux-ohos；再对 aarch64-unknown-linux-gnu、x86_64-pc-linux-gnu、arm-apple-darwin 做回归。只 grep 文本是否插入不足以判定成功，本例中仓内工具正是这样报了 ok 却无效。
4. 补丁只改构建系统脚本，不引入任何平台宏，符合 R8 与 preflight PF5 的默认禁令，无需例外说明。

## Fallback

用本机新版 config.guess/config.sub 覆盖上游旧版（automake --print-libdir 下自带），或 autoreconf 自举。代价：与上游发行包内容漂移（PR 需说明理由）、需要 tool_requires automake/autoconf、上游若依赖旧脚本特定行为还要逐条回归。

## Forbidden Approaches

1. 用 --build/--host 传伪装的 gnu 三元组绕过（E205 与 autotools-patterns.md 第 0 条明令禁止）：host_os 记成 linux-gnu，平台分支走错，经验无法复用。
2. 在 pre-2010 config.guess 里插入 GUESS= 形式的分支：静默无效，补丁器还会报 ok。
3. 只补 config.sub 的 KERNEL-OS 白名单就收工：得到 rc=0 的畸形三元组 linux-gnu-ohos，比直接报错更难查。
4. 用「补丁后 grep 是否含 linux-ohos」当成功判据：必须实跑三元组校验。

## Verification

可执行命令见配对 .kv 的 verification_cmd。本次实测：补丁前 config.sub 对三种 ohos 形态全部拒绝、config.guess 在假 HarmonyOS uname 下 exit 1；只补 KERNEL-OS 白名单时返回 aarch64-unknown-linux-gnu-ohos 且 rc=0；两处都补后返回 aarch64-unknown-linux-ohos，config.guess 亦返回该三元组，gnu 与 darwin 对照组回归无变化。端到端证据：conan create 日志中 configure 打印 checking host system type... aarch64-unknown-linux-ohos；远程 HarmonyOS CI 构建 #65959 全绿（上游 make check 通过、conan test_package 通过、L0 与 L1 门禁通过）。

## Prevention

1. 适配任何自带 configure 的 tarball 时先看 config.guess/config.sub 头部时间戳；早于 2010 年即按本条处理，不要直接套仓内 perl 工具或 E122/E160 的命令。
2. 把「实跑 config.sub 与 config.guess 并断言输出」固定为补丁后的必做动作，而不是 grep 文本。
3. 框架侧建议：patch-autotools-ohos.pl 增加年代形态分支（检测不到 GUESS= 时改用 echo 加 exit 形态），Score 小于 5 时以非 0 退出并去掉误导性的 ok 行；prescan 可用 .kv 的 prescan_pattern（脚本头部 last modified 年份）提前标记旧版脚本。

## References

- 本仓知识：E007、E072、E122、E160、E205、E268、E279、E490；references/iron-rules.md R8；knowledge/operations/build-systems.md 第 3 节
- 实证载体：archives/s/smalt/0.7.6/patches/0001-config.guess.patch、patches/0002-config.sub.patch、notes.md 问题表第 1 与第 2 行
- PR #14095（远程 CI 构建 #65959 通过）
