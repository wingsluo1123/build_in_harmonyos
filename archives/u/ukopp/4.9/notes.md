# ukopp 4.9 适配笔记

## 编译环境
- 构建系统: makefile（上游 2014 年裸 Makefile，非 autotools）
- 编译日期: 2026-10-16
- 编译器: clang/clang++ 15（OpenHarmony SDK llvm，交叉三元组
  `aarch64-linux-ohos`）
- 状态: built

## 软件概况

ukopp — disk-to-disk backup（作者 Michael Cornelison，kornelix.com）：

- 单二进制 `ukopp`（bin/）：把挂载磁盘或目录的文件复制到另一磁盘/
  目录（"备份盘"）。全量/增量备份、备份后校验、按天/周/月保留旧版本
  （过期清理）、文件报告/查找、恢复任务（按文件/目录/版本）。
- GTK3 GUI 为主界面（菜单 + 工具栏 + 日志窗）；另有无 GUI 命令行模式：
  `ukopp -nogui`（输出到 STDOUT）、`-job jobfile`（载入任务）、
  `-run jobfile`（载入并立即执行）——适合脚本化/计划任务。
- zfuncs.cc/h：kornelix 系工具共用的小部件与工具函数库（GTK3 C API）。
- data/（用户手册 userguide-en.html + 图像）与 icons/ 供 GUI 运行时读取。

## 编译步骤

```bash
# 交叉编译（WSL，host=OHOS/armv8/clang15/libc++/cppstd17，build=x86_64 Linux）
cd /root/ohpcd-work/build/ukopp-4.9
conan create /root/ohpcd-work/wt-ukopp/archives/u/ukopp/4.9 \
    -pr:h ohos-aarch64-wsl-xbuild -pr:b default --build=missing
```

1. 配方 `source()` 拉 Debian 官方打包归档（上游 kornelix.com 分发的
   同一 orig tarball）
2. `generate()` 出 `PkgConfigDeps`（gtk+-3.0.pc / glib-2.0.pc 等，指向
   本机 conan 缓存绝对路径）+ 显式注入 `PKG_CONFIG_PATH`
   （`conanbuild_pkgconfig` 环境脚本）
3. `build()` 先 `apply_conandata_patches()`（patches/0001：C++11 UDL
   空格修复，见"源码修改"），再跑上游 Makefile 默认目标
   （in-source 编译 ukopp-4.9.cc + zfuncs.cc，链接
   `pkg-config --libs gtk+-3.0 -lpthread`），
   `make -j1 SHELL=/bin/sh CXX=<conf 里的编译器>`（R9：HMDFS 不允许
   jobserver FIFO；R33：编译器从 conf 获取）
4. `package()` 手工布局产物（上游 `make install` 依赖 xdg-desktop-menu，
   OHOS 无此工具，不能直接跑）：`bin/ukopp`、
   `share/ukopp/{data,icons}`、`share/doc/ukopp`、
   `share/man/man1/ukopp.1`、`share/applications/ukopp.desktop`、
   `licenses/copyright`
5. `test_package/` 用 `sh test_ukopp.sh <ukopp-bin>` 跑 7 个断言
   （分层探针 + `-nogui` 真实运行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 直接 `make` 用 g++（WSL 有 g++，编出来是 x86_64 二进制） | Makefile 未定义 CXX，make 缺省 g++ | make 命令行传 `CXX=<conf tools.build:compiler_executables 的 cpp>`（R33；bart-view 同款） |
| 2 | `pkg-config --cflags/--libs gtk+-3.0` 找不到或解析到错误路径 | gtk 包自带 .pc 的 prefix 是 CI worker 路径（/storage/...），本地不存在；PkgConfigDeps 生成的 .pc 才是本机 conan 缓存绝对路径 | `PkgConfigDeps(self).generate()` + 显式 `PKG_CONFIG_PATH=generators 目录`（`conanbuild_pkgconfig` 环境脚本；bart-view 同款） |
| 3 | 上游 `make install` 失败/不可用 | install 目标调用 `xdg-desktop-menu uninstall/install`（OHOS 无此工具），且 gzip/菜单逻辑与 conan 布局不合 | 不跑上游 install：package() 手工拷贝（bin/share/doc/man/desktop/licenses，与 Debian 包一致） |
| 4 | headless 运行 `ukopp -nogui` 拿不到 stdout 输出 | zfuncs `zinitapp()` 在 stdin 非 tty 时把 stdout/stderr `freopen` 到 `$HOME/.ukopp/logfile`（追加模式，v.5.7 行为） | 测试断言读 `$HOME/.ukopp/logfile`，不依赖 stdout |
| 5 | 无 `$HOME` 运行直接崩溃 | `zinitapp()` 用 `getenv("HOME")` 拼 `zuserdir` 并 mkdir；HOME 缺失时得到 `(null)/.ukopp` → mkdir 失败 → `zappcrash` | 测试提供全新可写 `$HOME`（mktemp -d） |
| 6 | 版本横幅断言在 root/非 root 下输出不同 | `initfunc()` 按 `getuid()` 分支：非 root 打印 `ukopp v.4.9` + 许可行（Help/about 路径）；root 打印 `you have root privileges` | 测试两分支都接受（qemu-user 下 getuid 透传宿主 uid；CI worker 同一脚本） |
| 7 | `-nogui` 仍可能拉起 GTK？ | 不会：`main()` 先解析 `-nogui` 置 `Fgui=0`，GUI 路径（gtk_init 等）在其后的分支里 | `-nogui` headless 安全，可作功能测试入口 |
| 8 | `make -j` 卡住/报 FIFO 权限 | E074：HMDFS 不允许创建 jobserver 管道 | `make -j1 SHELL=/bin/sh`（R9） |
| 9 | `ukopp-4.9.cc:1277` 编译报 `invalid suffix on literal; C++11 requires a space between literal and identifier [-Wreserved-user-defined-literal]` | `sscanf(pp2,RSEP1" %d , %d "RSEP2,...)`：close-quote 紧跟宏名 `RSEP2`，C++11 词法把它当用户自定义字面量后缀，宏不展开（2014 年源码，老 gcc gnu++98 时代合法） | `patches/0001-cxx11-udl-space.patch`：字面量与宏之间补一个空格（语义不变，恢复宏展开）；全源码扫描仅此一处 |

