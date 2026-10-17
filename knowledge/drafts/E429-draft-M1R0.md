# E429 — 老版 config.guess 无 GUESS 出口机制：E007 补丁插入的 HarmonyOS 分支不生效

## 错误特征

```
configure: error: cannot guess build type; you must specify one
```

按 E007 用 `patch-autotools-ohos.pl` 给 `config.guess` 打了 HarmonyOS 分支后，
单独执行 `sh admin/config.guess` 仍输出：

```
config.guess: unable to guess system type

This script, last modified 2012-02-10, has failed to recognize
the operating system you are using. ...
uname -s = HarmonyOS
```

即补丁"看起来应用成功"（文件中确实出现了 `HarmonyOS` 分支），但行为没有变化。

## 触发条件

- 构建系统: autotools（源码包内含**预生成**的 `configure` / `config.guess` / `config.sub`）
- 辅助脚本年代: 约 2010–2014（本案例为 `timestamp='2012-04-18'`）
- 阶段: configuration（`AC_CANONICAL_HOST` 触发的 `config.guess` 调用）

## 根因分析

新版（约 2015 之后）的 `config.guess` 主 `case` 各分支采用统一出口：分支内只给
`GUESS=` 赋值，脚本末尾统一 `echo "$GUESS"` 输出。因此补丁脚本按这种风格插入：

```sh
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64) MACHINE=aarch64 ;;
	    ...
	esac
	GUESS=${MACHINE}-unknown-linux-ohos      # 只赋值，无输出
	;;
```

而本案例的 2012 版 `config.guess` **没有** GUESS 出口机制：每个分支必须自带
`echo ... ; exit ;;`，脚本末尾是报错块（`unable to guess system type` + `exit 1`）。
于是插入的分支赋值后被 fall through 到末尾，直接报错退出。

同代 `config.sub` 同样缺新版锚点：没有 `android-linux)` 分支，也没有
`gnu* | android*` 的 OS 列表，三处 ohos 支持一处都没有命中（本案例改动手工完成）。

## 诊断方法

```bash
# 1. 看主 case 的出口风格（有无 GUESS 变量机制）
grep -n "GUESS" admin/config.guess        # 只出现在你插入的那一行 = 老版，无出口机制
grep -n "unable to guess system type" admin/config.guess   # 存在 = 走报错出口

# 2. 直接验证脚本行为（不要只看补丁是否应用成功）
sh admin/config.guess                       # 期望：aarch64-unknown-linux-ohos
sh admin/config.sub aarch64-unknown-linux-ohos   # 期望：原样返回该三元组
```

## 修复方案

1. `config.guess`：插入分支改为自带输出与退出：

```sh
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64) MACHINE=aarch64 ;;
	    armv7*|armv8*) MACHINE=arm ;;
	    x86_64|amd64)  MACHINE=x86_64 ;;
	    i?86)         MACHINE=i686 ;;
	    *)            MACHINE="$UNAME_MACHINE" ;;
	esac
	echo "${MACHINE}-unknown-linux-ohos"
	exit ;;
```

   参考仓库既有写法：`archives/a/abook/0.6.1/patches/0001-config.guess.patch`
   （该补丁同时把 `HarmonyOS` 加进 `Linux|GNU|GNU/*` 的 LIBC 检测分支）。

2. `config.sub`：手工补三处（老版无 `android-linux` 锚点可依赖）：
   - `maybe_os` 列表加入 `linux-ohos*`
   - 内核-OS 校验列表加入 `-linux-ohos*`
   - OS 校验分支加入 `-linux-ohos*) os=-linux-ohos ;;`
   参考 `archives/a/acpitool/0.5.1/patches/0002-config.sub.patch`。

3. 禁止用 `--build=`/`--host=` 绕过：那会让 `AC_RUN_IFELSE` 等运行时检查全部跳过、
   生成错误的 `config.h`（autotools-patterns #0）。

## 验证

```bash
sh admin/config.guess                              # aarch64-unknown-linux-ohos
sh admin/config.sub aarch64-unknown-linux-ohos     # aarch64-unknown-linux-ohos
./configure && make && make check
```

实测案例（miredo 1.2.6，2026-10-14）：`admin/config.guess` 为 2012 版，
按上述改法后 configure 通过、`make check` 11 PASS / 1 SKIP。

## 相关

- E007（config.guess/config.sub 缺 HarmonyOS 识别——本条是其"老版脚本"边界）
- archives/a/abook/0.6.1/patches/0001-config.guess.patch
- archives/a/acpitool/0.5.1/patches/0002-config.sub.patch
