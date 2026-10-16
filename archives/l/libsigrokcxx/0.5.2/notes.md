# libsigrokcxx 0.5.2 — 当前 Conan 适配记录

`libsigrokcxx` 是 libsigrok 源码树里的 `bindings/cxx/` 子目录（C++ 绑定），**没有独立上游 tarball**，因此本包与 `libsigrok/0.5.2` 共用同一份源码归档 `libsigrok-0.5.2.tar.gz`，只取其中 `bindings/cxx/` 部分构建。

## 与上游构建链的差异（三处，均在本包内部完成，不改上游源码）

1. **doxygen → gen_enums.py**。上游 `bindings/cxx/Doxyfile` 用 doxygen 从 `libsigrok.h` 的枚举生成 `enums.hpp`。CI 环境没有 doxygen，且枚举生成本质是「机械解析 C 头文件」，因此改由 `patches/gen_enums.py` 直接解析已安装的 `libsigrok.h`，产出 `enums.hpp` + `enums.cpp`。11 个枚举（LogLevel / PacketType / Quantity / Unit / QuantityFlag / ConfigKey / Capability / DataType / ChannelType / TriggerMatchType / OutputFlag）全部生成。
2. **autotools + libtool → 直接调用 clang++**。`bindings/cxx/` 的 autotools 目标依赖 libtool 与已构建的 `libsigrok.la`；OHOS 上用 libtool 包装共享库会额外引入 `.la` 路径与 wrapper 脚本问题。本包直接用目标 clang++ 编译 `classes.cpp`（它通过 `#include <enums.cpp>` 内联枚举实现）并链接成 `libsigrokcxx.so.0.5.2`，显式设置 `-Wl,-soname,libsigrokcxx.so.0`。
3. **上游无 test 目标（R51 清点证据）**：

   - **清点结论：本包上游测试 = 0 个**。
   - 清点对象与命令（对 conan 已按 sha256 校验解压的源码树执行，路径
     `<conan-home>/p/libsi…/s/`，即 `libsigrok-0.5.2/`）：
     - `ls bindings/cxx/` → 仅 10 个条目：`classes.cpp`、`ConfigKey_methods.{cpp,hpp,i}`、
       `QuantityFlag_methods.{cpp,hpp}`、`enums.py`、`Doxyfile`、`libsigrokcxx.pc.in`、`include/`；
     - `find bindings/cxx -maxdepth 1 \( -name Makefile.am -o -name Makefile.in -o -name '*test*' \)`
       → **0 命中**（既无构建测试目标，也无任何测试源文件）；
     - `ls tests/ | grep -i 'cxx\|bindings'` → **0 命中**。
   - 源码树里确有 `tests/*.c`（Check 框架），但**归属 C 库 `libsigrok/0.5.2`**：
     其中 12 个文件含用例，`grep -c START_TEST` 合计 69、`grep -c tcase_add_test` 合计 68；
     `libsigrok/0.5.2` 归档登记 `upstream_check_cases: 76` / `upstream_suites: 12`（12 与
     实测套件数一致），76 出自该包 W3 日志的 Check 断言行 `Checks: 76, Failures: 0, Errors: 0`
     （断言执行次数，非用例条数）。该结论已在那边统计，**不计入本包**，本包也不重复执行。
   - 因此本包的可执行验证由 `test_package` 消费者探针承担（1 消费者用例 + 2 项鸿蒙特有检查，
     见 `reports/test-report.md`）。

## GLib 版本冲突的处置（本包的关键决策）

两个直接依赖把 GLib 钉在不同版本上：

| 依赖 | 钉住的 GLib | 该 GLib 的形态 |
|------|-------------|----------------|
| `libsigrok/0.5.2` | `glib/2.88.0` | **static**（`shared=False`） |
| `glibmm/2.66.7.1` | `glib/2.84.0.1` | **shared** |

同一个 conan 图里容不下两个 glib 版本，必须由上层 recipe 用 `override` 归一。

**归一到哪一侧不是随便选**：先试过归一到 `glib/2.88.0`（即随 libsigrok 走），结果是重建后的 `glibmm/2.66.7.1` 测试套件 31/33 当场 `SIGABRT`：

```
Bail out! GLib:ERROR:../glib/gquark.c:63:g_quark_init: assertion failed: (quark_seq_id == 0)
```

原因是 static glib 会被静态链进 `libglibmm-2.4.so.1` 与 `libgiomm-2.4.so.1` 两个共享库，进程里出现两份独立的 GLib 全局状态，`g_quark_init()` 第二次进入即断言失败。

改归一为 **`glib/2.84.0.1`（shared）** 后：
- `glibmm/2.66.7.1` 直接复用制品仓已发布 binary（package_id `91be7014a920f4…`），**不需要重建**；
- 只有 `libsigrok/0.5.2` 因 package_id 变化在干净环境需要源码重建（本机缓存中已有匹配 binary，conan 图本轮判定为 `Cache`）；其上游 Check（该包 W3 日志断言行 `Checks: 76, Failures: 0, Errors: 0`）由 `libsigrok/0.5.2` 配方自身强制校验，结论登记在该包归档中，不计入本包。