## 源码修改

`patches/0001-cxx11-udl-space.patch`（1 行，portability）：
`ukopp-4.9.cc:1277`（parse_retention）在字符串字面量 `" %d , %d "` 与
宏 `RSEP2` 之间补空格。C++11 起 close-quote 紧跟标识符被词法为 UDL
后缀（`-Wreserved-user-defined-literal`），clang 15 硬错误；加空格
恢复普通宏展开，拼接结果与语义完全不变。生成方式：对上游原始文件
`diff -u` 手工生成，`apply_conandata_patches()` 应用（marco 同款机制）。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| glib | 2.84.0.1 | zfuncs/ukopp 使用 GTK3 C API（transitive headers/libs，mednaffe 同款；版本须与 gtk/3.24.43 依赖闭包一致，marco 同款搭配） |
| gtk | 3.24.43 | GTK3 GUI + 命令行模式共用（pkg-config gtk+-3.0） |

## 验证结果

```bash
$ conan create ... -pr:h ohos-aarch64-wsl-xbuild -pr:b default --build=missing
# （见 build 输出：make -j1、pkg-config gtk+-3.0、包 ID）
$ file bin/ukopp
bin/ukopp: ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked
$ readelf -d bin/ukopp | grep NEEDED
  (NEEDED) libgtk-3.so.0 / libgdk-3.so.0 / libglib-2.0.so.0 / ...（GTK3 动态栈）
```

（运行时 ABI 见 test_package 验证记录；依赖按制品仓预编译二进制解析。）

`test_package`（R34 实质消费者测试）：7 断言。执行模型由
test_package/conanfile.py 按**产物 ELF 头**（e_machine）判定，不用 Conan
的 cross_building()（OHOS 交叉 profile 的 -pr:h/-pr:b 同文件，Conan 误报
host == build）：本机 WSL（x86_64）→ `qemu-aarch64 -L /opt/ohos-guest
-E LD_PRELOAD=/opt/ohos-guest/lib/libfdchkshim.so` 用户态仿真执行（shim
补 `__fd_chk`，musicpc/tasksh/array-hash/vimpc 同款）；CI 的 OHOS worker
上 ELF 与宿主同架构 → 原生直跑同一脚本。

```
$ sh test_package/test_ukopp.sh <pkg>/bin/ukopp
ok - A1 packaged binary exists and is executable
ok - A2 ELF64 AArch64 (e_machine=0xb7)
ok - A3 DT_NEEDED closure carries the GTK3 stack (N NEEDED entries)
ok - A4 ukopp -nogui exits rc=0
ok - A5 $HOME/.ukopp/logfile produced by zinitapp redirect
ok - A6 startup banner present in logfile
ok - A7 root-privileges notice reported (getuid()==0 branch)
1..7
# passed: 7
# failed: 0
```

覆盖：打包完整性（二进制存在/可执行）、目标架构正确（ELF64/AArch64）、
动态链接闭包（GTK3 栈 NEEDED）、真实功能运行（`-nogui` 全链路：
zinitapp 目录初始化 + stdout 重定向 + initfunc 设备探测 BDpoop + 干净
退出 rc=0）、输出重定向产物与启动横幅、版本/root 分支报告。

上游测试 0 项运行（Makefile 无 check/test 目标，tarball 无测试代码，
见 test_package/MANIFEST.yml）。

## 测试四维账本

| 维度 | 数量 | 说明 |
|------|------|------|
| 上游静态声明 N_static | 0 | Makefile 仅 ukopp/install/uninstall/clean 目标，无 check/test 钩子；tarball 无 tests/ 目录、无 *test* 源文件 |
| 实际执行 N_executed | 0 | 上游无测试可运行，配方未集成 |
| 跳过/未执行 | 0 | 上游无独立可执行测试（见 MANIFEST.yml note） |
| 新增消费者测试 N_consumer | 7 | test_package/test_ukopp.sh 7 断言（A1 存在/可执行、A2 ELF64 AArch64、A3 DT_NEEDED GTK3 栈、A4 rc=0、A5 logfile 产生、A6 启动横幅、A7 版本/root 分支） |

## 注意事项

- GUI 模式需要图形环境（GTK3）；headless/脚本场景用 `-nogui`
  （不调 gtk_init()）
- `zinitapp()` 在 stdin 非 tty 时把 stdout/stderr 重定向到
  `$HOME/.ukopp/logfile`（追加）；管道/重定向运行时输出在该文件，
  不在 stdout
- `$HOME` 必须设置且可写（应用启动即 mkdir `$HOME/.ukopp`，失败即
  zappcrash 退出）
- 编译期固化路径：`PREFIX=/usr`、`DOCDIR=/usr/share/doc/ukopp`
  （zfuncs -D PREFIX/-D DOCDIR，与 Debian 打包一致；仅影响 GUI 帮助
  文档定位）
- 备份/恢复操作需要目标设备/目录的写权限（GUI 下可用 root 按钮提权）
- 本包为 application：`cpp_info.bindirs=["bin"]`、`libs=[]`、
  `includedirs=[]`、`libdirs=[]`（单二进制，无公开链接接口）

**编译结束**: 2026-10-16
**最终状态**: built
