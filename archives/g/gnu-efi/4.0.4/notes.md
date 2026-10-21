# gnu-efi 4.0.4 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile + Make.defaults + Make.rules，非 autotools）
- 编译日期: 2026-10-16
- 编译器: clang 15.0.4（`aarch64-unknown-linux-ohos` target）、ld.lld、llvm-ar/llvm-ranlib
- 二进制工具: GNU objcopy 2.45（`-O efi-app-aarch64` 可用 ⇒ `SYSTEM_HAS_EFI_OBJCOPY=1`）
- 状态: built

## 编译步骤

上游没有 configure，`make` 直接使用 `Make.defaults` 里 `$(CROSS_COMPILE)gcc` 形态的
工具变量，**不会**读 Conan 的 toolchain 文件 ⇒ 编译器/二进制工具必须在命令行显式传入
（R33：不得依赖未定义的 shell 环境变量）：

```bash
make -j4 ARCH=aarch64 \
     CC=clang HOSTCC=clang AS=clang LD=ld.lld AR=llvm-ar RANLIB=llvm-ranlib \
     OBJCOPY=objcopy INSTALL=ginstall VERSION=4.0.4
make install INSTALLROOT="<package_folder>" PREFIX=/ \
     ARCH=aarch64 CC=clang HOSTCC=clang AS=clang LD=ld.lld AR=llvm-ar \
     RANLIB=llvm-ranlib OBJCOPY=objcopy INSTALL=ginstall VERSION=4.0.4
```

`CC/HOSTCC/AS/LD/AR/RANLIB` 由配方在运行时解析（`tools.build:compiler_executables`
优先，其余走 PATH 查找），作业数取 `tools.build:jobs`（构建槽闸导出的值）。
`VERSION` 取配方自身的 `self.version`（见下表第 4 行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` 报 `make[1]: install: No such file or directory`、`Error 127` | OpenHarmony 无 `install(1)`（`command -v install` 为空）；上游 `INSTALL := install` 硬编码 | 显式传 `INSTALL=ginstall`（GNU coreutils，设备在册）。已知机制，见 `E108` |
| 2 | 产物落在 `<pkg>/usr/local/{lib,include}`，`cpp_info.libdirs=["lib"]` 找不到库 | 上游 install 用**两层前缀**：`INSTALLROOT`（`DESTDIR` 只是其回退值）只给外层根，`LIBDIR/INCLUDEDIR` 仍挂死在硬编码 `PREFIX := /usr/local` | 同时传 `INSTALLROOT=<package_folder>` 与 `PREFIX=/` ⇒ 直落 `<pkg>/{lib,include}`（新机制，见草稿） |
| 3 | 装出的 `gnu-efi.pc` 前缀为 `/usr/local`、且 `install` 阶段改 `PREFIX` 不生效 | `gnu-efi.pc` 在 **`make` 阶段**由 `gnu-efi.pc:` 规则生成，`install:` 目标不依赖它、只做拷贝 | 打包后把 .pc 改写成可重定位形式（`prefix=${pcfiledir}/../..`），并如实记录上游行为（新机制） |
| 4 | 装出的 `gnu-efi.pc` 的 `Version:` 为 `4.0.3`，而包/tag 是 `4.0.4` | 上游 `Makefile:45` `export VERSION = 4.0.3` 未随 tag 同步（tag `4.0.4` = commit `37cd8f069bde6715eebdc5e38a8f15ee6de5edcf`），而该变量正是 `gnuefi/Makefile` 里 `@VERSION@` 的唯一来源 | 在 make 命令行传 `VERSION=<配方 self.version>`（命令行覆盖上游 `export VERSION`，**不改上游源码**）⇒ 交付的 `.pc` 报 `Version: 4.0.4`，与包版本一致。源码树内的滞后仍如实披露（见「注意事项」），不隐瞒 |
| 5 | 消费者用 `Print(L"…")` 编译失败：`incompatible pointer types passing 'unsigned int[29]' to parameter of type 'const CHAR16 *'` | 目标平台 `wchar_t` 是 4 字节，而 gnu-efi 的 `CHAR16` 是 2 字节 `unsigned short`；上游示例统一用 C11 `u"…"`（`char16_t`，天然 2 字节），`README.md:406` 亦说明传统 `L"…"` 需额外 `-fshort-wchar` | 消费者侧改用 `u"…"`（本包 `test_package` 即如此）；确要用 `L"…"` 时必须自带 `-fshort-wchar` |
| 6 | 消费者测试原先只在文本里声称 11 条断言，日志不打印 N/N | 断言用裸 `assert`，无计数出口 | `test_package/test_gnuefi.py` 改为 `Checks.check()` 计数（16 条 = 13 值断言 + 3 到达型），末尾打印 `assertions N/M`；`MANIFEST.yml` 的 `assertion_count: 16` 与之对齐 |

## 源码修改

无补丁（`patches_applied: []`）。全部差异都在 Conan 配方层（`make` 变量、`INSTALLROOT`/`PREFIX`、
.pc 前缀改写）。

## 依赖版本

无 Conan 依赖（`requirements()` 为空）。构建期只用设备自带工具链：
clang 15.0.4 / ld.lld / llvm-ar / llvm-ranlib / GNU objcopy 2.45 / ginstall（coreutils）/ GNU make 4.4.1。

## 验证结果

```bash
# 1) 打包布局（应直接落在包根，不得出现 usr/local）
find <package_folder> -maxdepth 2 -type d
# → <pkg>/{lib,include,licenses} + <pkg>/lib/pkgconfig