这一现象与 `E538`（统一 C++17/libc++ profile 后发布依赖图选项不一致）和 `DRAFT-24650`（conan 2 override 改 package_id → binary 失配 → 源码重建）同源。

## OHOS 签名

仓库中所有已发布 OHOS 库（`libsigrok`、`libsigc-2.0`、`libglibmm-2.4`）都带 `.codesign` 段；未签名的 ELF 在设备上无法加载。因此本包把签名做成**强制步骤**（对齐 `libsigrok/0.5.2` 的 `_sign_elf`）：`binary-sign-tool` / `readelf` 缺失直接 `ConanInvalidConfiguration`，签名后复核 `.codesign` 存在，已带签名的副本先用 `llvm-objcopy` 去签再重签。

## 消费者验证（真实执行）

本机 worker 就是 OHOS aarch64，`can_run` 为真，因此消费者探针是**真的跑起来**而不是只编译：

```
api: LogLevel=NONE(0) PacketType=LOGIC(10004) Quantity=VOLTAGE(10000)
enum: Quantity::values() -> 33 entries
closure: loaded libsigrokcxx.so.0 -> 0x…      ← dlopen 句柄地址，每次运行不同
libsigrokcxx consumer probe: OK
CONSUMER_1_OF_1_PASS
```

其中：
- `Quantity::values()` 读的是 `sigrok::EnumValue<...>::_values` —— 该符号只在 `libsigrokcxx.so.0` 内部定义，能读出 33 条即证明链接到的是真库而非头文件；
- `closure: loaded libsigrokcxx.so.0` 是鸿蒙特有非断言用例（rule12）：`dlopen(RTLD_NOW)` 强制解析整条 `DT_NEEDED` 闭包，观测加载结果，不断言具体值。

## 构建证据

- 驱动命令（与 CI 同路径，走 `ci/conan` 脚本）：`bash ci/conan/build_and_test.sh libsigrokcxx/0.5.2`
- 结果（原始日志 `reports/w3-local-ci.log`）：
  - `libsigrokcxx/0.5.2: Forced build from source`
  - `libsigrokcxx/0.5.2: libsigrokcxx.so.0.5.2 signed (.codesign verified)`
  - `libsigrokcxx/0.5.2: libsigrokcxx built successfully`
  - `libsigrokcxx/0.5.2 (test package): consumer built successfully (compile + link OK)`
  - `libsigrokcxx/0.5.2 (test package): CONSUMER_1_OF_1_PASS`
- G2（`conan-verify` 内的独立 `conan create`）另有一份日志 `reports/conan-create.log`；本轮该图全部命中缓存（`Cache`），未重建
- 依赖：`glib/2.84.0.1`、`glibmm/2.66.7.1`、`libsigc/2.10.8`、`libzip/1.11.4`、`pcre2/10.45`、`zlib/1.3.1.1` 均取自制品仓；`libsigrok/0.5.2` 本轮由缓存复用，其上游 Check 由该包配方自身强制校验
- 产出库属性：`SONAME=libsigrokcxx.so.0`，`DT_NEEDED` 为 `libsigrok.so.4 / libglibmm-2.4.so.1 / libgiomm-2.4.so.1 / libglib-2.0.so.0 / libsigc-2.0.so.0 / libc++_shared.so / libc.so`
- 完整性：`reports/w3-local-ci.log` 的 SHA-256 由 `finish` 记入 `.ci-result.json`（`log_sha256`），并附 `integrity_hash = sha256(timestamp:software:version:exit_code)[:16]` 防伪造；两者已复核一致

## 已知限制

- 依赖 `libsigrok/0.5.2` 的 binary 在干净环境可能因 package_id 随 glib 归一变化而失配，CI 侧会走 `--build=missing` 重建这一步；重建耗时与其上游 Check（由该包配方强制校验）测试时长需计入构建预算。
- 底层 libsigrok 以 `--without-libusb` 构建，本包只声明 bindings 层可用，不声明 USB 采集可用。
### 对话 #1 [2026-10-15]

- 问题: 把 libsigrokcxx 0.5.2（libsigrok 源码树中的 `bindings/cxx/` C++ 绑定，无独立 tarball）
  适配到 HarmonyOS PC (aarch64)；要求核验上游测试入口、真实构建、test_package 与鸿蒙非断言
  消费者用例、conan-verify/finish/W2/W3 与 PR 文件原子性。
- 操作: 建立隔离 worktree（`feat/libsigrokcxx-0.5.2`，基线 `official/main` `b544378a4e`）→
  R36 逐项 `conan download` 验证依赖可消费 → 定位 glib 静态/动态冲突并归一到
  `glib/2.84.0.1`(shared) → 以 `gen_enums.py` 替代 doxygen、以 clang++ 直编替代
  autotools/libtool → 强制 `.codesign` 签名 → 跑通 conan create / conan-verify(G0-G4+L2/L4/L5)
  / W3 本地 CI 模拟。
- 结果: 构建成功；消费者探针在 OHOS aarch64 上**真实运行** 1/1（枚举 API +
  `Quantity::values()` 33 条 + closure `dlopen`）；上游 `bindings/cxx/` 经核验既无测试入口
  也无测试源（0 用例，如实申报）；提交前按流程 STOP 等待确认。
---

**编译结束**: 2026-10-15 19:30
**最终状态**: built
