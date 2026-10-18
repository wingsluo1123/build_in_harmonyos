# 测试报告 — gnu-efi 4.0.4

- **日期**：2026-10-16
- **构建系统**：makefile（上游手写 Makefile，无 configure / CMake）
- **目标平台**：OpenHarmony aarch64（profile `ci/conan/profiles/ohos-aarch64`，host=build）
- **工具链**：clang 15.0.4（`aarch64-unknown-linux-ohos`）、`ld.lld`、`llvm-ar`、`llvm-ranlib`、GNU objcopy 2.45、GNU make 4.4.1

## 1. 本地 CI 模拟（W3，`ci/conan/build_and_test.sh`）

- 结果：**通过**（`setup.sh` 通过；`build_and_test.sh gnu-efi/4.0.4` 通过）
- 日志：`reports/w3-local-ci.log`

## 2. Conan 配方验证（`conan-verify`，G0–G4 / L2·L4·L5）

- G1 配方完整性：通过（name/version/source/build/package/package_info/export_sources、conandata 完整、test_package 与 MANIFEST 存在）
- G2 `conan create`（干净构建）：本地手工 `conan create` 通过（见第 3 节）；`conan-verify` 包装器另有说明见第 5 节
- 报告：`reports/conan-verify-report.md`

## 3. 消费者测试（`test_package`，真实执行）

`test_package/test_gnuefi.py` 以包内工具链构建一个真实 UEFI 应用：

```
clang -c hello.c -I<pkg>/include/efi [-I .../aarch64] [-I .../protocol] \
      -ffreestanding -fno-stack-protector -fPIC -fno-jump-tables \
      -std=c11 -O2 -g -Wall -Wextra -Werror -DCONFIG_aarch64
ld.lld -nostdlib -z common-page-size=4096 -z max-page-size=4096 ... \
      <pkg>/lib/crt0-efi-aarch64.o hello.o -o hello.so \
      -T <pkg>/lib/elf_aarch64_efi.lds -lefi -lgnuefi <libclang_rt.builtins.a>
objcopy -j .text -j .sdata ... -O efi-app-aarch64 hello.so hello.efi
```

**结果：assertions 16/16（13 值断言 + 3 到达型断言）**，末尾输出：

```
assertions 16/16
gnu-efi consumer test OK: hello.efi (58363 bytes, PE32+ aarch64 EFI application)
```

断言明细：`include/efi/efi.h`、`include/efi/efilib.h`、`libefi.a`、`libgnuefi.a`、
`crt0-efi-aarch64.o`、`elf_aarch64_efi.lds`、`pkgconfig/gnu-efi.pc` 且前缀可重定位、
编译成功、链接成功、ELF 产物成立、PE32+ 且 machine=`0xAA64`、subsystem=10（EFI 应用）；
其中编译 / 链接 / `objcopy` 三步各自 `subprocess.run(check=True)` 之后的**到达型断言共 3 条**
（`os.path.isfile(hello.o)` / `hello.so` / `hello.efi`）。计数由脚本内 `Checks.check()`
累计并打印 `assertions N/M`，与 `test_package/MANIFEST.yml` 的 `assertion_count: 16`
及 `assertion_count_breakdown`（13 + 3）一致 —— 计数是运行期读数，不是自我申报。

## 4. 上游测试套件

上游 `tests/run_tests.sh` 为 QEMU/OVMF 驱动套件（`tests/test_list.txt` 4 个场景：ConOut 文本输出、
参数传递、参数打印、驱动加载），前置要求 `$QEMU_CMD` 指向 `qemu-system-aarch64 -bios AAVMF_CODE.fd`。

- **未执行**：构建环境无 `qemu-system-aarch64`、无 AAVMF/OVMF 固件。
- 不缩小分母、不伪造通过率；以第 3 节的消费者断言覆盖"工具链可用 + 产物形态正确"的内核。

## 5. 交付物元数据核对（包内实读）

从 Conan 缓存包目录实读 `lib/pkgconfig/gnu-efi.pc`：

```
prefix=${pcfiledir}/../..
exec_prefix=${prefix}
includedir=${prefix}/include
libdir=${prefix}/lib
...
Version: 4.0.4
```

- `Version:` 与包/上游 tag `4.0.4` **一致**（配方在 make 命令行传 `VERSION=<包版本>`；
  上游树内 `VERSION` 变量写的是 4.0.3，属上游滞后，已在 `notes.md` 与 PR 正文如实披露）。
- 前缀为可重定位形式（`${pcfiledir}/../..`），未把构建期绝对路径写进包。

## 6. 已知环境性偏差（非配方缺陷）

- `conan-verify` 的 G2 包装器会在运行前把 conandata 里的 GitHub URL 临时改写为
  `ghfast.top` 镜像（E017 预防机制）；该镜像在本次运行期间不可达（连接超时），
  故包装器侧 G2 报下载失败。**同一配方用官方 URL 手工 `conan create`（含 test_package）
  通过**（第 3 节），属镜像通道问题，非配方缺陷；预热下载缓存后 `conan-verify` 亦 **PASS**。
- `finish` 的 G0「干净构建验证」按 autotools 假设执行 `./configure`，本项目为手写
  Makefile、无 configure，故该非阻塞步骤报 `exit 127`；不影响 W3 阻塞门禁结果。
