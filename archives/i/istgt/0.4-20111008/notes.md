# istgt 0.4-20111008 — 适配笔记

## 源码
- 上游项目站点（shell.peach.ne.jp）已消亡，SourceForge 项目页反爬（403）。
  本版本权威源码归档取 **Debian pool 的 orig tarball**（未经 Debian 修改的
  上游原件；md5 `f9a685851e127f018502a07181d7799e` 与 Debian 发布的 .dsc
  元数据一致，与 lice 4.2.5i（任务 #8456）先例同口径）。
- URL: https://ftp.debian.org/debian/pool/main/i/istgt/istgt_0.4~20111008.orig.tar.gz
- sha256: 41ddc49dbd0cda81c3f7557e76d27b851e042a32acb448dac1b743c759b0b37e
- HTTP 200 已实测（http 与 https 均 200，sha256 相同）
- tarball 顶层目录 `istgt-20111008`（recipe 用 strip_root=True）

## 构建
- 2011 年预生成 configure（autoconf 2.62 世代）随 tarball 分发，无需 autogen。
- **in-source 构建**（`folders.build = ""`，quagga 1.2.4 同法）：src/Makefile.in
  用 .SUFFIXES 后缀规则（.c.o），后缀规则不查 VPATH，out-of-tree 时
  `No rule to make target 'istgt.c'`（W3 第 1 轮实测）；in-source 同时规避
  CI worker 的 HMDFS getcwd 风暴（E386）。
- configure.in **无 AC_CANONICAL_HOST** → 不运行 config.guess/config.sub，
  无需 E007 补丁（与 icecast 2.4.4 的关键差异）。
- 外部依赖仅 libcrypto：`AC_CHECK_LIB([crypto], [MD5_Update])`。house 规则
  （本仓 AutotoolsToolchain 不聚合依赖 cpp_info，先例 callisto/rawtran）→
  generate() 显式注入 openssl 的 `-L/-I`，并以 `-Wl,-rpath` 嵌入依赖 libdir
  （L2 smoke 裸跑无 LD_LIBRARY_PATH，先例 icecast）。
- openssl 固定 **1.1.1w**：src/istgt_md5.c 使用经典 MD5_Init/MD5_Update/
  MD5_Final 底层 API（3.x deprecated 但保留，4.0 移除）。与 Debian 包 istgt
  对 libssl1.1 的依赖世代一致。
- `AC_CHECK_LIB([cam])`（FreeBSD CAM API）在 OHOS 缺失，可选依赖，由生成
  config.h 的 HAVE_LIB_CAM 守卫。
- `AC_PATH_PROG(MKDEP, "mkdep")` 在 OHOS 为空；src/Makefile.in 第 100 行
  `if [ "x$(MKDEP)" != "x" ]` 已守卫，依赖生成安全跳过。
- pthread 符号在 OHOS musl 下由 libc 直接提供；AC_CHECK_LIB([pthread])
  探测失败时 LIBS 不加 -lpthread，链接不受影响。
- **-fcommon**：头文件以 tentative definition（无 extern）声明共享全局
  （ISTGT_LU_TASK_RESULT/ISTGT_LU_TASK_TYPE 等），每个包含该头的 .c 各出
  一份强符号；老 GCC 默认 -fcommon 由链接器合并 COMMON 符号，OHOS clang 15
  默认 -fno-common → ld.lld duplicate symbol（W3 第 2 轮实测）→ CFLAGS
  追加 -fcommon（quagga 1.2.4 同因同法；仅编译选项，不改源码）。

## 补丁
- `patches/0001-src-istgt_iscsi.c-pthread-cancel-fallback.patch`（唯一补丁，
  **纯特性宏、不含平台宏**）：引入 `HAVE_PTHREAD_CANCEL`（缺省 1 = 上游原行为），
  把 `src/istgt_iscsi.c` 的 5 处取消点调用改为间接层：1×
  `ISTGT_SETCANCELSTATE()` + 2× `ISTGT_TESTCANCEL()` + 2×
  `ISTGT_CANCEL_THREAD()`。配方对 OHOS 传 `-DHAVE_PTHREAD_CANCEL=0`。
- 缺口实测（OHOS SDK sysroot，aarch64-linux-ohos clang 15）：`<pthread.h>`
  **不声明**、`libc.so` **不导出** `pthread_cancel` / `pthread_setcancelstate` /
  `pthread_testcancel`（最小链接探针复现 3 个 undefined symbol）；
  `PTHREAD_CANCEL_ENABLE` 常量仍由头文件提供。
