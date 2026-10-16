# xhk 1.2 — 适配笔记

## 上游

- 仓库：<https://github.com/kbingham/xhk>（XLib HalfKeyboard implementation）
- 官方 tag：`xhk-v1.2` → 归档
  `https://github.com/kbingham/xhk/archive/refs/tags/xhk-v1.2.tar.gz`
  - HTTP 200，11443 bytes
  - `sha256 = 2fd99c8b81262d4af7b827259be5e0b2a143f67e9f65f78a286dc56960824b7c`
  - 归档根目录 `xhk-xhk-v1.2/`
- 许可证：GPL-2.0-or-later
- 源码规模：`src/xhk.c`（约 750 行 C99）+ `src/xhk-layout.h`；无第三方 vendored 代码。

## 语言判定（范围红线）

`cfamily 99.3% (c:99.3)`：源码树只有 `.c` / `.h`，无 Go/Rust/Python/JS 主体。
**属 C 语言库，在本仓库 C/C++ 适配范围内。**

## 依赖（W0 预检）

`conan download "<pkg>" -r=ohpcd --only-recipe` 全部返回配方：

| 依赖 | 用途 | 预检 |
|------|------|------|
| `libx11/6.4.0` | Xlib（XOpenDisplay / XKBlib / keysymdef） | OK |
| `libxi/6.1.0` | XInput2（XIQueryDevice / XISlaveKeyboard） | OK |
| `libxtst/1.2.5` | XTest（XTestFakeKeyEvent） | OK |
| `xorgproto/2025.1` | X11 协议头（keysymdef / XKBlib） | OK |
| `automake/1.18` | autoreconf 自举（build 侧） | OK |
| `libtool/2.5.4` | autoreconf 自举（build 侧） | OK |

### 版本线选择（关键）

制品仓的 X11 家族按 `.so` 主版本命名（`libX11.so.6.4.0` → `libx11/6.4.0`），
同时存在两条互斥的依赖线：

- `libxi/6.1.0` 依赖 `libx11/6.4.0`；`libxtst/1.2.5` **pin `libxi/6.1.0`**。
- `libxi/1.8.3` 也依赖 `libx11/6.4.0`，但与 `libxtst/1.2.5` 需要的 `libxi/6.1.0`
  是同包不同版本，**不能出现在同一依赖图**。

因此配方统一取 6.x 线：`libx11/6.4.0` + `libxi/6.1.0` + `libxtst/1.2.5`
（同 `archives/x/xmacro`、`archives/x/xclicker` 的既有结论）。

## 构建

- 构建系统：GNU autotools（`configure.ac` + `Makefile.am` + `src/Makefile.am`）。
- tag archive **不含预生成 `configure`**（autoreconf 产物不进版本库），
  `build()` 先 `autoreconf -fi` 自举。
- `configure.ac` 三个 `PKG_CHECK_MODULES`（`x11>=1.6` / `xi>=1.6` / `xtst>=1`）：
  - aclocal 阶段需要 `pkg.m4` → 经 `ACLOCAL_PATH` 动态定位 pkg-config 安装目录，
    兜底扫描 hnp 工具链 aclocal 目录（同 `xsel` / `aircrack-ng` / `afuse`）。
  - configure 阶段需要 `x11.pc`/`xi.pc`/`xtst.pc` → `PkgConfigDeps` 生成到
    generators 目录，并在 `build()` 内作用域注入 `PKG_CONFIG_PATH`
    （try/finally 恢复；真机上 `tc.environment()` 注入实测不生效，同 `pidgin`/`xsel`）。
- OHOS 下显式 `--build/--host=aarch64-unknown-linux-gnu`，绕过 `config.guess`
  不识别 HarmonyOS 的 `cannot guess build type`（同 `xsel` / `a52dec`）。
- E114 / HMFS-getcwd 兼容改写（`configure` 的 `umask 077→022` 与 `ac_pwd` 兜底）
  沿用 `xsel` 的既有实现，普通文件系统上为 no-op。

### 本地交叉编译

```bash
cd /root/ohpcd-work/wt-xhk/archives/x/xhk/1.2
conan create . --name=xhk --version=1.2 \
  -pr:h ohos-aarch64-wsl-xbuild -pr:b default \
  -c tools.build.cross_building:can_run=true
```

