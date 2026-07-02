# rlwrap 0.47.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-02
- 编译器: clang
- 状态: success

## 编译步骤
```bash
# Conan recipe uses Autotools toolchain
conan create . --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 失败 | HMDFS umask 077 导致 mktemp -d 创建目录权限异常 | 补丁 0001 将 configure 中 umask 077 改为 022 |
| 2 | bool 类型未定义 | C99+ 需要 stdbool.h | 补丁 0002 添加 #include <stdbool.h> |
| 3 | config.guess 不识别 HarmonyOS | uname -s 返回 HarmonyOS | 补丁 0003 添加 HarmonyOS 系统识别 |
| 4 | config.sub 不识别 ohos | ohos-linux 三元组未注册 | 补丁 0004 添加 ohos-linux 支持 |
| 5 | CONFIG_SHELL 路径不存在 | Conan profile 设置 CONFIG_SHELL=/data/service/hnp/bin/bash | 在 build() 中替换 $CONFIG_SHELL → /bin/sh |
| 6 | 硬编码路径不可移植 | build() 中硬编码了 /storage/Users/currentUser/.harmonybrew 路径 | 改用 AutotoolsToolchain + os.path.expanduser |

## 验证结果
- `rlwrap --version` ✅
- conan-verify 8/8 gates 通过
- 静态链接 (R26) ✅

## 注意事项
- 使用 Conan Autotools 工具链，不直接调用 ./configure
- harmonybrew 路径通过 os.path.expanduser("~/.harmonybrew/...") 获取，CI 可移植
- CONFIG_SHELL 修复保留在 build() 中，不绕过 Conan 工具链
---

**编译结束**: 2026-07-02 11:59
**最终状态**: built
