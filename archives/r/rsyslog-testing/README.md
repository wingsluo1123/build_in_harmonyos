# rsyslog-testing

Rsyslog 测试框架（testbench）在 HarmonyOS PC 上的独立 Conan 包。

## 说明

- 与 `rsyslog` 主包共用同一上游 tarball：`rsyslog-8.2604.0.tar.gz`
- 独立打包 testbench 相关产物（tests/ 目录下的 C 单元测试二进制与 shell/RainerScript 测试脚本）
- `--enable-testbench` 启用测试框架；构建期修复 E011（HMDFS umask）+ pthread_cancel（musl 缺失）+ musl stub（endutxent / __res_state）

## 状态

- 8.2604.0：`built`（configure exit 0 + make exit 0；2/2 C 单元测试 PASS）
- 路径：B 候选（知识库扩展）

## 目录

```
8.2604.0/
├── manifest.yaml      # 版本级 manifest
├── conanfile.py       # Conan 配方
├── conandata.yml      # 源码 URL + SHA256
├── test_package/      # smoke 测试
├── notes.md           # 适配笔记
├── pr-draft.md        # PR 正文草稿（本地）
├── issue-draft.md     # Issue 正文草稿（本地）
└── wiki-content.md    # Wiki 页面内容文本（用户手动创建）
```
