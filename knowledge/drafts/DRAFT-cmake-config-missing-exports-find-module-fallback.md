# OHOS SDK 的 CMake config 包导出目标引用缺失工件时 find_package 配置期即硬错——应禁用该包查找，改走上游自带 Find 模块并显式注入路径变量（libclang/Clang 案例）

> Contributor: irony-mode-1.6.1 适配 | Status: Draft（未合入，最终编号 Exxx 由主编确认） | Updated: 2026-10-09
> Source: archives/i/irony-mode/1.6.1（PR irony-mode 1.6.1 适配；触发事件 = 该 run 权威 CI run1 真实构建失败）
> 申报域: 八分类之**构建系统语义**（兼涉工具链行为） | 分层: L1（平台 SDK 打包语义，单库可申报，enzyme run 为事实第二实例） | 阻塞面: 构建失败（真实 CI 失败日志为证）

## 现象

在 OHOS PC 上对依赖 libclang 的 CMake 工程（irony-mode 1.6.1 `server/src/CMakeLists.txt:4`
的 `find_package(Clang)`）执行 `conan create`，**配置期**（CMake include 阶段，先于任何
生成逻辑）即硬错：

```
CMake Error at .../native/llvm/lib/cmake/llvm/LLVMExports.cmake:1150 (message):
  The imported target "LLVMDemangle" references the file
     ".../native/llvm/lib/libLLVMDemangle.a"
  but this file does not exist.
-- Configuring incomplete, errors occurred!
```

CI run1 实测：`conan create` 失败（CI_EXIT=1），L1_RESULT=fail。

## 机理（root cause）

OHOS 系统 SDK（`llvm-config --prefix` 所指的 native/llvm）只发布共享库
（libclang.so / libclang-cpp.so / libLLVM.so），**不发布任何静态归档**；但其
`lib/cmake/llvm/LLVMExports.cmake`（及 clang 侧 `ClangTargets.cmake`）按
`install(EXPORT)` 惯例声明 STATIC IMPORTED target，`IMPORTED_LOCATION` 指向
`lib/libLLVMDemangle.a`、`lib/libclangBasic.a` 等不存在的文件，并在 exports 文件内
逐个 EXISTS 校验、缺失即 `message(FATAL_ERROR)`。`ClangConfig.cmake` 会级联
`find_package(LLVM)` → `include(LLVMExports.cmake)`，因此任何在该 SDK 前缀上执行
`find_package(Clang)`/`find_package(LLVM)` 的工程都在 configure 期中断。

这不是消费方库的 quirk：同一 SDK 对所有库一致复发——irony-mode 1.6.1 的
`find_package(Clang)` 与 enzyme 0.0.284 的 `find_package(LLVM)` 两次独立命中同一
exports 文件的同一缺陷。

## 证据

1. **工具实现证据**（自包含，设备新 shell 可跑）：

```bash
LLVM=$(llvm-config --prefix)
ls "$LLVM/lib/" | grep -c '\.a$'                                   # → 0（无静态归档）
test -e "$LLVM/lib/libLLVMDemangle.a" && echo EXISTS || echo "MISSING libLLVMDemangle.a"
grep -n "libLLVMDemangle.a" "$LLVM/lib/cmake/llvm/LLVMExports.cmake" | head -3
```

2. **定向复现**（最小工程，配置期 FATAL，无需 REQUIRED）：

```bash
P="$HOME/tmp/probe-clangcfg"; mkdir -p "$P" && cd "$P"
printf 'cmake_minimum_required(VERSION 3.5)\nproject(probe LANGUAGES CXX)\nfind_package(Clang CONFIG)\n' > CMakeLists.txt
cmake -S . -B build -DCMAKE_PREFIX_PATH="$LLVM" 2>&1 | grep -m1 "not all the files it references"
```

3. **逃逸生效**：

```bash
cmake -S . -B build2 -DCMAKE_PREFIX_PATH="$LLVM" -DCMAKE_DISABLE_FIND_PACKAGE_Clang=ON \
  && grep -n "Clang_DIR:PATH=Clang_DIR-NOTFOUND" build2/CMakeCache.txt
```

4. **真实 CI 日志**：run1 失败日志（LLVMExports.cmake:1150 FATAL → Package build failed →
L1_RESULT=fail）为阻塞面证据；禁 config 查找修复后同 run 分支 CI 全门禁 PASS。

## 方案（rec）：disable-config-package-use-upstream-find-module

- `CMAKE_DISABLE_FIND_PACKAGE_<Pkg>=TRUE`（本例 `<Pkg>=Clang`；**必须为 cache 变量**随
  toolchain 注入）使 find_package 跳过损坏的 config 包；
- 驱动上游自带 Find 模块兜底（irony-mode 自带 `cmake/modules/FindLibClang.cmake`）；
- 显式注入发现变量，避免 Find 模块硬编码发行版路径落空：
  `LIBCLANG_INCLUDE_DIR` / `LIBCLANG_LIBRARY`（经 `llvm-config --includedir/--libdir`
  动态查询后传 cache 变量；R33 禁止硬编码绝对路径）；
