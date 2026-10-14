# DRAFT-xeus-5.0：conandata.yml 注释裸 URL 前缀污染 sources.url —— pre-download 子串替换误伤

> Contributor: pc3-5 | Status: Draft | Updated: 2026-10-09
> Source: xeus 5.0.0 适配任务（OHOS aarch64，task xeus-5.0.0-r01-pc3-5-20261009T094604Z）
> 关联先例: E333（PyPI 连字符 URL 正则截断，同门禁不同根因）

## 背景

xeus 5.0.0 适配时，`finish` W3 本地 CI 模拟（ci/conan/build_and_test.sh + conan create）
反复报：

```text
ERROR: xeus/5.0.0: Error in source() method, line 51
  get(self, **self.conan_data["sources"], strip_root=True)
  NotADirectoryError: [Errno 20] Not a directory:
  '/…/.build-cache/predl_cache/90aa7908_xeus/archive/refs/tags/5.0.0.tar.gz'
```

## 错误特征

- conan create 报 NotADirectoryError，指向 `.build-cache/predl_cache/` 下的路径；
- 日志同时出现 `Could not download from the URL https://gh-proxy.com/file://…`（file:// 被套镜像）；
- W3 固定阻塞，提示"检查 conandata.yml URL/sha256"但 URL/sha256 本身正确。

## 根因

build_and_test.sh 的 pre-download 机制（line ~1164-1300）在 conan build 前把 conandata.yml
中**每个** https URL 用 `content.replace(url, f'file://{local_path}')` 改写成本地缓存路径。
这是**子串替换**。当 conandata.yml 注释中出现裸仓库主页 URL（`https://github.com/jupyter-xeus/xeus`），
而真实 sources.url 是 `https://github.com/jupyter-xeus/xeus/archive/refs/tags/5.0.0.tar.gz` 时，
主页 URL 恰好是 tarball URL 的**前缀** —— 同一 replace 把 sources.url 一起改写成了
`file://<predl_dir>/…` 的非法路径，conan get() 无法处理 → NotADirectoryError。

## 修复

1. conandata.yml 注释移除一切裸 https:// URL，只保留文字描述（"官方 tag 5.0.0 tarball"）；
2. sources.url 保持官方 HTTPS 单 URL + 真实 sha256（R39/PF7 合规）；
3. 清理 `.build-cache/predl_cache/` 残留后重跑 W3。

## 验证

- 修复前: W3 build_and_test.sh 失败（NotADirectoryError，JC 通过后卡 conan create）
- 修复后: `finish` W3 通过，`.ci-result.json` exit_code=0，log_sha256 已写入；
  `conan create`（test_package 消费者 + 鸿蒙专项）2/2 通过；上游 51 用例 51/51。

## 适用边界

- 适用: 所有 conandata.yml 注释含裸 URL 且为 sources.url 前缀的配方（GitHub 托管库最常见）；
- 反例: 注释不含 URL 或 URL 非 sources.url 前缀时不触发；
- 与 E333 区分: E333 是 URL 自身被正则截断（连字符），本条是注释 URL 作为前缀被 replace 误伤。

## 查重差异

- 正式条目 E333: 同门禁、同 pre-download 机制，但错误路径不同（截断 vs 前缀污染）→ 新增差异成立；
- 无同名草稿 → 建本 DRAFT。
