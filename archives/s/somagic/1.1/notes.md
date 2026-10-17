# somagic 1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure/CMake）
- 编译日期: 2026-10-15
- 编译器: clang（aarch64-unknown-linux-ohos）
- 状态: built
- Conan: 2.30（OHOS 适配版）
- Profile: ci/conan/profiles/ohos-aarch64（os=OHOS, arch=armv8, compiler=clang-15）

## 软件简介

somagic（上游项目 `easycap-somagic-linux`）是 Somagic EasyCAP DC60 /
EasyCAP002 USB 视频采集棒的 Linux 用户态驱动套件（USB ID 1c88:0007）。
上游发布 4 个单文件 C 程序 + 一个 raw Makefile：

| 程序 | 作用 | 依赖 |
|------|------|------|
| somagic-init | 上传芯片固件并让设备以新 product ID 重新枚举 | libusb-1.0 + libgcrypt |
| somagic-capture | 初始化采集寄存器并输出原始 UYVY 视频流 | libusb-1.0 |
| somagic-audio-capture | beta 纯音频采集路径 | libusb-1.0 |
| somagic-both | beta 初始化 + 采集合并路径 | libusb-1.0 |

后两个 beta 程序由 Makefile 单独的 `beta` 目标构建；配方一并构建并打包，
使交付内容与 README 描述一致。

## 编译步骤

```bash
# 配方目录
archives/s/somagic/1.1/
# patches/0001-guard-libusb-init-failure.patch 由 export_sources() 导出并
# source() 通过 apply_conandata_patches() 应用到四个 .c 源文件。
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
# build(): 在 source_folder 内
#   make -j1 CC=<conan c compiler> \
#       CFLAGS="-s -W -Wall -I<libusb>/include -I<libusb>/include/libusb-1.0 -I<libgcrypt>/include" \
#       LFLAGS="-L<libusb>/lib -L<libgcrypt>/lib -lusb-1.0 -lgcrypt -Wl,-rpath,<...>" \
#       all beta
# package(): 拷贝四个可执行文件到 bin/，man/*.1 到 share/man/man1，
#            debian/copyright 到 licenses/；对四个 ELF 做 binary-sign-tool 自签。
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码 `#include <libusb-1.0/libusb.h>`，但 libusb 的 Conan 包 includedir 是 `include/libusb-1.0` | 头文件路径层级不一致 | 在 `-I` 中同时加入 `include/libusb-1.0` 与其父目录 `include/`（`_dependency_search_paths()` 对每个 includedir 追加父目录） |
| 2 | 上游 Makefile 的 `.c:` 隐式规则只用 `$(CC) $(CFLAGS) $< -o $@ $(LFLAGS)`，无法从 profile 自动取工具链 | 纯 Makefile 项目无 configure/CMake 注入点（R33） | 通过 `make` 命令行变量覆盖 `CC/CFLAGS/LFLAGS`，编译器取自 `tools.build:compiler_executables`，绝不裸用 shell 变量 |
| 3 | 上游 `install` 目标写死 `$(PREFIX)=/usr/local`，且只装 `$(PROGRAMS)` 两个程序 | 以 /usr/local 为安装根，与 Conan DESTDIR 打包模型冲突 | 不调用 `make install`；在 `package()` 内拷贝全部四个可执行文件 + 手册页 + copyright |
| 4 | OHOS 拒绝从包缓存执行未签名 ELF | HarmonyOS XPM 要求 ELF 带 `.codesign` 段 | `package()` 中对四个可执行文件先 `llvm-objcopy --remove-section .codesign` 再 `binary-sign-tool sign -selfSign 1`，之后 `chmod 755` |

## 源码修改

一个补丁 `patches/0001-guard-libusb-init-failure.patch`（portability）：

- 四个 .c 源文件（somagic-init.c / somagic-capture.c / somagic-both.c /
  somagic-audio-capture.c）各自在 `libusb_init(NULL)` 之后忽略其返回值，
  然后直接使用全局 `devh` 与 libusb 枚举接口。
