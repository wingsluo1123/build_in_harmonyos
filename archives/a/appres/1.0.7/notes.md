# appres 1.0.7 适配笔记

## 编译环境
- 构建系统: autotools（上游同时带 `meson.build`，本配方走 autotools，理由见下方"问题 5"）
- 编译日期: 2026-10-07
- 编译器: clang 15.0.4（`aarch64-unknown-linux-ohos`）
- 状态: built

## 编译步骤

1. W0 依赖发布检查：`preflight_check.sh appres/1.0.7 --deps "libx11/1.8.13 libxt/1.3.1 xorgproto/2025.1"` → 三项 `[OK] 已发布`；
   **并用 `conan graph info` 验可解性（rc=0）** —— 见问题 1。
2. 源码：`init-build --url=https://www.x.org/releases/individual/app/appres-1.0.7.tar.xz --tar tar.xz`
3. 手动探索编译（验证上游路径可行）：
   ```bash
   # 依赖 .pc 由 PkgConfigDeps 生成（x11/xt/xproto）
   conan install --requires=libx11/1.8.13 --requires=libxt/1.3.1 \
                 --requires=xorgproto/2025.1 --generator=PkgConfigDeps ...
   perl scripts/patch-autotools-ohos.pl config.guess config.sub   # E007/E072
   # + config.sub kernel 白名单补 linux-ohos*（脚本因 guard 误判跳过，见问题 3）
   # + configure 的 umask 077 && mktemp → 022 && mkdir（E110/E112，见问题 4）
   PKG_CONFIG_PATH=<pc dir> CC=clang ./configure --prefix=<prefix>   # rc=0
   make -j2                                                          # rc=0，产物 appres 31168B
   make install DESTDIR=<staging>                                    # rc=0（bin/appres + man/appres.1）
   make check                                                        # rc=0，空转（上游无测试）
   ```
4. 配方固化：`conan-init` 生成首稿 → 按上述实测逐项改写 → `conan-verify`（`conan create` 干净构建 + G0-G4/L2/L4/L5）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan graph info` 报 `Version conflict: Conflict between libx11/1.8.13 and libx11/6.4.0` | **`libxt/1.3.1` 自身 requires `libx11/1.8.13`** ⇒ 与 `libx11/6.4.0` 互斥 | 改用 `libx11/1.8.13 + libxt/1.3.1 + xorgproto/2025.1`，`graph info rc=0` 实证。**教训：依赖"已发布"≠"可解"，`preflight --deps` 与 `conan graph info` 是两道闸、缺一不可** |
| 2 | `configure: error: cannot guess build type; ... unable to guess system type` + `can't create $TMPDIR/cgXXXXXX/dummy.c: Permission denied` | ① `config.guess`(2023-01-01) 无 `uname -s = HarmonyOS` 分支（E007）；② 脚本内 `umask 077 && mktemp -d` 建 700 目录，HMDFS 拒写（E110） | ① 打 E007/E072 补丁（HarmonyOS case → `aarch64-unknown-linux-ohos`）；② `umask 077` → `022`、`mktemp -d` → `mkdir` |
| 3 | 打完 E007/E072 补丁仍报 `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | E072 **第 3 处**（kernel-OS 白名单 `linux-ohos*`）未生效：补丁脚本的 guard 用裸 `unless (/linux-ohos/)`，而**第 1 处 triplet patch 已写入子串 `linux-ohos`** ⇒ 误判"已存在"而跳过 | 配方内单独补该处，guard 改用**完整行** `linux-gnu* \| linux-dietlibc* \| linux-ohos*` 判存在（ncview 配方注释已明确警告此坑） |
| 4 | `./config.status[790]: can't create ./confXXXXXX/subs1.awk: Permission denied` | config.status 沿用 `umask 077 && mktemp -d` ⇒ 700+setgid 目录，HMDFS 拒写（E112），且 chmod 无效（E046） | 改 configure 内模板为 `umask 022 && mkdir`（config.status 由其生成，一并生效） |
| 5 | `build` 一条龙首轮 `EXIT_REASON: meson_failed / STEP_FAILED: Step3`，设备 `meson: command not found` | driver 的 `_detect_build_system()` **只看 `meson.build` 存在即返回 meson**（cmake 分支有 `not configure` 保护、meson 分支没有），且**无条件覆盖** init-build 已判对的 `BUILD_SYSTEM=autotools` | 不改框架（`scripts/` 只读）。走 `§12.60①`「配方就位后直接 conan-verify（其 create 不触发 init）」。**按上游官方发布路径走 autotools**，CI 侧也因此可复现 |
| 6 | `ModuleNotFoundError: No module named 'conan.tools.pkg_config'` | `PkgConfigDeps` 的导入路径是 `conan.tools.gnu`（与 Autotools 同处），不是 `conan.tools.pkg_config` | 改 import 后 `conan inspect` 与 G1/G2 通过 |
| 7 | 上游 `PKG_CHECK_MODULES(APPRES, [x11 xt xproto >= 7.0.17])` 找不到 `xproto` | conan `xorgproto` 配方只声明 `pkg_config_name=xorgproto`；而 **xorgproto 正是提供 xproto 头的项目**（真实系统 xorgproto 包同样安装 `xproto.pc`） | `generate()` 内 `set_property("pkg_config_name", "xproto")` 别名；`x11.pc`/`xt.pc` 的 `Requires:` 链随同一属性同步改名，全图一致 |

## 源码修改

