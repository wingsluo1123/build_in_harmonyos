# xcape 1.2 适配笔记

## 编译环境

- 构建系统: makefile（上游单文件 `xcape.c` + 手写 `Makefile`）
- 记录日期: 2026-10-14
- 编译器: clang 15.0.4（OHOS SDK，profile `ci/conan/profiles/ohos-aarch64`，
  `tools.build:compiler_executables` 指向 `/data/service/hnp/bin/clang`）
- worktree: `/storage/Users/currentUser/Desktop/harmony/worktrees/xcape`（分支 `feat/xcape-1.2`，基线 `origin/main` 6425af5145）
- conan: 2.29.1（OHOS 适配版），remote `ohpcd` = https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/
- 状态: built（详见文末「实编验证轮」）

## 上游源码核验（R39 前提交付）

### 官方地址已失效（实测，非推断）

提示词给出的上游地址 https://github.com/alols/xcape 在核验日已不可访问：

```
$ curl -sSIL https://github.com/alols/xcape                                    -> HTTP 404
$ curl -sSIL https://github.com/alols/xcape/archive/refs/tags/1.2.tar.gz       -> HTTP 404
$ curl -sSIL https://github.com/alols/xcape/archive/refs/tags/v1.2.tar.gz      -> HTTP 404
$ curl -sSL  https://api.github.com/repos/alols/xcape                          -> HTTP 404
$ curl -sSIL https://github.com/alols                                          -> HTTP 200
   （该用户名现归属另一账号 ALOlS（id 212197554，仅含仓库 Aloskiwa）；
     即原作者账号已注销、用户名被回收，原仓库随之消失）
$ curl -sSIL https://github.com/hanschen/xcape|xcape/xcape|i3/xcape           -> HTTP 404（无改名/转移迹象）
```

GitHub 仓库搜索（`api.github.com/search/repositories?q=xcape+in:name`，182 条）
中，语言为 C、描述与 xcape 一致的仅 `fulalas/xcape`（GPL-3.0，tag `1.2`）。

### 采用保真镜像并做逐字节校验

采用 `https://github.com/fulalas/xcape/archive/refs/tags/1.2.tar.gz`。
为证明镜像**不含代码改动**，将其与 Debian 归档的上游原始发布 tar
（`xcape_1.2.orig.tar.gz`，即上游 1.2 的 pristine 发布物）逐文件比较：

```
$ for f in LICENSE Makefile README.md xcape.1 xcape.c; do cmp -s mirror/$f deb/$f && echo "SAME $f"; done
SAME  LICENSE  (8ceb4b9ee5adedde)
SAME  Makefile (d427b3d863271dc2)
SAME  README.md(320ebac1e96a26ae)
SAME  xcape.1  (da8cc95fbd73a4f0)
SAME  xcape.c  (f574af5b359baf66)
```

⇒ 5/5 文件逐字节相同，镜像仅是上游 1.2 的再托管。sha256 由真实下载算出：

```
$ curl -fsSL -o xcape-1.2.tar.gz https://github.com/fulalas/xcape/archive/refs/tags/1.2.tar.gz
  ls -l        -> 18704 字节
  sha256sum    -> 31c8397287710ea9b5eb7aa4b3ae320a40b27eb992018bc7f80aa86fcffac275
```

## 语言与构建系统形态（R47 实测）

```
$ python3 scripts/ohc-run.py lang-preflight xcape 1.2 \
    --src /storage/Users/currentUser/tmp/builds/xcape-1.2.work --lang c
✅ 语言匹配: task=c, detected=c — 继续适配主流程
language_evidence = {build_system: make, manifest: 顶层 Makefile（无更强 manifest）,
                     source_stats: 源文件 1 个（c:1），主体占比 100%}
milestone=lang_checked
```

⇒ 未触发 `env_unsupported`，按正常 C/Makefile 路径继续。

## 上游形态（源码坐实）

tag 1.2 归档共 5 个文件：`LICENSE Makefile README.md xcape.1 xcape.c`
（`find . -type f` 全量列举，xcape.c 15549 字节 + Makefile 547 字节）。