# 2) 包内 pkg-config 元数据
grep -E '^(prefix|libdir|includedir|Version)' <pkg>/lib/pkgconfig/gnu-efi.pc
# → prefix=${pcfiledir}/../.. / includedir=${prefix}/include / libdir=${prefix}/lib / Version: 4.0.3

# 3) 消费者测试（test_package，真实编译+链接+objcopy+PE 断言）
python3 test_gnuefi.py <package_folder>
# → gnu-efi consumer test OK: hello.efi (PE32+ aarch64 EFI application)

# 4) 上游测试套件（★2026-10-17 返修新增：真实执行）
cd <harness> && export UEFI_DIR=./image QEMU_CMD="<见「上游测试」节原文>"
./tests/gen_tests.sh ./tests/test_list.txt && ./tests/run_tests.sh
# → # TOTAL: 4 / # PASS: 4 / # FAIL: 0 / # ERROR: 0，rc=0
#   逐条：run_tests.sh {001,002,003,004} <同号> → 各自 rc=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libefi.a` | UEFI Boot/Runtime Services 封装（`libefi`） |
| `lib/libgnuefi.a` | GNU-EFI 运行期辅助库（`libgnuefi`） |
| `lib/crt0-efi-aarch64.o` / `lib/crt0-efi-aarch64-local.o` | aarch64 EFI 入口桩（objcopy / 汇编合成两条路径各一） |
| `lib/elf_aarch64_efi.lds`（+ `_local`） | EFI 链接脚本 |
| `include/efi/**` | EFI 头文件树（`efi.h`/`efilib.h`/`protocol/`/`aarch64/`/`legacy/`） |
| `lib/pkgconfig/gnu-efi.pc` | pkg-config 元数据（前缀已改为可重定位） |
| `lib/gnuefi/apps/*.efi` | 上游示例 EFI 应用（上游 `APPSDIR` 落在 lib 下，非宿主可执行文件，故无 `commands.json`） |

## 上游测试（★2026-10-17 返修：已真实执行，4/4 通过）

上游自带 QEMU/AAVMF 驱动套件：`tests/run_tests.sh` + `tests/gen_tests.sh` + `tests/test_list.txt`，
共 **4 个场景**：001 ConOut 文本输出、002 参数传递、003 参数打印、004 驱动加载。
`run_tests.sh` 强制要求 `$QEMU_CMD`，并支持 `run_tests.sh <MIN> <MAX>` 逐条执行。

### 执行环境（补齐前置，非"环境不支持"）

| 前置件 | 来源 | 实读 |
|---|---|---|
| `qemu-system-aarch64` 11.1.1 | 制品仓 `qemu/11.1.1` 配方**重建为 `--target-list=aarch64-softmmu`**（在册二进制只含 riscv64 目标） | `--version` → `QEMU emulator version 11.1.1`，rc=0 |
| `AAVMF.fd` 固件 | https://efi.akeo.ie/AAVMF/AAVMF-AA64.zip （与上游 CI 同源） | 67108864 B，`_FVH` 固件卷签名在册 |
| UEFI Shell `bootaa64.efi` | UEFI-Shell 24H2 `shellaa64.efi`（与上游 CI 同源），置于 `image/efi/boot/` | 1060864 B，PE32+ machine=0xAA64 subsystem=10 |
| 被测 `.efi` | **交付包自身** `lib/gnuefi/apps/` | `t.efi`/`tcc.efi`/`t8.efi`/`drv0.efi`/`drv0_use.efi` 均 PE32+ machine=0xAA64（`drv0.efi` subsystem=11 = EFI driver） |

### 执行命令（原文）

