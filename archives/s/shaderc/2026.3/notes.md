# shaderc 2026.3 （OHOS arm64）适配说明

## 一、软件与产物

- 上游：`google/shaderc`，tag `v2026.3`（与制品仓版本号 `2026.3` 对齐）
- 语言：C++（主体），构建系统 CMake，构建工具 ninja
- 本包交付：`libshaderc` 系列静态库 + `glslc` 命令行（GLSL/HLSL → SPIR-V）
- 外部依赖：无。glslang / SPIRV-Tools / SPIRV-Headers 随源码树同源构建，不引用制品仓内的同名独立包

## 二、源码与 third_party 布局（本包最关键的适配点）

shaderc 主仓**不携带 git 子模块**（`third_party/` 下仅有 `CMakeLists.txt`），其构建要求同级的
`third_party/{glslang,spirv-tools,spirv-headers}` 三个源码目录，且 SPIRV-Tools 额外要求
自身 `external/spirv-headers` 下有同源副本。三者的提交由上游 `DEPS` 文件固定：

| 组件 | 固定提交 |
|---|---|
| glslang | `168d452a4f460d24b588fed08477a81c44ee27a1` |
| SPIRV-Tools | `b707790a898e44038547df54580022fc1cf89c3d` |
| SPIRV-Headers | `29981f65241605e08b0ede4cfeb999fe3b723c6a` |

配方在 `source()` 中按上表提交拉取三份 tarball 并还原该目录布局（含 `external/spirv-headers` 副本拷贝）。
之所以不复用制品仓内已归档的同名包：其版本与上游 DEPS 固定提交不一致，会引入行为与 ABI 差异。

## 三、OHOS 适配点

1. `-Werror` 与 OHOS clang 驱动冲突：OHOS clang 会向编译命令注入 `--gcc-toolchain=<sdk>`
   一类参数，shaderc 默认开启的 `-Werror` 将其判为 `-Wunused-command-line-argument` 直接报错。
   配方以 `SHADERC_ENABLE_WERROR_COMPILE=OFF` 关闭该开关（不改动上游源码）。
2. 产物裁剪：`SHADERC_SKIP_TESTS / SHADERC_SKIP_EXAMPLES / SHADERC_SKIP_COPYRIGHT_CHECK=ON`；
   vendored 组件的可执行文件一律不构建（`ENABLE_GLSLANG_BINARIES=OFF`、`SPIRV_SKIP_EXECUTABLES=ON`）；
   打包阶段再清理 vendored 的头文件、CMake 包配置与共享库，使本包只对外提供
   shaderc 头文件、静态库与 `glslc`。
3. 共享库 SONAME（知识库条目 E092）：构建侧 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 无对应 platform module，
   上游 `libshaderc/CMakeLists.txt` 的 `SOVERSION 1` 不生效，`libshaderc_shared.so` 既无版本后缀也无 `DT_SONAME`。
   本包声明为 `static-library`，故在 `package()` 阶段剔除该共享库，并把 `lib/pkgconfig/shaderc.pc` 的链接项
   改写为静态库；`glslc` 已静态链接，仅依赖 `libc++_shared.so` 与 `libc.so`。
   `CMAKE_AR` / `CMAKE_RANLIB` / `CMAKE_NM` / `CMAKE_STRIP` 无需配方覆盖：CMake 依 clang 驱动自动解析为
   LLVM 版工具（实测 `llvm-ar` / `llvm-ranlib` / `llvm-nm` / `llvm-strip`），故未使用 E012。

**未对上游源码打任何补丁**（`patches/` 为空，`conandata.yml` 的 `patches` 为空列表）。

## 四、上游测试与结果

上游测试依赖 googletest / effcee / re2 / abseil（仅测试期使用），本包不构建它们，
但测试套件本身是纯 Python 驱动（只需 `glslc` 与 `spirv-dis`），故在完整构建树上实测：

| 套件 | 用例数 | 结果 |
|---|---|---|
| `glslc/test/expect_unittest.py` | 4 | 通过 4/4 |
| `glslc/test/glslc_test_framework_unittest.py` | 2 | 通过 2/2 |
| `glslc/test/glslc_test_framework.py`（集成用例） | 445 | 通过 445/445 |

