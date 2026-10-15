# INDI Pentax

Pentax DSLR 的 INDI 相机驱动。此归档适配上游 1.0 的 aarch64 MSC 构建，并增加共用图像读取代码的 `indi_pentax_image` 离线转换命令。

| Conan 版本 | 上游身份 | 目标 | 验证边界 |
|---|---|---|---|
| 1.0 | indilib/indi-3rdparty `4e700ab0487f1e636a84c927e3e4e368bb1e896a` | OHOS armv8 | 图像消费及无相机错误路径；实拍待验 |

源码内部明确标记 1.0；发行版 `1.0+20221221102411` 的源码内部为 1.1，二者不混用。

```bash
conan create archives/i/indi-pentax/1.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build='indi-pentax/*'
```

运行时使用 Conan `VirtualRunEnv` 提供的动态依赖路径。驱动通过标准输入/输出与 INDI 客户端通信；`indi_pentax_image jpeg|raw INPUT OUTPUT.fits` 用于离线 FITS 转换。已有输出文件保持原内容。硬件拍摄需要 Pentax 相机、MSC 模式和相应 SCSI 设备权限。

上游 1.0 本就排除了 aarch64 的 Ricoh PTP 后端；本归档没有增加 Ricoh ARM64 SDK，也没有将离线图像转换计作相机拍摄成功。本次按 A 路径（基础适配）提交，硬件功能仍需后续验收。详见 [适配笔记](1.0/notes.md) 和 [测试清单](1.0/test_package/MANIFEST.yml)。
