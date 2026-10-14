# sctk 2.4.12 适配笔记

## 编译环境
- 构建系统: Makefile（顶层 makefile + src/ 各子模块 makefile.in；`make config` 由 sed/config.sh 生成各子模块 makefile）
- 编译日期: 2026-10-03
- 编译器: clang/clang++（OHOS SDK 15.0.4，target aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```bash
# make config 生成各子模块 makefile（PREFIX 传入源码根）
make config
# 编译全部 26 个工具（C 二进制 + perl 脚本 + shell 脚本）
make all
# 安装到 bin/
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sh/config.status 临时目录写入失败（`can't create confstat*/subs.sed: Permission denied`） | HMDFS 下 `umask 077 && mktemp -d ./confstatXXXXXX` 创建的 0700 目录继承父目录属主（setgid），当前用户非属主无法写入（E206 同源） | 3 个 config.sh（asclite/core、asclite/test、utf_filt）临时目录改 `${TMPDIR:-.}/confstatXXXXXX` |
| 2 | perl 脚本 shebang `/usr/bin/perl` 不存在，`env: exec perl -w: No such file` | OHOS 无 /usr/bin/perl（E049 硬编码 shebang） | 批量将 perl 脚本 shebang 改 `#!/usr/bin/env perl`（去掉 `-w` 参数，env 不支持带参）；18 个脚本以补丁固化，md-eval.pl（CRLF 行尾无法生成补丁）由 conanfile.py package() 兜底统一修复 |
| 3 | csrfilt.sh 测试失败（无法写 /tmp） | 鸿蒙 /tmp 只读（E002） | csrfilt.sh/tsclite.sh 硬编码 `/tmp` 改 `${TMPDIR:-$HOME/tmp}` |
| 4 | asclite aligninfo confidence 字段输出巨大垃圾值（2.75e23） | `LineStyleInputParser` 构造函数未初始化 `m_Confidence` 等成员，libc++ 下读到垃圾值（E632 草稿） | 构造函数初始化全部成员（m_bUseConfidence/m_bUseExtended/m_Confidence/m_starttime/m_endtime） |
| 5 | conan create 中 asclite config.sh conftest 运行检测失败 | conftest 运行需 libc++_shared.so（SDK aarch64-linux-ohos 目录）；且 usr/local/lib 的 libxml2 污染 SDK lld（E266） | conanfile.py build() 用干净 LD_LIBRARY_PATH（SDK llvm/lib + aarch64-linux-ohos + /system/lib64）覆盖 |

## 源码修改

共 24 个补丁（patches/0001-0024）+ conanfile.py package() 兜底修复，覆盖：
- 18 个 perl 脚本 shebang 补丁（/usr/bin/perl → /usr/bin/env perl）
- 3 个 config.sh 临时目录修复（${TMPDIR:-.}）
- csrfilt.sh、tsclite.sh 的 /tmp 硬编码（${TMPDIR:-$HOME/tmp}）
- linestyle_inputparser.h 构造函数初始化（E632）
- md-eval.pl（CRLF 行尾无法生成补丁）：由 conanfile.py package() 统一将
  打包后的 perl/shebang 脚本 shebang 修复为 `#!/usr/bin/env perl`（幂等兜底）

## 依赖版本

- perl/5.42.2（运行期 perl 脚本必需，conan 制品仓已发布）

## 验证结果

```bash
# 上游测试（make check）
# asclite 全部通过；rfilter1/csrfilt/chfilt/hamzaNorm/tanweenFilt/acomp/def_art/slatreport 通过
# hubscr 4/6 通过（test1-sastt/test2-sastt 仅 aligninfo 行序差异：libc++ vs libstdc++
#   指针 map 迭代顺序差异，排序后内容 0 差异、sgml/mdeval 0 差异、prf 仅日期行）
# utf_filt 跳过（上游因 NSGMLS 未装主动跳过 RC=0）；rttmSort 等 8 工具无上游测试

# conan-verify（G1-G4 + L2/L4/L5）全部 PASS
# W3 本地 CI 模拟（build_and_test.sh）L0-L5 全 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application 工具集；build 含 make config/all/install） |
| conandata.yml | 源码声明 + 24 个补丁引用 |
| test_package/ | test.sh 消费者测试（rfilter1 端到端 + sclite 版本 + perl 工具）+ MANIFEST.yml |
| patches/ | 24 个 OHOS 适配补丁 |
| commands.json | 工具声明（26 个命令行工具） |

## 注意事项

- 行序差异（hubscr test1-sastt/test2-sastt）：libc++ 对 `map<Segment*,AlignedSegment*>` 指针 key 迭代顺序与 libstdc++ 不同，导致 aligninfo.csv 行序不同；内容排序后完全一致，不影响评分结果
- LD_LIBRARY_PATH 需干净覆盖（避免 usr/local/lib 的 libxml2 污染 SDK lld）
---

**编译结束**: 2026-10-03 06:11
**最终状态**: built