集成套件在**构建目录路径不含 `.` 时** 445/445 全通过。若构建目录名为默认的 `<name>-<version>.work`
（路径含点），`TestShaderStageWithNoExtension` 一项会失败：上游 expect 框架用**整条路径**做扩展名截断
（`rsplit('.', 1)`），路径中的目录名被误当作扩展名，导致对无扩展名输入的产物名推导错位。
该现象由构建路径引发，与本适配无关，故可通过更换构建目录名规避。

## 五、端到端功能验证

`glslc` 在本机（OHOS arm64 真机）可直接运行，实测链路：

```
glslc -fshader-stage=vert -o shader.vert.spv shader.vert   # GLSL → SPIR-V，magic 0x07230203
spirv-val shader.vert.spv                                  # 判定为合法 SPIR-V
spirv-dis shader.vert.spv                                  # 可反汇编回文本
```

## 六、对话记录

### 对话 #1 [2026-10-13] 共享库 SONAME 与交付面复核

- 问题: 复核发现 `libshaderc_shared.so` 无 `DT_SONAME`（`readelf -d` 仅两条 `NEEDED`），且它会被
  `collect_libs()` 收进 `cpp_info.libs`，消费者将连带链接该共享库；同时 `pr-body.md` 与本文件原记有
  「配方对 OHOS 显式覆盖 CMAKE_AR / CMAKE_RANLIB」「使用知识库 E012」两处表述，与配方实际内容不符。
- 操作: 逐项复算——`grep -nE "CMAKE_AR|CMAKE_RANLIB|CMAKE_SYSTEM_NAME" conanfile.py` 零命中；
  查 conan 构建树 `CMakeCache.txt`，`CMAKE_AR`/`CMAKE_RANLIB`/`CMAKE_NM`/`CMAKE_STRIP` 由 CMake 依 clang
  驱动自动解析为 `/data/service/hnp/bin/llvm-ar|llvm-ranlib|llvm-nm|llvm-strip`；查 SDK `native/llvm/bin`
  确认 `llvm-ranlib` 存在。随后在 `package()` 中新增 `_drop_soname_less_shared_lib()`，剔除该共享库并把
  `lib/pkgconfig/shaderc.pc` 链接项改写为静态库，并在本文件订正上述两处表述、改记真实适配点（E092/E383）。
- 结果: `conan create` 复跑通过，包内 `lib/` 只剩三个静态库，`shaderc.pc` 指向 `-lshaderc -lshaderc_util`；
  真门禁 `conan-verify` 的 G0–G4 全 PASS。

### 对话 #2 [2026-10-13] 断言口径与测试包 shell 取用

- 问题: `test_package/MANIFEST.yml` 的 `assertion_count: 468` 与实测口径（445+4+2+13=464）不符；
  `test_package/conanfile.py` 用 `shutil.which("bash")` 取 shell，依赖 PATH，脆弱且与仓库模板不一致。
- 操作: 按框架模板与既有归档约定改为 `os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")`，
  并订正 `assertion_count` 为 464。
- 结果: 消费者测试 13/13 通过，与门禁 `conan create` 日志一致；`conanfile.py` 中 `_install_shaderc_util`
  的异常类型同步改为 `ConanException`。

### 对话 #3 [2026-10-13] 收尾门禁暴露的档案缺口

- 问题: `ohc-run.py finish` 收尾报 Step6 `finalize-archive` 缺失 1 项（软件级 `README.md` 不足 5 行）与
  一致性问题 1 项（`notes.md` 缺 `### 对话 #` 记录）；W5 知识检查 `unreferenced=3`（`knowledge_gained`
  三条未标注证据引用）；Step10 缺 `.staging-verified` 标记。
- 操作: 按其判据逐项补齐——软件级 `archives/s/shaderc/README.md` 改写为「上游/许可证/语言/依赖 + 版本索引
  + 平台说明」；本文件补「对话记录」（即本节）；`manifest.yaml` 的 `knowledge_gained` 每条追加
  `(reference: …)` 并新增 SONAME 一条；解包 `packaging/shaderc-2026.3-ohos-aarch64.tar.gz`，实测
  `bin/glslc --version` 与 GLSL→SPIR-V 编译（magic `0x07230203`）通过后写入 `.staging-verified`。