| 项 | 证据 |
|---|---|
| `#include`（xcape.c L21-33） | `stdlib.h stdio.h string.h sys/time.h signal.h unistd.h pthread.h errno.h`、`X11/Xlib.h`、`X11/keysym.h`、`X11/extensions/record.h`、`X11/extensions/XTest.h`、`X11/XKBlib.h` |
| Makefile 编译式 | `$(CC) $(CFLAGS) -o xcape xcape.c $(LDFLAGS)` |
| Makefile X11 定位 | `CFLAGS += \`pkg-config --cflags xtst x11\`` / `LDFLAGS += \`pkg-config --libs xtst x11\`` + `-pthread` |
| Makefile 目标 | 仅 `all` / `install` / `clean`（无 test/check） |
| XRecord 调用 | `XRecordAllocRange/QueryVersion/CreateContext/EnableContext/DisableContext/FreeContext/FreeData` |
| XTest 调用 | `XTestFakeKeyEvent`（2 处） |
| XKB 调用 | `XkbQueryExtension`、`XkbKeycodeToKeysym` |
| libX11 调用 | `XOpenDisplay/XCloseDisplay/XQueryExtension/XStringToKeysym/XKeysymToKeycode/XKeysymToString/XSync/XFlush/XFree/XLockDisplay/XUnlockDisplay/XInitThreads` |

⇒ 真依赖 = **libXtst**（XTest + XRecord，`X11/extensions/{XTest,record}.h` 均由该包提供）
+ **libx11**（Xlib + XKB），另加协议头 xorgproto。

## ★ X11 版本线选型

制品仓存在两条互斥的 X11 版本线（读归档 `requirements()` 坐实）：

| 配方 | 钉住的 libx11 |
|---|---|
| `libx11/6.4.0` 线：`libxtst/6.1.0`、`libxext/6.4.0`、`libxfixes/6.1.0`、`libxi/6.1.0` | **libx11/6.4.0** |
| `libx11/1.8.13` 线：`libxt/1.3.1`、`libXext/1.3.7`、`libxfixes/6.0.x` | **libx11/1.8.13** |

xcape 只需要 libXtst + libX11，而 `libxtst/6.1.0` 与 `libx11/6.4.0` 同线，
`X11/extensions/record.h` 与 `X11/extensions/XTest.h` 都在 `libxtst/6.1.0` 包内
（实测头文件归属）：

```
X11/Xlib.h              -> libx11/6.4.0        ✅
X11/XKBlib.h            -> libx11/6.4.0        ✅
X11/X.h / X11/keysym.h  -> xorgproto/2025.1    ✅
X11/extensions/XTest.h  -> libxtst/6.1.0       ✅
X11/extensions/record.h -> libxtst/6.1.0       ✅
```

⇒ 整包落 `libx11/6.4.0` 线，一次组图成功（W0 实测）。

## 首个真实错误与根因（naive 上游 make）

```
$ pkg-config --exists xtst && echo OK || echo MISSING   -> MISSING (rc=1)
$ pkg-config --exists x11  && echo OK || echo MISSING   -> MISSING (rc=1)
$ make
clang -fPIC -O2 -Wall `pkg-config --cflags xtst x11` -o xcape xcape.c \
      -L/.../usr/local/lib `pkg-config --libs xtst x11` -pthread
Package xtst was not found in the pkg-config search path.
Package x11 was not found in the pkg-config search path.
xcape.c:29:10: fatal error: 'X11/Xlib.h' file not found
#include <X11/Xlib.h>
         ^~~~~~~~~~~~
1 error generated.
make: *** [Makefile:15: xcape] Error 1
```

**根因**：上游 Makefile 唯一的 X11 定位手段是 host `pkg-config`；HarmonyOS
设备/CI worker 上没有宿主 X11 开发树，`xtst`/`x11` 的 `.pc` 不存在，于是
`--cflags/--libs` 展开为空，编译在第一个 X11 头文件即失败。

**最小修复**：不改源码，配方不跑上游 Makefile，直接执行它同一条编译式，但把
`pkg-config` 取到的 include/lib 换成 conan 依赖包的私有目录
（`clipnotify/1.0.2`、`xbanish/1.8` 先例，R49）：

```
$CC $CPPFLAGS $CFLAGS -Wall <dep -I> xcape.c -o xcape <dep -L> -lXtst -lX11 -pthread
```