- C API 消费者如需资源目录，另注入 `CLANG_RESOURCE_DIR`：clang 须由
  `llvm-config --prefix` 推导为 `<prefix>/bin/clang` 再 `-print-resource-dir`——
  generate 期裸 PATH 查 clang 实测不可靠（llvm-config 查询成功的同一 generate 阶段，
  subprocess 裸名查 clang 报 `No such file or directory`），失败再结构兜底
  `<prefix>/lib/clang/<ver>`（以 `include/stddef.h` 存在为准）。

**验证要求（诚实注记）**：缺 `CLANG_RESOURCE_DIR` 时构建与 `--version` 冒烟均正常，
唯 TU 解析报 `'stddef.h' file not found`（irony-mode 1.6.1 适配 run2 首版即如此：
CI WARN + CMakeCache 无该变量 + 包外 TU 探针复现）。**必须用真实 TU 解析冒烟验证
（负例须产出诊断防空转，正例含 builtin 头须零诊断），`--version` 不能证明 resource
dir 可用。**

## 禁止做法（forbid）

- **手工修改系统 SDK 的 `lib/cmake/**` 文件**——SDK 为全机共享（hnp），改动污染其他
  库/用户且 SDK 升级即失效；后果：跨 run 环境漂移、不可复现。
- **配方内硬编码 SDK 绝对路径**（R33）——release CI worker 路径可能不同；应经
  llvm-config/shutil.which 动态发现；后果：换机即失败。

## 退路（fallback，带权衡）

- **cmake-overlay-replace-config**（E286 式）：overlay 重写/替换 LLVMConfig.cmake，
  自建指向单体 libLLVM-15.so 的 IMPORTED target。权衡：掩盖与重造而非修复，维护面大；
  仅当项目确实需要 LLVM CMake 机制（`llvm_config()`、`add_llvm_library`、TableGen）
  时才值得——C API 消费者不应退到这一档。
- **self-build-llvm-with-clang**：conan 自编 `LLVM_ENABLE_PROJECTS=clang`。权衡：构建
  成本极高；现有 archives/l/llvm 包 `LLVM_ENABLE_PROJECTS=""` 无 libclang，属最后退路。

## 与现有知识的关系（similar_to）

去重基准（修正）：以**本 run worktree（active base `fc7d3c42`）的 `knowledge/`** 为唯一基准
重扫——`knowledge/drafts/` 实测 3026 个 `.kv`，`knowledge/graph/` 全量 grep
`CMAKE_DISABLE_FIND_PACKAGE|LLVMExports|ClangConfig|find_package(Clang)|FindLibClang|CLANG_RESOURCE_DIR|config 模式|config 包`。
早前"233 文件/仅两相邻/零命中"的表述基于设备主仓旧谱系快照，作废。真实相邻与差异：

- **DRAFT-stale-config-mode-cmake-cache**（最近邻·同解法·同错误签名族）：其
  error_signature `The imported target "<pkg>" references the file "<abs-path>" but this
  file does not exist` 与本条 run1 报错几乎同文，解法同为
  `CMAKE_DISABLE_FIND_PACKAGE_<Pkg>`。**差异**：根因是 CI Worker 上残留的三方发布坏包
  （freetype-config.cmake 指向打包者本机绝对路径 `libfreetype.a`），属环境残留、逐机偶发
  →解法到"disable + 上游跳过可选组件"即止；本条根因是**系统 SDK 出厂即缺静态归档**
  （exports 承诺与安装工件不符），平台保证对所有库一致复发，且解法链更长：disable 之外
  还须**上游 Find 模块兜底 + llvm-config 动态注入 LIBCLANG_*/CLANG_RESOURCE_DIR**（否则
  configure 虽过、libclang 不可用）。
- **E451**（graph；clang/LLVM 消费·ClangConfig 邻接）：关键词族同（find_package(Clang)、
  ClangConfig.cmake、CMAKE_PREFIX_PATH）。**差异**：E451 场景是 conan clang 包（自带完整
  config、含组件目标）被 CMakeDeps 生成的裸 ClangConfig **遮蔽**→解法是"只用
  CMakeToolchain、让 find_package 命中完整 config"；本条是系统 SDK 的 config **本身损坏**
  （include 期即 FATAL）→必须反向"禁用该 config 查找"。两者互为反向操作，且 E451 的前提
  （存在可用的完整 config）在本条场景中不成立。
- **E429-draft-0B67**（OpenMP·同款 disable 手法）：同样用
  `CMAKE_DISABLE_FIND_PACKAGE_<Pkg>`（OpenMP）切断错误接线。**差异**：E429 根因是上游
  "只判 `TARGET OpenMP::OpenMP_CXX` 存在"的错误接线 + SDK 自带 libomp 造成误链接（问题
  显现于**链接/运行期** `__kmpc_*` 未定义符号）；本条根因是 SDK exports 与工件不一致，
  问题显现于**配置期** include 硬错；E429 无"Find 模块兜底 + 动态注入变量 + 资源目录"
  维度，affected_scope 亦不同（OpenMP 多线程库 vs libclang C API 消费者）。
