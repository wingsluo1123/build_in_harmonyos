# fbset 2.1 适配笔记（HarmonyOS PC · 裸 Makefile）

## 定位
- 产出命令行工具 `bin/fbset`（无库、无头文件；另有模式数据库 `share/fbset/fb.modes.*`）。
- 上游：Geert Uytterhoeven（linux-fbdev），最新版 `fbset-2.1.tar.gz`（1999/06/23），GPL-2.0-only。

## 源（W0 头号风险：官方原址已死，新址已核验）
- 官方原址 `http://www.tenftjo.be/~geert/utils/fbset/` → curl rc=6 / http=000（DNS 不可解析）。
- **作者迁移现站** `http://g33rt.be/migrated/Linux/fbdev/` → http=200，页面自述
  “The latest version of fbset is fbset-2.1.tar.gz (dated 1999/06/23)”。
  依据：Debian 2.1-35 `.dsc` 的 `Homepage:` 与 `debian/watch` 均指向该址；`g33rt.be` 与作者 GitHub
  主页 blog `glider.be` 解析到同一 IPv6（`2001:4b98:dc2:950::115`），与作者长年站点 `linux-m68k.org`
  同网段。
- 源 URL：`http://g33rt.be/migrated/Linux/fbdev/fbset-2.1.tar.gz`
- sha256（自算）：`40ff4ab0247b75138a0887ed40f81c1a6184f340b77126c16d074b1075b41c20`（27721 B）
  - 交叉校验 1：Fedora lookaside 同名件 sha1/sha256 逐字节相同。
  - 交叉校验 2：与 Debian `fbset_2.1.orig.tar.gz`（sha256 `517fa062…`，27736 B）**解包树 `diff -r` 完全一致**
    （仅 gzip 封帧差 15 B），即同一上游源码树的另一次打包。
- **PF7/R39 风险（必须披露）**：作者站点只提供明文传输 —— `https://g33rt.be:443` 握手失败、
  `https://www.g33rt.be:443` 连接拒绝（实测）；PF7 会把 `http://` 判为「明文 http 源」。
  逃生口按 PF7 自带文案「确属官方托管例外须 PR 说明并 `--no-preflight` 跳过」+ AGENTS §8「先留正确基线 PASS 证据」。
- **下载稳定性实测**：该站对 IPv6 路径频繁 RST（Python urllib 默认双栈 6 次仅 2 次成功；
  **强制 IPv4 后 5/5 成功**，curl `-4` 同样 5/5）。本地以 `curl -4` 预置 tarball 后 `init-build` 走缓存；
  CI 侧 `build_and_test.sh` 的预下载使用 `curl --retry 3 --retry-delay 10`。
- ⛔ `www.g33rt.be/.../fbset-2.1.tar.gz` 返回 200 但只有 2308 B 且两次 sha256 不同（HTML 报错页）——不可用。

## W0 / W0b / R47
- `preflight_check.sh fbset/2.1`：无依赖声明（首次适配），rc=0 通过。
- 依赖面：`tool_requires` `flex/2.6.4`、`bison/3.8.2` 已用 `conan download … --only-recipe -r=ohpcd` 实测
  rc=0（R35：未用 conan list 判定）。
- `lang-preflight`：task=cpp、detected=c（c↔cpp 兼容族），证据 build_system=make / manifest=顶层 Makefile /
  source_stats=源文件 2 个（c:2，100%），rc=0 通过。
- `recipe-search fbset`：语料 9011 条无相似配方（首稿走 conan-init 模板），rc=0。

## 探索构建（真机 `builds/fbset-2.1.work`）
1. 源码树清点：`fbset.c` `GetVideoMode.c` `modes.l` `modes.y` `fb.h` `fbset.h` `Makefile`
   `fbset.8` `fb.modes.5` `modeline2fb` `etc/fb.modes.*` —— **无 tests/、Makefile 无 check/test 目标**。
2. 首轮 `make CC="clang -Wall -O2 -I."` → 失败：
   `./fbset.h:41:5: error: unknown type name '__u32'`（14 处，仅 lex.yy.o 一处触发面，因为 fbset.c 先包含 fb.h）。
   根因：`fbset.h:18` 的 `#ifdef __GLIBC__` 包裹 `#include <asm/types.h>`；本机 probe 实测
   `<asm/types.h>` 单独包含即可定义 `__u32`（OHOS SDK sysroot）⇒ 只需去掉条件。