- 语义（策略 S1，同 house 先例 xmcd 3.3.2 / 知识条目
  `knowledge/drafts/musl-pthread-cancel-gap/`）：
  * `setcancelstate` 只是取消配置，无取消能力时无事可做；
  * `testcancel` 两个调用点其后**紧接着**重新检查 `conn->state != CONN_STATE_RUNNING`
    即退出，协作式退出路径不受影响；
  * `pthread_cancel(xconn->thread)` 是**升级路径**：调用前目标连接早已置
    `CONN_STATE_EXITING` 并 `istgt_yield()+sleep(1)` 让对端自行退出，仅当
    `num > max_conns + 1` 才强杀。跳过该请求后连接仍走正常 worker 清理收线。
- 未采用（知识库明令禁止）：`-lpthread`（空壳库）、弱符号空 stub、只补声明。

## 测试
- 上游无自动化测试套件（Makefile.in 无 TESTS/make check 目标）。
- build() 末尾 `_smoke()`：直接执行 in-tree aarch64 二进制（WSL binfmt
  qemu），`istgt -V`（0.4/20111008）+ `istgtcontrol -V`（CI L1c 口径）。
- test_package/test_istgt.py 15 项断言：A 包布局 8 项 + B 命令行契约 3 项 +
  C 守护进程端到端 4 项（最小配置 `istgt -D` 启动，uctl 控制端口 38261 与
  iSCSI 数据 portal 38262 双监听；`istgtcontrol noop` uctl 往返 rc=0；
  `istgtcontrol version` 经控制协议取回 daemon 版本；SIGTERM 10s 内干净退出）。
  口径同 icecast「启动服务 + 请求状态页」先例（CI 无 iSCSI initiator 可用）。

## 验证

### 本地交叉编译（WSL 原生盘，非 /mnt）

工作目录 `/root/ohpcd-work/build/istgt-0.4-20111008`（ext4），conan 缓存
`/root/.conan2`（盘内已有 1000+ 包）：

