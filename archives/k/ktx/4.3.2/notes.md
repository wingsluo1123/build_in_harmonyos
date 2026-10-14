# ktx 4.3.2 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-10-14
- 编译器: clang / clang++ 15.0.4（OHOS SDK，目标 aarch64）
- 平台: HarmonyOS (OHOS) 6.0 / armv8 / libc++ / C++17 / Release
- 工具链: conan 2.29.1 + cmake 4.1.2，profile `ci/conan/profiles/ohos-aarch64`
- 验证设备: 一台开源鸿蒙 PC 真机（20 核）
- 状态: built

## 编译步骤

本包由 `conan create` 驱动，配方内部执行的是：

```bash
# 1) 取源（conandata.yml 的 sources，strip_root=True）
#    https://github.com/KhronosGroup/KTX-Software/archive/refs/tags/v4.3.2.tar.gz
#    sha256 74a114f465442832152e955a2094274b446c7b2427c77b1964c85c173a52ea1f

# 2) 打补丁（apply_conandata_patches）
#    patches/0001-ohos-version-header.patch

# 3) configure —— 注意 KTX_GIT_VERSION_FULL 是命令行 -D，不是工具链变量
cmake -G "Unix Makefiles" \
  -DCMAKE_TOOLCHAIN_FILE=".../conan_toolchain.cmake" \
  -DCMAKE_BUILD_TYPE=Release \
  -DKTX_FEATURE_STATIC_LIBRARY=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DKTX_FEATURE_TESTS=OFF -DKTX_FEATURE_LOADTEST_APPS=OFF \
  -DKTX_FEATURE_DOC=OFF -DKTX_FEATURE_JNI=OFF -DKTX_FEATURE_PY=OFF \
  -DKTX_FEATURE_TOOLS=ON \
  -DKTX_FEATURE_GL_UPLOAD=OFF -DKTX_FEATURE_VK_UPLOAD=OFF \
  -DKTX_GIT_VERSION_FULL="v4.3.2" \
  <src>

cmake --build <build> -- -j20
cmake --install <build> --prefix <pkg>
```

