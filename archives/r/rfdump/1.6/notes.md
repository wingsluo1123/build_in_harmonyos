# rfdump 1.6 适配笔记（HarmonyOS PC / arm64）

## 编译环境
- 构建系统：autotools（发布包自带 autoconf 2.61 生成的 configure，**不跑 autoreconf**）
- 编译日期：2026-10-18
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`，native OHOS arm64）
- profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS arch=armv8 compiler=clang-15 libc++ Release）
- 状态：built（本地 `conan create` rc=0 + test_package 19/19）

## 软件与产物
RFDump 是 RFID 标签读写工具：串口连接 ACG/兼容读写器，读写标签 ID/类型/厂商与用户
数据区。上游 1.6 是最后一个发行版（2008-06），界面为 GTK2 + libglade。

构建产物（`package_type=application`，R38 已在软件级声明 `commands.json`）：

| 路径 | 说明 |
|------|------|
| `bin/rfdump` | 唯一可执行文件（OHOS 侧已自签名） |
| `share/rfdump/rfdump.ui` | GtkBuilder 界面（由 libglade `.glade` 转换而来） |
| `share/rfdump/rfd_types.xml`、`rfd.dtd`、`mifare.txt`、`rfdump.png`、`rfdump.xpm` | 运行期数据 |
| `share/applications/rfdump.desktop`、`share/pixmaps/rfdump.png` | 桌面集成（`Icon=rfdump`，全部落在 `$prefix` 内） |

## 依赖决策
| 包 | 版本 | 说明 |
|----|------|------|
| gtk | 3.24.43 | ohpcd 已发布 shared 二进制；**只开 broadway 后端**（`-Dx11_backend=false -Dwayland_backend=false -Dbroadway_backend=true`），正好对应鸿蒙无原生显示系统 |
| expat | 2.8.2.1 | `src/xml.c` 直接用 `XML_ParserCreate`；`gtk+-3.0.pc` 不携带它，故显式声明并注入 flags（版本与 gtk 闭包中 fontconfig 的 pin 一致，否则 conan 图报版本冲突） |

上游 `configure.in` 探测的是 `gtk+-2.0 >= 2.4.0` + `libglade-2.0 >= 2.4.0`：
制品仓**两者都不存在**（`conan list -r=ohpcd "gtk/*"` 只有 3.24.x；`libglade` 0 命中）。
ohpcd 的 GTK3 是唯一可用图形栈，因此走 GTK3 移植而不是引入 GTK2。

## 6 个补丁（`patches/`，strip=0）

| # | 文件 | 类型 | 内容 |
|---|------|------|------|
| 0001 | `port-gtk2-to-gtk3-builder.patch` | portability | libglade → GtkBuilder / GTK2 → GTK3（改编自 Arch Linux `drop-libglade.patch`，同一份也被 Debian 收为 `05_gtk3.patch`）；删除 `rfdump.glade`/`rfdump.gladep`，新增 `rfdump.ui` |
| 0002 | `modern-toolchain-fixes.patch` | portability | clang 15：`error_dialog()` 的 `-Wformat-security` 清理 + 去掉 `callbacks.c` 里与 `main.h` 重复定义的全局量（GCC10 `-fno-common`） |
| 0003 | `packaging-paths.patch` | portability | `pixmapdir` 收到 `$(prefix)` 内；`.desktop` 去掉 `Encoding`、`Icon=rfdump`、补 `Keywords` |
| 0004 | `shipped-autotools-gtk3.patch` | portability | 把发布包**自带的生成产物**改到与移植后的 `configure.in`/`src/Makefile.am` 一致（gtk+-3.0 探测、去掉 libglade 探测、`GTK2_*`→`GTK3_*`、去掉 perl 改写 CFLAGS 的块、剥掉 HMDFS 不能写的 `umask 077`、同步 `config.status` 替换计数 84→82） |
| 0005 | `ohos-runtime-paths.patch` | portability | 可重定位数据查找（`<bin>/../share/rfdump/<file>` 优先）+ `/var/lock` 不存在时串口锁降级为提示后继续 |
| 0006 | `headless-cli-and-reader-probe.patch` | test | `--version`/`--help` 在 `gtk_init` 之前回答；新增 `--probe-reader`（不开窗跑 GtkBuilder 资源 + expat 设备表 + termios 串口 bring-up，按失败类别返回不同退出码） |

> `strip: 0` 是刻意的：本补丁集含「新增 `src/rfdump.ui`」与「删除 `rfdump.glade`/`rfdump.gladep`」
> 两种形态，而 conan 的 `patch_ng` 对新增/删除分支会先 `decode_clean` 掉 `a/`/`b/` 前缀、再按
> `strip` 二次剥路径（`strip: 1` 会把 `src/` 一并剥掉）；`strip: 0` 三种形态都正确（同仓库
> altermime 先例）。

## 遇到的问题与解决方案（全部实测）

| # | 现象 | 根因 | 解决 |
|---|------|------|------|
| 1 | `configure: error: cannot run C compiled programs`（conftest 是空的 `int main(){}`） | 设备用 lld 链接，**lld 不像 GNU ld 默认 `--as-needed`**：我注入的 `-lexpat` 即使 conftest 从不调用也会留下 `DT_NEEDED`，运行时找不到 `libexpat.so.1` → 程序"编出来了但跑不起来" | `generate()` 把每个 host 依赖的 `libdir` 前置进 `LD_LIBRARY_PATH`，configure 期间可解析 |
| 2 | `configure: error: could not make ./config.status` | autoconf 2.61 把「替换行数」硬编码进 `config.status` 生成循环；我删掉 2 行 `LIBGLADE_*` 后行数 82 ≠ 字面量 84，重试 6 次后报错 | 补丁里同步把字面量改成 82（按 heredoc 行数计算并断言） |
| 3 | `config.status: error: could not setup config files machinery`（`./confXXXXXX/subs1.awk: Permission denied`） | `make` 触发 2008 maintainer 规则，设备上的 autoconf 2.73 重写 `configure`，把 `umask 077` 的 AS_TMPDIR 又带回来；HMDFS 上这种目录落盘后不能写 | `build()` 在补丁后给 `aclocal.m4/configure/config.h.in/Makefile.in/src/Makefile.in` 盖章（`os.utime`），声明生成产物为准，不重生成 |
| 4 | 运行期 `did not find rfd_types.xml` | 我第一版把可重定位查找插在 `return 0;` 之后（不可达） | 把查找移到候选循环之前，并加 `PROBE tagtypes=N` 断言（实测 26） |
| 5 | 上游串口 bring-up 在 `/var/lock/LCK..ttyUSB0` 上失败 | HarmonyOS 根目录没有 `/var`（实测 `ls -ld /var` → No such file or directory） | 锁目录不存在时打印一行可 grep 的提示后继续，失败点回到真正缺失的设备节点 |
| 6 | GUI 在 broadway 后端 abort | `GtkTreeView` 触发 `infinite surface size not supported`，随后 `_gdk_broadway_server_window_update: assertion failed: (data != NULL)`；同后端最小 GTK3 程序正常 ⇒ rfdump 控件树专有 | 不修控件树，GUI 交付到编译/链接/资源加载级并登记为已知限制；串口/设备表路径改由 `--probe-reader` 覆盖 |

## 验证结果

```bash
# 依赖硬门禁（R35：用 conan install 而不是 conan list）
conan install --requires=gtk/3.24.43 --requires=expat/2.8.2.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=never
#   → 20 个包全部 Already installed（含 gtk/3.24.43）

