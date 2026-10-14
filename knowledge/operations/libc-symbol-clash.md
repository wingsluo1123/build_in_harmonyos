# libc × 内核 UAPI 同名符号重定义（musl 派生 sysroot）

> 关联工具：`knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py`
> 关联模板：`knowledge/tools/libc-symbol-clash/libc-detection-guard.md`
> 关键词：`sockaddr_storage`、`redefinition of struct`、UAPI、`linux/rtnetlink.h`、
> `__GLIBC__`、bionic、musl、libc 鉴别探针

## 1. 一类什么问题

同一份 C/C++ 源码在 glibc 发行版上编译正常，交叉编译到 OpenHarmony（musl 派生 sysroot）
时报：

```
error: redefinition of 'struct sockaddr_storage'
```

触发条件（三者同时满足即复现）：

1. 同一编译单元**既**包含 libc 头（`<sys/socket.h>`、`<net/if.h>`、`<netinet/in.h>` …），
2. **又**包含内核 UAPI 头（`<linux/rtnetlink.h>`、`<linux/socket.h>`、`<linux/if.h>` …），
3. sysroot 的 UAPI 头是 **bionic 派生**版本（缺少 glibc 生态那层 `#ifndef __GLIBC__` 互斥）。

这不是某个库的特例：凡是"网络/守护进程 + 需要 netlink/ioctl 细节"的移植都会撞上，
`struct sockaddr(_storage)`、`msghdr`、`iovec`、`ifreq`、`termios`、`in_addr` 等成对出现。

## 2. 机理

| | glibc 生态 | OpenHarmony（musl 派生） |
| --- | --- | --- |
| libc 头定义 `struct sockaddr_storage` | ✅ | ✅ |
| UAPI 头（bionic 派生）同结构 | `#ifndef __GLIBC__` 守卫 → 不定义 | 守卫缺失 → 也定义 |
| 同时包含两者 | 无冲突 | **重定义** |

正确修法 = **libc 鉴别探针 + 引入 UAPI 头期间重命名内核侧定义**，见模板文件。
不要用 `__OHOS__` 平台宏（不可移植；preflight PF5 在建 PR 前拦截）。

## 3. 工具与检测原理

`knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py` 四个模式：

| 模式 | 输入 | 判定 | 典型用途 |
| --- | --- | --- | --- |
| `includes` | `--src`（+ 可选 `--sysroot`） | 逐 TU 解析 include 链（含项目内头递归），同一 TU 内出现冲突头文件对 → 命中 | 适配前体检、kea 类冲突复查 |
| `sysroot` | `--sysroot` | 实测两侧（libc 侧 × UAPI 侧）同名声明 → 命中（权威） | 新 sysroot/SDK 升级后重建冲突清单 |
| `source` | `--src`（+ 可选 `--sysroot`） | 项目自身声明与 libc/UAPI 符号同名 → 命中 | 排查项目自定义类型撞名 |
| `lint` | `--patches` | 补丁新增行含 `__OHOS__` → `GUARD-001`（HIGH） | 提交前合规自检（与 PF5 同向） |

判定口径与误报控制：

* 冲突头文件以**触发集**表达（`libc_triggers` / `uapi_triggers`）：musl 的 `<net/if.h>`、
  `<netinet/in.h>` 都会拉入 `<sys/socket.h>` 定义，故"包含 `<net/if.h>`"即视为 libc 侧可见。
* 内置基线 8 条，每条带 `confidence`：`verified`（有归档实证，如 `sockaddr_storage`）与
  `candidate`（同族已知重叠、需 `--sysroot` 复核）在报告里显式区分，不把未实证结论说成定论。
* **sysroot 收敛**：给 `--sysroot` 时只保留"两侧都声明"的标识符（实测未复现的候选直接剔除，
  命中标 `confidence=verified`）—— 这是权威口径，也是可当门禁的形态。
* **已 guard 降级**：TU 内已存在针对该符号的强见证（`#define <ident> <新名>` / `#undef <ident>`，
  即本模板形态 A）时，命中降为 `LOW` + `confidence=guarded`（默认阈值不报红，`--min-severity LOW`
  仍可见，保留审计留痕）。因此**修复后可判绿**，同一命令能同时用于"体检"与"回归门禁"。
* `--min-severity` / `--ignore <ID列表>` 收敛噪声；`--no-baseline` 只用 sysroot 实测结果。
* 退出码：`0` 无 HIGH/MEDIUM 命中、`1` 有命中、`2` 用法错误 —— 可直接串进脚本。

