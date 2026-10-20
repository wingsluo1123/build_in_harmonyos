# pdl

**PDL（Perl Data Language）** —— Perl 的数值/数组计算扩展，核心为 XS(C) 实现。

- 上游：https://metacpan.org/dist/PDL （源码仓库 PDLPorters/pdl）
- 平台任务：id=9406，version=2.104
- 本仓适配：`archives/p/pdl/2.104/`

本仓此前已发布的 `perl-*` 模块均为**纯 Perl（无编译）**；PDL 是**第一个含 XS 的 Perl 包**，
需要在构建期真跑 `Makefile.PL`、编译 XS，并在**进包缓存前于构建树内**完成 ELF 签名
（OHOS 要求）。相关知识与配方见版本目录下的 `notes.md` 与 `conanfile.py`。
