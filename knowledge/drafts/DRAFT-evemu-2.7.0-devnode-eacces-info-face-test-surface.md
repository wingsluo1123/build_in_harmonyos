# 设备节点 EACCES 时把测试面收窄到「信息面 + 设备无关 API」

> 草稿 `DRAFT-evemu-2.7.0-devnode-eacces-info-face-test-surface`（`.kv` 同 stem 成对）
> 触发实例：`evemu 2.7.0`（输入事件录制/回放工具 + `libevemu`）

## 1. 可复现症状与稳定错误签名

测试进程打开硬件设备节点一律 `errno=13 EACCES`：

```
open("/dev/input/event0")  -> errno=13 (EACCES) Permission denied
open("/dev/input/event1")  -> errno=13 (EACCES) Permission denied
open("/dev/uinput")        -> errno=13 (EACCES) Permission denied
open("/dev/input") 目录    -> errno=13 (EACCES) Permission denied
listdir("/dev/input")      -> errno=13 (EACCES) Permission denied
ls -l /dev/input           -> rc=1, stderr "Permission denied"
```

稳定签名 = `EACCES(13)` **且节点本身存在**（`ls /dev` 能列出 `input`、`uinput`）。
进程态读数（两台构建机一致）：

```
CapPrm/CapEff: 000000000000002a      # 只有 CAP_CHOWN(0) + CAP_DAC_OVERRIDE(1) + CAP_KILL(5)
Seccomp: 2   Seccomp_filters: 1
NoNewPrivs: 0
uid/gid: 20020084(B 机) / 20020105(A 机)
```

⇒ **无 `CAP_SYS_ADMIN(21)`、无 `CAP_SYS_RAWIO(17)`**。

## 2. 根因与最小复现

根因是**运行期权限面**：测试进程是非特权进程，被 DAC/LSM 拒绝访问硬件设备节点。
它与另外两种「能力墙」**性质不同**，必须先分辨，否则会误判成放弃：

| 档 | 判据 | 处置 |
|---|---|---|
| ① 直接墙 | 编译/归档期过不去、交不出二进制 | 停下上报（放弃是用户终局裁定，执行者不自行裁定） |
| ② 本条 | **编译过、二进制交得出**，只是运行期设备节点被限 | **继续**：收窄测试面 + 如实披露 |
| 乙 | 唯一功能面被拦且上游无替代，又不满足 ② | 停下上报，不得自行定性「等价交付」 |

最小复现（30 行级、不含三方库代码，正反对照必须同时给）：

```python
import os, errno
for p in ["/dev/null", "/proc/self/status"]:      # 正对照：证明基础 open 可用
    try:
        fd = os.open(p, os.O_RDONLY); os.read(fd, 20); os.close(fd)
        print("POS", p, "OK")
    except OSError as e:
        print("POS", p, "errno", e.errno)
for p in ["/dev/input/event0", "/dev/uinput"]:    # 反对照
    try:
        fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK); os.close(fd); print("NEG", p, "OK")
    except OSError as e:
        print("NEG", p, "errno", e.errno, errno.errorcode.get(e.errno))
print(open("/proc/self/status").read().split("CapEff:")[1].splitlines()[0].strip())
print(os.getuid())
```

**没有正对照就无法区分**「节点不存在」与「有节点但无权限」——本例中 `os.path.exists` /
`listdir` 在 `EACCES` 下都会给出与事实相反的结论（工作区已有两次同类教训）。

## 3. 已尝试（与不采用的）方案

- **❌ 直接跑录制/回放做集成测试**：运行期必然 `EACCES`，测试必红，且红的原因是权限不是代码。
- **❌ `|| true` 吞掉失败**：把「权限受限」伪装成「通过」，属 P0 欺骗性行为。
- **❌ 断言「可录制事件」**：没有任何读数支持，与 `notes.md` 自相矛盾。
- **❌ 要求 root / 改设备权限 / 装内核模块**：超出配方边界，且测试进程能力由平台决定。
- **❌ 据此判放弃**：① 档判错了 —— 编译期全过、二进制交得出，不构成直接墙。

## 4. 最终方案与真实验证

**把测试面收窄到两块，两块都是真实输出断言：**