# 配方端到端
conan create archives/r/rfdump/1.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
#   → rc=0；HMBS_TEST_PACKAGE_RESULT {"discovered":19,"passed":19}

# 无头 reader 探测（broadway 提供显示连接；本机无串口硬件）
GDK_BACKEND=broadway BROADWAY_DISPLAY=:7 <pkg>/bin/rfdump --probe-reader -p /dev/ttyUSB0
#   PROBE ui=OK widgets=5/5 file=<pkg>/bin/../share/rfdump/rfdump.ui
#   PROBE tagtypes=26
#   PROBE serial_device=/dev/ttyUSB0 fd=-1
#   PROBE reader=ABSENT
#   PROBE device_node=MISSING           → 退出码 5
#   stderr: lockfile directory unavailable ... / using serial device ... / Unable to connect ...
```

## 上游测试清点（R51 三步法）

上游 **N = 0**（清点证据）：
- `find -iname '*test*' -o -iname 'check*'` → **0 命中**（源码树只有 `src/` 一个子目录）
- 全树 `Makefile.am`（2 个）grep `TESTS|check_PROGRAMS|XFAIL` → **0 命中**
- prescan 报告 `有测试: False`
- `make check` 实测 **rc=0** 且 `make[1]: Nothing to be done for 'check'.`

故上游表 TOTAL = 0（PASS 0 / FAIL 0 / SKIP 0 / NOT_RUN 0），**不是**"未运行"伪装。
鸿蒙侧新增 19 条消费者断言**分栏**统计（见 `test_package/MANIFEST.yml`），不并入上游分母。

## 已知限制
- **GUI 无法在鸿蒙 broadway 后端运行**（问题 6）：主窗口 `GtkTreeView` 让 broadway 后端
  断言 abort。同后端的最小 GTK3 程序可正常运行，说明后端本身可用、问题在 rfdump 的控件树
  （`.ui` 仅加载并 show 即复现，与 rfdump 的 C 代码无关）。GUI 交付到编译/链接/资源加载级。
- **本机无串口设备节点**（`/dev/ttyUSB0`、`/dev/ttyS0`、`/dev/input` 全部 ABSENT，仅
  `/dev/tty` 存在），RFID 读写只能验证到确定性降级路径（`--probe-reader` 退出码 5）。
- `share/rfdump/rfdump.xpm` 在 GTK3 下无 XPM loader（`gdk-pixbuf` 未带 loader），
  启动时打 `Could not load image` 警告；不影响 `rfdump.ui` 与数据加载。
- `ENABLE_NLS` 未被 configure 定义（`config.h` 0 命中），prescan 的 NLS 提示为惰性分支。
