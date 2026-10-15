# fox 1.6.57 适配笔记

## 上游信息

| 项 | 值 |
|----|----|
| 上游 | FOX Toolkit（C++ GUI 工具包） |
| 官网 | https://www.fox-toolkit.org/ |
| 版本 | 1.6.57（2018-07-25 发布） |
| 构建系统 | autotools |
| 许可 | LGPL-2.1-or-later |
| 源码 | https://cdn.netbsd.org/pub/pkgsrc/distfiles/fox-1.6.57.tar.gz |
| sha256 | 65ef15de9e0f3a396dc36d9ea29c158b78fad47f7184780357b929c94d458923 |

选源说明：官网 fox-toolkit.org 只提供明文 http，且实测下载被截断（curl rc=18、gzip 校验失败）；
官方站 https 证书不可用；GitHub 上只有非官方镜像（R39 不允许）。最终采用 NetBSD 官方
pkgsrc distfiles 镜像（cdn.netbsd.org / ftp.netbsd.org）与 mirrorservice.org 镜像，三个源
sha256 完全一致（`65ef15de9e0f3a396dc36d9ea29c158b78fad47f7184780357b929c94d458923`，
4284018 字节，gzip 完整性实测通过），均为权威镜像。

版本口径：本包按依赖任务口径取 **1.6.57**。rezound 0.13.1beta 的
`src/frontend_fox/fox_compat.h` 兼容上限锁在 1.6 系（`REZ_FOX_VERSION<=10600`），1.6.57 满足该约束。
（注：1.6 系并非止于 1.6.57，1.6.58/1.6.59 同样存在；选择 1.6.57 是任务口径，非"末版"推断。）

## 依赖

FOX 自身不依赖其他未适配库，全部依赖均已发布在制品仓：

| 依赖 | 版本 | 说明 |
|------|------|------|
| libx11 | 6.4.0 | X11 客户端库（挂历史栈，见下） |
| libxext | 6.4.0.1 | X 扩展库 |
| xorgproto | 2025.1 | X 协议头 |
| libpng | 1.6.58 | PNG（`--with-png` 自动探测命中） |
| libjpeg-turbo | 3.2.0 | JPEG（`--with-jpeg` 自动探测命中） |
| libtiff | 4.7.2 | TIFF（`--with-tiff` 自动探测命中） |
| zlib | 1.3.1.1 | 与 libpng/1.6.58 锁定值对齐，避免图中出现两个 zlib |
| bzip2 | 1.0.8 | bz2（`--with-bz2lib` 自动探测命中） |

**X11 栈版本取向**：现代栈（libxft/2.3.9 一族）锁 `libx11/1.8.13`，但其配套
`libxext/1.3.7` 在制品仓缺失（远端策略拒绝），因此 FOX 挂 6.4.0 版 libx11/libxext
历史栈（该栈已在制品仓发布）。Xft 相关可选能力以 `--without-*` 显式关闭，配方与
该栈保持一致，不引入版本分叉。

## 补丁清单

| 补丁 | 作用 | 理由 |
|------|------|------|
| `0001-config.sub-linux-ohos.patch` | 让 `config.sub` 接受 `aarch64-linux-ohos` | FOX 1.6.57 的 `config.sub` 为 2017-08-15 快照，不认识 ohos 三元组；仓库通用脚本 `patch-autotools-ohos.pl` 的锚点（`__ANDROID__`/`LIBC=android`）在本包不存在，故手写最小补丁（实测输出 `patched`） |
| `0002-configure-umask-hmdfs.patch` | `configure` 内 `umask 077` → `022` | 鸿蒙 HMDFS 会把 `umask 077` 建出的临时目录归一化为 `drwx--S---`（owner 为 file_manager，构建进程仅同组无 x 位），导致 `subs1.awk: Permission denied`；依据知识库 E011 |
| `0003-thread-cancellation-musl.patch` | `FXThread.cpp` 提供 pthread 线程取消最小兼容层 | OHOS musl 不实现 `pthread_cancel`/`pthread_setcancelstate`/`pthread_setcanceltype`（`pthread.h` 零处声明）。FOX 仅在 `FXThread::cancel()` 与 `~FXThread()` 使用；FOX 与 rezound 均未调用 `cancel()`，属死代码路径，故兼容层仅做最小 shim（不做替换语义） |

补丁中不含平台宏（R8），改动均为平台无关的真实逻辑。

## 交叉编译关键决策

1. **不使用 `AutotoolsDeps`**（OHOS 下的既有模式，参照 `archives/l/libx11/6.4.0`）：
   `AutotoolsDeps` 会把全部传递依赖塞进 `LIBS`，使 configure 的探测程序带上无法加载的
   `.so`，在本机 `--build`/`--host` 同三元组场景下退出码 127，configure 误判"编译器不可用"。
   改为自行注入 `CPPFLAGS/LDFLAGS/LD_LIBRARY_PATH`。