设计约束（对齐知识库拓展要求）：仅标准库、无网络、不读本地缓存、不写死绝对路径
（sysroot 来自 `--sysroot` 或环境推断）、OHOS aarch64 的 python3 可直接运行、输出确定性。

## 4. 用法

```bash
# 适配前体检（无需 sysroot；本仓库/目标源码目录即可）
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py includes --src <src>

# 拿到 SDK/sysroot 后做权威实测，并把结果落盘
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py sysroot --sysroot "$OHOS_SYSROOT" --json --out /tmp/clash.json

# 提交前检查补丁是否用了平台宏
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py lint --patches <patches/>

# 打印 guard 模板
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py --print-template
```

## 5. 修复

见 `knowledge/tools/libc-symbol-clash/libc-detection-guard.md`（形态 A/B/C + 反例 + 验证清单）。
提交前务必过一遍该文件的验证清单，其中第 4 项（干净环境 `conan create`）是 W3 硬要求。

## 6. 局限（如实声明）

* `includes` 模式的项目内 include 解析是**启发式**：按"相对当前文件 → 项目内相对路径 →
  同 basename 唯一命中"三级解析，不做真实的 `-I` 目录与条件编译求值；宏包裹的 include
  （`#if defined(X)` 里的 include）不做可达性分析，可能多报。
* 只覆盖 **libc × 内核 UAPI** 同名这一类；`-D_GNU_SOURCE` 缺失、glibc-only 函数
  （`secure_getenv` 等）、不透明结构（`_IO_FILE`）属其它条目（E032/E033/E081/E020）。
* 内置基线中 `candidate` 条目未经真实 OHOS sysroot 逐条复核，须用 `sysroot` 模式确认后再
  作为结论使用（给 `--sysroot` 跑 `includes` 会按实测自动剔除未复现的候选）。
* "已 guard"判定是**文本级**的：同一 TU 内出现对该标识符的 `#define`/`#undef` 即视为已处理，
  不保证 guard 覆盖了该 TU 中所有使用点（跨文件、宏展开等仍以 `conan create` 结果为准）。
* 不做"同一标识符是否真被同一 TU 的预处理结果同时展开"的精确模拟 —— 结论定位在"需要
  guard"的层面，最终以 `conan create` 结果为准。

## 7. 证据

| 项 | 内容 |
| --- | --- |
| 实证样例 | Kea 3.0.3 `src/lib/dhcp/iface_mgr_linux.cc`：`<net/if.h>`（经 `<sys/socket.h>` 取 libc 定义）× `<linux/rtnetlink.h>` → musl 派生 sysroot 重定义；归档补丁 `archives/k/kea-hook-host-cmds/3.0.3/patches/0002-src-lib-dhcp-iface_mgr_linux.cc.patch` 以形态 A 修复，全族（lease-cmds/host-cmds/perfmon/…）逐字节一致复用 |
| 实机验证 | 对 Kea 3.0.3 上游源码树（1436 个 TU）跑 `includes`：唯一 HIGH 命中 `CLASH-001`(verified) 落在 `src/lib/dhcp/iface_mgr_linux.cc`，与归档补丁实际修的文件一致；把归档补丁真机应用（`patch -p1 --dry-run` rc=0、应用 rc=0）后复测：**HIGH 清零**，`--min-severity HIGH` 退出码 0（该符号降级为 `guarded`/LOW 留痕） |
| 语料统计 | 本仓库 `archives/**/*.patch` 中 430 个包使用 libc 鉴别探针（`!defined(__GLIBC__)` 等）表达 musl/glibc 差异；680 个补丁仍含 `__OHOS__` 平台宏（PF5 拦截对象，存量） |
| 自测 | `knowledge/tools/libc-symbol-clash/test_libc_symbol_clash.py`（27 断言，纯合成 fixture：合成 sysroot、对照组 TU、自身重定义、已 guard 形态、补丁样例），`python3 knowledge/tools/libc-symbol-clash/test_libc_symbol_clash.py` 一次跑全（不注册进 `tests/run_all.py`——框架目录不在知识库扩展的改动范围） |
| 复现 | 无网络、无 conan 缓存、无真实 sysroot 亦可运行（fixture 自带合成 sysroot），确定性输出；纯标准库（argparse/json/os/re/sys/pathlib），无绝对路径硬编码 |
