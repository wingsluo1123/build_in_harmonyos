# termbox2 2.5.0 适配笔记

## 编译环境

- 构建系统：GNU Make（上游 Makefile）
- 编译日期：2026-09-26
- 编译器：OHOS Clang 15.0.4，目标 `aarch64-unknown-linux-ohos`
- Conan：2.29+ OHOS 适配版
- 状态：built（本地 Conan、仓库门禁与 HarmonyOS PC 真机测试通过，未发布）

## 上游说明

- termbox2 是 termbox 的继任者，单文件头库 `termbox2.h`（MIT，无第三方依赖，
  仅依赖 HarmonyOS libc/POSIX 接口），可编译为 static/shared 库。
- 构建：`make libtermbox2.a` 或 `make libtermbox2.so.2.0.0`。共享库真实 ELF 为
  `libtermbox2.so.2.0.0`，SONAME 为 `libtermbox2.so.2`，Makefile 用 `ln -sf`
  生成 `.so.2` 与 `.so` 别名。

## 上游测试清点与接入

- 上游自带 `tests/` 套件：16 个 `test_*/test.php` 用例（test_basic、test_64bit、
  test_color_8bit、test_color_true、test_egc、test_error、test_invalid_term、
  test_invalid_utf8、test_invalidate、test_large_input、test_mod、
  test_non_printable、test_non_spacing_mark、test_output_mode、test_print、
  test_resize），由 `tests/run.sh` 驱动，Makefile 提供 `make test`（Docker）与
  `make test_local`（`./tests/run.sh`）。
- 该 harness 是 PHP-FFI + X11 显示驱动：`Xvfb`（无头 X 服务器）、`xterm`，
  `xvkbd` 注入按键、PHP 8.x + FFI 扩展，并把每次渲染的 ANSI 输出与
  `expected.ansi` 做截图比对（`tests/Dockerfile` 安装 `php-cli xvfb xterm
  xvkbd`）。
- 该 PHP-FFI/X11 工具链在无头 OHOS/aarch64 设备上不存在，但每个用例的真实逻辑
  是对 termbox2 C API 的一串调用。因此把 16 个用例逐一移植为原生 C 程序
  `test_package/test_<name>.c`，用共享头 `tb_test_os.h` 在真机建 PTY
  （`tb_init_fd`）调用同一真实 termbox2 API，作为上游测试套件
  在 test_package 内全部执行。由于本包以 `-DTB_LIB_OPTS` 编译（强制
  `TB_OPT_ATTR_W=64` + `TB_OPT_EGC`），`tb_attr_width()==64`、
  `tb_has_truecolor()`、`tb_has_egc()` 均为真，上游 feature 门控的用例在 OHOS
  全部真实运行（不跳过）。
- 输入注入用例（test_basic Ctrl-A、test_large_input、test_mod）用
  `tb_init_fd(slave)` 让 termbox 在 PTY slave 上读写，向 PTY master 写原始输入
  字节（写入 master 的字节会送达 slave 输入端，被 termbox 读取）；test_resize
  用 `raise(SIGWINCH)`。

## 编译步骤

