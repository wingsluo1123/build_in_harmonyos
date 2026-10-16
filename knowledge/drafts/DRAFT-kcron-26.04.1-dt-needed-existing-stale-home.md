# DRAFT-kcron-26.04.1-dt-needed-existing-stale-home

> 来源: kcron 26.04.1 真机适配（archives/k/kcron/26.04.1）| Status: Draft | 2026-10-16

## 现象

共享真机上，已发布 KF6 制品因无 DT_SONAME，被链接时把建造机缓存绝对路径烙进
DT_NEEDED（机制见 E537）。与「CI 上路径不存在」的常见形态不同，本形态是：

```
$ readelf -d libKF6*.so | grep NEEDED | grep /
(NEEDED)  /storage/Users/currentUser/.cache/conan2/p/<hash>/p/lib/libKF6ConfigWidgets.so
#    ↑ 在真机上 ls 一下：**存在**（残留的旧 conan home）
```

于是三类既有处置全部失明或失效：

1. **「路径是否存在」判据失明**——没有缺失可修，看起来一切正常；
2. **加载器跟随装进图外副本**——含 `/` 的 DT_NEEDED 直接 open 该路径，
   装进来的是旧 home 的陈旧副本（同一 package_id 的缓存副本内容不保证相同，
   kcachegrind 26.04.0 已实证同 package_id 两份字节不同）；而旧副本内部又
   记着构建树相对条目（`../../bin/libKF6*.so`），从外部无从修复；
3. **symlink 补齐法不可用**——真机 HMDFS 全盘拒 symlink（EACCES），且此处
   根本无缺失可补。

kcron 真机实录（consumer 侧拦截动作）：

```
conan-create.log:1055 patching absolute DT_NEEDED /storage/…/.conan2/p/b/kcore…/p/lib/libKF6CoreAddons.so -> libKF6CoreAddons.so in kcron_helper
conan-create.log:1056 patched 1 absolute DT_NEEDED entries
conan-create.log:532  NEEDED sanitized in kcm_cron.so: 10     # 被测包自身，package() 侧根治
conan-create.log:747+ link farm skip … Permission denied（308 条全 skip，套件仍全绿）
```

## 推荐方案

**判据（先测归属，再决定是否动作）**：对每个绝对 DT_NEEDED 解析 realpath，
检查是否落在「本图任一依赖 package_folder 前缀」内；不在 → 图外（陈旧副本），
必须修；文件名不存在 → 缺失型（DRAFT-13577/E5xx 的 symlink 法适用面）。

**处置（consumer 测试期，referrer 原位改写）**：

- 扫描面 = 本图依赖 `lib/*.so` + 被测包全部 ELF；
- 每条图外绝对条目 → 裸基名，白名单 = basename 命中本图闭包索引，
  闭包外条目保持原样（本来只能靠烙死路径解析）；
- 改写链路 = `llvm-objcopy --remove-section .codesign` →
  `patchelf --replace-needed <绝对路径> <基名>` →
  `binary-sign-tool sign -selfSign 1`（**必须重签**，E517/14403 族；幂等）；
- 被测包自身产物应在 `package()` 侧根治：等长 `.dynstr` 原位补丁 + 重签
  （DRAFT-14403 路线，kcron 自产 kcm_cron.so 10 条即此路）；
- **不要依赖 symlink farm**：真机 308 条建链全 EACCES 而套件全绿，
  farm 是装饰不是机制——靠它"看着过了"会掩盖 referrer 未改写。

治本退路（E537 rec）：链接期就不产生绝对条目——无 SONAME 依赖打
IMPORTED_SONAME 或 `target_link_directories` + `-l:libKF6X.so` 精确名。

## 验证

- 修复侧：`patching absolute DT_NEEDED … -> libKF6CoreAddons.so in kcron_helper`
  + 重签后消费者 ctest 100%（`reports/test-package-ctest.log` 25 PASS）；
- 负判据：link farm 308 条 skip 而全绿，证明通过与否不依赖 farm；
- 同设备旁证：kcachegrind 26.04.0 同一 package_id 两份缓存副本 NEEDED 字节
  不同（conan 不校验字节），本机"恰好存在"掩盖缺陷的机理一致。

## 关联与划界

- **DRAFT-13577 / DRAFT-E5xx（缺失型）**：路径不存在 → 内容不变的 symlink
  补齐；本条是**存在型**（图外陈旧副本），symlink 法无效，判据与处置都不同；
- **DRAFT-14403 / DRAFT-ohos-dt-needed-bare-name-normalization**：产物
  owner 侧（package()）的等长 `.dynstr` 归一化 + 重签；本条是 **consumer
  测试期对依赖闭包**的兜底改写，两者互补（owner 治己，consumer 兜人）；
- **DRAFT-kcachegrind-26.04.0**：同一双 home 现实的 CI 侧投影（相对条目 +
  CWD recon）；本条给出设备侧的统一判据（realpath 归属）与设备现实修正；
- **E537**：无 SONAME → 绝对烙入的机理本体与链接期治本方案。