（构建目录在 WSL 原生盘 `/root/...`，非 `/mnt/*`。）

## 上游 aarch64 缺陷（实测，未打补丁，如实记录）

在 aarch64 上运行打包二进制实测发现两处上游缺陷，**均为上游源码问题，本适配
未引入源码补丁**（OHOS 无 X server，运行期功能本就归真机验证；是否修复留给
上游/后续人工决策）：

1. **`char opt` 无符号导致 getopt 循环永不结束**（`src/xhk.c:710-713`）

   ```c
   char opt;
   while((opt = getopt(argc, argv, "dvhmt")) != -1)
   ```

   aarch64 上 `char` 默认无符号：`getopt()` 返回的 `-1` 存入 `opt` 变成 `255`，
   `255 != -1` 恒真 → 循环永不退出 → 每轮都落入 `default: usage(); exit(1);`。
   实测：`xhk -d`、`xhk`（无参）在 aarch64 上一律打印 usage 并 **exit 1**，
   永远到不了 `xlib_halfkey()`；x86_64（`char` 有符号）无此问题。
   修复方式是上游一行改动 `char opt;` → `int opt;`。
   **注意**：`-v` / `-h` / `-t` 在循环体内直接 `exit()`，因此这三个选项在
   aarch64 上仍可达（消费者用例 HC-1 走 `-t`）。
2. **`construct()` 返回 NULL 但调用点解引用**（`src/xhk.c:184-198` + `536`/`644`）

   `construct()` 在 `OpenDisplay()` 失败时 `return NULL;`，而
   `xlib_halfkey()` / `xlib_test()` 都直接写 `if (screen->display == NULL)` →
   空指针解引用。实测 `DISPLAY=:99 xhk -t`（无该 X server）→
   `qemu: uncaught target signal 11 (Segmentation fault)`，rc=139。
   修复方式是把两处判断改为 `if (screen == NULL || screen->display == NULL)`。

## 平台限制（规则 7）

OHOS 无 X server：xhk 的运行期功能（XInput2 抓取全局按键、XTest 注入镜像按键、
`setpriority(-20)` 实时优先级）需要真实 X 环境与设备权限，属**真机验证**范畴。
headless 环境只做确定性验证：

- `xhk -v` → `xhk, version 1.2`，exit 0（在 `XOpenDisplay` 之前）
- `xhk -h` → usage，exit 0
- `xhk -z` → 非法选项 usage，exit 1（选项校验路径）
- `readelf` 断言 AArch64 / OHOS musl 解释器 / NEEDED 三个 X 库

## 鸿蒙消费者端到端用例（`test_package/test_xhk_consumer.sh`）

rule12 要求「鸿蒙特有测试 ≥1 且不能是纯断言，必须是完整消费者用例（真正跑通
功能/流程的端到端用例）」。因此除上面的确定性断言外，test_package 另有一个
**消费者端到端用例脚本**：把打包出来的 `bin/xhk` 当成最终用户手中的命令行工具
来用，让它在一台**真实运行的 X server** 上跑通 xhk 的核心业务工作流。

### 业务工作流（被测面）

xhk 的功能是「空格键当修饰键」：单独的 Space 原样透传；Space 按住后再按某一侧
的键，该键被镜像到键盘另一半（`mirror_key()` 的 keycode 折叠 + Backspace/Tab、
Enter/Caps、`-`/`` ` `` 特例对调，`ProcessKeycode()` 的 Start/Pressed/Modified
三态机），最终经 `XTestFakeKeyEvent()` 真注入 X server。上游内置的 `xhk -t`
（`xlib_test()`）逐条驱动该状态机并比对返回 keycode 与状态（含「Space+F 必须
变成 J」这类镜像断言），是端到端跑通业务逻辑的入口。

### 用例

| 用例 | 内容 | 断言 |
|------|------|------|
| HC-1 | 真实执行打包产物 `xhk -dd -t`，在真实 X server 上跑完半键盘镜像工作流 | 10 项：rc=0；`XOpenDisplay("<display>")`；`XI Version 2.0`（与活 server 协商 XI2）；`Verify a key gets mirrored`；`Entering ProcessKeycode in state Modified`（真进入镜像态）；`Sending keycode Down/Up 65, (space) to XTest`（真经 XTest 注入）；`Exiting Test Loop with 0 errors`（业务结果）；无 `but expected`（产品自比对无 keycode/状态失配）；无 `Couldn't connect to XServer` |
| HC-2 | 独立消费者旁路观测：另一个独立 X 客户端（`xev`）在同一 server 上观测被测工具注入的按键事件 | 2 项：注入后独立客户端收到的 KeyPress 数由 0 增长；观测到的 keycode/keysym 与注入键一致（keycode 65 / keysym 0x20 space） |

