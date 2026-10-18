# tsctp 0.8.6 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，`PROJECT(tsctp LANGUAGES C)`，单源 src/tsctp.c）
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4（OHOS SDK `aarch64-unknown-linux-ohos`，profile `ci/conan/profiles/ohos-aarch64`）
- Conan: 2.29.1（OHOS 适配版，`os=OHOS` / `arch=armv8`）
- 目标平台: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0）
- 状态: published（conan-verify G0-G4 全通过）

## 上游测试入口核验（R51 第一步）

- **无自动化单元测试**：根 CMakeLists.txt 无 `enable_testing()` / `add_test()` / `include(CTest)`，
  实测 `ctest -N` → `Total Tests: 0`。
- 无 `tests/` 目录、无 pytest、无 `debian/tests`（debian/rules 无 `override_dh_auto_test`）。
- 真实功能测试入口是上游 `src/` 下两个 shell 驱动脚本（端到端 SCTP 流量）：
  `src/batch`（bufsize 递增批量发送）、`src/batchLoop`（bufsize 步进循环发送）。
- `ci/ci-build`、`ci/ci-test`、`freebsd/tsctp/test-packaging` 属打包/安装脚本，不是功能测试。

## 编译步骤

1. `init-build tsctp 0.8.6 --url=https://github.com/dreibh/tsctp/archive/refs/tags/tsctp-0.8.6.tar.gz`
   → 顶层目录 `tsctp-tsctp-0.8.6`，tarball sha256
   `c4defcd5228b4f02598f8ee660e35c9cd32794354006b2db909b623621873785`。
2. `lang-preflight` → detected=c（任务语言 cpp，C/C++ 兼容族），通过（R47）。
3. 基线 configure 取证（先复现真实错误）：
   ```bash
   cmake -S . -B build-ohos -DCMAKE_SYSTEM_NAME=HarmonyOS \
         -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang
   # CMake Error at CMakeLists.txt:73 (MESSAGE):
   #   HarmonyOS not supported (yet?)
   ```
4. 源码改动（探索阶段直接改源，随后 `refresh-patch --auto` 固化为补丁）：
   在 OS 白名单加入 HarmonyOS 分支；把 `FIND_LIBRARY(SCTP_LIB sctp REQUIRED)` 的
   Linux 分支扩为 `MATCHES "Linux|HarmonyOS"`。
5. 注入 Conan 依赖路径重新 configure + build：
   ```bash
   cmake -S . -B build-ohos -DCMAKE_SYSTEM_NAME=HarmonyOS \
         -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
         -DCMAKE_REQUIRED_INCLUDES=<lksctp>/include \
         -DCMAKE_C_FLAGS=-I<lksctp>/include \
         -DSCTP_LIB=<lksctp>/lib/libsctp.a
   cmake --build build-ohos -j4          # [100%] Built target tsctp
   cmake --install build-ohos --prefix $TMPDIR/test-install-tsctp-0.8.6
   ```
   安装产物：`bin/tsctp`、`share/man/man1/tsctp.1`、
   `share/bash-completion/completions/tsctp`。
6. 固化 Conan 配方：`application` 型 + `requires("lksctp-tools/1.0.21")`；
   `generate()` 用 `CMAKE_REQUIRED_INCLUDES` / `CMAKE_LIBRARY_PATH` / `extra_cflags(-I)`
   把依赖头与库喂给上游自带的探测逻辑（不改上游 CMake 探测代码）。
7. `conan-verify tsctp 0.8.6` → G0/G1/G2/G3/G4 + L2/L4/L5 PASS（conan create 含 test_package 3/3 PASS）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 直接 `FATAL_ERROR: HarmonyOS not supported (yet?)` | 上游 CMake 的 `CMAKE_SYSTEM_NAME` 白名单只有 Linux/FreeBSD/NetBSD/Darwin；Conan OHOS profile 把 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`（不是 OHOS），落进 ELSE 分支 | patches/0001 增加 `ELSEIF (CMAKE_SYSTEM_NAME MATCHES "HarmonyOS")` 分支（Linux 兼容语义） |
| 2 | 若只加 OS 白名单，`netinet/sctp.h` 找不到 | OHOS SDK sysroot 只有内核 uapi `linux/sctp.h`，没有 `netinet/sctp.h`，也没有 libsctp | 依赖 `lksctp-tools/1.0.21`（ohpcd 已有 OHOS 预编译二进制），generate() 注入 include/lib 路径 |
| 3 | 只注入 include 时 `FIND_LIBRARY(SCTP_LIB sctp)` 仍找不到库 | 该分支对非 Linux 系统的 `FIND_LIBRARY` 是**非 REQUIRED**，找不到就静默置空，链接期才报 undefined reference | 补丁把 HarmonyOS 并入 Linux 分支（`MATCHES "Linux|HarmonyOS"`），保持 REQUIRED 语义 |
| 4 | 编译告警 `'HAVE_KERNEL_SCTP' macro redefined` | CMake `ADD_DEFINITIONS(-DHAVE_KERNEL_SCTP)` 与 lksctp 的 `netinet/sctp.h` 内 `#define HAVE_KERNEL_SCTP` 重复；上游在 Linux 上同样如此 | 不改（上游既有行为，仅告警） |
| 5 | 运行期 `socket: Protocol not supported` | HarmonyOS HongMeng Kernel 1.12.0 未内置 SCTP 协议栈：`socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP)` 返回 `EPROTONOSUPPORT(93)`；`/proc/net/sctp` 不存在、`sysctl net.sctp` unknown、无 `/lib/modules` | 编译期适配不受影响；运行期端到端 SCTP 流量测试在本机无法执行（如实记录，见 reports/test-report.md） |

