# indi-starbook

INDI 天文框架的 **Vixen StarBook 赤道仪驱动**（C++ 可执行程序，非库），覆盖 Ten 代以前的 StarBook 控制器。

- 上游：[indilib/indi-3rdparty](https://github.com/indilib/indi-3rdparty)（`indi-starbook/`，本包源码为 2022-12-22 快照，Debian `indi-starbook_0.8+20221222163625.orig.tar.gz`）
- 协议：HTTP（StarBook 命令集：GOTORADEC/ALIGN/MOVE/GETSTATUS 等；响应藏 HTML 注释 `<!--KEY=VAL-->`，std::regex 解析），libcurl 传输
- 产物：`bin/indi_starbook_telescope`（INDI::Telescope 子类驱动，由 INDI 服务框架加载运行）
- 姊妹篇：[../indi-starbook-ten](../indi-starbook-ten)（同协议，传输层为 bundled cpp-httplib 而非 curl）

## 依赖

| 包 | 版本 | 用途 |
|---|---|---|
| libindi | 2.2.2.1 | INDI 框架（INDI::Telescope 基类） |
| libnova | 0.16 | 天文计算（ln_equ_to_hequ / ln_lnlat_to_hlnlat，静态链入） |
| curl | 8.15.0.1 | HTTP 传输（connectioncurl.cpp） |
| gtest | 1.17.0.2 | test_requires：上游官方单元测试 |

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.8-20221222163625 | built | 初始适配（patches 0001-0004：libindi 2.x 迁移 + 上游死测试 ltrim 修复） |

适配细节见 [0.8-20221222163625/notes.md](0.8-20221222163625/notes.md)。
