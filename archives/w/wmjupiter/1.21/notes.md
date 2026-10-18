# wmjupiter 1.21 — 适配笔记

## 一、上游与选型

| 项 | 值 |
|---|---|
| 软件 / 版本 | wmjupiter / 1.21 |
| 上游仓库 | https://github.com/engerim42/wmjupiter （tag `1.21`） |
| 上游作者 | Thomas Kuiper（inxsoft.net，1998-2001 原始版本）；engerim42 为现维护者 |
| 许可证 | BSD-3-Clause（tag 内 LICENSE 为三条式 BSD 文本；FreeBSD ports 记 GPLv2/BSD3CLAUSE 双授权，本仓库归档只带 BSD 三条式，故取 BSD-3-Clause） |
| 语言 / 构建系统 | C / 裸手写 GNU Makefile（无 configure、无 automake） |
| 源码 sha256 | `435f494737c61339536d5d47225685a29787ba62691ccdf1ad5ce1d17ef2942c` |
| 源码 URL | `https://codeload.github.com/engerim42/wmjupiter/tar.gz/refs/tags/1.21` |

**语言预检（R47）**：`lang-preflight wmjupiter 1.21 --src <work>` 判定 **C / 主体 100%**
（tarball 内 2 个 `.c` + 1 个 `.h`，无任何其他语言源码；构建系统为手写 Makefile，
无 manifest 类文件）→ 与任务语言 cpp 同族，通过，无需迁移。

**URL 取证（R39）**：`search-url` 无候选，故按包名人工定位。FreeBSD ports 的
`USE_GITHUB=yes GH_ACCOUNT=engerim42 GH_PROJECT=wmjupiter` 指向 GitHub 官方仓，
`api.github.com/repos/engerim42/wmjupiter/tags` 实测有 tag `1.21`（无 `v` 前缀）。
`codeload.github.com` 是 GitHub 官方归档下载端点（`github.com/<owner>/<repo>/
archive/refs/tags/<tag>.tar.gz` 会 302 到该端点），**不是第三方镜像**；仓库内同类
官方归档源有 533 处先例（3proxy/0.9.5、abcmidi 等）。本地实测：`github.com/.../archive`
跳转段超时（下载失败），而 `codeload.github.com` 直连 1.4s 返回 10423 字节 ——
字节数与 FreeBSD distinfo 记的 SIZE 完全一致，sha256 亦一致（见上表），可确认同源无损。
**注意**：`ci/conan/build_and_test.sh` 的镜像 fallback 注入只匹配 `https://github.com/...`
形态，codeload 形态不会获得镜像改写，故 CI 直接走该官方端点（与上述 533 处先例同路径）。

**R51 上游测试清点（发布包一手证据）**：
- tarball 条目数 `tar tzf | wc -l` = **9**：`wmjupiter-1.21/`、LICENSE、Makefile、
  README.md、wmJupiter.c、wmJupiter_mask.xbm、wmJupiter_master.xpm、xutils.c、xutils.h
  —— 无 `tests/`、`test/`、`t/` 目录，无 `test_*` / `*_test.*` 文件。
- Makefile 全文 34 行，目标只有 `all:` `clean:` `install:` 三个；
  `grep -c 'check\|test' Makefile` = **0**（无 check/test/check-local 目标）。
- 结论：**上游测试数 N = 0，可运行测试数 N' = 0**，通过率不适用（0/0）。
  消费者验证由 test_package 真实执行被测二进制承担（24 条断言：A 类失败路径 7 条 +
  B 类端到端消费者用例 17 条，后者以 headless X11 协议对端驱动完整绘制流程）。

## 二、W0 依赖发布核验（适配前第一件事）

| 依赖 | 制品仓状态 | 核验方式 |
|---|---|---|
| libx11/6.4.0 | 已发布（本地已装） | `conan install --requires=libx11/6.4.0 ... --build=never` → 通过 |
| libxext/6.4.0 | 已发布（本地已装） | 同上，`--build=never` 无源码构建 |
| libxpm/3.5.17 | 已发布（binary 实测下载成功） | `conan download libxpm/3.5.17 -r=ohpcd` + `conan install --build=never` |
| xorgproto/2025.1 | 已发布 | 同上 |

**版本线选择**：整张 X11 图统一钉在 cmd-pkgs **6.4.0 线**。依据：`libxpm/3.5.17`
配方内部写 `self.requires("libx11/6.4.0", force=True)`，`libxext/6.4.0` 亦钉
`libx11/6.4.0`；若把 libx11 反向钉到 1.8.x 会让 `package_id` 变化并触发 libxpm 源码
重建，撞上 autotools configure 在沙箱下的 fork/EAGAIN（历史上 14288 #86220 的实例）。

