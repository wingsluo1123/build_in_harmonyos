# DRAFT — OHOS 的 `uname().release` 不以数字开头 ⇒ 自带内核版本前置闸的 fs 工具被**两层**拒绝

> 草稿 ID：`DRAFT-exfatprogs-1.4.3-non-numeric-uname-release-kernel-gate`
> 来源事件：exfatprogs 1.4.3 HarmonyOS PC 适配（平台任务 15241，2026-10-15 真机实测）
> 状态：草稿（待主编 promote 为正式 E 条目）

## 1. 稳定错误签名与可复现症状

未打补丁时，`fsck.exfat` / `mkfs.exfat` / `tune.exfat` / `exfatlabel` / `dump.exfat`
**全部**在第一个前置检查就退出：

```text
$ fsck.exfat exfat.img
exfatprogs version : 1.4.3 (2026-08-14)
failed to get kernel version.
failed to open /…/exfat.img. -1
$ echo $?
8
```

上游数据驱动套件的汇总行同样是全灭：

```text
$ bash tests/test_fsck.sh
Running ./bad_root
failed to get kernel version.
failed to open exfat.img. -1
Failed to detect corruption for ./bad_root
Passed 0 of 23
$ echo $?
1
```

正则签名（可直接喂引擎）：

```text
failed to get kernel version\.|failed to open .*\. -1|pre-2\.6 kernel version not supported
```

## 2. 根因：这是**两层**闸，只修第一层修不好

`uname()` 实读：

```text
sysname='HarmonyOS' release='HongMeng Kernel 1.12.0' machine='aarch64'
```

**第一层（解析）** — `lib/libexfat.c:exfat_cmp_kernel_ver()`：

```c
ret = uname(&uts);
if (ret) return -1;
switch (count_dots(uts.release, 65)) {
default:
    ret = sscanf(uts.release, "%hu.%hu.%hu", v + 0, v + 1, v + 2) != 3;
}
if (ret) { errno = EINVAL; return -1; }          // ← 落这里
```

`sscanf` 只认**字符串开头**的数字，首字符 `'H'` 直接匹配失败 ⇒ `return -1`
⇒ 调用方 `exfat_get_blk_dev_info()`：

```c
switch (exfat_cmp_kernel_ver(MIN_KERNEL_VER)) {   // MIN_KERNEL_VER = {2,6,0}
case -1: exfat_err("failed to get kernel version.\n"); return -1;
case  1: exfat_err("pre-2.6 kernel version not supported\n"); return -1;
}
```

**第二层（比较）** — 即便把解析改成"取第一个数字段"拿到 `1.12.0`：

```text
nhost = 1<<32 | 12<<16 = 0x1_000C_0000
nreq  = 2<<32 |  6<<16 = 0x2_0006_0000   ⇒ nreq > nhost ⇒ return 1
```

第二层立刻以 `pre-2.6 kernel version not supported` 再拒绝一次。**两层共用同一个
`exfat_cmp_kernel_ver()`，任何只改解析的修法都会被第二层挡回来。**

闸的前提在本包身上并不成立：`exfat_get_blk_dev_info()` 只有在 `fstat()` 判定
`S_ISBLK` 之后才去碰 `/sys/dev/block`（本机该路径实测 `Permission denied`），
普通文件镜像的 `S_ISREG` 路径完全不经过那段代码 —— 也就是说"内核 ≥2.6 才有
sysfs 接口"这条前提，对本包实际交付的面**既不可验证也不被需要**。

## 3. 最小复现

```bash
# 1) 确认 release 非数字前缀
python3 -c "import os;print(os.uname().release)"      # HongMeng Kernel 1.12.0
# 2) 不打补丁跑上游套件
bash tests/test_fsck.sh                                # Passed 0 of 23, rc=1
# 3) 只修解析（假设已改），再跑
bash tests/test_fsck.sh                                # 仍然全灭，首错变成
                                                       # pre-2.6 kernel version not supported
# 4) 打上本草稿的补丁
bash tests/test_fsck.sh                                # Passed 23 of 23, rc=0
```

## 4. 已尝试 / 被排除的方案

| 方案 | 结论 | 为什么 |
|---|---|---|
| 只把 `sscanf` 改成"跳到第一个数字再解析"（即既有条目 `DRAFT-ohos-kernel-version-string` 的推荐方案） | **不成立** | 解析成功后 `1.12.0 < 2.6.0`，第二层仍返回 1，工具照旧全灭 |
| 把 `MIN_KERNEL_VER` 从 `{2,6,0}` 调低（如 `{1,0,0}`） | **不成立** | 治不了第一层（解析仍返回 -1）；且改掉 Linux 上的判定语义，真 2.4 内核会被误放行 |
| 注入 `#ifdef __OHOS__` 走平台分支 | **不采用** | CI `PF5` 平台宏闸直接拦（patches 新增行禁 `__OHOS__`）；且非 OHOS 内核上这段代码没有意义 |
| 读 `/proc/version` 交叉判断 | **不采用** | 本机 `/proc/version` 实测 `Permission denied`，多引一个受限面 |
| 环境层绕过（改 profile / `LANG` / `LC_ALL`） | **无效** | 该判定是纯 C 的 `sscanf`，与 locale、环境无关 |

## 5. 最终方案与真实验证

补丁 `patches/0001-lib-exfat-skip-kernel-version-gate-for-non-numeric-release.patch`
（+14 行，`strip: 1`）：