- 结果: 收尾各步转正。仍存两条属框架侧问题并已记录待框架 PR 处理：`clean_verify.py` 对 CMake 项目
  无条件执行 `./configure`（exit 127）；`finish.py` 的 `step6_gen_summary` 生成摘要时抛
  `'str' object has no attribute 'append'`。
### 对话 #4 [2026-10-14] CI 编译失败归因（worker fork EAGAIN）与配方加固

- 问题：PR #15630 的 `conan-build-test` 在 CI-010（build #90378）与 CI-022（build #91195）
  两次失败，日志停在 `cmake.configure()`：CMake 编译器可用性探测的 try-compile 报

  ```
  Run Build Command(s): cmake -E env VERBOSE=1 /data/service/hnp/bin/make -f Makefile cmTC_*/fast
  resource temporarily unavailable
  ...
  Check for working C compiler: /data/service/hnp/bin/clang - broken
  Call Stack: CMakeLists.txt:17 (project)
  ```

  即失败发生在 `build()` **第一个** make 子进程上，彼时尚未执行任何本包构建逻辑。
- 归因（判环境，不判配方）：同一份配方在 CI-028（build #89806）用**同一个**
  `-G "Unix Makefiles"` 生成器完整构建通过（L0/L1 门禁与 test_package 全绿）。两次失败
  之间配方只改了 `package()` 阶段与文档/元信息（`0eb1013` / `6e403ce` / `aa9c6fc`），
  与配置阶段无因果。`resource temporarily unavailable` 是 fork/exec EAGAIN（worker 进程/
  句柄耗尽）的裸 strerror 文本，与仓库既有签名同族：mgen #70890
  （`clang++: Resource temporarily unavailable`）、libcolord #70263（`[Errno 11]`）、
  islamic-menus #14595（同一步「CMake 编译器探测 + make」同报此文）。两台失败 worker 的
  同一轮日志里连源码预下载都因 `curl` 缺失而全部失败（`[Errno 2] No such file or
  directory: 'curl'`），属 worker 侧状态而非包内行为。
- 操作（不改测试口径、不跳过任何测试）：
  1. `build()` 的 CMake 配置改为按 EAGAIN 签名退避重试（4 次，20/40/60s 退避；重试前清掉
     上一次失败留下的 `CMakeCache.txt` / `CMakeFiles` 半截探测结果）。签名从异常串与 CMake
     自身的 `CMakeFiles/CMakeConfigureLog.yaml` / `CMakeError.log` / `CMakeOutput.log`
     两路回查（conan 抛出的是不带 try-compile 原文的 `Error 1 while executing`）。
     **仅签名命中才重试**，真实配置错误一次即抛，避免重试掩盖缺陷。
  2. 生成器固定为 Ninja（按 `HMBS_NINJA` → `user.hmbs:ninja_path` → PATH → hnp 顺序探测）
     并钉死 `CMAKE_MAKE_PROGRAM`：Makefiles 生成器要额外 fork `/bin/sh` 执行每条规则，
     在进程/句柄紧张的 worker 上是 try-compile 最先失败的环节（知识 E346）；探测不到 ninja
     时保持 conan 默认生成器，行为与改动前完全一致，不引入新的硬依赖。主配方与
     `test_package` 同步加固（L1 消费者同样要跑 `cmake.configure()`）。
- 结果：本地 W3 复验（`finish` 内嵌 `ci/conan/build_and_test.sh`）exit 0——
  `Success: 1 / Failed: 0`，G2 `conan create` 与 test_package 消费者测试全通过；
  日志已确认生成器生效：`cmake -G "Ninja" -DCMAKE_MAKE_PROGRAM="/data/service/hnp/bin/ninja"`
  （包内与 test_package 两处配置均如此）。测试用例数、断言口径与产物交付面均未变。
---

**编译结束**: 2026-10-14 19:02
**最终状态**: built
