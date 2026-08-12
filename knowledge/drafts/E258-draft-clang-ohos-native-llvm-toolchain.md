# E258-draft — OHOS 真机原生构建 clang/llvm 工具链需组合处理平台识别、SDK 运行时捆绑与签名

- **id**: `E258`
- **来源**: clang/22.1.8 适配尝试（llvm-project 真机原生构建，PR !3868，分支 feat/clang-22.1.8）
- **状态**: 草稿（未由主编审核合入，对应 kv 见 `E258-draft-clang-ohos-native-llvm-toolchain.kv`）
- **难度**: 中等（上游 check-clang/check-llvm lit + unittest 约 3–4 万量级）

## 错误特征

```
Unable to determine platform
config.guess: unable to guess system type
get_host_triple: ... (LLVM 不认 uname=HarmonyOS)
CMake Error: ... does not define the platform (缺 Platform/HarmonyOS)
undefined reference to `clang_rt.crtbegin' / `clang_rt.crtend'
error: unable to find library -lc++ (缺 libc++_shared.so)
Permission denied / Operation not permitted (未签名 ELF/.so 被 OHOS XPM 拦截)
file too large / 408MB (静态 clang 触碰制品仓单文件上限)
OHOS_SDK_LLVM_ROOT ... not a directory / No SDK clang resource dir
```

## 根因

在 HarmonyOS PC 真机上从 llvm-project 原生构建可分发的 clang 工具链时，失败不是
单个补丁能覆盖的孤立 bug，而是一组相互耦合的平台约束：

1. **平台识别**：设备 `uname=HarmonyOS`，LLVM 自带 `config.guess`/`get_host_triple`
   失败（`Unable to determine platform`）；CMake 缺 `Platform/HarmonyOS` 会 FATAL。
2. **交叉陷阱**：若为"修平台"而设 `CMAKE_SYSTEM_NAME=HarmonyOS`，会把构建变成交叉
   编译，主机工具 tblgen 崩溃（E019 类交叉链路）。
3. **运行时缺口**：仅 `-DLLVM_ENABLE_PROJECTS=clang` 且不编 runtimes 时，安装树缺
   crtbegin/crtend/builtins 与 libc++_shared.so，自编 clang 无法完整链接 C/C++。
4. **体积上限**：静态链接 clang 体积可达数百 MB，触碰制品仓单文件上限。
5. **XPM 签名**：OHOS 要求 bin/ ELF 与 lib/*.so 经 binary-sign-tool 自签，否则
   dlopen/exec 报 Permission denied。

既有条目分别覆盖 autotools config.guess（E007/E160）或一般 CMake 平台识别，未把
「LLVM 真机原生 + 不设 SYSTEM_NAME + SDK clang_rt 动态捆绑 + dylib 瘦身 + ELF 签名」
写成可复用的组合方案。

## 推荐方案

按组合方案处理（`composite-ohos-native-llvm-clang-toolchain`），而非逐个打孤立补丁：

1. **平台识别组合**：stub 覆盖 LLVM `config.guess` 输出 `aarch64-unknown-linux-ohos`；
   注入 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）；**不设**
   `CMAKE_SYSTEM_NAME`（否则 tblgen 被拖进交叉编译失败）。
2. **自包含运行时组合**：从 OHOS SDK **动态发现** `lib/clang/<ver>/lib/aarch64-linux-ohos`
   与 `libc++_shared.so` 捆绑进包内 resource-dir/lib，缺失则 `ConanException`
   （禁止静默空壳工具链；fallback：要求 `OHOS_SDK_LLVM_ROOT` 且校验存在）。
3. **体积与安全组合**：`LLVM_BUILD_LLVM_DYLIB`/`LLVM_LINK_LLVM_DYLIB` 绕过制品仓单文件
   上限；`binary-sign-tool sign -selfSign 1` 对 bin/ ELF 与 lib/*.so 签名。
4. **验证策略组合**：上游约 3–4 万级 lit/unittest 因 runtime 版本错配、无 runtimes
   工程、musl/glibc、10800s 墙钟等具体技术原因无法整套启用；以 test_package 真实
   编译链接运行（clang --version + C 编译链接运行 + C++ 编译链接运行，3/3）作为
   R34 反空壳证明，并在 MANIFEST/notes 写明豁免技术原因。

```bash
# build:
#   stub config.guess + CMAKE_MODULE_PATH=.../Platform/HarmonyOS.cmake
#   -DLLVM_ENABLE_PROJECTS=clang -DLLVM_BUILD_LLVM_DYLIB=ON
#   -DLLVM_LINK_LLVM_DYLIB=ON -DLLVM_INCLUDE_TESTS=OFF
# package:
#   动态发现 SDK llvm + clang_rt；copy crt/builtins/libc++_shared.so；
#   binary-sign-tool sign -selfSign 1（bin ELF 与 lib/*.so）
# test:
#   test_package 3/3（version + C + C++ 编译链接运行）
```

## 禁止项

- ❌ 设 `CMAKE_SYSTEM_NAME=HarmonyOS` 修平台识别 → 触发交叉编译、tblgen 崩溃。
- ❌ 硬编码 SDK 路径（ohos-sdk_X.Y.Z.W / lib/clang/15.0.4）或静默跳过 clang_rt → 升级即失效、产物不可链接。
- ❌ 在 OHOS CI 上整套启用 check-clang/check-llvm（无同树 compiler-rt、musl 假设）→ 系统性 lit 失败 + 超时。

## 关联

- 相似条目：E007/E160（autotools config.guess）、E019（共享库加载）、E100、E214（LLVM dylib）
- 前置依赖：castxml、cling、enzyme、flang-ohos 等 llvm-project 工具链 / 自编 Clang 驱动链路
- 验证命令：`conan create archives/c/clang/22.1.8 --build=missing`；test_package 3/3
- 关键提交：`e503884c` / `4281c117` / `439ada9f` / `e8b1e877` / `985b2b0c` / `db0a4fdf` / `dd820cd3`
- 作者：yanjiaxin
