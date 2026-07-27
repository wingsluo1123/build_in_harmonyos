# 编译笔记 — lmod 9.2.5

**软件名称**: lmod (Lua Environment Module System)  
**版本**: 9.2.5  
**编译日期**: 2026-07-26  
**编译状态**: built

---

## 软件简介

Lmod 是德州大学 TACC 开发的环境模块系统，基于 Lua 实现。它提供 `module` 命令，
方便用户在 shell 中动态添加/删除/切换环境变量（PATH、LD_LIBRARY_PATH 等）。
完全兼容传统 TCL 模块文件格式，且内建软件层级（Software Hierarchy）支持。

**源码地址**: https://github.com/TACC/Lmod/archive/refs/tags/9.2.5.tar.gz

---

## 依赖分析

### 直接依赖
| 依赖 | 版本 | 状态 |
|------|------|------|
| lua | >= 5.1, < 5.5 | ✅ lua/5.4.8 (已归档, built) |

### 依赖发布检查 (W0)
lua/5.4.8 已在 archives/l/lua/5.4.8/ 中存在，状态为 built，依赖满足。

---

## 编译过程

### 构建系统
Autotools（标准 configure + make + make install）

### 编译步骤
```bash
./configure --with-lua=<lua-prefix>  # 由 Conan dependencies 动态提供
make -j1
make install DESTDIR=/path/to/staging
```

### 关键配置参数
- `--with-lua=<prefix>`: 指定 Lua 安装路径（由 Conan 依赖提供）

---

## 质量门禁

| 门禁 | 名称 | 预期 |
|------|------|------|
| R26 | 系统同名库静态链接 | lmod 不是系统同名库，使用动态链接 |
| R32 | OHOS 平台兼容 | conanfile.py `settings` 含 `os=OHOS`，Conan 原生支持 |
| R33 | 禁止裸用 shell 环境变量 | 编译器/标志从 Conan Toolchain 获取 |
| R34 | test 必须实质依赖被测包 | test.sh 实际调用 `module --version` |
| R38 | 命令行工具声明 commands.json | ✅ 已创建 archives/l/lmod/commands.json |
| R39 | 源码 URL 必须为官方源 | ✅ GitHub 官方 tags 地址 |

### 补丁说明
本次首次适配无需补丁。

---

## 知识沉淀

### 关键发现
1. Lmod 是 Lua 应用，核心逻辑在 Lua 脚本中，C 代码仅用于少量辅助功能
2. `--with-lua` 是必需的配置参数，指向 Lua 安装路径
3. 作为 tool 类型包，需要 software 级 commands.json 声明
4. lua/5.4.8 作为静态库依赖，lmod 通过 Lua C API 调用

### 注意事项
- `/etc/lmod/` 配置目录需在运行时创建
- Lmod 需要 Lua 的 `luaposix` 模块支持全部功能
- 在 HarmonyOS 上运行时，需要确保 bash 可用

---

## 编译结束

**最终状态**: built  
**产物类型**: tool（module 命令）
