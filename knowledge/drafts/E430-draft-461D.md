# E430 — ohc E017 ghfast.top 镜像注入劫持与 .ghfast-bak 回滚覆盖

## 错误特征

conan create 源码下载超时（URL 被临时改写为 ghfast.top 镜像）：

```
ERROR: ... Unzip failed / download ...
https://ghfast.top/https://github.com/... : connect timeout
```

日志伴行：`🔧 E017 预防: GitHub URL 已临时注入 ghfast.top 镜像`；崩溃后下次启动出现
`🔄 已恢复上次崩溃残留的 conandata.yml（镜像注入回滚）`，且 conandata.yml 内容被静默还原。

## 触发条件

- sources.url 匹配 `github.com` 形态（`github.com/<org>/<repo>/archive/...`），被 E017 预处理改写
- 当前设备网络对 ghfast.top 不可达（connect timeout）
- （回滚覆盖分支）上一次 ohc 构建中途崩溃/被杀，`conandata.yml.ghfast-bak` 残留

## 根因分析

E017 预防机制在 conan create 前把 github.com URL 临时前缀 ghfast.top 镜像、备份原文件为
`.ghfast-bak`、构建后回滚。注入只匹配 github.com URL（codeload.github.com 形态不命中）；
ghfast.top 不可达时 github.com 形态 URL 必被劫持到死镜像。崩溃残留的 bak 会在下次 ohc 启动
触发"恢复"逻辑覆盖 conandata.yml，吞掉期间的手工修改。

## 解决方案

### 推荐方案

1. 网络侧：source URL 用 codeload 裸形态避开注入匹配（配合 E429 显式 filename）；
2. 每次重跑 ohc 前：`rm -f <archive>/conandata.yml.ghfast-bak`，并 `grep -n url: conandata.yml` 核对内容未被回滚覆盖。

### 禁止做法

- ❌ 构建失败后不删 bak 直接重跑（bak 会覆盖手工修复，导致反复用错误 URL 构建且难定位）

## 验证

```bash
ls <archive>/*.ghfast-bak        # 存在即有残留
grep -c ghfast <archive>/conandata.yml   # 构建后应为 0
```

## 关联条目

- 相关: E429（codeload URL + filename 的组合解法）

## 来源

- 草稿: E430-draft-461D
- 事件: keycloak-config-cli 6.4.0 conan-verify 第三轮 G2 失败 + 第四轮 bak 回滚发现
