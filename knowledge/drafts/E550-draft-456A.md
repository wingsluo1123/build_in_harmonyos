# E550: zsh heredoc 临时文件走 TMPPREFIX，OHOS /tmp 只读导致脚本门禁失败

## 基本信息
- **严重度**: 2（🟡medium）
- **类别**: shell
- **来源**: osdclock 0.5 适配（feat/osdclock-0.5，HarmonyOS PC / OHOS aarch64）
- **贡献者**: 456A（草稿）

## 错误特征
```
can't create temp file for here document: read-only file system
```

## 根因
W3 的 setup.sh/build_and_test.sh 用 zsh 执行，zsh 的 heredoc 临时文件走 TMPPREFIX（默认 /tmp/zsh），而 OHOS 上 /tmp 只读；仅设 TMPDIR 无效（zsh 不读 TMPDIR）。

## 推荐方案
跑 finish/submit（或任何驱动 build_and_test.sh 的入口）时同时导出 TMPPREFIX=<可写目录>/zsh 与 TMPDIR=<可写目录>；否则所有含 heredoc 的 L0 门禁会报只读文件系统而失败。

## 关联
- 配方: `archives/o/osdclock/0.5/conanfile.py`、`patches/`
- 测试: `archives/o/osdclock/0.5/test_package/test_osdclock.sh`

> 本文件为草稿配套文档（R31/W5：E###.kv ↔ doc/E###.md 配套），待主编审核后 promote 为正式条目。
