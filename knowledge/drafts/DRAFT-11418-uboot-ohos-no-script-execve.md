# DRAFT-11418 — OHOS 内核禁脚本 execve（binfmt_script 缺失）：Kbuild/Kconfig 辅助脚本改经 sh/$(CONFIG_SHELL) 解释执行（不可改写调用点用同名 ELF 包装器）

- **条目 ID**: `DRAFT-11418-uboot-ohos-no-script-execve`
- **严重度**: 1（conf 构建链解析期即炸、无绕过路径；但修复模式固定可复用）
- **类别**: kernel, permissions, build, execve
- **触发工具/阶段**: make | kconfig | conf | sh — conan_build
- **来源**: u-boot 2026.07 适配（task #11418，OHOS PC 真机 2026-09-29，上游 denx 发行包 + 补丁）

## 错误特征

```
/bin/sh: scripts/gcc-version.sh: Permission denied    （直接 exec）
sh: scripts/gcc-version.sh: Permission denied          （sh -c file）
# rc=126；而 sh scripts/gcc-version.sh 正常执行
```

## 场景

OHOS 内核不提供脚本解释器 execve（binfmt_script 缺失级平台策略）：
对带 shebang 的脚本直接 exec 一律 **EACCES rc=126**，`sh -c scriptfile`
同样被拒，而 `sh scriptfile`（显式解释器）正常——与文件属主、目录、
mode、mtime 全无关（真机实测：新建文件同样被拒），ELF 二进制 exec
正常。Linux/macOS 无感。

u-boot Kbuild 四个直接 exec 点实测全炸（patch 0002 覆盖，炸点全集
枚举见 notes.md 决策表第 8 条）：

1. `scripts/Kconfig.include:34` 的 `gcc-version` 宏——conf 解析 Kconfig
   时 `$(shell,)` 直接 exec `gcc-version.sh`；
2. 顶层 `Kconfig:90/98` 的 `$(shell ... gcc-version.sh / clang-version.sh)`；
3. `Makefile` 的 `cmd_ofcheck` 在 `all` 配方里直接 exec `check-of.sh`；
4. `scripts/Makefile.build:249` 的 `cmd_check_local_export`——每个
   `.o` 编译后直接 exec `check-local-export`（该脚本还是 bash 脚本：
   用 shopt，设备 /bin/sh 无 shopt、/bin/bash 不存在，bash 在
   /data/service/hnp/bin/bash）。

另外 2 处（endian-swap/mkuboot）因无大端/SPL 配置不触发，保持上游
原样。第 5 处 gen_ll 曾初判不触发是**误判**（教训：判断开关终态以
.config 为准）——sandbox 的 Kconfig `imply LTO`（arch/Kconfig:236）
在 defconfig 无字面量的情况下仍把 CONFIG_LTO 拉成 y（qemu_arm64 无
LTO 不受影响）；LTO 开启后 keep-syms-lto.c 生成规则在链接前直接
exec `gen_ll_addressable_symbols.sh`（生成链接器列表符号的
__ADDRESSABLE 引用、防 LTO 消符号）→ 真机 make[1] Error 126
（build.log 实证）。patch 0011 同款 `$(CONFIG_SHELL)` 前缀修复。

## 推荐方案（patch 0002，真机验证）

四处直接 exec 改显式解释器路由：

- `Kconfig.include` 的 gcc-version 宏与顶层 Kconfig 两条 version 宏：
  改为 `$(shell $(CONFIG_SHELL) scripts/gcc-version.sh ...)`；
- `cmd_ofcheck`：`check-of.sh` 前加 `$(CONFIG_SHELL)`；
- `cmd_check_local_export`：`check-local-export` 前加 `$(CONFIG_SHELL)`；
  配套配方传入 `CONFIG_SHELL=bash`（u-boot Makefile 硬编码
  `CONFIG_SHELL:=sh`，Kbuild 标准覆盖位），因该脚本是 bash 脚本；
- `cmd_keep_syms_lto`（patch 0011，LTO 开启后暴露）：keep-syms-lto.c
  生成规则直接 exec `gen_ll_addressable_symbols.sh`，同款
  `$(CONFIG_SHELL)` 前缀。

通用原则：OHOS 上所有「构建系统 exec 脚本」的路径必须显式经
sh/bash 解释（CONFIG_SHELL/SHELL 变量、cmake 的 `execute_process`
加 `COMMAND sh`、autotools 的 CONFIG_SHELL）。

