# luatex 0.99997 适配笔记

## 编译环境
- 构建系统: custom (复用 XeTeX 源码树)
- 编译日期: 2026-07-10
- 状态: built (编译成功，链接受阻)

## 构建策略
复用 XeTeX 0.99997 的源码树和所有 HMDFS 修复：
- automake/libtool 已安装
- fontconfig/ICU/graphite2/harfbuzz/libpng 已构建
- umask/config.guess/build-aux 已修复
- 顶层 configure + web2c Makefile 已生成

## 新增依赖构建
| 依赖 | 来源 | 构建方式 |
|------|------|---------|
| Lua 5.2.4 | lua.org FTP | 直接编译 .c 文件 |
| GMP 6.3.0 | GNU FTP | autotools (--build 指定) |
| MPFR 4.2.1 | GNU FTP | autotools (--with-gmp) |
| cairo | stub | C stub 实现 |
| pixman | stub | C stub 实现 |
| zziplib | stub | 空 stub + rebuild Makefile |

## 阻塞问题
CWEB (.w) 源文件不在 texlive-source git 仓库中：
- `mainbody.w`, `commands.w` 等核心引擎源文件缺失
- `ctangle` 从 stub .w 生成空 .c，覆盖了 texlive-src 的预生成 .c
- 导致 `main_body`, `lua_initialize` 等核心函数未定义
- 需要：从 TeX Live SVN 或完整源码包获取 .w 文件

## 解决方案
1. 获取完整 TeX Live 源码包（包含 .w 文件）
2. 或从 SVN 仓库 checkout .w 文件
3. 或手动从 texlive-src 复制预生成 .c 文件并修改 Makefile 跳过 ctangle
---

**编译结束**: 2026-07-10 15:10
**最终状态**: built