```bash
cd <harness>                      # 含 tests/ 与 image/（image/efi/boot/bootaa64.efi）
export UEFI_DIR=./image
export QEMU_CMD="qemu-system-aarch64 -M virt -cpu cortex-a57 -m 1024 -nodefaults -nographic \
  -serial stdio -net none -drive if=pflash,format=raw,unit=0,file=<harness>/AAVMF.fd,readonly=on \
  -drive format=raw,file=fat:rw:image"
./tests/gen_tests.sh ./tests/test_list.txt
./tests/run_tests.sh              # 全量：TOTAL 4 / PASS 4 / FAIL 0 / ERROR 0 → rc=0
./tests/run_tests.sh 001 001      # 逐条：rc=0
./tests/run_tests.sh 002 002      # 逐条：rc=0
./tests/run_tests.sh 003 003      # 逐条：rc=0
./tests/run_tests.sh 004 004      # 逐条：rc=0
```

> 说明：`run_tests.sh` 的 shebang 为 `#!/usr/bin/env bash`（上游原文，未修改）；本平台
> `/usr/bin/env` 为 toybox 符号链接，故以 `bash ./tests/run_tests.sh` 显式调用 ——
> **只改调用方式，未改上游任何测试源码/清单/判据**。

### 逐条结果（rc + 判据复核）

| # | 场景 | rc | 上游判据（`tail -n N output.txt \| diff -Z --strip-trailing-cr <case>.dat -`） |
|---|------|----|----|
| 001 | ConOut text output | **0** | 无差异（实际尾部两行 = `Hello World!` ×2） |
| 002 | Test args | **0** | 无差异（13 行全中，含 `Returning Failure works`） |
| 003 | Print args | **0** | 无差异（`Argc=3` 与 `Argv[0..2]` 全中） |
| 004 | Test driver | **0** | 无差异（`Hello was called 1 time(s).`） |
| — | **全量 `run_tests.sh`** | **0** | `# TOTAL: 4 / # PASS: 4 / # FAIL: 0 / # ERROR: 0` |

### 重建 `qemu-system-aarch64` 的两处必要改动（如实披露）

在册 `qemu/11.1.1` 配方硬编码 `--target-list=riscv64-softmmu`，无法运行 aarch64 guest。以该配方
重建 `aarch64-softmmu` 时，本机（宿主 meson 报 `host_os='linux'`）另遇两处 **clang 15 与 QEMU 11 源码
不兼容**，均在**临时构建副本**内处理，**未改动 `archives/q/qemu` 归档原件**，也未改动上游：

1. `net/can/can_socketcan.c`：配方补丁 0002 的跳过条件为 `host_os=='linux' and host_os_orig=='linux'`，
   而本机 `host_os_orig` 本就是 `linux` ⇒ 条件成立、该文件被编译，撞上 SDK sysroot 的
   `sockaddr_storage` 重定义（`linux/socket.h` vs `sys/socket.h`）⇒ 从 `net/can/meson.build` 移除该源文件
   （CAN 与 `-M virt` 无关）。
2. `hw/arm/fsl-imx8mm.c` / `fsl-imx8mp.c`（及 `imx8mm-evk.c`/`imx8mp-evk.c`）：clang 15 不接受
   `static const MemMapEntry` 数组成员用于静态初始化（`initializer element is not a compile-time constant`）
   ⇒ 从 `hw/arm/meson.build` 移除这 4 个 NXP i.MX8M 单板（与 `-M virt` 无关）。

其余 3100+ 目标一次通过；产物重新走配方既有的 OHOS 签名流程
（`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`）后实测可加载。

### 适配侧消费者测试（与上游测试互补，未被替代）

`test_package/test_gnuefi.py`（16 条断言 = 13 值 + 3 到达型，运行期打印 `assertions 16/16`）覆盖
上游 4 个场景**不检查**的交付物打包形态：`lib/`、`include/` 布局、入口桩/链接脚本随包安装、
`gnu-efi.pc` 可重定位。两者均已执行、均通过。

## 注意事项

- `ARCH` 必须为 `aarch64`：上游用 `$(CC) -dumpmachine` 自动探测，设备上 clang 报
  `aarch64-unknown-linux-ohos` ⇒ 自动取到 `aarch64`，但显式传入可避免工具链差异导致误判。
- `PREFIX=/` 只影响安装路径拼接（`//include`、`//lib`），编译期头文件搜索走
  `-I$(TOPDIR)/inc`，不受影响（实测）。
- 包版本 `4.0.4` 与上游**源码树内** `VERSION=4.0.3` 的差异是上游滞后（tag `4.0.4` 未同步
  该变量）。配方已在 make 命令行传 `VERSION=4.0.4`，因此**交付的** `gnu-efi.pc` 里
  `Version:` 实读为 `4.0.4`，下游 `pkg-config --modversion gnu-efi` 读到的是正确版本；
  上游树内滞后本身仍如实记录在此，未改上游源码。
---

**编译结束**: 2026-10-16 20:45
**最终状态**: built
