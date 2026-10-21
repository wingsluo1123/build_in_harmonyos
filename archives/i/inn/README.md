# inn

InterNetNews (INN) 1.x：ISC/Rich Salz 的 Usenet 新闻传输系统，面向不需要
INN 2.x 复杂度的小站点。提供 innd/nnrpd 新闻服务、inews/rnews 投递前端、
expire/expireover 过期维护工具链，以及可被外部程序链接的 libinn 基础库
（wildmat、parsedate、qio、dbz、clientlib 等）。

## 功能概述

- 完整的 NNTP 新闻服务（innd 服务端 + nnrpd 阅读服务端）
- 新闻投递与批处理（inews/rnews、backends 系列、sendbatch/send-uucp）
- 历史/概览数据库维护（makehistory、expire、expireover、fastrm）
- libinn C 库：供 news 相关工具链接（tin 等新闻阅读器历史上即链接它）

## OHOS 适配要点

- INN 1.x 没有 configure 脚本：通过 `config/config.data`（config.dist 的
  站点化拷贝）+ `config/subst` 工具做配置，配方按 Conan conf 生成该文件
  （编译器、CFLAGS、包内安装根）；已知问题与绕坑细节见各版本 notes.md。
- 本机无系统 perl：`PERL_SUPPORT=DONT`，且配置阶段只跑 `make substitutions`
  （跳过 perl 改写器）；perl 钩子代码编译为空桩。
- 构建沙箱无 news 账号/chown：从不执行顶层 `make install`（makedirs.sh），
  改为逐目录 `make install`；`installit.sh -O/-G` 非 root 自动跳过 chown。
- 上游无测试套件：test_package 承担全部验证（libinn API 断言 + convdate
  烟雾测试），并复发上游 `no_tests` 审计标记。

## 依赖关系

- 编译依赖：无（仅 libc；yacc/bison 由真机工具链目录提供）。
- 运行依赖：无（perl 脚本类示例需 perl5 才能运行，见版本 notes）。

## 参考资料

- 上游主页：https://www.eyrie.org/~eagle/software/inn/
- INN GitHub（2.x 线）：https://github.com/InterNetNews/inn
- 历史源码归档：https://downloads.isc.org/isc/inn/OLD/
- 本目录版本：`1.7.2q`（Debian/Ubuntu 发行版 canonical 版本，见版本 notes
  “上游版本说明”）。
