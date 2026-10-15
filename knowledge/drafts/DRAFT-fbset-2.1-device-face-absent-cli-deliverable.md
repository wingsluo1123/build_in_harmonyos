# 设备面缺失型 CLI 工具的可交付判定与四段配方口径（fbset 2.1 实证）

> **草稿 DRAFT-fbset-2.1-device-face-absent-cli-deliverable**
> 实证：`fbset 2.1`（framebuffer 显示模式查询与调整，FB ioctl 族）· OHOS PC aarch64 · clang 15.0.4 · 2026-10-15
> 面向：编译期可得、运行期依赖设备节点/内核接口的命令行工具与外设库族
> （framebuffer、i2c/spi/gpio、netlink、perf、drm …）

## 1. 一句话机制

**设备缺失（运行期墙）不是停手理由，停手判据只有"编译墙"**；判定为运行期墙后，按
**① 编译墙/运行期墙分界 → ② 构建面 make 变量覆盖 + 手工安装 → ③ L2 smoke 信息型退出码
→ ④ 消费者测试双态断言 + 运行期墙如实披露** 四段交付，即可同时过 W3（本地 CI 模拟）、
L2（smoke）与 rule4/R51（上游测试如实申报）三道门。

## 2. 可复现症状与稳定错误签名

```text
# 第一段（真正的阻塞，编译期）
$ make CC="clang -Wall -O2 -I."
./fbset.h:41:5: error: unknown type name '__u32'      # 共 14 处
make: *** [<builtin>: lex.yy.o] Error 1

# 第二段（构建面，改完第一段才会暴露）
$ make                 # 上游 Makefile 写死 CC = gcc -Wall -O2 -I.
make: gcc: No such file or directory                  # 本平台无 gcc/cc

# 第三段（门禁面）
$ ./fbset --help ; echo $?
1                                                     # Usage() 经 Die() → exit(1)，L2 smoke 判失败

# 第四段（运行期能力，交付后的真实行为）
$ ./fbset -s
open /dev/fb0: No such file or directory              # 退出码 1
$ ./fbset -s -fb /dev/null
ioctl FBIOGET_VSCREENINFO: Not a tty                  # 任务点名的 ioctl 已被真实走到，ENOTTY 说明设备面缺失
```

错误签名（`error_signature`）：
`open /dev/fb0: No such file or directory` · `ioctl FBIOGET_VSCREENINFO: ` ·
`unknown type name '__u32'` · `make: gcc: No such file or directory`

## 3. 根因与最小复现

1. **`fbset.h` 第 18 行把 `#include <asm/types.h>` 放在 `#ifdef __GLIBC__` 内** —— musl/OHOS
   不定义 `__GLIBC__`，类型声明整段被跳过 ⇒ `__u32` 未定义。`fbset.c` 因先包含**源码内置**的
   `fb.h`（其第 4 行无条件包含 `<asm/types.h>`）而未暴露，只有由 `modes.l` 包含 `fbset.h` 的
   `lex.yy.o` 会炸 —— 所以"第一处真实错误"出现在词法目标而非主文件。
   - 最小复现：`printf '#include <asm/types.h>\n__u32 x;' | clang -c -x c -` → **OK**
     （证明头文件可得、只是被条件跳过 ⇒ **不是编译墙**）。
2. **裸 Makefile 烧死工具链与安装语义**：`CC = gcc -Wall -O2 -I.`、`INSTALL = install`，
   且 `install` 目标写 `/sbin`、`/usr/man` 并 `mknod /dev/fb0..fb7` —— 既没有 `gcc`/`install`
   命令，安装动作本身在包内也不可执行。
3. **信息型请求与错误路径共用退出码**：`Usage()` → `Die()` → `exit(1)`，
   `--version` 则打印横幅后继续打开设备、失败同样 `exit(1)`。
4. **设备面缺失**：本平台无可访问帧缓冲节点（`ls /dev/fb*` → `Permission denied`）。

## 4. 已尝试方案（含不采用的）

| 方案 | 结论 |
|---|---|
| 直接按"编译墙"停手上报 | ❌ 不成立 —— 第 3 节复现证明头文件可得，一行级修复即可过 |
| 定义 `__GLIBC__` 让原条件成立 | ❌ 会连带开启其它 glibc 专属分支，语义造假（同族反例见 E503 的 forbid） |
| 只改 PATH 指向 gcc | ❌ 平台无 gcc；且 `INSTALL=install`、绝对路径安装同样不可用 |
| 改用 Debian/Ubuntu 池源规避原站不稳 | ❌ PF7 黑名单与 R39（`conandata` 只写上游官方源） |
| 让查询失败也返回 0 来"过 L2/测试" | ❌ 欺骗类（R34/R40），审查按 P0/P1 打回 |
| **最终采用**：四段口径（见下） | ✅ W3 本地 CI 模拟 RC=0、消费者 6 断言 6 过、PF 口径无隐瞒项 |

## 5. 最终方案（四段）与真实验证

### ① 分界：先证不是编译墙
`patches/0002-fbset.h.patch`（+0/-2）去掉 `#ifdef __GLIBC__` 条件，`<asm/types.h>` 无条件包含
—— 与 Yocto meta-oe 同名补丁 `0001-fbset-including-asm-types.h-is-needed-on-all-linux-s.patch`
同一结论，属可移植性修复，**无平台宏**（R8/PF5）。

