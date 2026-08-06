# fdupes 2.4.0 适配笔记 (Conan 适配)

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: success (Conan 适配完成)
- 版本号: 2.4.0 (首次 Conan 适配，上游版本不变)

## 特性说明

本次适配**不裁剪任何功能**，所有特性均已启用：

| 特性 | 依赖 | 状态 |
|------|------|------|
| 交互模式 (ncurses) | ncurses/6.5 (本地源码编译) | ✅ 启用 |
| 正则表达式 (pcre2) | pcre2/10.45.1 (ohpcd 制品仓) | ✅ 启用 |
| 哈希数据库 (sqlite3) | sqlite3/3.49.1 (ohpcd 制品仓) | ✅ 启用 |

## 编译步骤

1. **下载源码**: 从 GitHub releases 获取 fdupes-2.4.0.tar.gz (release tarball, 含 autotools 生成文件)
2. **安装依赖**: conan install pcre2/10.45.1 sqlite3/3.49.1 (从 ohpcd 制品仓)
3. **构建 ncurses**: 从源码编译 ncurses 6.5 (静态库, 宽字符)
4. **configure**: 使用 clang 编译器, 依赖路径通过 Conan 管理
5. **config.status 修复**: HMDFS 平台 mktemp -d 不工作 (E002), 修补 config.status 使用固定目录
6. **make**: 编译所有源文件 (含 ncurses-interface, hashdb 等)
7. **make install**: 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | HarmonyOS 网络限制 | 使用 GitHub API (api.github.com) 下载 |
| 2 | configure config.guess 不识别平台 | 缺少 HarmonyOS 检测 | 修补 config.guess 添加 *:HarmonyOS:* case |
| 3 | config.status mktemp -d 失败 | HMDFS 不支持 mktemp 创建的目录写入 (E002) | 修补 config.status 使用固定目录 + bash 执行 |
| 4 | ncurses 不在制品仓 | ncurses 从未进行 Conan 适配 | 创建 ncurses conanfile.py, CI 使用 --build=missing 从源码编译 |
| 5 | ncurses progs/tic 链接失败 | boolcodes/strcodes/numcodes 未编译到 tic | 跳过 progs 构建 (消费者不需要 tic 工具) |

## 依赖版本

- ncurses/6.5 (本地源码编译, 静态库, 宽字符)
- pcre2/10.45.1 (ohpcd 制品仓, 静态库, 含 pcre2-32 组件)
- sqlite3/3.49.1 (ohpcd 制品仓, 静态库)

## 验证结果

```bash
$ fdupes --version
fdupes 2.4.0
```

## 源码修改

无源码修改。release tarball 的 configure/make 直接可用。
旧版补丁 (0001-0007) 已移除，因为它们只是更新 autotools 辅助脚本版本，不影响编译。

## 注意事项

- **ncurses 依赖**: ncurses/6.5 尚未发布到 ohpcd 制品仓。CI 的 L0i-1 fallback 机制会从 archives/ 目录查找本地 conanfile.py 并使用 --build=missing 从源码编译。
- **HMDFS mktemp 问题**: config.status 使用 mktemp -d 在 HMDFS 上失败，conanfile.py 的 build() 方法已自动修补此问题。
- **全功能编译**: 本配方不使用 --without-ncurses 或 --without-sqlite，所有功能均已启用。
---

**编译结束**: 2026-08-06 12:34
**最终状态**: built