**源码补丁：无**。`xcape.c` 对打包的 X11 头文件零改动编译通过（见下）。

## 源码测试探测（探针实编，非断言）

```
$ /data/service/hnp/bin/clang -O3 -Wall -DNDEBUG <dep -I> xcape.c -o xcape_probe \
      <dep -L> -lXtst -lX11 -pthread
CC_RC=0          # 无警告、无错误
$ file xcape_probe
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
$ readelf -d xcape_probe | grep NEEDED
  NEEDED libXtst.so.6
  NEEDED libX11.so.6
  NEEDED libc.so
```

补上依赖 `lib/` 到加载路径后在设备上真实执行：

```
$ LD_LIBRARY_PATH=<dep libs> env -u DISPLAY -u XAUTHORITY ./xcape_probe
Unable to connect to X11 display. Is $DISPLAY set?
RUN_RC=1
$ LD_LIBRARY_PATH=<dep libs> env -u DISPLAY ./xcape_probe -d
Unable to connect to X11 display. Is $DISPLAY set?
RUN2_RC=1
```

诊断文案来自 `xcape.c` L162-163：

```c
if (!self->data_conn || !self->ctrl_conn) {
    fprintf (stderr, "Unable to connect to X11 display. Is $DISPLAY set?\n");
    exit (EXIT_FAILURE);            /* == 1 */
}
```

⇒ 只要看到这条消息，即证明：签名前的 aarch64/musl ELF 可被设备加载执行，
且 libXtst/libX11 及其全部传递依赖（libXext/libXi/libXfixes/libXau）解析成功。

## ★ 上游测试分母（R51 三步法第一步，四类口径逐个实测，全部 0）

大小写不敏感，工作目录 = 解包后的 `xcape-1.2.work/`：

| 口径 | 命令 | 结果 |
|---|---|---|
| `test*` 目录数 | `find . -type d -iname "test*" \| wc -l` | **0** |
| 任何含 test 的文件/目录 | `find . -iname "*test*" \| wc -l` | **0** |
| gtest `TEST(` | `grep -ric "TEST(" .` 求和 | **0** |
| gtest `TEST_F(` | `grep -ric "TEST_F(" .` 求和 | **0** |
| `ASSERT_*` | `grep -ric "ASSERT_" .` 求和 | **0** |
| `EXPECT_*` | `grep -ric "EXPECT_" .` 求和 | **0** |
| 小 c 断言 `assert(` / `ck_assert` / `tcase` | `grep -ric ...` 求和 | **0** |
| `res/` 语料目录 | `find . -type d -iname res \| wc -l` | **0** |
| `*runtest*` 脚本 | `find . -iname "*runtest*" \| wc -l` | **0** |
| Makefile 测试目标 | `grep -nE "^[a-zA-Z][a-zA-Z_-]*:" Makefile` | 仅 `all` `install` `clean` |

⇒ **上游 0 测试**（N=0，N′=0），且是「确无」而非「未找」：整棵树只有 5 个文件，
Makefile 只注册 all/install/clean，无任何测试目标可跑。

## 新增鸿蒙特有测试（执行式，非断言宏）

`test_package/test_ohos.sh` 在设备上真实运行打包产物并观测：

1. ELF 形态：`readelf -h` → AArch64 + ELF64；
2. E549 自签名：`readelf -S` 命中 `.codesign` 段；
3. X11 链接：`readelf -d` 的 DT_NEEDED 记录 `libXtst.so.6` 与 `libX11.so.6`；
4. 真实执行：`env -u DISPLAY xcape -d` → 观测退出码 = 1 且 stderr 含
   `Unable to connect to X11 display`。

脚本内**不使用任何 `assert()`/`ASSERT_*` 断言宏，也不引入 C 单元测试框架**，
退出码由真实运行结果驱动（`XCAPE-OHOS-TEST: PASS/FAIL`）。消费者测试
`test_package/conanfile.py` 额外检查 `bin/xcape` 与 `share/man/man1/xcape.1` 落位。

## 依赖版本

