# tqftpserv 1.2 适配笔记

## 编译环境
- 构建系统: Meson
- 设备: HarmonyOS PC aarch64
- 编译器: OHOS clang 15.0.4
- 状态: built（本地 conan create 通过，含 test_package 执行）

## 适配过程

1. 上游 GitHub `linux-msm/tqftpserv` tag `v1.2`，SHA256 `a3850c34e48f23b7bc360d70f1e91700de2f8c60af003eda93e14182f8cf6af1`
2. 依赖预检：qrtr/1.2、zstd/1.5.7 均已在制品仓发布（conan download 确认，R36 通过）
3. Meson 构建需要从 `compiler_executables` 推导 llvm-ar/llvm-ranlib 全路径注入 `conan_meson_native.ini`（Conan MesonToolchain 不写 ar/ranlib）
4. `meson.build` 第 37 行引用 `systemd_system_unit_dir`，但该变量仅在 systemd 依赖找到或 `systemd-unit-prefix` 非空时才定义 → OHOS 上 undefined variable → 补丁 `0001-ohos-systemd-init.patch` 在 `endif` 后插入空串初始化（经 conandata.yml 声明，`apply_conandata_patches` 应用）
5. `package_type = "application"`（产出可执行文件，非库）
6. test_package 验证：签名后 `tqftpserv -h` 正常输出用法

## 上游测试

上游 v1.2 **无测试套件**（R51 三步法清点）：
- 仓库不存在 `tests/` 目录
- `meson.build` 没有调用 `test()`
- 没有 `ci/` 或 `.github/workflows` 测试 workflow
- 仅含 `make build`，无 `make check`

## 消费者测试（test_package）

- 验证 `bin/tqftpserv` 是有效的 aarch64 ELF
- OHOS 环境下用 `binary-sign-tool -selfSign 1` 签名后执行 `tqftpserv -h` 正常通过（鸿蒙特有测试，非断言）

## 交付物

- `bin/tqftpserv` — TFTP server 可执行文件
- `licenses/LICENSE` — BSD-3-Clause

### 对话 #1 (2026-10-15)

- 完成 tqftpserv/1.2 全流程适配：配方编写、依赖核验（R36）、OHOS 适配、conan create、conan-verify（G0-G4 + L2/L4/L5 PASS）、finish（W3 本地 CI 模拟 PASS）、打包（PackageBuilder 10 步，release + debug tar.gz）。
- 关键修复：① conandata.yml 恢复官方单 URL（PF7/E017）；② 补丁机制从 source() 内联 replace_in_file 重构为标准 patches/ + apply_conandata_patches（house pattern），消除双重应用；③ test_package ELF magic 比较改用转义写法避免原始 0x7F 控制字节；④ 软件级三件套（README.md/manifest.yaml/commands.json）补齐。
---

**编译结束**: 2026-10-15 18:19
**最终状态**: built
