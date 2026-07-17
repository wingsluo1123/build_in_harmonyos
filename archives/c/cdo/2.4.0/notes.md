# cdo 2.4.0 编译进度

**日期**: 2026-07-15
**状态**: ✅ 编译成功

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | init-build 成功，下载解压完成 |
| Step 2 patches | ✅ | config.guess + config.sub 打补丁（HarmonyOS 识别） |
| Step 3 configure | ✅ | --host=aarch64-linux-ohos 配置成功 |
| Step 4 make | ✅ | make -j1 编译完成 |
| Step 5 install | ✅ | 安装到 staging 目录 |
| Step 6 package | ✅ | 打包为 ohos-aarch64 tar.gz |

## 发现与知识

1. **config.guess/config.sub 补丁**: CDO 使用 autotools 构建，需要更新 config.guess/config.sub 以支持 HarmonyOS 平台识别，否则 configure 无法识别 aarch64-linux-ohos 目标。
2. **CONFIG_SHELL**: 需要设置 CONFIG_SHELL=/data/service/hnp/bin/bash 以解决 HMDFS 兼容问题。
3. **静态编译**: 使用 --enable-static --disable-shared 避免动态库依赖问题。
4. **C++20 要求**: 上游 CDO 2.4.0 已切换到 C++20，Conan 配方需显式追加 `-std=c++20`，否则在 CI 共享 profile 的 `compiler.cppstd=17` 基线下会在 `configure` 阶段失败。
5. **上游测试执行**: 在目标程序可运行的场景下，Conan `build()` 阶段执行 `make check`，让 CI 的 L1 能看到上游官方测试痕迹；纯交叉构建场景则跳过并保留 `test_package` 验证。

---

**编译结束**: 2026-07-15
**最终状态**: built
