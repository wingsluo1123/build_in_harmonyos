# DRAFT-libfprint-1.94.10-source-download-timeout-gitlab-freedesktop

> Contributor: gcw_eQ4VpLdf | Status: Draft | Updated: 2026-10-14
> Source: libfprint 1.94.10 HarmonyOS PC 适配（PR #14631, CI #90157 vs #85262）
> 领域：conan / network / ci-infra / source / ohos-platform

## 背景

libfprint 1.94.10 在 HarmonyOS PC（aarch64-linux-ohos）适配中，`conan create` 的
`conan-build-test` 阶段多次在 **source() 源码下载**时失败，报：

```text
HTTPSConnectionPool(host='gitlab.freedesktop.org', port=443): Read timed out.
('Connection broken: IncompleteRead(0 bytes read, 1 more expected', ...)
WARN: network: Download failed, check server, possibly try again
```

CI 失贴审止触加当类一「睑络问题/池码下载超时」，提示「已知可达: zlib.net; 已知不可)达:
ftp.gnu.org」。但同一域名 `gitlab.freedesktop.org` 上其它已合入 main 的包却能正常通过：

| 包 | 源码包 | 大小 | 状态 |
|----|--------|------|------|
| libfprint/1.94.10 | libfprint-v1.94.10.tar.bz2 | **9,065,283 B (~9MB)** | ❌ Read timed out |
| libinput/1.26.2 | libinput-1.26.2.tar.gz | ~1MB | ✅ 合入 main |
| accountsservice/26.27.3 | accountsservice-26.27.3.tar.gz | 686KB | ✅ 合入 main |
| libevdev/1.13.7 | libevdev-libevdev-1.13.7.tar.gz | 166KB | ✅ 合入 main |

## 错误签名

```text
HTTPSConnectionPool(host='gitlab.freedesktop.org', port=443): Read timed out.
('Connection broken: IncompleteRead(0 bytes read, 1 more expected)', IncompleteRead(...))
libfprint/1.94.10: WARN: network: Download failed, check server, possibly try again
ERROR: libfprint/1.94.10: Error in source() method ...
```

## 根因

1. **包大小差异**：Worker 到 `gitlab.freedesktop.org` 的带宽极慢，`CONAN_REQUEST_TIMEOUT=300s`
   内 166KB~1MB 的小包能下完，9MB 的大包必然 `Read timed out` / `IncompleteRead`。域名本身
   **可达**（小包能过），问题在传输耗时。

2. **CI 镜像表不含该域名**：`ci/conan/build_and_test.sh` 的 `get_mirrors`（L1019-1235）只覆盖
   github.com、ftpmirror.gnu.org、download.gnome.org、gitlab.gnome.org、cdn.kernel.org、
   xorg.freedesktop.org 等；**没有 gitlab.freedesktop.org**。因此 conandata.yml 的单值官方
   URL 不会被 CI 改写为「官方 + 镜像」列表，conan 只能裸连官方源（E549 的镜像注入对本域名
   不生效）。

3. **Worker 缺 curl**：`pre-download` 步骤报 `[Errno 2] No such file or directory: 'curl'`，
   CI 预下载缓存（DOWNLOAD_CACHE/file:// 改写）也无法兜底。

**判据（环境性而非配方缺陷）**：同一 commit 在不同 worker 上结果不一致——#85262（CI-011）
源码下载成功、编译 113/113 目标全过；#90157（CI-025）等多轮在 source() 阶段 Read timed out。
同型判据见 DRAFT-libfprint-1.94.10-meson-eagain-unknown-compiler-worker（同一 SHA 不同
worker 结果不一致 = worker 环境问题）。

## 处置（不改配方 URL）

1. **先判环境**：本地用与 CI 完全相同的命令复跑
   `CI_PACKAGES=archives/l/libfprint/1.94.10 CI_BRANCH=feat/libfprint-1.94.10 CI_PR_NUMBER=14631 zsh ci/conan/build_and_test.sh`，
   本地全绿即证明配方与 URL/sha256 无误；
2. **/rebuild 换 Worker**：对同一 SHA 发起 /rebuild，观察是否落到网络可达的 Worker
   （#85262 已证明存在可下载成功的 Worker）；
3. **确认域名不在镜像表后再决定是否换源**：`grep -n "gitlab" ci/conan/build_and_test.sh`；
   若确认不在镜像表且大包反复超时，可考虑（a）在 CI 镜像表中为 gitlab.freedesktop.org
   增加镜像映射（属 CI 基础设施改动，需单独评估），或（b）按 E549 原则保持单值官方 URL +
   换可达镜像地址（须对实际下载内容重算 sha256），**切勿**把镜像写成第二个列表项
   （会静默关掉 CI 镜像注入）。

## 禁止做法

- ❌ 把环境性网络超时当作配方缺陷，去改 URL/sha256 或加无谓重试逻辑
- ❌ 在 conandata.yml 写多 URL 列表（E549：列表形态会让 CI mirror fallback 静默跳过）
- ❌ 把失败状态改为通过 / 跳过测试以绕过间歇失败（违反 R9/伪造状态规则）

## 验证

```bash
# 判环境：同一 SHA 对比不同 worker：#85262（CI-011）编译 113/113 全过（下载成功）
#        vs #90157（CI-025）source 阶段 Read timed out
# 本地同命令复跑（应全绿，本机到 gitlab.freedesktop.org 实测 9MB 约 6s 下完）：
CI_PACKAGES=archives/l/libfprint/1.94.10 CI_BRANCH=feat/libfprint-1.94.10 \
  CI_PR_NUMBER=14631 zsh ci/conan/build_and_test.sh
```

## 关联条目

- 相关: E549（conandata.yml 多 URL 列表导致 CI mirror fallback 静默跳过，单值 URL 原则）
- 相关: E299（Conan source 失败分层诊断：timeout/403/404/sha256 分治，保留官方源）
- 相关: E372（Worker 缺 curl/SSL 的 Hash-bound HTTP fallback）
- 相关: DRAFT-libfprint-1.94.10-meson-eagain-unknown-compiler-worker（同 SHA 不同 worker 判据）
- 相关: DRAFT-conandata-single-url-ci-mirror-fallback
