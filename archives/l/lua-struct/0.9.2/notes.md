# lua-struct 0.9.2 适配笔记

## 编译环境
- 构建系统: Pure Lua library (no compilation)
- 编译日期: 2026-08-07
- 编译器: clang 15.0.4 (for test_package C program)
- 状态: published

## Conan 适配

### 适配概述
lua-struct 是纯 Lua 库，无需编译步骤。Conan 配方使用 no-op build() 方法，
仅将 struct.lua 文件安装到 lib/lua/5.4/ 目录。

### 关键文件
- conanfile.py: Conan 配方，依赖 lua/5.4.7
- conandata.yml: 源码 URL + sha256 + 补丁声明
- test_package/: C 程序嵌入 Lua 解释器测试 struct 模块
- patches/0001-lua54-compat-frexp-ldexp.patch: Lua 5.4 兼容性补丁

### 依赖
- lua/5.4.7 (从 conancenter 获取，--build=missing 从源码构建)

### 补丁
1. **0001-lua54-compat-frexp-ldexp.patch**
   - 问题: Lua 5.4 移除了 math.frexp 和 math.ldexp 函数
   - 修复: 添加纯 Lua 实现的 fallback 函数
   - 类型: portability

### 测试
- test_package 使用 C 程序链接 liblua.a，嵌入 Lua 解释器
- 测试覆盖: pack/unpack for I, h, B, b, ss, d 类型
- 所有断言通过

### 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan 报 package_type=library 但无 shared option | Conan 2.x 要求 library 类型必须声明 shared 选项 | 添加 options={"shared": [True, False]} |
| 2 | test_package 找不到 lua.h | CMakeDeps 未正确传播 lua 的 include 目录 | 改用直接编译方式，通过 cpp_info 获取路径 |
| 3 | math.frexp 调用失败 | Lua 5.4 移除了 math.frexp 和 math.ldexp | 添加纯 Lua fallback 实现 |

## 验证结果
- conan-verify: ✅ PASS (G0-G4, L2/L4/L5)
- 本地 CI 模拟: ✅ PASS (setup.sh + build_and_test.sh)
- test_package: ✅ All tests passed

## 编译产物
- `lib/lua/5.4/struct.lua` — Lua 模块文件

## 注意事项
1. lua-struct 是纯 Lua 实现，无二进制文件
2. 使用时需要设置 LUA_PATH 环境变量或在 Lua 代码中设置 package.path
3. 模块路径为 `require("struct")`
4. 支持 pack/unpack 操作，类似 PHP 的 pack/unpack 函数
5. Lua 5.4 兼容性补丁必须应用，否则 float/double 打包解包功能不可用
