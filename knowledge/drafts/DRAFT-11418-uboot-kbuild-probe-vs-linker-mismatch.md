# DRAFT-11418 — Kbuild 探测用链接器与实际链接器错配：GNU ld 接受的旗标被 lld 硬拒，按实际链接器守卫探测

- **条目 ID**: `DRAFT-11418-uboot-kbuild-probe-vs-linker-mismatch`
- **严重度**: 1（链接期硬错、无绕过路径；但修复模式固定可复用）
- **类别**: build, toolchain, linker, kbuild
- **触发工具/阶段**: make | clang | ld.lld — conan_build
- **来源**: u-boot 2026.07 适配（task #11418，OHOS PC 真机 2026-09-30，上游 denx 发行包 + 补丁）

## 错误特征

```
ld.lld: error: unknown argument '--no-warn-rwx-segments'
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
```

## 场景

Kbuild 的探测函数只对「探测时」的组件做兼容性测试，组件被替换后
结论即失效：

1. 顶层 `Makefile:1036` 以 `ld-option` 对 `$(LD)`（GNU ld）探测
   `--no-warn-rwx-segments`——bfd 2.39+ 的 RWX LOAD 段警告抑制旗标，
   GNU ld 接受，探测通过后经 `KBUILD_LDFLAGS` → `-Wl,` 进入
   `cmd_u-boot__` 链接命令；
2. 配方层以 `LTO_FINAL_LDFLAGS=-fuse-ld=lld`（OHOS 上 clang LTO
   缺 LLVMgold 插件的既定路由，见 DRAFT-11418-uboot-ohos-no-script-
   execve 的问题 12 配套）把实际链接器换成 lld；
3. 探测通过时生效的旗标直达 lld——lld 无此旗标且对未知旗标**硬错**
   （非忽略）→ 真机 LTO u-boot 链接失败（build.log 实证）。

`scripts/Makefile.lib-u-boot:76` 的同名探测（`KBUILD_EFILDFLAGS`）
不受影响：EFI 链接直接用 `$(LD)`，不经过 lld，真机该段已构建成功
——所以只修 `KBUILD_LDFLAGS` 一条。

## 推荐方案（patch 0012）

按实际链接器守卫探测——仅 lld 路由生效时跳过：

```make
# --no-warn-rwx-segments 是 GNU ld 的警告抑制旗标；lld 无此旗标
# 且硬报 unknown argument。经 lld 链接（如 OHOS 上 LTO_FINAL_LDFLAGS
# 带 -fuse-ld=lld）时跳过该探测，其余环境保持上游原样。
ifeq ($(filter -fuse-ld=lld,$(LTO_FINAL_LDFLAGS)),)
KBUILD_LDFLAGS  += $(call ld-option,--no-warn-rwx-segments)
endif
```

其余环境（上游 gcc、CI clang+GNU ld）保持原样。跳过后 OHOS 上
失去的仅是 bfd 警告抑制（lld 本不产生该警告），无功能差异。

**通用原则**：任何「换链接器」的适配（`-fuse-ld=lld`、
`LD=ld.lld`、LDFLAGS 直传）必须全量复核 `ld-option`/`cc-ldoption`
类探测结论；反之若只想调整探测本身，可用 ld-option 的三参形式
`$(call ld-option,flags,fallback,probe-command)` 让探测与实际链接器
一致（一处修复全部探测）。

## 影响

适用一切 Kbuild 工程（u-boot/内核）在 OHOS 或任何 lld 路由环境
的适配：bfd 2.39 时代新增的 `--no-warn-rwx-segments` 只是首个实例，
ld-option 探过的其他 bfd 专用旗标在 lld 下同样会踩。错误签名固定：
`ld.lld: error: unknown argument '--xxx'`。与 u-boot 无关的通用
平台约束。

## 恢复

若链接器替换无法避免，可整体性方案：把 ld-option 的探测命令改为
实际链接器（三参形式传入 `clang -fuse-ld=lld` 包装），一处修复
全部探测；但 u-boot 场景只有一处实际踩雷，按实际链接器守卫该
探测更诚实、最小化。不可直接把旗标从 `KBUILD_LDFLAGS` 全局摘除
——那会改变所有 GNU ld 环境的警告行为。

## 证据链

真机 2026-09-30（上游 denx 2026.07 发行包 + 补丁，reports/）：

- 0011 + 配方 lld 路由落地后，LTO u-boot 链接报
  `ld.lld: error: unknown argument '--no-warn-rwx-segments'`、
  `clang-15: error: linker command failed with exit code 1`
  （build.log 实证）；
- 旗标来源定位：顶层 Makefile:1036 `KBUILD_LDFLAGS += $(call
  ld-option,--no-warn-rwx-segments)`，ld-option 对 `$(LD)`=GNU ld
  探测；`scripts/Makefile.lib-u-boot:76` 同名探测走 `$(LD)` 不受
  影响（EFI 链接实测正常）；
- 0012 修复后真机全链验证：待回填（重试环下一轮）；
- 详见 patches/0012-ldflags-no-warn-rwx-guard-for-lld.patch 与
  notes.md 决策表第 16 条。

## 验证命令

```sh
make O=<obj> HOSTCC=clang CC=clang NO_PYTHON=1 CONFIG_SHELL=bash \
  LTO_FINAL_LDFLAGS=-fuse-ld=lld sandbox_defconfig
# 修复前：LTO u-boot 链接 ld.lld unknown argument；修复后：链接通过
```

## 局限

1. 守卫信号绑定本适配的 lld 路由位（`LTO_FINAL_LDFLAGS` 带
   `-fuse-ld=lld`）；若未来 OHOS 改走其他 lld 注入路径（如
   `LD=ld.lld`），守卫需同步扩展；
2. 仅覆盖 `KBUILD_LDFLAGS` 一条探测；其他 ld-option 调用点如后续
   再踩，按同款守卫逐一处理。
