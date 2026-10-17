# E430 — config.guess 运行期 umask 077 临时目录在 HMDFS 下不可写

## 错误特征

config.guess 走编译探测路径时，先报建不了探测源文件，再报猜不出系统：
```
admin/config.guess: cannot create $TMPDIR/cgXXXXXX/dummy.c: Permission denied
admin/config.guess: unable to guess system type
```

与 E114 的区别：E114 报在 `config.status` 的 `could not setup config files machinery`，
本条目报在 configure 之前的 config.guess 阶段。

## 触发条件

- 构建系统: autotools，源码树位于 HMDFS（鸿蒙 PC 工作区）
- 阶段: configure（`configure` 首次调用 `$ac_aux_dir/config.guess`）
- 前置: config.guess 的已知平台分支未命中 HarmonyOS，因而退回编译探测
  （E007/E429 未修时会必然触发）

## 根因分析

旧版 config.guess 的探测逻辑用
```sh
(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX") 2>/dev/null
```
建临时目录再写 `dummy.c`。HMDFS 会把 0700 目录的属主归一化为其他 uid
（E110/E114 记录的平台特性），目录呈 `drwx--S---` 时连原属主也无写权限，
于是写 `dummy.c` 报 Permission denied，探测失败后脚本走到失败出口。

即 E114 的口径不只适用于 `configure`/`config.status` 生成的临时目录，
**config.guess 运行期自建的 `cgXXXXXX` 同样中招**。

## 解决方案

### 推荐方案（rec_priority 1）

去掉 config.guess 中所有 `umask 077`（三处 fallback 链都要改，只改一处仍会在
另一条候选路径上失败），改为默认 umask / `umask 022`，与 E114 对 configure 的
处理同口径。

```sh
grep -n "umask 077" admin/config.guess     # 定位全部命中点
```

miredo 1.2.6 实例：`patches/0004-admin-config.guess.patch`。

### 禁止做法

- ❌ 只改 `configure` 不改 `config.guess`：configure 之前就死在猜测阶段
- ❌ 用空操作绕过 config.guess 直接写死三元组（会丢掉 build/host 的真实判定，
  且掩盖后续 E429/E007 的修复）

## 验证

```bash
cd <源码根>
sh admin/config.guess 2>&1 | tail -5     # 期望直接输出 aarch64-unknown-linux-ohos
ls -ld $TMPDIR/cg* 2>/dev/null         # 不应再出现 drwx--S--- 且不可写的目录
```

## 关联条目

- 相关: E114（HMDFS 权限归一化 / configure 临时目录）、E429（旧版 config.guess 分支不生效）、E110