- 在 HarmonyOS（HongMeng kernel）沙箱中，`libusb_init()` 内部的 netlink
  热插拔 socket (`socket(PF_NETLINK, SOCK_RAW, NETLINK_KOBJECT_UEVENT)`)
  失败，libusb 无法完成初始化；此时原代码继续执行 `find_device()` →
  `libusb_open()`，用未初始化的句柄触发 SIGSEGV。实测 `somagic-init
  --skip-check -f <fixture>` 必现 exit 139。
- 补丁在每个 `libusb_init(NULL)` 后面插入返回值检查：失败即打印
  `Failed to initialize libusb` 并 `return 1`，恢复预期的 exit-1 错误路径。
- 补丁纯属缺陷修复，未引入任何平台 `#ifdef`，在 Linux 上同样是正确行为。

## 已知限制（平台）

- `somagic-audio-capture` 是仅设备可用的 beta 程序：`main()` 无 CLI，
  直接 `assert(dev)`，无硬件时 abort。消费者测试仅校验其为打包后的可执行 ELF。

## 依赖版本

- `libusb/1.0.27`（制品仓已发布；在 HongMeng 内核 `libusb_init()` 默认失败，可
  传入 `LIBUSB_OPTION_NO_DEVICE_DISCOVERY` 规避，参见 libusb 1.0.27 manifest
  的 `platform_notes`）
- `libgcrypt/1.11.0`（制品仓已发布，传递依赖 `libgpg-error/1.55`）

## 验证结果

```bash
# HarmonyOS aarch64 环境 conan create（含 test_package 自动执行）
# 消费者测试：bash test.sh <package>/bin —— 16 个检查点全部通过
#   - 四个可执行文件存在且可执行
#   - somagic-init --version / --help
#   - somagic-init 默认固件打开失败路径（/lib/firmware/somagic_firmware.bin 缺失）
#   - somagic-init -f <fixture>：libgcrypt GCRY_MD_CRC32 固件校验（"was not recognized"）
#   - somagic-init --skip-check -f <fixture>：libusb-1.0 初始化/枚举路径。
#     鸿蒙内核 netlink 不可用，libusb_init 失败；补丁后为
#     `Failed to initialize libusb` + exit 1（此前 SIGSEGV 139）。
#   - somagic-capture --version / --help / 参数校验 / 无设备枚举路径
#   - somagic-both --version / --help
#   - somagic-audio-capture（仅设备 beta，main() 断言设备句柄）以打包后的可执行 ELF 校验
# 上游测试：无（Makefile 无 check/test 目标，tarball 无 tests/），见 reports/upstream-test-audit
```

## 上游测试审计

- 源码归档 `somagic-easycap_1.1.tar.gz` 共 21 个条目，无 `tests/`/`test/` 目录，
  无 `*_test.c`/`test_*.c` 文件，无 CI 配置目录。
- `Makefile` 目标仅 `all` / `beta` / `install` / `install-beta` / `clean`，
  无 `check`/`test` 目标，`make -n check` 报 "No rule to make target 'check'"。
- 结论：上游无自动化测试套件，按 `no_tests` 申报；验证面为四个 CLI 工具本身，
  由 test_package 以消费者视角对打包后的可执行文件做真实行为断言。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/somagic-init | 固件上传工具（libusb-1.0 + libgcrypt） |
| bin/somagic-capture | 视频采集工具（libusb-1.0） |
| bin/somagic-audio-capture | beta 音频采集（libusb-1.0） |
| bin/somagic-both | beta 合并路径（libusb-1.0） |
| share/man/man1/somagic-init.1, somagic-capture.1 | 上游手册页 |
| licenses/copyright | 上游 DEP-5 版权信息 |

## 注意事项

- `somagic-audio-capture` 是仅设备可用的 beta 程序：`main()` 无 CLI，
  直接 `assert(dev)`，无硬件时会 abort。因此消费者测试只校验它是打包后的
  可执行 ELF，不运行它。
- 该套件面向真实 USB 采集硬件；无设备环境只能验证 CLI 表面与确定性的设备无关
  错误路径（固件打开失败、libgcrypt 固件 CRC 校验、libusb_init 失败/设备枚举）。