**W0b 历史归档核验**：本仓库 `archives/w/` 无 wmjupiter 任何历史版本（`git log` 无记录），
不存在需比对的旧绕坑命令；同目录 `wmcube/1.0.2`、`wmcalc/0.7`、`wmcdplay/1.1` 为同类
WindowMaker dockapp，其结论（依赖三件套走 6.4.0 轨、无 display 交付口径、测试用 POSIX sh）
已在本包逐项遵循。

## 三、复现的失败与修法（E491 同型）

### 3.1 现象（clang 15 默认 `-fno-common` 下链接期 duplicate symbol）

手工编译两个 TU 均干净通过，但链接期报重复符号：

```
ld.lld: error: duplicate symbol: display
>>> defined at xutils.c
>>> defined at wmJupiter.c
ld.lld: error: duplicate symbol: win
ld.lld: error: duplicate symbol: NormalGC
... (iconwin / screen / DisplayDepth 同)
```

### 3.2 根因

`xutils.h` 第 21-26 行把 7 个全局变量（跨 6 行 `extern` 声明，`iconwin, win` 同行）写成**试探性定义**（tentative definition）：

```c
Display		*display;
Window          Root;
Window          iconwin, win;
int             screen;
int             DisplayDepth;
GC NormalGC;
```

而 `wmJupiter.c`（第 13 行 `#include "xutils.h"`）与 `xutils.c`（第 40 行）**都包含该头**，
于是每个翻译单元各产生一份定义。1998 年的编译器把这类符号当 common symbol 合并掉，
**clang 15 起默认 `-fno-common`**（GCC 10 起亦同），链接期即报重复定义。

### 3.3 修法（按知识条目 E491 `rec_priority: 1`）

`knowledge/graph/E491.kv` 正是本模式：*"replace tentative definitions with extern
declarations plus one definition"*，并明确 `forbid_1` 为「加 `-fcommon` 全局放开」这条捷径
（在鸿蒙侧会掩盖其它同类缺陷，属禁止项）。据此落一对补丁：

| 补丁 | 内容 | patch_type |
|---|---|---|
| `0001-xutils.c.patch` | 在 `xutils.c` 中补齐 7 个全局变量的**唯一定义**（+10 行） | portability |
| `0002-xutils.h.patch` | `xutils.h` 中 7 个全局变量由试探性定义改为 `extern` 声明（6 行改 6 行） | portability |

两个补丁均为纯 C 声明/定义语义修正：**不含任何平台宏、不含条件编译**（R8 / PF5 自查：
`grep -c "__OHOS__" patches/*.patch` = 0）。补丁经 `ohc-run.py refresh-patch --auto` 生成登记（R3）。

## 四、Makefile 的接管面（只有两处，其余保留上游默认）

上游 Makefile 的关键两条规则：

```make
.c.o:
	$(CC) $(CFLAGS) -D$(shell echo `uname -s`) -c $< -o $*.o $(INCDIR)
wmJupiter:	$(OBJS)
	$(CC) $(CFLAGS) $(SYSTEM) -o wmJupiter $^ $(INCDIR) $(LIBDIR) $(LIBS)
```

与 `wmcube/1.0.2` 那类「把 `$(CPPFLAGS)`/`$(LDFLAGS)` 当自由通道」的 Makefile 不同，
**这里两条规则都不含 `$(CPPFLAGS)`/`$(LDFLAGS)`**，依赖头/库目录没有环境变量入口；
`CC`/`CFLAGS`/`INCDIR`/`LIBDIR`/`LIBS` 又都是 Makefile 内部**赋值**，命令行同名变量是
**替换**而非追加。因此配方只接过两处：

| 接管项 | 值 | 理由 |
|---|---|---|
| `CC` | Conan conf `tools.build:compiler_executables["c"]`（OHOS profile 里为 clang） | 上游硬编码 `CC = gcc`（构建机无 gcc 会直接失败；R33：编译器取自 conf，不读 shell 变量） |
| `INCDIR` / `LIBDIR` | 由 `self.dependencies` 逐依赖 `cpp_info.aggregated_components()` 汇总的头/库目录 | 上游写死 X11R6 陈旧路径 `/usr/X11R6/include`、`/usr/X11R6/lib` |