```
conan create . -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

工具链：`/opt/lpk-fixed/clang`（OHOS SDK clang 15，`--target=aarch64-linux-ohos`
+ OHOS sysroot，emulate CI 的 `/data/service/hnp/bin/clang`）。

**结果：`CONAN_CREATE_EXIT=0`**

- 编译链接：`make` rc=0，`ld.lld` 无 undefined symbol（补丁 + `-DHAVE_PTHREAD_CANCEL=0`
  生效，此前 3 个 pthread 取消族符号已消失）。
- `build()` 内 `_smoke()`：
  `istgt make check: istgt -V rc=0, version 0.4/20111008 OK`；
  `istgt make check: istgtcontrol -V rc=0 OK`。
- `test_package`：`CHECK_SUMMARY checks=15 passed=15 failed=0`
  （A 包布局 8 + B 命令行契约 3 + C 守护进程端到端 4）。
  端到端实测：`istgt -D` 最小配置下 uctl 38261 与 iSCSI portal 38262 **双监听**；
  `istgtcontrol noop` 往返 rc=0；`istgtcontrol version` 经控制协议回读
  0.4/20111008；SIGTERM 10s 内干净退出 rc=0。
- 产物：`bin/istgt`（319712 B）、`bin/istgtcontrol`（53040 B）、
  `man/man1/istgt.1.gz`、`etc/istgt/*.sample`（4）、`etc/rc.d/istgt`、
  `lib/pkgconfig/istgt.pc`、`licenses/COPYRIGHT`。

### 本地运行期的环境侧处置（pitfall T017；shim 不进配方）

本机执行 aarch64 产物靠 `binfmt_misc` + `/opt/ohos-guest`（**stock musl**）。
该 guest libc **不导出 `arc4random`**，而 OHOS SDK 的 libc 导出它（链接成功即为证），
故本地首跑报：

```
Error relocating .../src/istgt: arc4random: symbol not found   (rc=127)
```

处置：**只在环境侧**预载已有 shim，配方/补丁/测试脚本一律不动：

```
LD_PRELOAD=/opt/ohos-guest/lib/libarc4shim.so conan create . -pr:h=... -pr:b=...
```

- 宿主 x86 侧刷 `ERROR: ld.so: object ... cannot be preloaded ... ignored`
  属**正常噪声**（aarch64 shim 对 x86 ld.so 不可用），不是失败。
- 自检（T017 口径）：`grep -rn 'arc4shim\|LD_PRELOAD\|preload' archives/i/istgt/`
  → 命中项**仅为本节 notes.md 自身的说明文字**（T017 明确允许「只命中 notes.md
  的说明文字」）。`conanfile.py`、`patches/`、`test_package/` 三个交付物
  **零命中**，即配方与测试脚本内不含任何 shim / LD_PRELOAD / 绝对路径。
  （按 T017：命中 conanfile.py 才是 P1。）
- CI 在真机 OHOS 上跑，libc 自带 `arc4random`，无需 shim。

### 已知边界

- 补丁把 `pthread_cancel` 的跨线程强杀降级为「跳过」：连接在此前已被置
  `CONN_STATE_EXITING` 并 `yield+sleep(1)` 等待自行退出，故协作式收线不受影响；
  仅在 `num > max_conns + 1` 的异常堆积场景下少了最后的强杀兜底。
- upstream 无自动化测试套件，故无 `make check`；`MANIFEST.yml` 已如实申报
  `upstream_test_in_build: false`，验证靠 `test_package` 的 15 项实质断言。

### CI 环境侧事故：make install 静默空转（2026-10-16，CI #94783）

现象：`conan create` 编译与 `_smoke()` 全过，但 `package()` 后包内**只有**
`licenses/COPYRIGHT` 与 `lib/pkgconfig/istgt.pc`，test_package 的 A1~A4、A7、A8
全部 FAIL（`bin/istgt`、`bin/istgtcontrol`、man 页、`etc/istgt/*.sample` 均缺失）。

日志证据（CI #94783，2026-10-16 14:09）：

```
istgt/0.4-20111008: RUN: make install DESTDIR=<pkg> -j20
make: jobserver mkfifo: /storage/Users/currentUser/.cache/tmp/GMfifo63421: Operation not permitted
make: 'install' is up to date.
istgt/0.4-20111008: package(): Packaged 1 file: COPYRIGHT
istgt/0.4-20111008: package(): Packaged 1 '.pc' file: istgt.pc
```

根因：`autotools.install()` 未指定 jobs，沿用 `tools.build:jobs`（worker 上为
`-j20`）。`-j>1` 时 GNU make 需要创建 jobserver fifo，而该 worker 禁止此操作；
make 在 fifo 创建失败后直接把 `install` 当作**已完成**，于是静默什么都不装——
配方侧看不到任何错误码，属于「静默成功产出空壳包」，比明确失败更危险。

处置（两条一起做）：

1. `autotools.install(args=["-j1"])`：串行安装不创建 jobserver fifo，避开该陷阱。
   同 house 先例 `meterec/0.9.3` 的 `autotools.install(args=["-j1"])`（其 CI #94782
   已在该 worker 上通过）；build() 侧本配方原就使用 `autotools.make(args=["-j1"])`，
   本次是把同一处置补齐到 install。
2. `package()` 内新增安装产物兜底断言：`bin/istgt`、`bin/istgtcontrol`、
   `etc/istgt/istgt.conf.sample`、`etc/istgt/auth.conf.sample` 以及
   `man/man1/istgt.1(.gz)` 任一缺失即当场 `RuntimeError`，不再产出残缺包。

本地（jobserver 可用的 WSL）对照：同一配方产出的包内容为
`bin/istgt`(319,712 B)、`bin/istgtcontrol`(53,040 B)、`etc/istgt/{istgt,auth,istgt.large,istgtcontrol}.conf.sample`、
`etc/rc.d/istgt`、`man/man1/istgt.1.gz`、`lib/pkgconfig/istgt.pc`、`licenses/COPYRIGHT`
——即第 2 条断言在正常环境不会被误触发。该差异也解释了为何本地验证发现不了此问题。

### 二次修：顶层 `make install` 被判 up to date（2026-10-16，CI #94874）

上一轮把 `autotools.install()` 换成 `args=["-j1"]` 后，worker 上的输出变成：

```
istgt/0.4-20111008: RUN: make install DESTDIR=<pkg> -j1
make: 'install' is up to date.
```

即 jobserver 的报错没有了，但 install **依然一个文件都没装**，上一轮加的兜底断言直接
当场失败（`make install did not install bin/istgt`）——断言按设计工作了。

根因：上游 tarball 自带大写 `INSTALL` 文本文件，而顶层 Makefile 的目标名是小写
`install`。worker 的 `/storage`（HMDFS）大小写不敏感，make 于是把 `install` 当成
**已存在的文件目标**（它无任何依赖）⇒ 判定 "up to date"、不执行 for 循环 recipe。
本地 ext4 区分大小写，因此这个现象**只在 worker 上出现**（本地 `make install` 正常）。

处置：不再使用顶层 install 目标，改为显式逐子目录安装：

```python
for _sub in ("src", "etc", "doc"):
    self.run('make -C "%s" -j1 install DESTDIR="%s"' % (_sub, self.package_folder),
             cwd=self.build_folder)
```

三个子目录的 `install` 规则都真实存在且 honor `DESTDIR`，本地实测 rc=0、产出与断言
要求的完全一致：`bin/istgt`、`bin/istgtcontrol`、`etc/istgt/{istgt,auth,istgt.large,
istgtcontrol}.conf.sample`、`etc/rc.d/istgt`、`man/man1/istgt.1.gz`。`-j1` 保留，
用于规避同一 worker 上并行 make 的 jobserver fifo 限制（CI #94783）。
