# E549 — Harmonybrew bottle URL 轮换导致 cargo 运行期 bottle 404（E509 下游延伸）

## 错误特征

conan create 在构建第一步（`_prepare_cargo_runtime` 调 `self.conan_data["cargo_runtime"]`
里的 bottle URL 下载）即失败：

```
wpmeta/0.2.0: Downloading ... from https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.4.arm64_ohos.bottle.tar.gz
NotFoundException: Not found: https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.4.arm64_ohos.bottle.tar.gz
ERROR: wpmeta/0.2.0: Error in build() method
```

特征：失败 URL 是 Harmonybrew bottle 仓（harmonybrew.atomgit.com/bottles/...），
HTTP 404；配方本身无语法问题，且同一路径在先例任务中曾可用。

## 触发条件

- 构建系统: conan（配方 conandata.yml 含 `cargo_runtime` bottle URL）
- 阶段: build() 第一步（E509 路径：为 cargo/rustc 提供运行期 libssl/libcrypto/libz）
- 场景: 配方从先例（weggli/below/argc/alass 等）静态照抄 bottle URL，
  数周后 bottle 仓轮换下架旧版 bottle

## 根因分析

Harmonybrew bottle 仓持续轮换：每个 formula 只保留当前 stable 版本的 bottle，
旧版（如 openssl@3 3.6.4、zlib-ng-compat 2.3.3_1，乃至不带 `.bottle.1`
后缀的 3.6.4_1 / 2.3.3_2）会整体下架（404）。配方 conandata.yml 中静态
写死的 bottle URL 因此随时间腐烂，导致 E509 的 cargo 运行期注入路径在
构建首步失败。本次 wpmeta 0.2.0 适配（2026-10-13）实测：weggli（2026-10-01）
使用的 openssl%403-3.6.4 与 zlib-ng-compat-2.3.3_1 均 404。

## 解决方案

### 推荐方案

从 Harmonybrew 官方 formula API 动态获取当前发布的 bottle URL + sha256，
不静态照抄先例配方：

1. 拉取 `https://harmonybrew.atomgit.com/api/formula.jws.json`（payload 为
   纯 JSON 数组）；
2. 按 formula name 查当前 stable 版本（如 openssl@3 → 3.6.5_1、
   zlib-ng-compat → 2.3.3_2），取其 `bottle` 段中 arm64_ohos 的
   `url` 与 `sha256`；
3. 本地下载实测核验 sha256 后写入 conandata.yml 的 cargo_runtime 段
   （wpmeta 0.2.0 实测：`openssl%403-3.6.5_1.arm64_ohos.bottle.1.tar.gz`
   sha256 `ae1d5bf9252d65d86053e68d7c91fc9d0066016bce50662ce4a32a0b0e954ef2`、
   `zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.1.tar.gz` sha256
   `7092bfe7af8908f4a7c72493881291fe2416f27fc6502c34e22346a4dbfc4c51`）；
4. 在 conandata.yml 注释中记录发现日期，便于后续轮换排查。

### 禁止做法

- ❌ 静态照抄先例配方的 bottle URL（会随轮换腐烂）；
- ❌ 去掉 sha256 校验或用宽松通配绕过 404（破坏供应链完整性）。

## 验证

```bash
# 确认旧 bottle 已下架（应输出 404）
curl -sS -o /dev/null -w "%{http_code}\n" \
  https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.4.arm64_ohos.bottle.tar.gz
# 从 formula API 取当前 bottle url + sha256
curl -sS https://harmonybrew.atomgit.com/api/formula.jws.json -o formula.jws.json
# 下载新 bottle 后本地核对 sha256 与 API 记录一致
sha256sum openssl*3.6.5_1*.tar.gz zlib-ng-compat-2.3.3_2*.tar.gz
```

## 关联条目

- 相关: E509（cargo 运行期 OpenSSL 共享库 bottle 注入——本条目是其 URL 轮换风险）
- 证据: wpmeta 0.2.0 适配实测（2026-10-13）+ weggli 0.2.4 先例对照
