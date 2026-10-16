# DRAFT-10863: HMDFS uid 映射 + umask 077（0700）目录 → 落 group 分支无权限 → configure EACCES

- **来源**：sox_ng 14.8.0.1 适配（2026-10-13）
- **领域**：文件系统权限模型（HMDFS）× autotools 构建系统
- **邻近但不同**：DRAFT-10767（puredata config.guess 双失败：uname 不识别 HarmonyOS + HMDFS tmp 编译探测 Permission denied，修复 = 显式 `--build/--host` 跳过探测）——该条是 config.guess 阶段探测被拒写；本条是 config.status 所建 0700 目录的 group 权限问题，修复不同

## 现象

鸿蒙 PC 真机上 `./configure` 中止：

```
configure: error: could not setup config files machinery
```

伴随错误：写 `confXXXXXX/subs1.awk`（autoconf 生成的替换中间文件）
EACCES / Permission denied。

## 根因

两个平台事实叠加：

1. **HMDFS uid 映射**：文件属主 uid（实测 20001006）≠ 进程 kernel
   uid。VFS 权限检查无法进入 owner 分支，只能落到 group 分支
   （group 为 `file_manager`）；
2. **umask 077**：autoconf 生成的 `configure`/`config.status` 用
   `(umask 077 && mktemp -d "./confXXXXXX")` 建安全临时目录 →
   mode 0700（owner rwx，group/other 无权限）。

叠加：进程创建目录后向 `confXXXXXX/subs1.awk` 写入时，权限检查落
group 分支、0700 无 group 权限 → EACCES。

### 对照实验（实测）

| 环境 | 命令 | 目录 mode | 可写？ |
|------|------|---------|--------|
| tmp 挂载（属主 uid 与进程 uid 匹配） | `umask 077 && mktemp -d` + 写 | 0700 | ✅ WRITE_OK |
| HMDFS | 普通 `mkdir`（umask 002） | 2731（group rwx） | ✅ |
| HMDFS | `mktemp`（umask 077） | 2700（group 无权限） | ❌ EACCES |

→ 问题不在 umask 本身，而在 **uid 不匹配 + 0700** 的组合。

## 修复（patch umask，无平台宏，glibc 行为不变）

把构建工具脚本中的 `umask 077` 改为 `umask 007`（保留 group rwx，
去掉 other）：

- patch 对象：`configure`、`config.guess`（构建路径上的 autoconf
  生成脚本），本条实测共 5 处；
- 不 patch：`Makefile.in` 的 umask 077（位于 installcheck/distdir
  规则，非构建路径）;
- glibc/tmp 挂载（uid 匹配）下：目录变 0770，进程有 owner 权限，
  行为完全不变（无副作用）；
- R8 合规：`umask 007` 是可移植无害改动，不引入 `__OHOS__` 宏。

## 排查口诀

> HMDFS 真机 configure 报 "could not setup config files machinery" /
> 写 confXXXXXX/*.awk Permission denied：先 `stat` conf 目录 mode
> （应为 0700/2700）+ 属主 uid 与 `id -u` 对比，两者不匹配 → 基本
> 就是本条。通用修法：把构建脚本里该 umask 从 ≥070 改为 007。

## 三段式证据链（本条已实测）

| 步骤 | 状态 | 结果 |
|------|------|------|
| 未打补丁 | configure 失败 | 写 confXXXXXX/subs1.awk EACCES → "could not setup config files machinery" |
| 对照实验 | 根因确认 | 同命令 tmp 挂载 OK；HMDFS 2731 可写 / 2700 不可写 → uid 映射 + 0700 |
| 打 umask 007 补丁 | 通过 | `./configure` + `make check` 退出码 0（src 168 ok + check.sh 74 OK + 2 VOID，0 失败） |

反向验证：还原 umask 077 后 configure 失败复现。

## 适用范围

- 所有在 HMDFS 下运行 configure/config.status 的 autotools 项目
- 更一般：任何在 HMDFS 上用 `umask ≥ 070` 创建目录/文件的构建工具
  （meson、老 GNU 工具的安全临时目录模式等）
- 诊断口径：conf 目录 mode 0700/2700 + 文件属主 uid ≠ `id -u` +
  写入 EACCES

## 关联文件

- `archives/s/sox_ng/14.8.0.1/patches/0003-configure.patch`（umask 077→007）
- `archives/s/sox_ng/14.8.0.1/patches/0001-config.guess.patch`（umask 077→007，与 E007 triplet 修复同补丁）
- `archives/s/sox_ng/14.8.0.1/notes.md`（踩坑与解决 §9，含对照实验数据）