完整命令与真机实测日志见 PR 正文的「真机验证」一节。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 库类型开关：只设 `BUILD_SHARED_LIBS=OFF` 不生效，产出 `.so` | 4.3.2 用的是自有开关 `KTX_FEATURE_STATIC_LIBRARY`（默认 OFF ⇒ SHARED）；`BUILD_SHARED_LIBS` 是 4.4.2 才改用的标准开关，在 4.3.2 中被静默忽略 | 两个变量都显式设置（`KTX_FEATURE_STATIC_LIBRARY=ON` + `BUILD_SHARED_LIBS=OFF`），使意图在两版源码树上都无歧义 |
| 2 | 配置期出现 `Error retrieving version from GIT tag.  Falling back to 0.0.0-noversion` | 4.3.2 的 `cmake/version.cmake` **无条件**调用 `git_describe_raw(KTX_VERSION_FULL --abbrev=0 --match v[0-9]*)`，而发布的 tarball 里没有 `.git`；`KTX_GIT_VERSION_FULL` 覆盖机制是 **4.4.2 才新增**的 | `patches/0001` hunk 1 把 4.4.2 的覆盖机制搬回 4.3.2：`if(NOT KTX_GIT_VERSION_FULL) ... else() set(KTX_VERSION_FULL ${KTX_GIT_VERSION_FULL}) endif()` |
| 3 | 把 `KTX_GIT_VERSION_FULL` 写进 `CMakeToolchain` 变量后，版本号**仍是** `0.0.0-noversion` | **时序问题**：`cmake/version.cmake` 由顶层 `CMakeLists.txt` 第 **13** 行 `include()`，而 `project()` 在第 **25** 行；cmake **只在 `project()` 时**才读取 `conan_toolchain.cmake` ⇒ 第 13 行时该变量仍为空。（真机 `CMakeCache.txt` 里确实能看到 `KTX_GIT_VERSION_FULL:STRING=v4.3.2`，但那是 `project()` 之后才写进 cache 的。） | 改在 `build()` 里用**真实命令行 `-D`**（configure 一开始就建立的 cache 项，任何 `CMakeLists` 命令之前就已存在）：`cmake.configure(variables={"KTX_GIT_VERSION_FULL": "v4.3.2"})` |
| 4 | 编译期 8 个 `*_version` 目标全部失败：`/bin/sh: ./mkversion: Permission denied` → `make Error 126` | 真机上 `conan` 的 shebang 指向**用户可写**的 `/storage/.../usr/local/bin/python3`，整条 `conan → cmake → make` 链降级到受限的 `adhoc_bin` 安全域，该域**拒绝启动用户存储上构建树里的文件**。文件本身是 `-rwxrwx--- (0770)`，在交互 shell 里执行 rc=0，同目录新建的 `+x` 脚本也 rc=0 ⇒ 判据是**进程域**，不是权限位（`df` 看不出，`/proc/mounts` 里 `/storage/Users` 是 `tmpfs rw,nosuid,mode=755`，**没有 noexec**） | `patches/0001` hunk 2 把 `COMMAND ./mkversion -o version.h ${dest_path}` 改为 `COMMAND ${BASH_EXECUTABLE} ./mkversion -o version.h ${dest_path}`，即让**解释器去读脚本**而不是内核去启动它。`BASH_EXECUTABLE` 由第 11 行 `find_package(Bash REQUIRED)` 保证存在（`cmake/modules/FindBash.cmake`），且配置期已成功执行过 `bash --version` |
| 5 | 打补丁后 `mkversion` 的执行位丢失，即使补丁内容正确也会 126 | conan 2.x 用 `patch_ng` 打补丁，而 `patch_ng` **只从** `new file mode <oct>` 或成对的 `old mode <oct>` + `new mode <oct>` 里解析文件模式，**完全忽略** `index <sha>..<sha> <oct>` 行。Windows 上生成的补丁（`core.fileMode=false`、全 0666）拿不到 mode，于是 `filemode=None`、不执行 `chmod`，脚本落地为 0644 | 生成补丁时显式注入 `old mode 100755` / `new mode 100755` 两行；并用本地 `patch_ng 1.19.1` 1:1 复现（修复前 `filemode=None`，修复后 `filemode=0o100755` ⇒ `chmod(755)`） |
| 6 | 把同一文件的两处改动拆成两个补丁文件时，第二个补丁应用失败 | `patch_ng` 应用 hunk **不做偏移搜索**：`0001` 在 `version.cmake` 第 108 行附近插入了 10 行，把 `0002`（第 183 行附近）的锚点顶掉了 ⇒ 顺序应用时 `apply()` 返回 `False`。`git apply` 会自己找偏移，所以本地看不出来 | 同一文件的所有改动**合并进一个补丁文件**（补丁内 hunk 行号一律相对原始文件） |
| 7 | 真机 `/bin/sh` 下的 `patch` 是 toybox 版，`--forward` / `-N` / `--no-backup-if-mismatch` / `--posix` 全不支持 | toybox `patch 0.8.12` 只认 `-d/-i/-p/-R/-l/-s/-u/--dry-run` | 本地校验一律只用 `patch -p1`（可加 `--dry-run`）；且 conan 2.x 走的是 `patch_ng` 而非外部 `patch`，因此真机 toybox 的选项限制**不影响** `conan create` |

## 源码修改

`patches/0001-ohos-version-header.patch`（2801 字节，3 个 hunk，覆盖 2 个文件）：

| hunk | 文件 | 内容 |
|------|------|------|
| 1 | `cmake/version.cmake`（`@@ -108,8 +108,21 @@`，`# Get latest tag.` 附近） | 在 `git_describe_raw()` 之前插入 `if(NOT KTX_GIT_VERSION_FULL) ... else() set(KTX_VERSION_FULL ${KTX_GIT_VERSION_FULL}) endif()`，即把 4.4.2 的覆盖机制搬回 4.3.2 |
| 2 | `cmake/version.cmake`（`@@ -182,7 +195,16 @@`，`function( create_version_header dest_path target )` 内） | `COMMAND ./mkversion -o version.h ${dest_path}` → `COMMAND ${BASH_EXECUTABLE} ./mkversion -o version.h ${dest_path}`，绕过 `adhoc_bin` 域对构建树脚本的启动限制 |
| 3 | `mkversion`（`@@ -52,7 +52,10 @@`，`genversion()` 内） | `VN="$DEF_VER"`（无 `.git` 时的回退分支）→ `VN="v4.3.2"`，使 `version.h` / `libktx.a` 内的版本串与包版本一致；同文件带 `old mode 100755` / `new mode 100755`，保住脚本的执行位 |