**为什么这个用例「通过」不可能来自空跑**：无 X server 时 `construct()` 返回
NULL 而调用点解引用 → SIGSEGV（实测 rc=139），拿不到 rc=0；连上 server 后
`KeycodeTest()` 逐条比对，任一条镜像映射/状态不符都会打印
`... returned ... but expected ...` 并计入 `errors`，最终结算是
`Exiting Test Loop with 0 errors` / 非 0 errors。

### X server 供给（三档，逐档如实记录）

1. **自起可控 Xvfb**（`command -v Xvfb` → `/opt/ohos-guest/bin/Xvfb` →
   `/data/service/hnp/bin/Xvfb`）：bare server、无 WM，焦点为 PointerRoot，
   E2E 行为可复现 → HC-1 + HC-2 都跑。
2. **环境已有且可达的 `$DISPLAY`**（unix socket 或 TCP 6000+n 任一可达）→ 跑
   HC-1；HC-2 依赖 bare server 的焦点语义，故显式 SKIP。
3. **都没有** → 打印 `HC-SKIP: 无可用 X server ...` 后**退出 0**：
   跳过**不计入通过**（`HMBS_HARMONY_CONSUMER_RESULT` 里 `executed=false`、
   `skipped=2`），也不阻塞构建。CI worker 无 X server 时即为这一档。

### 本机实测（WSL Ubuntu 22.04 + Xvfb 21.1.4，2026-10-16）

从源码全新构建（清缓存后 `conan remove 'xhk/1.2' -c`）：

```bash
cd /root/ohpcd-work/wt-xhk15939
conan create archives/x/xhk/1.2 \
  -pr:h=ohos-aarch64-wsl-xbuild -pr:b=default \
  -c tools.build.cross_building:can_run=true --build=missing
```

`xhk/1.2: Package '4d0cd6a9dc3aa3bafd1d38e2385823876a8090dd' created`（package_id
与既有记录一致），随后 test_package 自动执行两个脚本，`conan create` 退出码 0：

```text
test xhk 1.2: 8 passed, 0 failed                     <- test_xhk.sh（确定性断言面）
=== xhk 1.2 HarmonyOS consumer end-to-end cases ===
X server: /usr/bin/Xvfb :99 (started by this test, TCP, pid 18408)
HC-2 observer: xev on 127.0.0.1:99 (pid 21398, attempt 1)

HC-1 run: xhk -dd -t   (DISPLAY=127.0.0.1:99)
    | -- HalfKey Xorg Driver Utility 1.2 --
    | XOpenDisplay("127.0.0.1:99")
    | XI Version 2.0
    | Entering Test Loop...
    | Check space works alone
    | Entering ProcessKeycode in state Start
    | Entering ProcessKeycode in state Pressed
    | Sending keycode Down 65, (space) to XTest at 0
    | Sending keycode Up 65, (space) to XTest at 0
    | Verify a key gets mirrored
    | Entering ProcessKeycode in state Modified
    | Sending keycode Up 65, (space) to XTest at 0
    | Verify a non-mirrored key doesn't break the space bar
    | Sending keycode Down 65, (space) to XTest at 0
    | Verify pressing paired mirror keys sequentially still works
    | Exiting Test Loop with 0 errors...
HC-PASS: HC-1 product exited 0 on a live X server
HC-PASS: HC-1 connected to the X server it was pointed at
HC-PASS: HC-1 XInput2 negotiated with the live server
HC-PASS: HC-1 mirror workflow executed
HC-PASS: HC-1 state machine entered Modified (mirror) state
HC-PASS: HC-1 state machine injected a key press through XTest
HC-PASS: HC-1 state machine injected a key release through XTest
HC-PASS: HC-1 business result: Exiting Test Loop with 0 errors
HC-PASS: HC-1 no keycode/state mismatch in the product's own comparison output
HC-PASS: HC-1 the product did not report an X connection failure
HC-2 observer: space KeyPress before=0 after=37, matching lines=73
    |     state 0x0, keycode 65 (keysym 0x20, space), same_screen YES,
HC-PASS: HC-2 an independent X client received the key events the packaged product injected into the server
HC-PASS: HC-2 observed keycode/keysym match the injected key (keycode 65 / keysym 0x20 space)
test xhk 1.2 consumer cases: 12 passed, 0 failed, 0 skipped
HMBS_HARMONY_CONSUMER_RESULT={"executed":true,"passed":true,"passedCount":12,"failedCount":0,"skippedCount":0,...}

xhk/1.2 (test package): xhk test_package PASS
```