### ② 构建面：make 变量覆盖 + 手工安装（零源码改动）
```python
# conanfile.py build()（R33：编译器取自 tools.build:compiler_executables，不读 shell 环境）
self.run(f'make CC="{cc}" CFLAGS="-O2 -Wall -fPIE -I." LDFLAGS="-pie -Wl,-z,relro,-z,now" LDLIBS="" -j1',
         cwd=self.source_folder, env="conanbuild")
```
- `flex`/`bison` 未预生成 `lex.yy.c`/`modes.tab.c` ⇒ `tool_requires("flex/2.6.4")` +
  `tool_requires("bison/3.8.2")`（制品仓实测 `conan download … --only-recipe -r=ohpcd` rc=0）；
- 不用上游 `install` 目标，`package()` 手工 `copy()` → `bin/fbset` + `share/fbset/fb.modes.*`，
  OHOS 下 `binary-sign-tool -selfSign 1`（`add codesign section success`）。

### ③ L2 smoke：信息型请求退出 0
`patches/0001-fbset.c.patch`（+12/-2）引入文件级 `static int Die_status = 1;`，`Die()` 改用该状态，
仅在 `-h/--help` 分支置 0：
```c
if (!strcmp(argv[0], "-h") || !strcmp(argv[0], "--help")) {
    /* asking for help is not an error: exit with status 0 */
    Die_status = 0;
    Usage();
}
```
验证：`./fbset --help` → **rc=0**；`./fbset -g`（缺参错误路径）→ **rc=1**（语义未被削弱）；
`-V` 保持上游行为（打印横幅后继续查询）。本机 `conan-verify` L2 因 cache 路径探测跳过，
手工复核打包产物 `fbset --help` rc=0；CI 侧 L2 为非阻断、`--help` 回退判过。

### ④ 消费者测试双态断言 + 运行期墙披露
`test_package/test_fbset.c`（1 程序 / 6 断言）真实 `fork/exec` 被测二进制：
- 有设备 ⇒ 断言真实输出（模式/版本横幅）；
- 无设备 ⇒ 断言**诊断信息指名设备或裁决点**（`/dev/fb*` 或 `ioctl`），两态都判真、
  崩溃/无输出判假；删除包产物 ⇒ `execve` 失败 ⇒ 测试必红（L1e 反向验证）。

真实汇总行（`conan create` 日志原文）：
```text
6 assertion(s), 0 failure(s)
```
W3 本地 CI 模拟：`build_and_test.sh` **RC=0**；`.ci-result.json` `exit_code=0`。
披露面：`notes.md`「运行期能力（可披露的运行期墙）」+ `README.md` 同节 + `reports/test-report.md`
「已知限制」+ PR 正文补充说明（R51：`N_static=0` 的上游清点证据与设备能力缺失一并如实申报）。

## 6. 适用范围 / 反例 / 解除条件 / 风险

- **适用**：编译期头文件可得、运行期依赖 `/dev/*`、netlink、sysfs 或内核接口的 CLI 工具与外设库；
  裸 Makefile 且 install 目标不可用的三方包；上游无测试套件（`N_static=0`）需要靠消费者测试
  撑起 rule4 的工具类包。
- **反例（不适用本口径）**：**编译墙** —— 头文件不可得且无法补、x86/私有汇编、私有工具链、
  语言不匹配（R47 `env_unsupported`）⇒ 按 fallback 停手上报，⛔ 不得走本口径硬交付。
- **解除条件**：平台将来提供可访问的帧缓冲设备节点后，双态断言的"有设备"分支自然接管，
  无需改配方。
- **风险**：① `--version` 保持上游语义（打印后继续查询），在无设备环境仍返回 1 —— 依赖 L2 的
  `--help` 回退；若将来 L2 取消回退，需按 E503 再收敛 `-V` 分支。② 源站仅明文 http 且对 IPv6
  路径偶发 RST，CI/本地下载需 sha256 校验 + 单栈重试兜底。

## 7. 查重与新增价值（组合型知识申报）

| 组分 | 既有条目/池件 | 与本草稿的关系 |
|---|---|---|
| A：L2 信息型退出码 | **E503**（`--version/--help` 不存在时补长选项并返回 0） | **沿用其解法**；但本包**有**长选项、签名是 `open /dev/fb0 …`、根因是 `Die()` 恒 1 ⇒ 单独看 hit，作为组分纳入 |
| B：make 变量覆盖 / install 缺失 | 池件 **M18**、**M13**；本仓 `DRAFT-lisgd-0.3.7-suckless-baked-paths-makevar-override`、`DRAFT-lzip-1.24.1-makefile-install-cmd-absent-makevar-override` | 沿用其解法（本例对象是 `CC=gcc`+`INSTALL=install`+`mknod /dev/fb*` 三合一） |
| C：无硬件外设测试设计 | `DRAFT-ohos-peripheral-lib-failed-open-footgun`（**库**的 failed-open footgun，结论"只测 open/close 错误路径"） | 同族不同解：本草稿对象是 **CLI 工具**，结论是**双态断言**（有设备时必须断言真实输出，不能只测错误路径） |
| D：glibc 条件包含隐藏系统头 | **E580**（`defined(linux)` + `-std=c++17` 严格 ISO 方言） | **未覆盖**：触发条件（musl 无 `__GLIBC__` vs 严格 ISO 方言）与解法（去条件化 vs 换宏）均不同 |

**组合后新增的解题路径**：把 A/B/C/D 串成「**先判编译墙/运行期墙 → 再走四段交付面**」的端到端
口径 —— 它回答的是链主的**继续 vs 停手**判据与**三道门（W3/L2/rule4）如何同时过**，
任一单条都不含这两件事。本工作区 `constype`/`ddccontrol`/`appres` 等同族任务此前均未沉淀该口径
（`grep -ril "ddccontrol|appres|constype" knowledge/` = 0 命中）。

**触发实例**：fbset 2.1，四段全部真实撞上并逐段验证（见第 5 节读数）。