## 影响

适用任何 make/autotools/cmake 构建在 OHOS 的适配：凡是配方或配置
解析直接 exec 辅助脚本（sh/perl/python 带 shebang 直跑）的都会
EACCES。与 u-boot 无关的通用平台约束。

**排查口诀**：错误签名是 EACCES/rc=126 而非 ENOENT，且 `sh file`
正常 → 必是脚本 execve 禁令，不是权限/存在性问题。易误判点：
`sh -c file` 也报 EACCES 会让「改用 sh -c」的直觉修复失效——必须
显式解释器直跑脚本路径。

## 恢复

两条路线，按调用方可改性分流：

1. 调用点可改写（patch 路线，u-boot 场景 4+1 处）：逐点改经显式
   解释器（sh/$(CONFIG_SHELL)）。注意不能仅靠 `CONFIG_SHELL=/bin/sh`
   绕（exec 的是脚本路径本身，与 CONFIG_SHELL 无关），必须改调用点
   为显式解释器；改完之后 CONFIG_SHELL 才起作用——此时若脚本是
   bash 脚本（shopt 等），配方须 `CONFIG_SHELL=bash`（设备 /bin/sh
   无 shopt、bash 在 HNP 工具链 PATH）。
2. 调用点是**上游不可改写的文字**、且以「命令」形式调用（PATH
   查找 / popen / `$(shell 变量)`）——sh 前缀改写不可行（实测
   busybox sh 对 `<script>` 操作数**不做 PATH 查找**，`sh sdl2-config`
   报 No such file，全路径才行），此时用**同名 ELF 包装器（shim）**：
   内核可 execve ELF，包装器 `execv("/bin/sh", ["sh", <真脚本全路径>,
   参数...])` 由 sh 打开脚本执行，参数/退出码透明转发；配方编译后
   置于 PATH 前位（或钉进 SDL_CONFIG 类覆盖位）+ 构建期冒烟
   `--version`。2026-10-10 真机实证：制品仓 sdl2/2.30.10 的
   sdl2-config（sh 脚本）经包装器后，arch/sandbox/Kconfig 探测
   `$(success,sdl2-config --version)` 由静默 n 翻 y
   （`CONFIG_SANDBOX_SDL=y` 落 .config）。

## 证据链

真机 2026-09-29（上游 denx 2026.07 发行包 + 补丁，reports/）：

- 真机实证：`sh file` 可读可跑、直接 exec 与 `sh -c file` 一律
  EACCES rc=126，与文件属主/目录/mode 无关（新建文件同样被拒），
  ELF exec 正常；
- 修复前 conf 构建链在 gcc-version.sh 处 EACCES 中断（build.log
  实证）；修复后 conf/zconf/lex 全链构建通过，sandbox_defconfig 与
  qemu_arm64_defconfig 均正常；
- 2026-09-30 第 5 炸点实证：CONFIG_LTO=y（sandbox `imply LTO`）后
  keep-syms-lto.c 规则 exec gen_ll_addressable_symbols.sh → make[1]
  Error 126；0011 修复后该规则经 bash 执行成功；
- 2026-10-10 包装器实证（命令式调用变体）：制品仓 sdl2 的
  sdl2-config 为 sh 脚本，直测 `sh -c 'sdl2-config --version'` →
  Permission denied rc=126（Kconfig `$(success,)` 探测即此形态）；
  同名 ELF 包装器（execv /bin/sh 打开真脚本）置 PATH 前位后探测
  翻 y（CONFIG_SANDBOX_SDL=y / CONFIG_VIDEO_SANDBOX_SDL=y 落 .config）；
- 详见 patches/0002-kbuild-script-exec-via-shell.patch 与
  patches/0011-keep-syms-lto-script-via-shell.patch。

## 验证命令

```sh
make O=<obj> HOSTCC=clang CC=clang NO_PYTHON=1 CONFIG_SHELL=bash sandbox_defconfig
# 修复前：gcc-version.sh EACCES rc=126；修复后：defconfig 正常写出
```

## 局限

1. 只覆盖构建期 exec 点；运行时程序内部 spawn 脚本需另行处理
   （posix_spawn 走 sh -c 或改为直接 exec 解释器）；
2. 若未来 OHOS 内核启用 binfmt_script，本修复自动退化为无害等价
   写法（上游兼容）。