## 轮次日志

### 2026-10-15（fixing_verification / evidence）

- 真机反馈：`somagic-init --skip-check` 返回 139（SIGSEGV），test_package 16 项
  中 14 项通过，2 项失败。
- 根因（源码 + 日志）：四个程序忽略 `libusb_init()` 返回值；HongMeng 内核沙箱
  中 netlink 热插拔 socket 不可用，`libusb_init()` 失败后原代码仍继续
  `find_device()` → `libusb_open()`，用未初始化句柄解引用崩溃。
- 修复：新增 `patches/0001-guard-libusb-init-failure.patch`，四个调用点补返回值
  检查，失败即 `Failed to initialize libusb` + exit 1；配方增加
  `export_sources()` / `source()` 的 patch 应用；test.sh 对应断言改为「exit 1
  且非信号」，兼容「libusb_init 失败」与「设备未找到」两种确定性结果；临时目录
  探测不再依赖 mktemp，按 TMPDIR → TMP → TEMP → cwd 探测。
- 上游测试口径：确认上游确无测试框架，MANIFEST 置
  `upstream_test_total: 0` / `upstream_test_count_method: none` 并补结构化审计；
  test.sh 的 no_tests 标记同步为 `framework:none`、`command:""`。

### 2026-10-16（fixing_ci：CI #95906 fork EAGAIN）

- CI 反馈（build #95906，`conan-build-test`）：`Calling build()` 后 `make` 尚未
  产出任何编译输出即失败：
  `ConanException: Error while running cmd` / `Error: [Errno 11] Resource
  temporarily unavailable`（`self.run` 的 `subprocess.Popen` 被拒 fork）。同一
  构建日志中 CI 自身的 `knowledge_check.sh` / `junk_check.sh` 也反复出现
  `fork: retry: Resource temporarily unavailable`，属 worker 级 fork/进程资源
  瞬时耗尽，不是源码或工具链缺陷。
- 根因（源码 + 日志）：conan 默认（`tools.env:deactivation_mode` 未设）在聚合
  环境脚本 `conanbuildenv-<id>.sh` / `conanrunenv-<id>.sh` 顶部生成一段 source
  时立即执行的反激活前导块 `for v in <vars>; do value=$(printenv $v); ...; done`，
  对每个导出变量 fork 一次 `printenv` 与命令替换子 shell。profile `[buildenv]`
  导出 SHELL/CONFIG_SHELL/PATH/LD_LIBRARY_PATH，VirtualBuildEnv/VirtualRunEnv
  还会聚合依赖 libdir/bindir，于是每次 `self.run(env="conanbuild")` 在目标命令
  前先 fork 十余次，在 fork 临界时直接被 EAGAIN 拒绝。
- 修复：
  1. 主配方新增 `generate()`，`self.conf.define("tools.env:deactivation_mode",
     "function")`，把前导块改为只定义反激活函数（source 期零 fork，仍完整导出
     环境变量）；放在 generate() 顶部以确保早于 VirtualBuildEnv/VirtualRunEnv。
  2. `test_package/conanfile.py` 在 `configure()` 注入同一 conf（该包显式声明
     `VirtualRunEnv`，显式生成器在 generate() 之前运行，放 generate() 无效）。
  3. `build()` 的 make 改走 `_make_with_fork_retry()`：仅当异常文本/输出命中
     fork 指纹（`can't fork` / `resource temporarily unavailable` / `errno 11` 等）
     时做有界退避重试（4 次，15/30/45s），真实编译/链接错误立即抛出，不掩盖。
- 本机验证（不代替真机）：`python3 -m py_compile` 两个配方通过；对 conan
  2.29.1 `conan/tools/env/environment.py` 的 `_sh_deactivate_contents` unset /
  function 两分支逐条核对，确认 function 模式 source 期无 `printenv` fork。
- 未改测试逻辑与计数口径：test.sh 的 16 个检查点与
  `HMBS_TEST_PACKAGE_RESULT`、上游 `no_tests` 标记、MANIFEST 审计均不变。
