# nsnake 3.0.1 测试报告

## 测试环境
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 构建系统: Makefile
- 目标平台: OHOS aarch64

## 编译测试
| 测试项 | 结果 | 说明 |
|--------|------|------|
| 源码下载 | ✅ 通过 | GitHub release v3.0.1 |
| 编译 | ✅ 通过 | 全部 33 个源文件编译成功 |
| 链接 | ✅ 通过 | 静态链接 libncurses.a |
| 二进制验证 | ✅ 通过 | nsnake --version 输出 v3.0.0（上游版本字符串未随 v3.0.1 tag 更新，不影响二进制功能验证） |

## 产物
| 文件 | 说明 |
|------|------|
| bin/nsnake | 贪吃蛇游戏二进制 (ELF aarch64, 543KB) |

## 已知问题
| # | 问题 | 根因 | 状态 |
|---|------|------|------|
| 1 | KEY_CTAB/KEY_ENTER 重复 case 值 | 鸿蒙 ncurses 头文件中 KEY_CTAB 和 KEY_ENTER 均为 0527 | 已修复，移除 KEY_CTAB case |
| 2 | ncurses 头文件缺失 | CI worker 无 ncurses dev 包 | 已解决，bundled res/headers + res/libs |

## 测试结论
- 编译状态: ✅ 通过
- 二进制验证: ✅ 通过
- 适配状态: built
