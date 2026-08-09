# llvm 15.0.4 编译笔记（HarmonyOS PC · 标准 Conan cmake · 静态组件版）

## 定位
- 产出 LLVM 15.0.4 **静态组件开发包**：完整 `libLLVM*.a` / `libclang*.a` + `LLVMConfig.cmake` /
  `LLVMExports.cmake` / `ClangTargets.cmake` CMake 导出，AArch64 OHOS（aarch64-unknown-linux-ohos），
  供 AdaptiveCpp 25.10.0 等消费方静态链接（R3 已证 AdaptiveCpp 需要静态归档而非 SDK 的 `.so`）。

## 与 20.1.0 recipe 的差异（静态化原因）
| 维度 | 20.1.0（共享） | 15.0.4（本 recipe，静态） |
|---|---|---|
| 输出 | libLLVM.so 聚合动态库 + 组件 | 全部静态组件 `libLLVM*.a`/`libclang*.a` + CMake 导出 |
| LLVM_BUILD_LLVM_DYLIB | ON | **OFF** |
| LLVM_LINK_LLVM_DYLIB | ON | **OFF** |
| BUILD_SHARED_LIBS | 默认 | **OFF** |
| LLVM_ENABLE_PROJECTS | ""（仅 LLVM） | **clang**（AdaptiveCpp 需 Clang 组件/导出） |
| 动机 | 制品体积（绕过单文件上限） | AdaptiveCpp 编译器插件需静态组件库（R3 首因 libLLVMDemangle.a 缺档） |

## 关键适配（沿用 20.1.0 的 OHOS 真机原生方案）
- 真机原生编译（aarch64→aarch64）：**不设 CMAKE_SYSTEM_NAME** → CMAKE_CROSSCOMPILING=FALSE →
  llvm-tblgen 原生编+跑，绕开 host tablegen 缺口（R4 已证 SDK bin 无 llvm-tblgen/clang-tblgen）。
- config.guess stub：设备 `uname -s = HarmonyOS` 不被 config.guess 识别 → 用 stub 输出
  `aarch64-unknown-linux-ohos`（config-ix.cmake 无条件调用 config.guess，-DLLVM_HOST_TRIPLE 挡不住）。
- Platform/HarmonyOS.cmake：cmake 无 HarmonyOS 平台模块 → UNIX 变量未置 → HandleLLVMOptions FATAL；
  提供 `include(Platform/Linux)` 的平台模块挂到 CMAKE_MODULE_PATH，保持 native。
- OHOS profile：os=OHOS arch=armv8 compiler=clang 15 libcxx=libstdc++11 cppstd=gnu14 Release（R7 已核验）。
- 可选依赖显式关闭：ZLIB/ZSTD/LIBXML2/TERMINFO/LIBEDIT/LIBPFM 全 OFF（R4 已证 host 侧开发头缺失，
  sysroot 仅 zlib.h）；显式关闭不吞错，避免链接到设备不存在的库。

## 依赖边界
- AdaptiveCpp 25.10.0 要求 LLVM >= 15（CMakeLists.txt:420 `if(LLVM_VERSION_MAJOR LESS 15)`），本包 15.0.4 满足。
- 本包为 AdaptiveCpp 的依赖供应：先 conan create 本 llvm/15.0.4 静态包，AdaptiveCpp 经
  `find_package(LLVM CONFIG)` 消费（R3/R7 已证，与 `ACPP_LLVM_COMPONENT=ON` 源码树内方案互斥）。
- libomp/15.0.4 已存在（archives/l/libomp/15.0.4），与本包版本对应，可作组件交叉引用参考。

## R6 源码证据
- 官方 tag：`llvmorg-15.0.4`（annotated tag object `cc892a255ad2f5283a25a02b53d7b92f723df0ff`）
- 解析 commit：`5c68a1cb123161b54b72ce90e7975d95a8eaf2a4`
- 归档：`llvm-project-15.0.4.src.tar.xz`（官方 release 资产，110936424 字节）
- 本地 SHA-256（R6 实算，官方未发布）：`a3112dca9bdea4095361829910b74fb6b9da8ae6e3500db67c43c540ad6072da`
- 许可证：`Apache-2.0 WITH LLVM-exception`（源码根 llvm/LICENSE.TXT）
- 源码位置（OHPC 隔离目录）：`/storage/Users/currentUser/tmp/adaptivecpp-r6-llvm15-source/llvm-project-15.0.4.src/`

## 状态
- `recipe_scaffold`（R8）：文件齐全、静态方案成形，**尚未执行 conan create**。
- 后续唯一 `conan create` 任务所需输入（待分析端下发新 task_id 并获用户授权）：
  - workdir：仓库 `build_in_harmonyos/`，recipe 路径 `archives/l/llvm/15.0.4/conanfile.py`
  - profile：`os=OHOS arch=armv8 compiler=clang 15 libcxx=libstdc++11 cppstd=gnu14 Release`
  - 命令形态（仅文本草案）：`conan create archives/l/llvm/15.0.4 -o shared=False -b missing`（-b missing 待定）
  - 内存约束：空闲仅约 2.3~3GB → LLVM_PARALLEL_LINK_JOBS=2 已写入 recipe，建议限制并行度
  - 预计长耗时：LLVM+Clang 15 全量静态构建数十分钟~数小时量级（未实测，待授权构建验证）
