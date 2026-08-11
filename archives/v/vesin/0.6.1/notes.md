# vesin 0.6.1 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libvesin.so，供 dlopen 及作依赖（供下游作计算依赖，无 CLI 工具）。

## 关键适配
1. **ohos.toolchain 自发现**：conan_toolchain 在 os=OHOS 下把 CMAKE_SYSTEM_NAME 映射成
   cmake 不认的值（ML-0035 "System is unknown to cmake"），配方绕开它，自发现
   `ohos.toolchain.cmake`（profile [conf] user_toolchain → $OHOS_NDK_HOME → SDK glob）。
2. **gpulite 离线携带**：上游 `vesin/CMakeLists.txt:85` 用 FetchContent 从 github 拉
   gpulite；上游自带逃生口——`vesin/external/gpulite.tar.gz` 存在就改用本地 URL。
   配方在 source() 预取该 tarball（按上游锁定 commit），configure 不再依赖网络。
3. **Catch2 离线携带（PR 审查改正）**：上游 `vesin/tests/CMakeLists.txt:6-12` 用
   FetchContent 拉 Catch2（GIT_TAG v3.5.3）。实测 git clone 与 tarball 下载均可达，
   但为构建可复现性，配方在 source() 下载 Catch2 tarball 解压到
   `vesin/external/Catch2-3.5.3`，configure 用 `-DFETCHCONTENT_SOURCE_DIR_CATCH2`
   指过去，上游单元测试真实构建并运行。
4. **上游测试静态构建**：共享库 `CXX_VISIBILITY_PRESET=hidden`（vesin/CMakeLists.txt:134），
   测试可执行文件链接 libvesin.so 时找不到内部符号（verlet.cpp 引用的
   `cpu::VerletList` 等）→ 链接失败。测试构建用静态库（BUILD_SHARED_LIBS=OFF）
   跑 ctest，交付构建仍用共享库（BUILD_SHARED_LIBS=ON）。
5. **签名**：libvesin.so 需代码签名（OHOS XPM），用 llvm-objcopy + binary-sign-tool。

## 上游测试结果（实测，PR 审查后补跑）
- 环境：aarch64 OHOS 主机 + lua 无关；Catch2 v3.5.3 本地 tarball（sha256
  8d723b0535c94860ef8cf6231580fa47d67a3416757ecb10639e40d748ab6c71）。
- `conan create` build() 内 `ctest --test-dir build-tests/vesin/tests`：

| 测试 | 结果 | 断言 |
|------|------|------|
| neighbors | ✅ All tests passed | 158 assertions in 5 test cases |
| verlet | ✅ All tests passed | 10 assertions in 2 test cases |
| memory | ✅ All tests passed | 28 assertions in 1 test case |
| cuda | ✅ 1 passed（无 CUDA 设备跳过 CUDA 路径） | — |

- **通过率 4/4（100%）**：上游 Catch2 单元测试在 HarmonyOS PC 上全部通过，
  不依赖网络（Catch2 离线携带）。
- test_package（消费者视角）：cutoff=1.5 → 6 对、cutoff=1.2 → 4 对，4/4 断言通过。

## 状态
built（本地 conan create + 上游 ctest 4/4 + test_package 全部通过）