**3 处修复以 `patches/` 下 3 个 portability 补丁落地**（五处同源：`conandata.yml` 的
`patches:` 3 件 · `manifest.yaml` 的 `patches_applied` 3 件 · `patch_generation.patches_count: 3`
· 磁盘 `patches/` 实物 3 件 · 本件与 `README.md` 同口径）。`conanfile.py` 的 `build()`
先 `apply_conandata_patches()` 应用，再跑幂等的 `_patch_autotools_scripts()` 兜底
（补丁已生效时为 no-op）。**R8/PF5：不引入平台宏**，全文**无 `__OHOS__` 字面量**
（config.guess 靠 uname 名 `HarmonyOS` 识别，不靠 C 宏）：

- `config.guess`：插入 `*:HarmonyOS:*:*` case（输出 `aarch64-unknown-linux-ohos`）+ `umask` 放宽
- `config.sub`：`ohos-linux` 三元组映射 + OS 白名单 `ohos*` + kernel 白名单 `linux-ohos*`
- `configure`：`umask 077 && mktemp -d "./confXXXXXX"` → `umask 022 && mkdir`（E110/E112）

⚠ **未采用 `--build`/`--host` 绕过 config.guess**：E007 根因栏明写「若用 --build/--host 绕过则误判为交叉编译，
导致 AC_RUN_IFELSE 等全部跳过、生成错误 config.h」。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libx11 | 1.8.13 | 由 `libxt/1.3.1` 约束（见问题 1） |
| libxt | 1.3.1 | 提供 `X11/Intrinsic.h`（appres.c 必需） |
| xorgproto | 2025.1 | 满足上游 `xproto >= 7.0.17` |

## 路径 B 判定

**B判定 = none**（理由：**无空白区机制命中，SCT 普查已逐项为 0**）

依据：SCT/SWT-1 一手普查（2026-09-26 08:25 取证补录，与登记表备注同源）——
`mmap_sync` / `dlopen` / `inotify` / `eventfd` / `utimensat` / `ppoll` / `getaddrinfo` /
`sysvshm` / `pty` / `termios` / `memstream` / `epoll` 共 **12 项空白区机制**，逐项 grep
**命中全为 0**；本包 c/c++ 源文件 1 个（`appres.c`）、脚本 0 个，实际系统调用面只有
Xlib 协议与 `select` ⇒ **纯 X11 客户端，无平台行为差异面**。
⇒ 不触发任何空白区机制、不构成「hit 四条件」中的任一命中，故不走路径 B；
亦不触发语言/构建系统不匹配例外（源码主语言 c、构建系统 autotools，均与任务声明一致）。

## 测试口径（rule4 三处同源：本件 + `test_package/MANIFEST.yml` + PR 正文两表）

- **上游 N = 0**（`§12.72` 四口径 2026-10-07 于源码树实测）：
  `test*/` 框架 0 · `*/res` 语料 0 · `**/*RUNTEST*` 0 · `src/demo|examples/*.c` 0；
  `Makefile.am` 无 `TESTS`/`check_PROGRAMS`、`configure.ac` 无测试宏；源码树唯一 `.c` 即主程序 `appres.c`。
  `make check` 实测 **rc=0 空转**（`Nothing to be done for 'check'`）。
- **适配后 N′ = 4**（`test_package/test.sh` 消费者断言）：
  ① `-version` 输出 `appres 1.0.7` 且 rc=0；② `-V` 同上；③ `-help` rc=0；④ `-help` 含 `usage:` 与 `-V` 文本。
- N′(4) ≥ N(0) ⇒ 满足 `适配后合计 ≥ 上游`。
- **披露：配方 `build()` 未调 `make check`** —— 上游 `Makefile.am` 无 `TESTS`/`check_PROGRAMS`、
  `configure.ac` 无测试宏 ⇒ `make check` 目标为空壳（`Nothing to be done for 'check'`、rc=0 空转），
  故 `build()` 只执行 `autotools.configure()` + `autotools.make(args=["-j2"])`。
  上游 N=0 已由 W4 在 pristine 树按 `§12.72` 四口径独立复算 = 0（未降分子）；
  上游 `make check` 的空转结果见上方「验证结果」实测记录。

## 验证结果

```bash
# 手动探索（配方固化前，本机实测）
$ PKG_CONFIG_PATH=<pc> CC=clang ./configure --prefix=<p>   # rc=0
$ make -j2                                                 # rc=0，CC appres.o / CCLD appres
$ make install DESTDIR=<staging>                           # rc=0 → bin/appres, share/man/man1/appres.1
$ make check                                               # rc=0（空转，上游无测试）

# 运行时（conanrun 注入 LD_LIBRARY_PATH 后，DISPLAY 仍为空）
$ appres -version   → "appres 1.0.7"  rc=0
$ appres -help      → usage 文本       rc=0
```

## 注意事项

- **X 能力面（B 机实测）**：`DISPLAY` 未设、`/tmp/.X11-unix` 不存在 ⇒ 设备**无本地 X server**。
  实测：`appres -version` / `-V` / `-help` **在连 X 之前就返回**（rc=0，无需 X）；
  而**裸执行 `appres` 与未知参数路径会打开 display**，报 `Error: Can't open display`（rc=1）。
  ⇒ `test_package` 只断言不需 X 的三条路径；需 X 的资源查询路径**如实记录于此，未纳入断言**（未降测试、未删夹具）。
- 运行期必需 `LD_LIBRARY_PATH`（libXt/libX11/libxcb/libXdmcp/libXau/libSM/libICE 来自 conan 缓存）；
  `test_package` 经 `VirtualRunEnv`（`env="conanrun"`）注入，裸跑二进制会 rc=127。
- `appres` 是**命令行工具**（无库、无头）⇒ 软件级 `commands.json` 已建，`package_info()` 只留 `bindirs=["bin"]`。
---

**编译结束**: 2026-10-07 18:45
**最终状态**: built
