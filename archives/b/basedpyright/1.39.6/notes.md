# basedpyright 1.39.6 适配笔记

## 编译环境
- 构建系统: npm (Node.js package, pre-built JavaScript)
- 编译日期: 2026-08-05
- 编译器: N/A (npm 包，无需编译)
- 状态: built (验证通过，未上传CI)

## 软件说明

basedpyright 是基于 pyright 的 Python 类型检查器，以 npm 包形式分发。
本适配使用 Conan 配方打包预构建的 JavaScript 文件，创建 bin wrappers 调用 node。

## 适配方案

### Conan 配方 (conanfile.py)
- `package_type = "application"` — 命令行工具
- `settings = ("os", "arch")` — 简化设置 (JS 包不需要 compiler/build_type)
- `source()`: 从 npm registry 下载 tgz
- `build()`: 无编译 (预构建 JavaScript)
- `package()`: 复制 JS 文件到 lib/node_modules/basedpyright/，创建 bin wrappers
- `package_info()`: bindirs=["bin"], libdirs=[]

### Bin Wrappers
每个 wrapper 使用相对路径定位 JS 入口文件:
```sh
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec node "${SCRIPT_DIR}/../lib/node_modules/basedpyright/index.js" "$@"
```

创建的命令: basedpyright, basedpyright-langserver, pyright, pyright-langserver

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip 安装失败 | nodejs-wheel-binaries 需要编译 nodejs | 改用 npm 包 + Conan 配方打包 |
| 2 | 传统编译流程不适用 | basedpyright 是 Node.js 包，非 C/C++ | 使用 Conan custom recipe 打包预构建 JS |
| 3 | bin wrapper 路径解析 | Conan 测试环境中 PATH 查找 | 使用相对路径 (dirname $0) 解析 |

## 源码修改

无补丁。npm 包预构建，无需修改源码。

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| nodejs | v24.13.0 | 系统预装 |
| npm | 11.6.2 | 系统预装 |
| Python | 3.12.9 | 系统预装 |
| Conan | 2.29.1 | OHOS 适配版 |

## 验证结果

### Conan 验证 (G1-G4 + L2/L4/L5)
- G1 配方完整性: PASS
- G2 conan create: PASS
- G3 系统同名库隔离: PASS
- G4 产物完整性: PASS
- L2 平台功能矩阵: PASS
- L4 安全扫描: PASS
- L5 产物基线: PASS

### CI 模拟 (W3)
- setup.sh: PASS
- build_and_test.sh: PASS

### Smoke Test
```
$ basedpyright --version
basedpyright 1.39.6
based on pyright 1.39.6
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (npm 包打包) |
| conandata.yml | 源码 URL + sha256 |
| test_package/test.sh | 冒烟测试 (basedpyright --version) |
| commands.json | 命令行工具声明 (R38) |

## 注意事项

1. **特殊软件类型**: basedpyright 是 Node.js 包，使用 Conan custom recipe 打包
2. **依赖优先**: 使用系统预装的 nodejs，避免 nodejs-wheel-binaries 编译失败
3. **Bin Wrappers**: 使用相对路径解析，不依赖环境变量
4. **版本匹配**: basedpyright 1.39.6 基于 pyright 1.39.6

---

**编译开始**: 2026-08-05 07:28
**编译结束**: 2026-08-05 07:39
**最终状态**: built (验证通过，未上传CI)