3. 打入 0001 后 `make CC="clang -Wall -O2 -I."` rc=0，产物 `fbset` 55744 B（仅 flex 生成代码 2 条 warning）。
4. 运行实测：
   - `./fbset --help`（补丁 0002 后）rc=0，stdout 横幅 112 B、stderr Usage 2692 B；
   - `./fbset -V` → stdout `Version 2.1 (23/06/1999)`，随后 `open /dev/fb0: No such file or directory` rc=1；
   - `./fbset -s -fb /dev/null` → **`ioctl FBIOGET_VSCREENINFO: Not a tty`**（任务点名的 ioctl 在运行期被真实走到，ENOTTY 说明设备面缺失而非代码问题）；
   - `./fbset -g`（缺参）rc=1 —— 错误路径退出码未被补丁改变。
5. 上游 Makefile 还写死 `CC = gcc`（本平台无 gcc/cc）、`INSTALL = install`（本平台无 `install`），
   故一律按 R33 在 make 命令行覆盖变量，且不使用上游 `install` 目标（其内容为写 `/sbin`、`/usr/man`
   与 `mknod /dev/fb0..fb7`，在包内不可执行）。

## 源码修改（patches/，由 refresh-patch --auto 生成）
| # | 文件 | 内容 | 分类 |
|---|------|------|------|
| 0001 | fbset.c | `--help` 属信息型请求：新增文件级 `Die_status`，`Die()` 改用该状态并在 `-h/--help` 分支置 0；其余诊断路径（缺参、设备打开失败）仍为 1（+12/-2） | portability，`platform_only=False`、`guard=none`（无平台宏，R8/PF5） |
| 0002 | fbset.h | `#include <asm/types.h>` 由 `#ifdef __GLIBC__` 改为无条件包含（musl/OHOS 需要 `__u32`；与 Yocto meta-oe `0001-fbset-including-asm-types.h-is-needed-on-all-linux-s.patch` 同一结论）（+0/-2） | portability，`platform_only=False`、`guard=none` |

两个补丁均已对 pristine 源（`fbset-2.1.orig`）`patch -p1 --dry-run` 干净通过；`conandata.yml` 的
`patches:` 两条 `patch_file` 与磁盘文件名一一对应。

## 上游测试账本（R51 三步法）
- 清点：Makefile 仅 `All` / `fbset` / `install` / `clean` 四个目标，**无 `check`/`test`**；源码树无
  tests/ 目录、无任何测试源文件 ⇒ **N_static = 0，N_registered = 0，N_executed = 0**（如实申报，
  不虚构上游测试）。
- 消费者测试（`test_package/test_fbset.c`）：**1 个程序 / 6 条断言**，真实执行被测二进制
  ① `--help` rc=0 + 横幅 + Usage；② `-V` 版本横幅 + 结果成形；③ `-s` 真实帧缓冲查询
  （有设备→输出模式；无设备→须指名设备/裁决失败原因）。删除包产物时 execve 失败 ⇒ 测试必红（L1e 反向验证）。

## 运行期能力（可披露的运行期墙）
- OHOS PC 无可访问的帧缓冲设备：`ls /dev/fb*` → `Permission denied`；`./fbset -s` →
  `open /dev/fb0: No such file or directory`（rc=1）。属**运行期墙**，非编译墙 ——
  工具编译、安装、消费者验证均通过，设备查询能力在本平台不可用，已写入 README/manifest/PR 披露。

## 状态
built —— conan create 真机验证通过后回填（见 `.ci-result.json` / `reports/`）。

---

## 本地验证读数（W3 / 消费者测试 / 安全属性）

- `conan-verify`（G0-G4）rc=0：G1 配方完整性、G2 `conan create` 干净构建、G3 无系统同名库冲突、G4 产物完整性均 PASS；
  本机 L2/L4/L5 因 cache 路径探测跳过（报告原文「跳过（无 cache 路径）」），已用手工复核替代：打包产物 `fbset --help` rc=0；
  `readelf -l -d` → DYN(PIE) / GNU_STACK RW(NX) / GNU_RELRO+FLAGS BIND_NOW(full RELRO)。
- `finish` W3 本地 CI 模拟：`build_and_test.sh` RC=0（`JUNK_PR_DIFF` 对齐 PR 口径后 JC/L0/L1/L2/L4/L5 全过）；
  `.ci-result.json` `exit_code=0`、`integrity_hash=f51dddabca263633`。
- 消费者测试：1 程序 / 6 断言，**6 passed, 0 failed**（真实汇总行见 `reports/test-report.md`）。
- 签名：`binary-sign-tool ... -selfSign 1` → `add codesign section success` / `write code sign data success`。
- 环境：conan 2.29.1 · clang 15.0.4 · profile `ci/conan/profiles/ohos-aarch64` · `CONAN_HOME=~/tmp/ch/home-主理-4-fbset`（ohpcd remote 自检通过）。

---

**编译结束**: 2026-10-15 01:33
**最终状态**: built
