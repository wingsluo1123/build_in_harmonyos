# smartlist 3.15 适配笔记

## 编译环境
- 构建系统: makefile (custom, 无 configure)
- 编译日期: 2026-10-18
- 编译器: clang/clang++ (Conan tools.build:compiler_executables)
- 状态: built (待真机 rule4 验证后由 HMBS 统一提交)

## 上游信息
- 上游仓库: https://github.com/procmail-org/SmartList (procmail-org 官方镜像)
- 版本: 3.15 (HISTORY 最后条目 2000/09/03 v3.15; master HEAD 即 3.15 内容)
- 源码包: https://github.com/procmail-org/SmartList/archive/refs/heads/master.tar.gz
- SHA256: c2580efb2ae6bbbf079986695f5243f7d33ce8867be68e6d2cda318effc3023f (本地下载实测; 真机预检将复核)
- 许可证: GPL-2.0-or-later (COPYING) / Artistic

## 编译步骤
1. `get()` 解包 (strip_root=True): 得到 `SmartList/` (脚本/文档) + `src/` (C 助手) + COPYING/Artistic。
2. `build()` generates `src/includes.h` shim in place (no patch file).
3. 用 Conan conf 的 clang 编译独立助手 (单命令, 无并行):
   `clang -std=gnu17 -O2 -fPIC -Isrc -c src/hsort.c -o src/hsort.o`
   `llvm-ar rcs src/libhsort.a src/hsort.o`
   `clang -std=gnu17 -O2 -fPIC -Isrc src/gethome.c src/libhsort.a -o src/gethome`
4. `package()` 安装: `bin/gethome` + `lib/libhsort.a` + `include/hsort.h` + `bin/smartlist/*` (19 个脚本) + `share/smartlist/{etc,examples,README,INSTALL,Manual}`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | multigram.c/flist 无法独立编译 | 上游 README 设计要求与 procmail 源码树混合 (需 includes.h/sublib.h/shell.h 等 7 个 procmail 头 + patchlevel.h/targetdir.h); SmartList  tarball 自身不含 Makefile | 本配方只构建独立助手 hsort/gethome; multigram/flist 不构建, 在本笔记与 PR 正文如实声明, 不伪装完整 |
| 2 | hsort.c/gethome.c 缺 `includes.h` | 该头来自 procmail 树 | 新增 0001 补丁提供最小 POSIX 垫片 (uchar/P/Q/DIRSEP/EX_*), 不改上游逻辑 |
| 3 | K&R 函数定义在新 clang 报错风险 | 两文件使用 K&R 风格 (C23 已移除) | 显式 `-std=gnu17` 编译 |
| 4 | 上游无测试套件 | 审计 tarball 全树无 tests/test/TESTS/check_PROGRAMS/ctest | test_package/MANIFEST.yml 声明 upstream_tests_exist:false + 4 条审计 + total 0; build() 不跑 make check |
| 5 | Windows 大小写冲突脏状态 | 仓库同时存在 archives/l/libXext 与 archives/l/libxext, Windows 盘只能存其一 | 对 4 个碰撞文件执行 git update-index --skip-worktree, 保持本机 status 干净; Linux 真机不受影响 |

## 源码修改
- build() generates `src/includes.h` in place (no patch file; new-file patch fragile across patch implementations).

## 依赖版本
- 无 Conan 依赖。运行时需 MTA (sendmail 兼容投递) 与 procmail (完整 flist 功能), 属环境要求, 非 Conan requires (R36: 无需 download 验证)。

## 验证结果
- 本地: 未在本机运行 conan (守则禁止); 待 HMBS 真机预检 (conan create + test_package + HMBS markers)。
- test_package 断言: 18 (hsort API 6 + 包与脚本 12), 详见 test_package/MANIFEST.yml。
- 上游测试: 0 (无套件), 状态 no_tests。

## 交付物
| 文件 | 说明 |
|------|------|
| bin/gethome | 安装助手二进制 (输出相对家目录路径) |
| bin/smartlist/* | 19 个邮件列表脚本 (subscribe/unsubscribe/digest 等) |
| lib/libhsort.a + include/hsort.h | heapsort 静态库与头文件 |
| share/smartlist/{etc,examples} | rc.* 配置与示例 |

## 注意事项
- 不提供 flist/multigram 二进制: 需要 procmail 树混合编译, 超出本 PR 范围; 如需完整列表投递, 请另行适配 procmail 后再扩展。
- 脚本为 Bourne shell (`sh`), 在 OHOS 上用 `sh` 调用, 不依赖 `/bin/sh` 硬路径。
- 本机 Windows 检出有 libXext/libxext 大小写碰撞, 已用 skip-worktree 隔离, 提交时以 Linux 真机树为准。