```bash
make CC=<OHOS clang> AR=<llvm-ar> -j1 libtermbox2.a
conan create archives/t/termbox2/2.5.0 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

配方直接复制 `termbox2.h` 与库文件，不执行上游 `make install`，避开其共享库
安装规则中的 `ln -sf` HMDFS 风险。共享库配置在打包后用 HarmonyOS
`binary-sign-tool` 自签，再把相同签名内容复制为 SONAME 与链接名对应的普通文件
别名。

## 依赖版本

无第三方依赖，仅依赖 HarmonyOS libc/POSIX 接口。

## 测试补全与验证

- 16 个上游用例移植为原生 C（`test_basic`..`test_resize`，经 PTY 调真实 API）在
  真机执行。
- 2 个消费者测试程序（`test_api.c` 21 断言不依赖终端；`test_ohos_pty.c` 19 断言
  限定 `__OHOS__`，真机建 PTY 验证 `tb_init_fd`/尺寸/模式/缓冲/`tb_present`）。
- `test_package/conanfile.py` 编译并运行 18 个可执行文件（2 消费者 + 16 上游移植），
  输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=2）与 `HMBS_UPSTREAM_TEST_RESULT`
  （discovered=16，按各可执行文件退出码真实统计 passed/failed）。
- 16 个上游移植用例共 136 处静态 CHECK 断言（test_mod 另有 7 处动态 modifier
  断言），加 2 消费者 40 断言。

## 源码修改

无上游源码修改、无补丁；仅 test_package 内新增移植测试与共享 harness。

## 验证结果

- 上游 16 个用例（移植原生 C 后经 PTY 在真机执行）：以 `HMBS_UPSTREAM_TEST_RESULT`
  真实计数为准（executed=16，passed/failed 来自各可执行文件退出码）。
- 消费者 `test_api`（21 断言）：PASS
- 消费者 `test_ohos_pty`（19 断言，HarmonyOS）：PASS

## CI 修复历史（保留）

### test_package 去掉 CMake，改为直接 clang 编译（2026-09-28）

- 现象：CI（PR #13503，build #63609）的 conan create 在 test_package 阶段失败，
  CMakeToolchain 编译器探测判裸 clang broken。库本身是纯 GNU Make 构建，consumer
  不必引入 CMake。
- 修复：`test_package/conanfile.py` 移除 `CMakeDeps/CMakeToolchain` 与
  `cmake_layout`，`build()` 直接用工具链 clang 编译+链接，与主库 make 构建同一把
  编译器、同一方式。

### 真机证据标记（2026-09-28 初版，2026-10-11 修订）

- 初版把 16 个上游用例声明为 ohos_feature gap（0/16 未执行），被 rule4 人工审查
  打回（“上游有用例 16 个但一个也没测，无论任何理由均不通过”）。
- 修订：把 16 个上游 `test_*/test.php` 逐一移植为原生 C（test_package/test_<name>.c）
  并经 PTY 在真机真实执行，`HMBS_UPSTREAM_TEST_RESULT` 改为
  discovered=16 / executed=16 / passed=按退出码统计，失败项以真实非零退出码计入
  gaps（test_failure）。
- 恒等式：passed + failed == executed（==16）；executed + skipped <= discovered；
  数字来源单一（每个移植用例可执行文件的退出码），不对 stdout 数数。

### 输入注入用例改用 tb_init_fd（2026-10-13）

- 现象：test_basic / test_large_input / test_mod 用 `tb_init_rwfd(master, slave)`
  （termbox 从 master 读、向 slave 写）时在真机/本地 PTY 上取不到注入的输入
  字节，事件计数为 0。
- 根因：`tb_init_rwfd(master, slave)` 把读 fd 指向 master、写 fd 指向 slave。
  对真实 PTY 而言，master 是「主机端」：向 master 写入的字节才会送到 slave 的
  输入队列；termbox 从 master 读根本收不到自己写入 master 的注入字节。上游
  test_large_input/test_mod 用 `memfd_create` 伪造的 tty（rfd/wfd 同一 fd 的
  可读写内存文件）才适用 rwfd 分离，真实 PTY 不适用。
- 修复：三个用例统一改为 `tb_init_fd(slave)`（termbox 在 slave 上读写），输入
  仍写 PTY master（写入 master 的字节送达 slave 输入端，被 termbox 读取）。
  `tb_os_init_rwfd` 辅助函数随之删除，注释/审计文案同步更新。
- 本地验证：用 Alpine x86_64 gcc + devpts chroot 编译并执行全部 17 个可执行
  文件（16 上游移植 + test_api），全部退出码 0（test_basic 12、test_mod 10、
  test_large_input 5、test_resize 7、test_api 21 断言）。

### 源码下载镜像回退（2026-10-13）

- 现象：真机 `source()` 直连 `https://github.com/.../v2.5.0.tar.gz` 连接超时
  （connect timeout=30），ConanException 终止。
- 修复：`conandata.yml` 的 `sources.url` 由单值改为有序列表，
  `https://gh-proxy.com/<官方URL>` 在前、官方 URL 兜底在末；`sha256` 保持官方
  归档原值不变（复用 `ci/conan/build_and_test.sh` 已实测的 GitHub 镜像规则）。

## 注意事项

- 头文件 `termbox2.h` 自带 `#define _DEFAULT_SOURCE/_XOPEN_SOURCE` 保护，无需
  额外传入 feature 宏（上游 Makefile 也显式传 `-D_XOPEN_SOURCE -D_DEFAULT_SOURCE`）。
- 消费者/移植测试全部在 HarmonyOS aarch64 真机上执行；`test_ohos_pty` 只在
  `__OHOS__` 下编译，移植测试依赖 POSIX PTY（`posix_openpt` 系列）。
- `test_large_input` / `test_mod` / `test_basic` 依赖输入字节注入，用
  `tb_init_fd(slave)`（termbox 在 slave 上读写，向 master 写输入字节）；其余
  同样用 `tb_init_fd(slave)`。
- 移植测试不用 `libm`（`test_large_input` 用整数运算替代 `ceil`），避免引入
  数学库链接。

## ABI 对齐（重要）

- 上游 Makefile 编译库时总是带 `-DTB_IMPL -DTB_LIB_OPTS`。在 `TB_LIB_OPTS` 下
  `termbox2.h` 强制 `TB_OPT_ATTR_W=64` 且开启 `TB_OPT_EGC`，因此库内
  `struct tb_cell` 是 40 字节布局（ch:4 + 对齐 + fg:8 + bg:8 + ech:8 + nech:8 +
  cech:8）。
- 若消费者直接 include 普通 `termbox2.h`（默认 `TB_OPT_ATTR_W=16`、无 EGC），
  `struct tb_cell` 只有 8 字节，读 `tb_cell_buffer()`/`tb_cell[]` 的 fg/bg 会落到
  错误偏移。
- 修复：配方 `package()` 里镜像上游 `make lib` 生成的 `termbox2.h.lib`，把
  `0 // __tb_lib_opts` 替换为 `1 // __tb_lib_opts` 后作为 `include/termbox2.h`
  打包，使消费者与库编译选项一致（同时使 `tb_attr_width()==64`、`tb_has_egc()`、
  `tb_has_truecolor()` 为真，feature 门控的上游用例全部真实运行）。
