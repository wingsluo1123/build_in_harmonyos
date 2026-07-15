# mkinitfs 3.4.5 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
cd $BUILD_SRC_DIR
make WITH_NLPLUG=0 PREFIX=$DEFAULT_PREFIX
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | nlplug-findfs 依赖不可用 | OHOS 不提供 nlplug-findfs 工具 | 设置 WITH_NLPLUG=0 禁用 nlplug-findfs 相关功能 |
| 2 | /tmp 只读 | OHOS /tmp 是只读文件系统 (E002) | 测试时设置 TMPDIR 到可写目录 |
| 3 | -Werror 导致编译失败 | CFLAGS 中 -Werror 将警告视为错误 | 补丁移除 -Werror |

## 交付物

CI 构建产物由 conan create 自动生成，无需手动打包。

---

**编译结束**: 2026-07-15
**最终状态**: built
