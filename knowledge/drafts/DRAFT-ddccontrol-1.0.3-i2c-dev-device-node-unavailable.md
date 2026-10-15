# DRAFT-ddccontrol-1.0.3-i2c-dev-device-node-unavailable — i2c-dev 设备节点在 OHOS 上不可用 ⇒ 依赖它的用户态工具运行期能力面判据

- **条目主题**：`/dev/i2c-*` 与 `/sys/class/i2c-dev` 在 OHOS 上不存在（ENOENT）、内核无 i2c 模块 ⇒ 依赖 i2c-dev 的用户态工具（DDC/CI 族、i2c-tools 族）**运行期打不开设备**；这是 `open()` 期能力面、**不是编译墙**。
- **状态**：草稿（B=create 成对交付件，待知识库主编审核提升编号 Exxx）
- **Software**：ddccontrol 1.0.3
- **关联 Issue**：#3830（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3830）
- **查重**：四范围 0 真命中（历史归档 / 知识图谱 index+E*.kv / 经验库含 `14-最终防错清单.md` / B草稿库），另 `OHOS行为探针清单.md` 对 `i2c/drm/smbus` 0 命中 ⇒ 真空白区机制。

## 适用场景

任何在运行期依赖 i2c-dev 或 drm 设备节点的用户态工具适配到鸿蒙 PC：

- DDC/CI 显示器控制族：`ddccontrol`、`ddcutil`、`m1ddc` 一类（读写显示器亮度/对比度等 VCP 寄存器）；
- `i2c-tools` 族：`i2cdetect` / `i2cget` / `i2cset`（直接 open `/dev/i2c-N`）；
- 走 `/dev/dri` 或 `/sys/class/drm` 的显示/渲染探测工具。

典型现象（本包实测）：编译全绿（头文件 `linux/types.h`、`linux/i2c-dev.h` 存在且可编译），
但任何真正走到设备访问的子命令在运行期立即失败。

## 判别方法（防假阴性，关键）

⛔ **别信 `os.path.exists` / `os.path.isdir`** —— 在 `EACCES` 场景它们返回 `False`，会把
「**存在但不可访问**」误判成「**不存在**」（假阴性；与 bindfs/cava 的 exists 教训同款）。

✅ **用 `ls -l` 或直接 `open()` 看 errno**：

| errno | 语义 | 归类 |
|---|---|---|
| `ENOENT(2)` | 节点真不存在 | 打不开 ⇒ 运行期核心功能不可用 |
| `EACCES(13)` | 节点存在但本进程不可访问 | **同样算打不开**（不可用结论不变） |

实测命令：

```bash
ls -l /dev/i2c-* /sys/class/i2c-dev /dev/dri /sys/class/drm   # 逐节点取存在性/权限
# 以 open() 实测取 errno（⛔ 不要用 exists() 判）
grep -E 'i2c|drm|smbus' /proc/modules                          # 内核模块面
```

## 证据（ddccontrol 1.0.3 同夜真机实测，errno 方式）

```
/dev/i2c-*  glob        → 无
/dev/i2c-0  open()      → ENOENT（真不存在）
/sys/class/i2c-dev      → ENOENT
/dev/dri    open()      → ENOENT
/sys/class/drm          → EACCES（目录存在但本进程不可访问）
/proc/modules i2c|drm|smbus → 无
编译期对照: <linux/types.h> / <linux/i2c-dev.h> 实测可编译 ⇒ 编译过、运行期全不可用
```

## 交付模式（appres 模式）

1. **编译照常交付**：设备节点是 `open()` 期能力，configure/make 不探测它们 ⇒ 不因打不开设备而砍功能分支；
2. **`test_package` 只断言非设备文本路径**：`-h` / `-V` / `--version` 这类**在任何 `open()` 之前返回**的输出
   （文本比对：版本横幅、usage 文本、上游退出码）；
3. **`notes.md` 如实披露**：逐节点列出 errno 与「运行期核心功能不可用」结论，与 `test_package/MANIFEST.yml`、
   PR 正文**三处同源**；
4. ⛔ **不谎称功能可用、不 mock 设备节点、测试不碰真设备**。

## 推广价值

- 所有 i2c 用户态工具族与 DDC/CI 族在鸿蒙 PC 上的立项预判（选型期即可判「运行期价值几何」）；
- 「编译墙 ≠ 运行期能力面」的通用判别套路（errno 三行 + 无模块佐证），可复制到别的设备节点域
  （`/dev/kvm`、`/dev/fb0` 等未来的空白区）。

## 查重关键词

i2c-dev、/dev/i2c、ENOENT、DDC/CI、ddccontrol、ddcutil、i2c-tools、运行期能力面、设备节点、
errno 判据、/dev/dri、EACCES、内核模块、smbus

---
*配套 `.kv`：`DRAFT-ddccontrol-1.0.3-i2c-dev-device-node-unavailable.kv`（成对同 slug）*