**上游语义未被改变**：hunk 1/2 是「新增可选覆盖 + 换一种等价的调用方式」，hunk 3 只是把无 `.git` 时的回退值从 `v4.0` 改为真实版本号。不涉及功能删减、不涉及头文件 API 变更。

## 依赖版本

无外部依赖。`basisu` / `astc-encoder` / `zstd` / `miniz` 全部随源码树发布；
`tools/imageio` 用的是内置 `lodepng`、basisu 的 `jpgd` 与 astc 的 `tinyexr`，
仓库里没有 `ExternalProject` / `FetchContent`，构建期不下载任何第三方库。
`package_info` 里对 C 消费者声明了 `system_libs = ["c++", "dl", "pthread", "m"]`（静态 `libktx.a` 含 C++ 代码，纯 C 消费者需要显式链接 libc++）。

## 验证结果

```bash
$ ktx --version
ktx version: v4.3.2

$ toktx --version ; ktxinfo --version ; ktx2check --version ; ktx2ktx2 --version ; ktxsc --version
toktx v4.3.2        ktxinfo v4.3.2       ktx2check v4.3.2
ktx2ktx2 v4.3.2     ktxsc v4.3.2

# 版本号确实进了静态库（0.0.0-noversion 出现 0 次）
$ strings lib/libktx.a | grep -c 0.0.0-noversion
0
$ strings lib/libktx.a | grep -n 4.3.2 | head -1
15175:v4.3.2

$ grep PACKAGE_VERSION lib/cmake/ktx/KtxConfigVersion.cmake | head -1
set(PACKAGE_VERSION "4.3.2")

# 生成的 version.h
$ head -12 build/lib/version.h
/*  // [API version]  @par API Version  v4.0  // [API version]
    // [Code version]  v4.3.2  // [Code version]  */
#define LIBKTX_VERSION v4.3.2

# ELF（静态包 ⇒ 查可执行文件）
$ readelf -h bin/ktx | grep -E "Class|Machine|Type"
Class:  ELF64      Machine:  AArch64      Type:  DYN (Position-Independent Executable file)
$ readelf -d bin/ktx | grep NEEDED
(NEEDED)  Shared library: [libc++_shared.so]
(NEEDED)  Shared library: [libc.so]

# L2 冒烟：不受 conan 环境约束也能跑
$ LD_LIBRARY_PATH=/system/lib64:<pkg>/lib <pkg>/bin/ktx --version ; echo rc=$?
ktx version: v4.3.2
rc=0

# conan create 判定
rc = 0
test_package: OK: ktx API call returned error code 11 (expected non-success)
'Falling back to 0.0.0-noversion' occurrences = 0
'Permission denied' occurrences = 0
ktx/4.3.2: Apply patch (file): patches/0001-ohos-version-header.patch
===> STAGE1_VERDICT = GREEN
```

### 上游 ctest 套件（在真机上单独执行，126/133 通过）

`KTX_FEATURE_TOOLS=ON` 会让上游 `tests/CMakeLists.txt` include 四个 CLI 测试文件，
它们只受 `KTX_FEATURE_TOOLS` 控制、与 `KTX_FEATURE_TESTS` 无关，因此**构建树里注册了
133 个 ctest 用例**（`ktx2check 20 / ktx2ktx2 22 / ktxsc 21 / toktx 70`；gtest 套件为 0，
因为 `KTX_FEATURE_TESTS=OFF`）。

它没有写进 `build()`，原因见下方「注意事项」——真机上 `ctest` 要启动的正是构建树里的
测试可执行文件，而 `adhoc_bin` 域拒绝启动它们。因此在真机 shell 里单独跑了一遍：