2. **头文件路径必须走 `CPPFLAGS`**：`configure.ac:60` 直接 `CXXFLAGS=""` 清空用户 CXXFLAGS，
   因此 `-I` 只能通过 `CPPFLAGS` 传递（已验证生效：`HAVE_JPEG/PNG/TIFF/ZLIB/BZ2LIB/XSHM/XSHAPE` 全为 1）。
3. **X11 探测需要单目录聚合前缀**：`configure.ac:82` 使用 `AC_PATH_X`/`AC_PATH_XTRA`，
   两者只接受一个 `--x-includes` 和一个 `--x-libraries` 目录，否则仅搜索固定系统路径，
   conan 缓存里的 X11 栈对其不可见（表现为链接期回落 Windows 默认库 `-lcomctl32`）。
   故 `generate()` 在 `build_folder/deps-prefix` 下建立**私有聚合前缀**（仅符号链接，
   不写任何共享系统目录），供 `--x-includes/--x-libraries` 与 `-I/-L` 使用。
4. **`-L` 走环境变量注入**：`AutotoolsToolchain.extra_ldflags` 实测未落到生成的
   toolchain 脚本中（脚本内 `-L` 计数为 0），改用 `Environment.append("LDFLAGS", ...)`，
   与已验证有效的 `CPPFLAGS` 同一通道。
5. **关闭可选 X 扩展与 OpenGL**：Xft/Xcursor/Xrender/Xrandr/Xfixes/Xinput/OpenGL
   全部 `--without-*`，使依赖闭包收敛到已发布的 6.4.0 X11 栈。

## 上游测试清点与实测（R51）

**上游测试清点**：`tests/Makefile.am` 只有 `noinst_PROGRAMS`，没有 `TESTS` 或
`check_PROGRAMS` 目标，顶层 `Makefile.am` 的 `SUBDIRS` 虽含 `tests`，但 `make check`
实际不会执行任何上游用例（上游无自动化测试集）。

**本次实测**：`conan create` 全流程通过（编译 + 打包 + test_package），test_package
提供两项鸿蒙侧消费者测试：

| 测试 | 内容 | 结果 |
|------|------|------|
| `test_fox`（C++ 消费者程序） | 交叉编译为 **目标架构 aarch64** 的消费者程序：链接包内 `libFOX-1.6`，调用 `fxversion[3]` 校验版本、用 `FXString` 做追加/拼接并核对结果 | 通过 |
| `reswrap` 实跑 | 运行包内 `bin/reswrap`（上游资源编译器）编译样本资源，校验生成数组名与逐字节内容 | 通过 |

`reswrap` 校验按实际输出格式判定：reswrap 以十六进制字节数组形式输出（每 16 字节换行），
故比对时先去掉换行/空格再逐字节匹配，避免以字面文本误导判定。

## 产物

- `lib/libFOX-1.6.so{,.0,.0.0.57}`、`lib/libCHART-1.6.so{,.0,.0.0.57}`
- `bin/reswrap`（资源编译器）、`bin/fox-config`（构建助手）
- `include/fox-1.6/`、`lib/pkgconfig/fox.pc`
- 上游默认还安装了示例程序（`adie`/`calculator`/`shutterbug`/`PathFinder` 等），保持上游 install 原样

## GUI 路径与适配完整性说明（R40）

FOX 属 UI 工具包，但窗口与输入事件并不由 FOX 自己实现，而是**全部委托给 X11 客户端库**
（`libX11`/`libXext`，本包依赖的制品仓已发布版本 6.4.0）。本包的适配工作是让 FOX 正确
链接并使用该 OHOS X11 栈（见上文"交叉编译关键决策"第 1、3、4 条），不涉及 stub 或
`return 0` 式的假适配。

如实披露的已知限制：

- 无显示环境（`DISPLAY` 为空）下无法验证窗口创建/事件循环路径；因此本包的
  test_package 只覆盖**不依赖 X display** 的两条真实路径（库链接 + 公共 API、
  随包命令行工具 `reswrap` 实跑）。
- 随包附带的上游 GUI 示例程序（`adie`/`calculator`/`shutterbug`/`PathFinder`）在无
  显示的 CI 环境中无法产生可观测行为，故未纳入自动化测试（与上游 `make check` 为空
  操作一致）。
- 上机（有 X 会话）验收建议：``DISPLAY=:0 fox-config --libs`` 后用上游示例程序
  `adie` 打开主窗口，确认窗口与事件正常。
---

**编译结束**: 2026-10-14 16:05
**最终状态**: built

---

## 补丁生成方式（R3 例外说明）

三个补丁均为**手写最小补丁**，未走 `refresh-patch --auto`。原因：仓库通用脚本
`patch-autotools-ohos.pl` 依赖 `config.guess` 中的 `__ANDROID__`/`LIBC=android` 锚点，
而 FOX 1.6.57 的 `config.sub` 为 2017-08-15 快照，无该锚点（脚本实测输出
`[warn] Could not find __ANDROID__/LIBC=android in config.guess`）。0002/0003 分别为
`configure` 内 `umask` 与 musl 线程取消能力探测，均无自动生成路径。补丁 hunk 计数已逐个复核，
`patch -p1` 实跑应用成功（见 `reports/conan-create.log`）。