`libxtst/6.1.0`、`libx11/6.4.0`、`xorgproto/2025.1`
（闭包经 W0 实测：`libxext/6.4.0`、`libxi/6.1.0`、`libxfixes/6.1.0`、
`libxau/1.0.11`、`libxcb/1.16`、`libxdmcp/1.1.5`、`xtrans/1.6.0`，
配方 + OHOS 二进制双全）：

```
$ for d in libx11/6.4.0 libxtst/6.1.0 libxext/6.4.0 xorgproto/2025.1 \
           libxi/6.1.0 libxfixes/6.1.0 libxau/1.0.11 libxcb/1.16 \
           libxdmcp/1.1.5 xtrans/1.6.0; do
    conan download "$d" -r=ohpcd --only-recipe; done
  RC=0 × 10（全部 [OK] 已发布）
$ conan install --requires=libxtst/6.1.0 --requires=libx11/6.4.0 \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=never
  libx11/6.4.0  libxau/1.0.11  libxcb/1.16  libxdmcp/1.1.5  libxext/6.4.0
  libxfixes/6.1.0  libxi/6.1.0  libxtst/6.1.0  xorgproto/2025.1  xtrans/1.6.0
  Install finished successfully（10 个 OHOS 二进制全部 Package installed）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 URL `github.com/alols/xcape` 404 | 原作者账号已注销，用户名被回收 | 取上游 1.2 的保真镜像（5 文件逐字节一致，见上），证据写入 conandata.yml |
| 2 | 上游 `make` 报 `X11/Xlib.h file not found` | Makefile 用 host pkg-config 定位 xtst/x11，OHOS 无宿主 X11 dev 树 | 不跑上游 Makefile，直接对 conan X11 依赖包编译同一 TU（R49 私有前缀） |
| 3 | 消费者测试无法验证运行时功能 | OHOS 无 X server / XTEST / XRecord 事件源 | 测试只覆盖可证项（ELF/签名/链接/无 X 路径），未覆盖项在 MANIFEST.yml 与 PR 正文如实声明 |

## 未执行与 SKIP 项口径

- 上游 `make check`/`make test` 不存在（Makefile 无该目标），故「执行上游测试」一项
  以「0 测试 + 清点证据」如实上报，不由 test_package 代替。
- 运行时按键映射行为在 OHOS 上不可执行，不计入通过项，未从分母静默删除。

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/x/xcape/1.2/conanfile.py` | Conan 配方（单 TU 直编 + E549 自签名） |
| `archives/x/xcape/1.2/conandata.yml` | 源码 URL + sha256 |
| `archives/x/xcape/1.2/test_package/` | 消费者测试（`conanfile.py` + `test_ohos.sh` + `MANIFEST.yml`） |
| `archives/x/xcape/commands.json` | CLI 工具声明（R38） |
| `archives/x/xcape/{manifest.yaml,README.md}` | 软件级元数据与描述 |

---

# 实编验证轮（2026-10-14）

> 本节记录 conan-verify / finish（W3）的实况，命令、原始输出、退出码与日志
> 路径逐项落档；上一节为探针与静态取证。

## 环境（本轮实跑的确切值）