- **E286**（enzyme，graph 内 draft，自标未合入）：同根因机制面——其 root_cause(1) 已记载
  "LLVMExports.cmake 引用不存在的 .a stub（LLVMDemangle.a 等），find_package(LLVM) 触发
  FATAL_ERROR"，与本条互为事实第二实例。但 E286 面向 **LLVM C++ 插件/pass 类库**（需
  AddLLVM/TableGen/lit 全套机制），解法为 cmake-overlay + stub tblgen + skip lit；未提
  CMAKE_DISABLE_FIND_PACKAGE、上游 Find 模块兜底、LIBCLANG_* 显式注入、
  CLANG_RESOURCE_DIR。本条是**不同解法类**：libclang C API 消费者的最小逃逸，问题域与
  方案空间与 E286 互为补集。
- **E218**（CastXML）：OHOS SDK LLVM monolith 运行期族（运行期双 dylib 问题），与本报
  构建期问题互补，同属"OHOS SDK LLVM 消费"知识族。
- **同款 disable 手法的其他散见**（技术同源、根因均不同，不构成重复）：DRAFT-kuickshow
  （KF6DocTools 可选组件裁剪双保险）、DRAFT-kf5windowsystem（X11 探测式后端关闭）、
  DRAFT-libical3（坏 .pc 改走 CMakeDeps+手动注入）、DRAFT-libkolabxml（XSDCXX 环切断）、
  libktorrent（OpenSSL→libgcrypt 后端切换）、E543-draft（KDEInstallDirs 宏模块可选禁用）、
  DRAFT-libgsasl（gnulib AC_LIB_HAVE_LINKFLAGS 系统前缀污染，自认与
  CMAKE_DISABLE_FIND_PACKAGE 同类）；另有 DRAFT-lfortran-llvm-dylib-component-fallback
  （制品仓 LLVM dylib 聚合包无组件目标——"包内容缺口"邻接，但非 config/exports 与工件
  不一致的配置期硬错）。以上均无"系统 SDK 出厂缺静态归档"根因与"Find 模块兜底 + 动态
  注入 + CLANG_RESOURCE_DIR"解法链。
- DRAFT-clang-ohos-native-llvm-toolchain（E258 候选）：从 llvm-project 原生构建工具链
  （反向场景），不覆盖 find_package 消费方逃逸，无冲突。

**本条未被覆盖的增量**：①根因定性为"平台 SDK 出厂打包语义缺陷"（exports 承诺 vs 实际
工件），区别于环境残留（stale-config）、遮蔽（E451）、错误接线（E429）、插件机制缺失
（E286）；②给出 C API 消费者的最小解法链（禁 config → 上游 Find 模块 → llvm-config
动态注入三件套 + CLANG_RESOURCE_DIR），且该解法链带双实例支撑（irony-mode find_package
(Clang) 与 enzyme find_package(LLVM) 命中同一缺陷文件）。

## 泛化（affected_scope）

任何在 OHOS PC 上经 CMake `find_package` 消费系统 SDK 包、且该包 Config/Exports 引用
缺失工件的项目；典型为 libclang/LLVM 的 C API 消费类（补全服务、clang 工具封装、语法
分析前端服务）。机理对任何"Config 包导出缺失工件"的平台包成立，不限于 LLVM/Clang。

## principles

P010（必须使用 LLVM 工具链——本方案是系统 SDK LLVM 的正确消费方式；禁改 SDK 亦属共享
环境完整性约束）。

## 验证状态

- **机制逃逸（禁 config + Find 模块 + LIBCLANG_* 注入）：已验证**。irony-mode 1.6.1 适配
  CI run1 FAIL → 修复后 run2 PASS（run2 全门禁通过）。
- **`CLANG_RESOURCE_DIR` 注入 + TU 解析：已验证（run3，path-update 后）**。run2 首版实际
  未生效（generate 期裸 PATH 查 clang 失败：WARN `No such file or directory: 'clang'`，
  CMakeCache 无该变量，上游 try_run NUM_DIAGNOSTICS=1；包外 TU 探针报
  `'stddef.h' file not found`）→ 加固（llvm-config --prefix 推导 `<prefix>/bin/clang` +
  `<prefix>/lib/clang/<ver>` 结构兜底 + test_package TU 冒烟）后 run3 实测：cmake 命令行
  带 `-DCLANG_RESOURCE_DIR=<prefix>/lib/clang/15.0.4`、全程无 WARN，TU 冒烟正例（含
  `<stddef.h>`）零诊断、负例（未声明符号）按预期产出 "use of undeclared identifier"，
  包外独立探针（仅 LD_LIBRARY_PATH）同样零诊断。
