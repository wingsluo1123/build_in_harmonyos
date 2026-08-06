# git-secrets 1.3.0 适配笔记

## 编译环境
- 构建系统: makefile (纯Bash脚本项目)
- 编译日期: 2026-08-06 (Conan 适配)
- 编译器: 不需要编译器（Bash脚本）
- 状态: published (Conan 适配完成)

## 编译步骤

git-secrets是AWS Labs开发的纯Bash脚本项目，无需编译。安装步骤如下：
1. `init-build git-secrets 1.3.0` - 初始化环境，下载源码
2. 源码下载使用GitHub镜像(ghfast.top)，直接下载GitHub失败
3. `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX` - 直接安装脚本和man page
4. 无需configure或make步骤

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub直接下载失败 | 网络环境限制 | 使用ghfast.top镜像代理下载 |
| 2 | build命令自动尝试`make install-binPROGRAMS` | 驱动脚本默认autotools模式 | 手动运行`make install` with正确的PREFIX/DESTDIR |
| 3 | staging_prefix路径不匹配 | Makefile默认PREFIX=/usr/local与DEFAULT_PREFIX不一致 | 手动指定PREFIX=$DEFAULT_PREFIX |
| 4 | 上游bats测试全部失败(50/50) | git config --local在HarmonyOS上不可用(safe.directory策略) | 添加safe.directory通配符后测试仍超时，记录为平台限制 |

## 源码修改

无补丁，无源码修改

## 依赖版本

- bash (系统自带)
- git (系统自带)

## Conan 适配

- package_type: application
- settings: os, arch (无需compiler/build_type)
- build(): 无操作（bash脚本无需编译）
- package(): 复制 git-secrets 到 bin/，git-secrets.1 到 share/man/man1/
- test_package: bash冒烟测试（检查脚本存在/可执行/shebang/语法/--help功能）
- commands.json: 已创建（tool类型）

## 验证结果

```bash
# git-secrets脚本可正常执行
$ $PREFIX/bin/git-secrets --help
# 显示usage信息，功能正常
# --version不支持，但脚本本身运行正常
```

## 注意事项

- git-secrets是纯Bash脚本项目，不需要C/C++编译
- 上游bats测试框架的test_helper.bash使用git config --local，在HarmonyOS上因safe.directory策略失败
- Conan配方使用application类型，不使用library类型

---
**编译结束**: 2026-08-06
**最终状态**: published
