# E-DRAFT: 构建规则硬编码 efitools 外部命令，OHOS 无命令也无 OpenSSL 可构建 → vendor 纯 stdlib Python 移植

- **触发实例**：u-boot 2026.07 适配（2026-09-29，任务 11418，分支 feat/uboot-2026.07，
  patch 0009-capsule-esl-gen-via-python.patch）
- **错误签名**：
  `/bin/sh: cert-to-efi-sig-list: inaccessible or not found` →
  `make[3]: *** [.../lib/efi_loader/Makefile:87: capsule_esl_file] Error 127`
- **类别**：external-build-tool-vendor
- **严重度**：2（确定性构建失败，但修复对象是纯数据包装、移植代价低且可字节级验证）

## 症状

```text
  CAPSULE_ESL_GEN  /data/storage/el2/base/.conan2/p/b/uboot.../b/build-release/sandbox/capsule_esl_file
/bin/sh: cert-to-efi-sig-list: inaccessible or not found
make[3]: *** [/data/storage/el2/base/.conan2/p/b/uboot.../b/lib/efi_loader/Makefile:87: capsule_esl_file] Error 127
```

## 根因

`lib/efi_loader/Makefile` 在 `CONFIG_EFI_CAPSULE_AUTHENTICATE=y`（sandbox_defconfig
默认开启）时：

```make
capsule_crt_full=$(srctree)/$(subst $(quote),,$(CONFIG_EFI_CAPSULE_CRT_FILE))
quiet_cmd_capsule_esl_gen = CAPSULE_ESL_GEN $@
cmd_capsule_esl_gen = cert-to-efi-sig-list $(capsule_crt_full) $@
```

上游默认构建机装好了 efitools（.azure-pipelines 里 apt 安装）。OHOS 真机：

- 没有 `cert-to-efi-sig-list` 命令；
- 也没有 OpenSSL 开发头可自行编译它（efitools 是 C 程序，链接 OpenSSL；
  OHOS SDK/HNP 工具链与 notes.md 决策表 11 行同况——密码学栈是 libohcrypto，
  不提供 openssl 头）。

而该操作本身是**纯数据包装**（读 vathpela/efitools 源码确认）：

1. `PEM_read_bio_X509` 读 PEM 证书；
2. `i2d_X509` 序列化为 DER；
3. 按 UEFI 规范包装：
   - `EFI_SIGNATURE_LIST`（28 字节头）：`SignatureType=EFI_CERT_X509_GUID`
     (a5c059a1-94e4-4aa7-87b5-ab155c2bf072)、`SignatureListSize=DER+44`、
     `SignatureHeaderSize=0`、`SignatureSize=DER+16`；
   - `EFI_SIGNATURE_DATA`：`SignatureOwner` = 全零 GUID（u-boot 调用不带
     `-g` 参数）+ `SignatureData` = DER 字节。

无签名、无加密，纯粹字节搬移。

## 最小修复（vendor stdlib-only Python 移植）

随源码附上 `scripts/cert-to-efi-sig-list.py`（纯标准库 base64/struct/sys）：
PEM 证书体 base64 解码即 i2d_X509 的 DER 字节；规则改一行：

```make
cmd_capsule_esl_gen = python3 $(srctree)/scripts/cert-to-efi-sig-list.py $(capsule_crt_full) $@
```

python3 在所有需要它的地方都在：OHOS 设备（conan 本身就跑在 python3 上）、
上游 CI。全环境行为一致，与决策表 9 行（NO_PYTHON 门）同原则。

**字节级交叉验证（本地已做）**：`openssl x509 -in board/sandbox/
capsule_pub_key_good.crt -outform DER` 与移植输出逐字节一致（787 字节 DER、
831 字节 ESL，SignatureType/owner/size 字段全对）——即与真实 efitools 的
i2d_X509 输出等价。

**测试面零损失**：`CONFIG_EFI_CAPSULE_AUTHENTICATE=y` 完整保留，
test/lib/efi_loader 的胶囊认证自测照常编译进 sandbox 二进制。

## 禁忌

- 禁止 `-d EFI_CAPSULE_AUTHENTICATE` 关特性（胶囊认证 ut 全部消失，直接损
  测试面，路径 C ≥90% 门槛下不可接受——列为 fallback）；
- 禁止 apt/opkg 装 efitools（OHOS 无发行版包管理器提供宿主工具）；
- 禁止源码编译真实 efitools（依赖 OpenSSL 头，平台刻意不提供，死循环）。

## 适用范围与查重

- **适用**：所有「上游 CI 靠发行版包装宿主工具、目标平台无包管理器且工具链
  缺该工具依赖」的构建规则硬编码——UEFI/签名/固件类项目重灾区（efitools、
  sbsigntools、pesign 等）。判断标准：若工具操作是纯数据变换（无密码学运算），
  Python 移植 + 上游语义交叉验证是首选。
- **查重**：grep 现有 drafts 无 efitools/ESL/cert-to-efi-sig-list 条目；
  E 系列「缺外部命令」类条目多为运行时依赖缺失（rc=127 的运行时形态），
  本条是构建期规则硬编码 + 无宿主安装途径的 vendor 型。draft-review 相似度
  预期 0.30 以下，建议 create。