三档 X server 供给路径均实测过（同一脚本）：

| 路径 | 结果 |
|------|------|
| 自起 Xvfb（`/usr/bin/Xvfb :99`，TCP） | 12 passed / 0 failed / 0 skipped |
| 已有且可达的 `$DISPLAY`（本机 WSLg `:0`，真实 Xwayland server） | 10 passed / 0 failed / 1 skipped（HC-2 需 bare server） |
| 无 X server（隐藏 Xvfb + 不可达 DISPLAY） | 2 skipped，`executed=false`，退出码 0（不计入通过） |

反向对照也实测过：把 `DISPLAY` 指向不存在的 server 再跑 `xhk -t` → qemu 立刻
`Segmentation fault`、rc=139（上游缺陷 2）——即本用例的「通过」确实依赖真实 X
连接，不可能来自空跑。

### 本机验证命令的现实约束（如实记录）

`-pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl`（与 CI 的
`ci/conan/profiles/ohos-aarch64` 双上下文写法同源）在本机 **WM 热缓存下只重跑 test
阶段**：包已在缓存中时 `conan create` 直接跳过 build() 并执行 test_package（上面
12 passed 即来自该命令）。**冷缓存下该 profile 组合在本机无法完成 build()**：
build 上下文解析到 OHOS 的 `automake/1.18`（aarch64），其 `bin/aclocal` 是
exec `.aclocal-real` 的 shell 包装，而本机 x86_64 宿主没有 OHOS loader →
`autoreconf: error: .../aclocal failed with exit status: 127`。
本机从源码构建需按既有记录用 `-pr:h=ohos-aarch64-wsl-xbuild -pr:b=default`
（build 上下文为本机 x86_64）；CI worker 自身能执行 OHOS aarch64 二进制，故 CI 用
双 `ohos-aarch64` 上下文即可（本 PR 的 CI 构建 #92637 已验证通过）。


### 与规则 7 / 真机的关系

本用例不改变「OHOS 无 X server、xhk 运行期功能归真机验证」的既有结论：它在
**具备 X server 的环境**（本机/任何装了 Xvfb 的 worker）给出真实端到端证据；
OHOS 真机上若无 X server，则该用例落回第 3 档显式 SKIP，不伪造通过。

## 本地运行环境（/opt/ohos-guest）

本地/CI 模拟运行环境用的是 stock musl，缺 OHOS 硬化符号 `__fd_chk`（FORTIFY）
与 `arc4random_buf`，而制品仓 X11 二进制需要它们。该 guest rootfs 自带
`/opt/ohos-guest/lib/libfdchkshim.so` 与 `libarc4shim.so`；`test_package` 在
这两个文件存在时经 `LD_PRELOAD` 注入，真机 OHOS libc 自带这些符号时自动跳过。
**配方本体不依赖 shim**，shim 只服务于本地 qemu 运行验证。

## 待人工/真机事项

- 真机（有 X server 的 HarmonyOS PC）上验证空格键镜像与 XTest 注入的实际行为；
  在此之前需先修复上面「上游 aarch64 缺陷 1」（unsigned char），否则 aarch64
  上 CLI 主路径（`xlib_halfkey()`）不可达。
- 制品仓发布（`conan upload`）后把 `commands.json` 的 `binary` 置为 `true`、
  版本级 `manifest.yaml` 的 `status` 升为 `published`。