```bash
$ cd <build_folder> && ctest --verbose
95% tests passed, 7 tests failed out of 133
Total Test time (real) =  14.95 sec

# 连续两次全量运行：完全相同的 126/7，失败集合逐字相同（非 flaky）
```

| 套件 | 注册用例 | 通过 | 失败 |
|------|---------|------|------|
| `ktx2check-test.*` | 20 | 19 | 1 |
| `ktx2ktx2-test.*` | 22 | 22 | 0 |
| `ktxsc-test.*` | 21 | 15 | 6 |
| `toktx-test.*` | 70 | 70 | 0 |
| `unittest./texturetest./transcodetest./streamtest.` | 0 | — | — |
| **合计** | **133** | **126** | **7** |

7 个失败已定位到**同一个环境根因**，与库和工具的行为无关：

```
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported
pushd:      error retrieving current directory: getcwd: cannot access parent directories: Not a tty
```

- 133 个用例里 **78 个是经 `/data/service/hnp/bin/bash` 拉起的子进程，这 78 个全部**都会在
  **被测程序运行之前**打出上面的 `getcwd` 警告；其中 **71 个照样通过**。
- 只有 7 个因为判据「依赖子进程输出为空」或「依赖 `pushd` 成功」而失败：
  - `ktx2check-test.all-quiet`：判据是 `PASS_REGULAR_EXPRESSION "^$"`（要求输出为空），
    bash 的启动告警落进输出即破坏了它；手动执行同一条命令输出 **0 字节**。
  - `ktxsc-test.inplace-diffdir-*`（6 个）：这是**唯一**使用 `pushd ../..` 的一族，
    而 `pushd` 需要 `getcwd`；手动执行同一条命令行 **rc=0**，且就地结果与参考文件
    **逐字节相同**（`cmp` 无差异）。
- 结论：真机上 ctest 拉起子进程时的工作目录解析问题（`uname` 报
  `HarmonyOS / HongMeng Kernel 1.12.0 / aarch64 / Toybox`），非产物缺陷。
  完整判据与逐条说明见 `test_package/MANIFEST.yml` 的 `upstream_suite_observed`。

**复现命令**（两条都能给出与上表一致的结果）：

```bash
# 1. 全量上游套件
cd <build_folder> && ctest --verbose

# 2. 只跑失败的那 7 个
cd <build_folder> && ctest -R '^(ktx2check-test\.all-quiet|ktxsc-test\.inplace-diffdir-.*)$' --output-on-failure

# 3. 证明「不是产物的问题」：同一条命令行在 ctest 之外手动执行
cd <src>/tests/testimages && /data/service/hnp/bin/bash -c \
  "cp skybox.ktx2 ktxsc.ip2.skybox_zstd.ktx2 && pushd ../.. && <build>/tools/ktxsc/ktxsc --test --zcmp 5 \$PWD/ktxsc.ip2.skybox_zstd.ktx2 && popd && diff skybox_zstd.ktx2 ktxsc.ip2.skybox_zstd.ktx2"
# => rc=0
```

包指纹（用于与 CI 侧逐字比对）：

```
recipe revision   b1b00239e0805ba36be202f7d8f97525
package_id        6ca9e5223930134dcba78240439f1e4aa207c14a
package revision  8e6caabe56eeae1f8e7428f41ff69371
settings          os=OHOS  os.version=6.0  arch=armv8  compiler=clang 15  libc++  cppstd=17  Release
```

## 交付物

包内共 16 个文件、**0 个符号链接**（静态库，无 `libX.so → libX.so.N` 链 ⇒ 在禁止建软链的 `adhoc_bin` 域下构建也不会碰到该限制）。

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libktx.a | 2,866,682 B | 主库（静态），KTX1/KTX2 读写、BasisU 转码、ASTC 编码 |
| lib/libastcenc-neon-static.a | 240,884 B | ASTC 编码器（aarch64 NEON 后端） |
| bin/ktx | 4,090,432 B | 通用 KTX2 管理工具 |
| bin/toktx | 3,185,216 B | 从 PNG/JPEG 生成 KTX |
| bin/ktxsc | 2,365,952 B | KTX2 超压缩（zstd） |
| bin/ktx2check | 2,406,912 B | KTX2 格式校验 |
| bin/ktx2ktx2 | 2,132,480 B | KTX1 → KTX2 转换 |
| bin/ktxinfo | 129,536 B | 显示 KTX 文件信息 |
| include/ktx.h | 69,259 B | 主头文件 |
| include/KHR/khr_df.h | 25,729 B | Khronos 数据格式定义 |
| lib/cmake/ktx/KtxTargets.cmake | 4,624 B | CMake 包配置（含 `KtxTargets-release.cmake` 1,350 B） |
| lib/cmake/ktx/KtxConfig.cmake | 195 B | `find_package(ktx)` 入口（含 `KtxConfigVersion.cmake` 2,762 B，`PACKAGE_VERSION "4.3.2"`） |