```c
	ret = uname(&uts);
	if (ret)
		return -1;
+	/*
+	 * A release string that does not begin with a digit carries no kernel
+	 * version this comparison can evaluate: the sscanf() below expects the
+	 * number in the leading field.  …
+	 * Treat such a release as "version unknown" and let the caller proceed.
+	 */
+	if (uts.release[0] < '0' || uts.release[0] > '9')
+		return 0;
```

判据是**字符串形状**而不是平台宏：Linux release（`6.6.0-…`）以数字开头，走原有
两层判定、行为逐字节不变；不以数字开头的 release 视为"版本不可评估 → 放行"。
一处改动同时关掉两层闸，不改 `MIN_KERNEL_VER`、不改任何测试断言。

**实测（2026-10-15，HarmonyOS PC / aarch64 / HongMeng Kernel 1.12.0 / clang 15.0.4）**：

| 项 | 补丁前 | 补丁后 |
|---|---|---|
| `fsck.exfat <image>` | rc=8，`failed to get kernel version.` | rc=0/4（能正常检出并修复损坏） |
| 上游 `tests/test_fsck.sh` | `Passed 0 of 23`，rc=1 | **`Passed 23 of 23`，rc=0** |
| 上游 `lib/tests/suite0000-bitmap` | 二进制被编译但从未被执行 | rc=0 |
| 消费者 `test_package`（mkfs→dump→fsck→exfatlabel 断言链） | 不可能执行 | 8/8 断言通过 |

反向验证：去掉补丁首错即复现（`Passed 0 of 23`），证明测试对补丁敏感、非空壳。

## 6. 适用范围 / 反例 / 解除条件 / 风险

- **适用**：任何自带 `MIN_KERNEL_VER` 一类内核版本前置闸、并用 `sscanf`/`atoi`
  从 `uts.release` **头部**取号的 fs/块设备工具（exfatprogs / f2fs-tools /
  btrfs-progs / ntfs 类）；任何在 OHOS 上按位置解析 `os.uname()[2]` 或
  `uts.release` 的 C 代码。
- **反例（不适用）**：只把 release 当不透明字符串透传、不参与任何判定的程序；
  以及真正需要 `/sys/dev/block` 的 `S_ISBLK` 块设备面 —— 那个面在本机对非特权
  用户是 `Permission denied`，属于另一个问题，不能靠本补丁"修好"。
- **解除条件**：若某内核给出"以数字开头但语义非 Linux"的 release（本机不是这种），
  本补丁不会生效，届时需要按具体语义另判 —— 这是本方案的边界，写在这里防止被
  当成万能钥匙。
- **风险**：放行后若目标平台真的缺 sysfs 接口，程序会在后续步骤以更靠后的错误
  退出，而不是在这里给出一句清晰的诊断。本包因 `S_ISREG` 路径不经 `/sys/dev/block`
  而不受影响；对走块设备的工具，放行必须与该面的能力实测一起做。

## 7. 查重与新增价值（四范围同批查重）

| 命中条目 | 关系 | 为什么不是它 |
|---|---|---|
| `knowledge/drafts/DRAFT-ohos-kernel-version-string.{kv,md}`（psutil 7.2.2 / PR #11263） | **同族根因、不同失败机制** | 它覆盖的是"从字符串开头取数字 → 空串 → 解析异常"（Python 侧 `ValueError: can't parse`），推荐方案是"鲁棒解析（正则取第一个数字段）"。**它没有覆盖第二层**：`MIN_KERNEL_VER {2,6,0}` 与 `1.12.0` 的比较；也**没有覆盖 C 侧 `sscanf` 位置解析**。更关键的是**修法不同** —— 本条按"字符串形状"放行（因为只做鲁棒解析会被第二层挡回来），这是既有条目里没有的一条解题路径与适用面。按"组合型知识不判重"，A（解析失败）+ B（闸值比较）组合后新增的解法属新增价值。 |
| `E036`（`uname -r` 含空格把路径拼坏）、`E160`（`config.guess` 认不出 `HongMeng Kernel`）、`E236`/`E237`（ACPI） | 同源不同机制 | 分别是路径拼接、构建期猜测、ACPI 接口缺失；都不涉及运行期内核版本判定。 |
| `E011`/`E052`/`E110`/`E112`/`E114`/`E118`/`E125`/`E126`（`config.status` / `mktemp` `umask 077`） | 无关 | 那是构建期临时目录权限，本条是运行期版本判定；本包同时踩了 E011，但在配方里按既有条目处置，不并入本条。 |
| `DRAFT-E549-ohos-toybox-sed-invalid-utf8-configure`（`could not make ./config.status`） | 无关 | 工具面（toybox sed 正则）而非运行期。 |
| `E468`（`PKG_CONFIG_PATH` 未含 generators 目录） | 无关 | 构建期 pkg-config 元数据路径，本包确实在配方里按它处置，不并入本条。 |

**盲区声明**：以上基于本地已合并知识（本地 main + 本分支）检索，无法保证外部
无人提交过同主题草稿。

## 8. 引擎关键词

`uname` / `uts.release` / `HongMeng Kernel` / `failed to get kernel version` /
`MIN_KERNEL_VER` / `pre-2.6 kernel version not supported` / `sscanf %hu.%hu.%hu` /
`exfat_cmp_kernel_ver` / `exfat_get_blk_dev_info` / `exfatprogs` / 版本闸
