# cmatrix 2.0 适配笔记

## 编译环境
- 构建系统: custom（Makefile 模板交叉编译）
- 编译日期: 2026-07-12
- 编译器: aarch64-linux-gnu-gcc (GCC Linaro 7.5.0)
- 状态: built

## 编译步骤
- 交叉编译：x86_64 Linux → OHOS aarch64
- 工具链：由 profile [buildenv] PATH 提供（`aarch64-linux-gnu-gcc`）
- ncurses：通过 `self.requires("ncurses/6.6")` 从 Conan 依赖链获取
- sysroot：由 `aarch64-linux-gnu-gcc --print-sysroot` 动态获取
- 编译方式：`conan create` 自动完成，无硬编码路径

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | E001: C compiler cannot create executables | `--host=aarch64-linux-ohos` 触发交叉编译但 clang sysroot 不存在 | 改用 GCC Linaro 工具链直接编译，不走 configure |
| 2 | conan create: settings.yml 坏链接 | `~/.conan2/settings.yml` 指向不存在的 `ci/conan/config/settings.yml` | 删除坏链接，用默认 settings.yml 添加 OHOS 和 GCC 16 支持 |
| 3 | conan create: SHA256 不匹配 | 原始 URL `xs4all.nl` 已重定向，缓存了错误文件 | 改用 GitHub release URL，更新 SHA256 |
| 4 | conan create: 缺少 config.h | GitHub 源码不含 autotools 生成的 config.h | 手动生成最小 config.h |
| 5 | test_package: 交叉编译二进制无法在 x86_64 运行 | 测试二进制是 aarch64 格式 | 使用 `can_run(self)` 跳过运行时测试 |

## 源码修改
- 无补丁（未配置 autotools，直接编译单文件）
- 生成最小 config.h 模拟 autotools 检测结果

## 依赖版本
- ncurses 6.6（通过 `self.requires("ncurses/6.6")` 由 Conan 解析）

## 验证结果
```bash
file cmatrix
# ELF 64-bit LSB executable, ARM aarch64, statically linked
# conan create 通过，编译+链接验证成功
```

## 注意事项
- 当前是交叉编译，产出的 aarch64 二进制需要在 OHOS 设备上运行测试
- conan profile 使用 `os=OHOS`（settings.yml 已添加 OHOS 支持）
- 如需在 OHOS 设备上原生编译，使用 `ci/conan/profiles/ohos-aarch64` profile
---

**编译结束**: 2026-07-12 11:23
**最终状态**: built
