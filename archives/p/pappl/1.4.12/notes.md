# pappl 1.4.12 适配笔记（OHOS / aarch64）

PAPPL（Printer Application Framework）是 Michael R Sweet 开发的 CUPS Printer
Application 框架，内嵌 IPP Everywhere 打印服务：IPP 服务端/客户端、多队列
打印管理、PWG Raster/Apple Raster/RAW 输出、JPEG/PNG 过滤、DNS-SD 广告、
USB printer-class/gadget、SNMP 网络发现、内嵌 Web 管理界面与 TLS。

## 构建形态

- 上游自带已生成 `configure`（autoconf 2.70+，`config.h.in` 为手维护模板，
  禁止 autoheader）。Autotools + 手写 Makefile（`Makedefs` include 结构）。
- 本配方：`--disable-shared --enable-static` → `libpappl.a` + 11 个公共头
  （`include/pappl/`）+ `pappl.pc` + `share/pappl/`（Web UI 资源）。
- 三元组：显式 `--build/--host=aarch64-unknown-linux-gnu`（避开 config.guess
  的 `uname -s = HarmonyOS` 分支，同时让上游落入 Linux 代码路径）。
- `configure.ac` 增补后用上游钦定的 `autoconf -f` 重新生成 `configure`
  （设备取 harmonybrew autoconf 2.73，CI worker 取 SDK 自带 autoconf）。

## 依赖（全部来自制品仓）

| 依赖 | 用途 | 备注 |
| --- | --- | --- |
| cups/2.4.19 | libcups/libcupsimage（硬依赖） | 静态；pc 名 `cups` |
| openssl/3.5.6 | TLS（硬依赖） | 与 cups 同版本对齐 |
| avahi-compat-libdns_sd/0.9_rc5 | DNS-SD（HAVE_AVAHI 路径） | 自带 avahi-client/common 静态库 + dbus |
| libjpeg-turbo/3.2.0 | JPEG 过滤 | pc 名 `libjpeg` |
| libpng1.6/1.6.58 | PNG 过滤 | pc 名 `libpng`，上游探测 `libpng16` → shim |
| libusb/1.0.27 | USB 打印机类支持 | 上游探测 `libusb-1.0` → shim |

pkg-config shims（`generate()` 写出 `pkgconfig-shim/*.pc`）：
`libpng16.pc`/`libusb-1.0.pc`（名字映射，`Requires:` 传导 conan 生成的 pc）
与 `avahi-client.pc`（直指 avahi-compat-libdns_sd 包目录）。

## 关键平台问题与补丁

1. **0001 pthread 取消族**：OHOS musl 无 `pthread_cancel`/
   `pthread_setcancelstate`。`configure.ac` 增 `AC_CHECK_FUNCS`、`config.h.in`
   增两个 `#undef` 模板、`pappl/printer-usb.c` 四处调用点用特性宏守卫
   （E127 同款做法，cups 2.4.19 先例）。gadget 工作线程本来就在 printer
   deleted/system shutdown 时自退，跳过 cancel 不改变行为。
2. **0002 双重 detach 崩溃**：`papplSystemRun` 用 `PTHREAD_CREATE_DETACHED`
   的 attr 创建 raw-socket/USB 线程后又调 `pthread_detach()`。glibc 返回
   EINVAL 无害；OHOS musl 里第二次 detach 解引用失效线程状态直接 SIGSEGV
   （真机 cppcrash 回溯实证：`papplSystemRun` → `pthread_detach` →
   `pthread_join+88` SEGV@0）。删除两处冗余 detach。
3. **0003 mDNS 主机名不可解析**：`papplSystemSetHostName(system, NULL)` 给
   裸主机名补 `.local`（mDNS 惯例）→ `localhost.local`；无 mDNS 应答器的
   OHOS 上 jpeg/png 远程路径连不上（`Name does not resolve`）。testsuite
   的 `connect_to_printer` 失败时回退 loopback。
4. **configure 阶段两个环境坑**（非补丁，配方内处理）：
   - conftest 链接共享依赖（libexpat.so.1 等）→ 全部 host 依赖 libdir 进
     `LD_LIBRARY_PATH`（env script）。
   - autoconf `(umask 077 && mktemp -d ./confXXXXXX)` 在 HMDFS setgid 目录
     上炸 `config.status`（E011/E129）→ `autoconf -f` 之后把生成的
     configure 里两处 umask 077 改 022。
5. **TMPDIR**：统一指 `/data/storage/el2/base/cache/pappl`（libc 临时文件、
   测试 spool 目录都走 `papplGetTempDir()` = TMPDIR 可写才用）。

## 上游测试（build() 内实跑）

| 阶段 | 命令 | 内容 |
| --- | --- | --- |
| 1 | `make -C testsuite -j1 test` | 上游钦定 `test:` 目标：`testhttpmon` + `testpappl -t api,client,pwg-raster` |
| 2 | （CI 跳过 `-t all`） | 全类别加测（jpeg/png + client-10x1000 压力）本地已验证；CI 3600s 内 `make test`+`-t all` 跑不完，故 CI 只跑上游钦定的 `make test` |
| 3 | `./testmainloop --version` | papplMainloop CLI 冒烟 |

计数（`grep -c ': PASS'`）见 PR 正文；失败为 0。
运行期特性：DNS-SD 注册失败按设计降级为日志错误（"Daemon not running"），
测试不受影响；`client-10x1000` 压力类与 jpeg/png 图像打印在 0003 之后
全量通过。

## 运行边界（如实申报）

- USB gadget（configfs/functionfs/UDC、`/dev/g_printer0`）与 USB 打印机类
  需要真机 USB 设备控制器/真打印机，构建机没有；编译路径已全量启用
  （UAPI 头在 OHOS sysroot：`linux/usb/functionfs.h`、`linux/usb/g_printer.h`）。
- mDNS 广告需 avahi-daemon + D-Bus；无守护时注册 API 返回错误并记录日志。