## 源码修改

| 补丁 | 内容 |
|------|------|
| `patches/0001-CMakeLists.txt.patch` | ① OS 白名单新增 HarmonyOS（Linux 兼容）；② `FIND_LIBRARY(SCTP_LIB sctp REQUIRED)` 的 Linux 分支扩为 `Linux\|HarmonyOS`。均为 `CMAKE_SYSTEM_NAME` 字符串匹配，未引入任何平台预处理器宏（R8 / PF5） |

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| lksctp-tools | 1.0.21 | ohpcd（`conan download` 实测可消费，含 OHOS armv8 预编译二进制 `4b977264…`） | 提供 `netinet/sctp.h` + `libsctp.a`（对应 Debian `libsctp-dev >= 1.0.5`）；其自身无第三方运行时依赖 |
| Threads | 系统 | OHOS sysroot | `FIND_PACKAGE(Threads REQUIRED)`，解析为 libc 内 pthread |

## 验证结果

```bash
# 1) 上游测试入口清点
$ ctest -N                      → Total Tests: 0
$ grep -rn 'enable_testing|add_test' CMakeLists.txt src/CMakeLists.txt
                                → 无匹配

# 2) 上游功能测试入口实际执行（需真实 SCTP 协议栈）
$ ./tsctp -L 0.0.0.0 -p 1234    → server mode / socket: Protocol not supported (rc=1)
$ sh src/batch 1 2 1 1 127.0.0.1 127.0.0.1
                                → client mode ×2 / socket: Protocol not supported (脚本 rc=0)
$ sh src/batchLoop 1 2 1 127.0.0.1 127.0.0.1
                                → client mode / socket: Protocol not supported (脚本 rc=0)
$ ./tsctp -Z                    → 上游 Usage 横幅（17 个选项）+ rc=1

# 3) test_package 消费者用例（conan create 内实跑）
PASS: 1 CLI usage surface (-Z => upstream usage banner + exit 1)
PASS: 2 SCTP socket path (server mode, no crash)
PASS: 3 libsctp linked in (3/3 upstream SCTP entry points)
--- tsctp 0.8.6 consumer: 3/3 PASS ---

# 4) 鸿蒙专项（test_ohos/run_ohos_test.sh）
T1 aarch64 ELF64 / T2 无宿主路径泄漏 / T3 静态链入 libsctp 3/3 /
T4 SCTP 协议栈探测（优雅报错，无崩溃）/ T5 上游 CLI 横幅  → ALL PASS (5/5)

# 5) conan-verify（G0-G4 + L2/L4/L5）
Verdict: PASS   conan create 日志: reports/conan-create.log
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | application 型配方（CMake + lksctp-tools 依赖注入） |
| conandata.yml | 官方 GitHub tag 归档 + sha256 + 补丁声明 |
| patches/0001-CMakeLists.txt.patch | HarmonyOS OS 白名单 + libsctp REQUIRED |
| test_package/{conanfile.py,test.sh,MANIFEST.yml} | 消费者用例（3 项断言） |
| test_ohos/run_ohos_test.sh | 鸿蒙专项验证（5 项断言） |
| commands.json | CLI 工具声明（R38，软件级） |
| reports/ | conan-create.log / conan-verify-report.md / test-report.md（gitignored，本地留档） |

## 注意事项

- **patches 里不能写 `__OHOS__`**：本次补丁只做 `CMAKE_SYSTEM_NAME` 字符串匹配（R8 / PF5）。
- **HarmonyOS ≠ OHOS（CMake 视角）**：`CMAKE_SYSTEM_NAME` 是 `HarmonyOS`，写 `MATCHES "OHOS"` 不会命中。
- **不要给 libsctp 走动态链接**：ohpcd 的 lksctp-tools 只发布 `shared=False` 二进制，本包因此静态链入
  `libsctp.a`，产物 `DT_NEEDED` 仅 `libc.so`（`test_ohos` T3 已核验）。
- **运行期 SCTP 能力取决于内核**：本机内核无 SCTP 栈，`test_package` / `test_ohos` 因此按
  "优雅报错即通过（且绝不崩溃）" 设计，避免在无 SCTP 内核上误判失败。
- 归档目录内 `conandata.yml.ghfast-bak`（conan-verify 镜像注入备份）与 `test_package/conan*.sh`
  （conan 生成器产物）均属临时垃圾，提交前已清理/已被 .gitignore 覆盖。
---

**编译结束**: 2026-10-17 18:10
**最终状态**: published
