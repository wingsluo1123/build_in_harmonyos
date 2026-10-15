# DRAFT-7871：自研 Makefile 的"生成式配置片段"不能手写 —— 丢了 CXXDEP/CCDEP 会让源文件被当命令执行

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-11
> Source: kmer 0-20150903-r2013 HarmonyOS PC 适配（archives/k/kmer/0-20150903-r2013）
> 对应：knowledge/drafts/DRAFT-7871-kmer-generated-make-compilers-tool-definitions.kv
> 相关：DRAFT-E640（uname 分支型 Makefile 的平台选择）、E114/E386（HMDFS 上 cwd 失效）

## 现象

kmer（Celera/JCVI）用自研非递归 make：`Makefile` + `Make.rules` + 各目录 `Make.include`，
平台配置由 `configure.sh` 的 `case` 分支写成 `Make.compilers`，Makefile 再 `include` 它。

第一次适配时为了绕过"`configure.sh` 不认识 HarmonyOS、Linux 分支还带 x86 的 `-m64`"，
直接手写了一份 `Make.compilers`（只写了 CC/CXX/*FLAGS*/CLIBS/INSTALL）。结果 `make` 立刻报：

```text
making /path/libutil/recordFile.C.d
/bin/sh: /path/libutil/recordFile.C: can't execute: Permission denied
making /path/libutil/speedCounter.C.d
/bin/sh: /path/libutil/speedCounter.C: can't execute: Permission denied
...
make: *** No rule to make target 'ESTmapper/mergeCounts.o', needed by 'ESTmapper/mergeCounts'.  Stop.
```

报错看起来像"HMDFS 权限问题"，实际是**规则被展开成了把源文件当命令执行**。

## 根因

`Make.compilers` 是混合体，里面有两类内容：

| 类别 | 内容 | 谁写 |
|------|------|------|
| 平台块 | `CC`/`CXX`/`CFLAGS_COMPILE`/`CXXFLAGS_COMPILE`/`CLDFLAGS`/`CLIBS`/`SHLIB_FLAGS`/`ARFLAGS`/`INSTALL/` | `configure.sh` 的 `case` 分支 |
| **公共工具定义** | `.EXE`/`.SO`/`.A`/`.O`、`CLD`、`CXXLD`、**`CCDEP`/`CXXDEP`**、`PYTHON*`、`WITHOUT` | `configure.sh` 末尾统一 `cat >> Make.compilers` 追加 |

手写整个生成物就丢掉了第二类。`Make.rules` 的依赖生成规则：

```make
${ALL_CXX_DEPS}:%.d:%
	@ dir=`echo $< | sed -e's~[^/]*$$~~'`; 	  ${CXXDEP} ${CXXDEPFLAGS} ${CXXFLAGS} $< | 	  sed -e"/:/s!^!$${dir}!" > $@
```

`${CXXDEP}` 为空时展开为 `  <src>.C | sed … > <src>.C.d`：命令行首 token 变成源文件路径，
`/bin/sh` 试图执行它 → `can't execute: Permission denied`。报错位置（依赖生成）与根因（少了几个变量定义）
相距极远，极易误判成文件系统权限问题。

附带陷阱：顶层 Makefile 通常带兜底——

```make
ifneq ($(shell ls -d ${MAKEFILE/}/Make.compilers 2> /dev/null), ${MAKEFILE/}/Make.compilers)
  MAKECOMPILERSNOTHING := $(shell ${MAKEFILE/}configure.sh)
endif
```

手写生成物会让这条兜底失效，上游的配置步骤被静默跳过。

## 判定方法（先看生成物，再改）

```sh
# 1) 配置片段是生成物吗？（Makefile 里引用 + "缺了就调 configure.sh" 的兜底）
grep -n "Make.compilers" Makefile

# 2) 生成后公共工具定义是否在位（缺这几个变量就会命中本条）
bash ./configure.sh OHOS-arm64
grep -nE "^(CXXDEP|CCDEP|\.O|CLD|CXXLD)" Make.compilers

# 3) 构建日志里出现 "<src>.C: can't execute" 且紧跟在 making *.d 之后 → 本条
```

## 处置（只加平台分支，让脚本生成）

```diff
--- a/configure.sh
+++ b/configure.sh
@@
+  OHOS-arm64)
+    rm -f Make.compilers
+    cat <<EOF > Make.compilers
+# -*- makefile -*-
+#  HarmonyOS PC (aarch64), optimized
+CC                := $CC
+SHLIB_FLAGS       := -shared
+CFLAGS_COMPILE    := -fPIC -D_REENTRANT -O3 -D_THREAD_SAFE -pthread -fmessage-length=0 -Wall -Wno-char-subscripts -fcommon -fno-strict-aliasing
+CLDFLAGS          :=
+CLIBS             := -pthread
+CXX               := $CXX
+CXXFLAGS_COMPILE  := -fPIC -D_REENTRANT -O3 -D_THREAD_SAFE -pthread -fmessage-length=0 -Wall -Wno-char-subscripts -fcommon -fno-strict-aliasing
+CXXLDFLAGS        :=
+CXXLIBS           := -pthread
+ARFLAGS           := ruvs
+INSTALL/          := $target/
+EOF
+    ;;
```

配方侧只需显式传目标（HarmonyOS 不在脚本的 `uname` 分支里，不要指望自动识别）：

```sh
CC=<clang> CXX=<clang++> bash ./configure.sh OHOS-arm64 && make -j1 && make -j1 install
```

**不要**手写/整体替换 `Make.compilers`，也**不要**把它提交进仓库。

## 验证

```text
kmer 0-20150903-r2013：改用 configure.sh 生成后
  conan create rc=0；make -j1 install → OHOS-arm64/{bin(58),include(58),lib(9 个 .a)}
  消费者用例 6/6 通过（KMER_CONSUMER_OK）
```

## 通用化建议

1. 见到"自研 make + 生成式配置片段"的工程，先确认片段里除了编译选项还有什么：
   `.O`/`CLD`/`CXXDEP` 这类**工具定义**往往就藏在同一个文件里，替换式修法会连带丢定义。
2. 报错是"某个源文件不能被当命令执行"时，优先怀疑 **make 变量为空导致规则退化**，而不是文件系统权限；
   `make -n` 或看 `make` 打印的实际命令行即可确认首 token。
3. 平台适配优先"给上游脚本加分支"，而不是"替上游写配置文件"——前者零语义漂移，后者会绕过上游的完整性校验与兜底逻辑。
