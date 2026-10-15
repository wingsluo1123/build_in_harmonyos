# E435 — 上游 tag 带 v 前缀 + sha256 与 .tarball-sha256 交叉验证

## 错误特征

按版本号直觉写 codeload URL 得到 404：

```
https://codeload.github.com/<org>/<repo>/tar.gz/refs/tags/<ver>  →  404: Not Found
```

（实际 tag 名为 `v<ver>`。）

## 触发条件

- 上游仓库 tag 名与版本号不同构（v 前缀 / release- 前缀 / 日期名等）
- keycloak-config-cli 即为 `v6.4.0` 形式，仓库内附 `.tarball-sha256` 文件记录官方摘要

## 根因分析

codeload 的 `refs/tags/<name>` 必须逐字等于真实 tag 名。版本号≠tag 名时 404。
sha256 应三方一致：本地下载计算值 = conandata 声明值 = 上游 `.tarball-sha256`（或 release 页 checksum）。

## 解决方案

### 推荐方案

先确认真实 tag 名再写 URL：

```bash
git ls-remote --tags https://github.com/<org>/<repo> | grep <ver>
```

下载后与上游 `.tarball-sha256` 交叉比对，一致再写入 conandata.yml。

### 禁止做法

- ❌ 404 后直接猜其他 URL 变体而不查 tag 列表

## 验证

```bash
sha256sum <tarball>   # 与上游 .tarball-sha256 文件内容比对
```

## 关联条目

- 相关: E429（conandata sources 声明）

## 来源

- 草稿: E435-draft-59D5
- 事件: keycloak-config-cli 6.4.0 W0 源码获取（sha256 c4196406… 三方一致）