1. **信息面**：非法选项在 `getopt_long` 的 `default` 分支就走到 `usage()`，
   **发生在任何 `open()` 之前** ⇒ 输出上游用法横幅、退出码恒为非 0。
   `test_package` 显式断言 `returncode == 1`（不是放行），再 `grep` 输出里的真实串。
2. **设备无关 API**：只分配结构体、不 `open` 任何节点的入口
   （`evemu_new()` → `libevdev_new()`，上游自己的 `test/test-c-compile.c` 用的就是它），
   做名称设置/读取回环断言。

真实验证读数（`archives/e/evemu/2.7.0/reports/`）：

- `conan-verify-report.md`：`Verdict: PASS`，`G0–G4` 全 PASS；
- `conan-create.log`：`make check` `TOTAL 3 / PASS 3 / FAIL 0`
  （三条上游用例全部设备无关：`test-c-compile`、`test-cxx-compile`、`test-evemu-create`，
  后者只用 `mkstemp()` + `evemu_new()/evemu_read()` 回环，不 open 设备节点）；
- `test_package` 消费者测试 `1/1 Passed`；
- `.ci-result.json`：`exit_code=0`、`step=W3_local_ci`、`integrity_hash=874a2b11072b4f58`。

## 5. 适用范围 / 反例 / 解除条件 / 风险

- **适用**：核心功能面绑定 `/dev/*` 硬件节点、但**编译与安装完全正常**的工具与库
  （`evdev` 族、`i2c` 族、`fuse`、`uinput` 等）；任何「运行期 I/O 无法在 CI 测试进程验证」的 Conan 包。
- **反例（不适用本条，应走别的处置）**：
  - 内核特性本身缺失（如 `AF_CAN` 协议族不存在、`fuse` 模块未加载）—— 那是 ① 档/乙档，
    症状是 `socket()`/`mount()` 返回 `EAFNOSUPPORT`/`ENOSYS` 而非设备节点 `EACCES`；
  - 编译期就打不开（交叉编译器、头文件、链接器不可用）—— ① 档，停下上报。
- **解除条件**：拿到具备相应能力的测试进程（root 或 `CAP_SYS_ADMIN`/`CAP_SYS_RAWIO`
  且节点属主可读写）后，本条的「未能实测」即可转为真实运行期验证。
- **风险**：收窄测试面 = 放弃了运行期功能面的回归证据。缓解是
  ① 尽量用上游自带的设备无关用例补位；② 正文/`notes` 明确披露未执行项与原因，
  绝不把「未实测」写成「已通过」。

## 6. 查重与新增价值

四范围查重（`evemu|evdev|uinput|/dev/input` 四个关键词，2026-10-09 实测计数）：

| 范围 | 位置 | 命中 |
|---|---|---|
| 1 | `经验文档/适配经验汇总.md`（索引，只 grep 不通读） | 0 |
| 2 | 平台知识图谱 `knowledge/graph/*.kv`（含 `prescan` 动态派生规则） | 0（`prescan` 只命中 `E007/E072` config.guess、`E465` dlopen/ctypes，与本条无关） |
| 3 | `经验库/14-最终防错清单.md`、`适配检查清单.md`、`手册/07-技术速查.md` | 0 |
| 4 | `经验文档/OHOS行为探针清单.md` | 0（最接近的 #19/#20/#21 是 `/dev/shm` 数据面/元数据面分野，症状与解法都不同） |

- **不判 `hit` 的理由**：四条件之一「症状一致 + 解法也被该条目覆盖」不成立 ——
  最接近的 `适配检查清单 #13`（AF_UNIX bind 全平台拒绝）症状是 `bind()` 返回 `EPERM/EACCES`
  于可写路径，解法是「路径补丁让它执行到 bind + 逐条申报能力缺失」，
  与本条「设备节点 `EACCES` ⇒ 收窄到信息面」既不同签名也不同解法。
- **新增价值**：给出**三档判档**这一可执行决策树（区分「权限墙」与「特性缺失墙」），
  加上**正反对照必须成对**的探针规范，以及**「信息面 + 设备无关 API」**这两类可复用测试面，
  并钉死 `⛔ || true` / `⛔ 未实测≠已通过` 的红线。
- **组分不重复**：`经验库` 里既有的权限类条目（`E011` umask/HMDFS 权限、`/dev/shm` 分野）
  与本条是不同对象、不同触发、不同解法；组合后新增的正是「如何在权限受限时仍能交出可验证交付」
  这条解题路径。