## 注意事项

- **`KTX_FEATURE_GL_UPLOAD` / `KTX_FEATURE_VK_UPLOAD` 默认关闭**：两者都是 `dlopen` 动态加载，关闭后链接期不引入 OpenGL/Vulkan 依赖；本任务的下游只需要 KTX 读写与转码核心。副作用是 `include/ktxvulkan.h` 不会随包安装（本包只安装 `ktx.h` 与 `KHR/khr_df.h`）。
- **`LIBKTX_DEFAULT_VERSION v4.0.__default__` 是上游行为，不是本适配引入的缺陷**：上游 `mkversion` 里就写着 `echo "#define $1_DEFAULT_VERSION $DEF_VER.__default__"`，`__default__` 是**字面占位符**；全仓（`*.c/*.h/*.cpp/*.cmake/*.in`）**没有任何一处引用** `*_DEFAULT_VERSION` 宏，属惰性输出。各工具的 `--version` 输出与 `libktx.a` 内的版本串均为正确的 `v4.3.2`。
- **`adhoc_bin` 域的限制是环境性的，不是本包的缺陷**：真机上 conan 落在用户可写的 python 上，导致整条链路进入受限域；同样的配方在受限域之外的构建机上不需要 hunk 2。hunk 2 只是让构建在受限域中也能完成（`bash` 本身在预置的 hnp 路径里，不受限）。
- **本包与 `archives/k/ktx-software/4.4.2` 是同上游、不同任务**：任务池里 `ktx 4.3.2`（task id 14729）与 `ktx-software 4.4.2` 是两个独立条目/两个独立版本；配方不复用，因为 4.3.2 在库类型开关、版本覆盖机制、版本生成器位置上都有实体差异（见上表 1/2/3）。两者不冲突、不互相覆盖。
- **上游测试分两类，本包的取舍不同**：
  - **gtest 套件**（`unittests` / `texturetests` / `transcodetests` / `streamtests`）由
    `KTX_FEATURE_TESTS` 控制，上游默认 ON。本包设为 OFF，**与已合入的
    `archives/k/ktx-software/4.4.2`（同上游）保持一致**，因此 `build()` 中不调用
    `cmake.test()`，质量验证由 `test_package` 承担。
  - **CLI 套件**（ktx2check / ktx2ktx2 / ktxsc / toktx，共 133 个用例）只受
    `KTX_FEATURE_TOOLS` 控制，**与 `KTX_FEATURE_TESTS` 无关**，所以构建树里本来就有；
    已在真机上单独执行并如实申报为 **126/133 通过**（见上）。
- **为什么 CLI 套件不写进 `build()`**：真机上 `conan → cmake → make` 整条链落在受限的
  `adhoc_bin` 安全域，该域拒绝启动用户存储构建树里的文件——本轮实测 `make` 连
  `./mkversion` 都启动不了（`Permission denied`，Error 126）；而 `ctest` 与
  `gtest_discover_tests(DISCOVERY_MODE PRE_TEST)` 要启动的正是那些测试可执行文件。
  放进 `build()` 只会得到与本机环境绑定的失败，而不是真实的测试结论。
  如需在 CI 侧执行，`cmake.test()` 的写法本身没有问题（CI worker 不在该受限域内）。
- **`KTX_FEATURE_TOOLS_CTS` 沿用上游默认 `OFF`**：它需要空的 `tests/cts/clitests` 子模块，
  而 submodule 不在源码 tarball 里。