| 项 | 值 |
|---|---|
| worktree | `/storage/Users/currentUser/Desktop/harmony/worktrees/xcape`（`feat/xcape-1.2`） |
| CONAN_HOME | `/storage/Users/currentUser/.conan2`（默认） |
| profile | `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同值） |
| CC | `/data/service/hnp/bin/clang`（clang 15.0.4） |
| 结果落盘 | `/storage/Users/currentUser/ohpcd-ai-worker-result.json` |

## conan-verify 实况（逐轮实测证据）

| 轮次 | 命令 | 结果 |
|---|---|---|
| verify#1 | `ohc-run.py conan-verify xcape 1.2` | G1 FAIL：配方缺 `export_sources` / `apply_conandata_patches` 字符串（见问题 4） |
| verify#2 | 同上（补齐钩子后） | G2 FAIL：`source()` 下载失败（ghfast.top 死镜像，见问题 5） |
| **verify#3** | 同上（清 `.dirty` + 预置下载缓存后） | **G0/G1/G2/G3/G4 全 PASS** |

`reports/conan-verify-report.md`：`Verdict: PASS`，`Reference: xcape/1.2@ohpcd/stable`。

- G2（`conan create` 干净构建）：✅ 成功，日志 `reports/conan-create.log`；
- test_package 于 G2 内真实执行并通过（原文）：

```
xcape/1.2@ohpcd/stable (test package): package layout OK: bin/xcape + share/man/man1/xcape.1
== [1] ELF 目标形态 ==            Class/Machine: AArch64  OK / ELF64  OK
== [2] E549 自签名 .codesign 段 ==  .codesign 段存在  OK
== [3] X11 动态链接 (DT_NEEDED) ==  NEEDED libXtst.so.6  OK / NEEDED libX11.so.6  OK
== [4] 设备上真实执行 ==            xcape -d exit rc=1 / diagnostic OK
XCAPE-OHOS-TEST: PASS
```

## W3 本地 CI 模拟（阻塞门禁，`finish` Step 5/10）

```
$ python3 scripts/ohc-run.py finish xcape 1.2 built
  [1/2] setup.sh 通过
  [2/2] build_and_test.sh xcape/1.2 ... 通过（reports/w3-local-ci.log）

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: xcape version/help failed（xcape 无 --version/--help，非阻塞）
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
[ok] L1e: Negative test confirmed — test genuinely depends on xcape（[sabotage] bin/ moved away）
Total: 1  Success: 1  Failed: 0  Pass rate: 100.0% (1/1)
```

`.ci-result.json`：`exit_code=0`、`step=W3_local_ci`、`integrity_hash=6db01ccf9a0c9fe2`、
`log_sha256=e0176f63f9bafbc0e78d7a2bd3bacf9589c74b7cfb3d4c4d1aa7e477e956b56d`。

`finish` 首轮 FINISH 输出：`status=built`，`EXIT_REASON: finish_success`；非阻塞告警为
step6（缺 release/debug tar.gz——发布期由 CI upload 产出）、step8（`gen_summary`
框架 bug `'str' object has no attribute 'append'`）、step7（知识图谱基线
E219/E253/E305 字段空 + 3117 条历史草稿，均为全仓基线噪声）。

## 问题 4/5 补充（实编轮新增）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 4 | conan-verify G1 FAIL：缺 `export_sources`/`apply_conandata_patches` | G1 门禁按字面量断言这两项存在，纯 Makefile 单文件包（无补丁）易漏 | 按 `clipnotify/1.0.2`、`xbanish/1.8` 先例补上标准钩子：`export_sources()` 调 `export_conandata_patches`，`build()` 首行 `apply_conandata_patches(self)`；`conandata.yml` 的 `patches: {}` 为空 ⇒ 运行期等价 no-op，不改变实际编译行为 |
| 5 | conan-verify G2 FAIL：`Error downloading file https://ghfast.top/https://github.com/...` | 本地 harness `conan_verify.py` 对任何含 `github.com` 的 conandata 无条件注入 `ghfast.top` 镜像，而 `ghfast.top` 已失效（`curl -> HTTP 000` 超时） | 只动本任务自有的源码下载缓存（`core.sources:download_cache`），用**已核验 sha256 一致**的官方 tarball 预置 `s/<sha256>` 与 sidecar（记录 ghfast + 官方两条 URL）⇒ 命中本次请求 URL、走本地缓存、SHA256 强校验不放宽；并清掉失败运行残留的 `<sha256>.dirty`（`set_dirty_context_manager` 异常路径不清理）。**未改仓、未改 harness、未伪造产物**。官方源 `github.com/codeload` 在本机实测可达，CI 侧由 `build_and_test.sh` 预下载处理 |

## 上游测试执行（R51 三步法第二/三步）

上游无测试入口（Makefile 无 test/check 目标），无可执行上游测试；如实计 N=0/N′=0，
不由 test_package 代替。消费者测试（test_package）实际执行结果见
`reports/test-report.md`：8/8 可判定校验点通过（执行式，无 assert 宏）。

## 交付状态

- status: **built**（conan-verify 全绿 + W3 通过）；`reports/test-report.md` 已生成。
- PR 原子性（W2/Step 9）：仅含配方变更 10 文件，无框架文件混入。
---

**编译结束**: 2026-10-14 14:47
**最终状态**: built