**故意不接管**：`CFLAGS` 保留上游 `-O2 -Wall`；`LIBS` 保留上游 `-lXpm -lX11 -lXext -lm`
（三个库都被源码真实引用：`XpmCreatePixmapFromData`→libXpm、`XShapeCombineMask`→libXext、
`XOpenDisplay` 系→libX11、`fabs` 系→libm）；`-D$(shell echo \`uname -s\`)` 保留
（展开为 `-DLinux`，源码中无任何 `#ifdef` 依赖它，实测无副作用）。

`make install` **不调用**：上游规则 `install -c -s -m 0755 wmJupiter $(DESTDIR)/bin`
会就地 strip，且 Makefile 把 `DESTDIR` 赋成 `/usr/X11R6`；`package()` 用显式 `copy`
复现安装布局（`bin/wmJupiter` + `licenses/LICENSE` + `share/doc/wmjupiter-1.21/README.md`）。

## 五、本地验证（W3）

`conan create` 全流程通过（R36 依赖核验 → 源码下载 → 补丁应用 → 编译 → 打包 → test_package）。
test_package 24 条断言全过（A 类失败路径 7 条 + B 类端到端消费者用例 17 条），日志与结果落 `reports/` 与 `.ci-result.json`（含日志 SHA256）。

产物取证（手工编译阶段一手记录）：
- `readelf -d wmJupiter` → `NEEDED: libXpm.so.4 / libX11.so.6 / libXext.so.6 / libc.so`
  （三个 X 库均为真实动态链接，非名义 require）
- `./wmJupiter`（无 DISPLAY，rc=1）→ stderr `wmJupiter: can't open display `
- `./wmJupiter -display :<N>`（rc=1）→ stderr `wmJupiter: can't open display :<N>`
  （该串系 argv 扫描后经 `XDisplayName()` 回显，可判定参数处理真实执行）
- **显示号不写死（一次真实踩中）**：负路径按 PID 取 300 段（TCP 6300-6399），
  对端自用 20-219 段（6020-6219），两段不相交；对端 bind 前先探测端口、避让残留
  监听，并加 `trap` 在被中断时带走对端进程。原因：一次更早的运行被强杀后，对端会
  留下「遗留监听」（实测本机 `:99`/TCP 6099 即被占住），此时写死该号的负路径会连上
  它、在 `XOpenDisplay` 里一直等 setup 应答，直到上界超时——症状还会伪装成
  「首次 exec 二进制卡住」，归因跑偏（实测排错 40 分钟后才定位到端口）。

## 六、已知限制

1. **功能性验证的边界**：CI 与鸿蒙 PC 均无 X server，故 test_package 以
   **headless X11 协议对端**（`x11_headless.py`，纯 Python stdlib，按 xcb/libX11
   权威线格式实现；不用 Xvfb、不设 `DISPLAY=:0`、不 dlopen）驱动被测二进制跑通
   `openXwindow()` 之后的完整绘制流程（XPM 贴图装载与像素上传、窗口/位图/形状遮罩、
   5 条 WM 属性、`XCopyArea` 动画主循环），并以对端按协议累积的服务端状态作断言
   （B 类 17 条）。**仍未覆盖**：绘制结果的画面语义（卫星位置、GRS 过中天时刻数值）、
   需窗口管理器配合的 dock 停靠、鸿蒙 PC 真机桌面下的显示效果 —— 见
   `reports/test-report.md` 第四节。
2. **运行期需 Conan 运行环境**：产物按 Conan 常规做法不烘焙 rpath（绝对路径会指向
   构建机），`libXpm.so.4` 等由 `conanrun` 的 `LD_LIBRARY_PATH` 解析（`test_package`
   即以 `env="conanrun"` 执行）。这与同目录其它 X11 包一致。
3. **dockapp 生态前提**：作为 WindowMaker 系 dockapp，需要支持 `_NET_WM_WINDOW_TYPE_DOCK`
   的窗口管理器/桌面环境才有正确停靠表现；本次只交付编译与交付件口径，未做桌面集成验证。

## 七、知识沉淀

- 本次错误模式命中既有条目 **E491**（试探性定义 duplicate symbol → extern + 单一定义），
  已按 `rec_priority: 1` 修法执行、并按 `forbid_1` 排除 `-fcommon` 捷径，无新增草稿。
- 可复用的本包结论：**裸 Makefile 的接管面判定法** —— 先看编译/链接规则里是否含
  `$(CPPFLAGS)`/`$(LDFLAGS)`；不含时不能依赖 `conanbuild` 环境注入，必须用 make 命令行
  变量替换上游内部赋值（本包 `INCDIR`/`LIBDIR` 即此类）。
---

**编译结束**: 2026-10-16 13:21
**最终状态**: published
