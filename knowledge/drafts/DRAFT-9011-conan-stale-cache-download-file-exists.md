# DRAFT-9011-conan-stale-cache-download-file-exists

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-9011-conan-stale-cache-download-file-exists.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-9011: conan 报 `Error, the file to download already exists: …/conan_package.tgz` —— 脏缓存条目清理

- 条目主题：`conan create/install` 拉取已发布依赖/工具链时报缓存内已有同名下载临时文件而中断；
  根因是上次中断（超时/被杀/断网）留下的 `conan_export.tgz` / `conan_package.tgz` 残片，
  处置是按报错路径删除该缓存条目后重试（可重建）。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxxx）
- 关联 PR：feat/pftools-3.2.12

## 现象

```console
ERROR: Package 'libfile-slurp-perl/9999.32' not resolved:
       Error, the file to download already exists:
       '/storage/Users/<user>/.conan2/p/libfibbf9a7773c82a/d/conan_export.tgz'. [Remote: ohpcd]

# 重试后可能换路径继续报：
ERROR: Error, the file to download already exists:
       '/storage/Users/<user>/.conan2/p/libfi62f835cc92129/d/conan_package.tgz'. [Remote: ohpcd]
```

特征：报错**不是**制品仓/网络问题（同一包单独 `conan download` 为 `exit 0`）；路径固定在
`~/.conan2/p/<pkg-hash>/d/conan_{export,package}.tgz`；重试间 hash 目录名可能变化。

## 处置

```bash
rm -rf /storage/Users/<user>/.conan2/p/<报错中的 hash 目录>     # 含 d/ 残片；conan 会重建
conan create <pkg_dir> -pr:h=<profile> -pr:b=<profile>          # 失败会给出新 hash → 重复本步
```

批量清理（从构建日志抽路径）：

```bash
grep -oE "/[^ ]*/.conan2/p/[A-Za-z0-9]+/d/conan_(package|export)\.tgz" build.log \
  | xargs -n1 dirname | sort -u | xargs -r rm -rf
```

## 判定与止损（避免误判为依赖缺失）

1. 先确认不是制品仓缺失：对同一包单跑 `conan download <pkg>/<ver> -r=ohpcd --only-recipe`；
   `exit 0` ⇒ 包存在，问题在本地缓存 → 清缓存重试，**不要**上报 `dependency_missing`。
2. 清理后仍报同一路径 ⇒ 可能有多进程共用 `CONAN_HOME` → 改独立 `CONAN_HOME` 规避。
3. 若含网络特征（reset/timeout/SSL/5xx/DNS）→ 按 conan 退避重试策略；本条目专治**非网络性脏缓存**。

## 证据（真实执行）

pftools 3.2.12（HarmonyOS/aarch64）适配期间实测：

- 第 1 次 `conan create` → `…/libfibbf9a7773c82a/d/conan_export.tgz`（exit 1）；
- 删该目录重试 → 换成 `…/libfi62f835cc92129/d/conan_package.tgz`（exit 1）；
- 再删重试 → `libfile-slurp-perl` 与 `flang-ohos` 均正常安装；
- 同包独立验证 `conan download libfile-slurp-perl/9999.32 -r=ohpcd` → **exit 0**；
- 最终 `conan create` **exit 0**。

## 推广价值

- 所有 conan 2.x 适配/CI 场景；把"缓存脏 / 依赖缺失 / 网络故障"三者区分开，
  避免把本地缓存问题误报为 `dependency_missing`。

## 查重关键词

Error, the file to download already exists、conan_package.tgz、conan_export.tgz、
~/.conan2/p/<hash>/d、脏缓存、conan download exit 0 但 create 失败、CONAN_HOME 并发
