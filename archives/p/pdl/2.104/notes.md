# PDL 2.104 适配工作笔记

平台任务：id=9406  name=pdl  version=2.104  lang=cpp（实为 Perl 发行版 + XS/C 核心）
上游：CPAN PDL-2.104（作者 ETJ，2026-04-08）

## 为什么这不是一个普通的 Perl 包

本仓已发布的 perl-* 模块（如 perl-file-which/1.27）配方注释写的是
"纯 Perl——无编译"，只是把 lib/*.pm 拷进 site-lib，连 perl 解释器都不 require。
PDL 相反：核心是 XS(C)，必须真跑 Makefile.PL 并编译。

## 两个决定可行性的环境事实（实测）

1. CI worker 本身就是 OHOS 机器（日志里 /data/service/hnp/bin/ruby 可直接执行），
   所以制品仓里 OHOS/armv8 的 perl/5.42.2.3 在构建期跑得起来，XS 才谈得上能编。
2. OHOS 会拒绝"先进 Conan 包缓存、后签名"的 XS ELF（perl 配方注释原话），
   必须在构建树里签名：/data/service/hnp/bin/binary-sign-tool + llvm-objcopy。

## 依赖策略（路线 A）

PDL 的 Makefile.PL 需要 4 个未发布模块：Devel::CheckLib 1.16（configure 硬门槛）、
File::Map 0.71（runtime，XS）、Test::Deep 1.205、Test::Warn 0.37（test）。
它们与本体一起以 url+sha256 固定进 conandata.yml，构建期依序装入包内 lib/perl5，
避免为 4 个小模块各开一轮 PR（与 jekyll 的 gem 闭包同构）。
另两个依赖（perl-file-which、perl-test-exception）已在制品仓，走 conan requires。

## 首轮 CI 已回答的问题（结论）

- XS 能否编过：**能**。PDL 全部 XS 模块编译通过，构建树内签名 18 个 .so。
- 构建树内签名是否被 OHOS 接受：**是**（见签名日志与 test_package）。
- vendored 依赖能否装进包：**能**（Module-Build / Sub-Exporter-Progressive / Devel-CheckLib / File-Map / Test-Deep / Test-Warn）。
- 测试结果：上游套件 Files=6, Tests=1510, Result: PASS；test_package 被 conan create 执行且通过；CI 汇总 Pass rate: 100.0% (1/1)，构建 #90914 全绿。
- L2（bin 下脚本的 --version/--help）按 CI 自身设计为 non-blocking：脱离 conan 运行环境直接执行必然缺 PERL5LIB，不构成打包缺陷。
- 详见 test_package/MANIFEST.yml 与 knowledge/drafts/DRAFT-pdl-2.104-ohos-perl-xs-module-packaging.md/.kv。
