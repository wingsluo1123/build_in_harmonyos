# SmartList

> Procmail 之上的邮件列表管理器 (脚本套件 + C 小助手)。

## 简介

SmartList 由 Stephen R. van den Berg 编写, 构建在 procmail 邮件处理包之上,
提供邮件列表的创建/订阅/退订/摘要/归档/退信处理等能力。核心是 Bourne shell
脚本 (`SmartList/bin`, `SmartList/etc`) 与少量 C 助手 (`src/hsort.c`,
`src/gethome.c`; 完整的 flist/multigram 需与 procmail 源码树混合编译)。

本仓库适配的 3.15 (2000/09/03) 为上游最终稳定版, 内容与
procmail-org/SmartList 的 master HEAD 一致。

## OHOS 适配要点

- 只构建可独立编译的 `hsort` 静态库与 `gethome` 二进制 (clang, `-std=gnu17`, `-fPIC`);
  垫片 `src/includes.h` (0001 补丁) 替代缺失的 procmail 头, 不改上游逻辑。
- 脚本套件原样安装到 `bin/smartlist` 与 `share/smartlist/{etc,examples}`;
  调用时使用 `sh`, 不依赖 `/bin/sh` 硬路径。
- 完整 flist/multigram 投递功能需 procmail 树, 本包不提供; 需要完整投递请另行适配 procmail。
- 上游无测试套件; test_package 从消费者视角验证 hsort() API、gethome 执行与脚本完整性。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| (无 Conan 依赖) | - | 运行时如需投递需系统 MTA / procmail, 属环境要求 |

## 功能验证

```bash
./test_hsort
python3 test_smartlist.py --package <pkg> --hsort-bin ./test_hsort
```

## 参考

- [上游仓库](https://github.com/procmail-org/SmartList)
- [Procmail 主页归档](http://www.ring.gr.jp/archives/net/mail/procmail/)
