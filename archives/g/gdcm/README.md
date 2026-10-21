# gdcm

Grassroots DICOM——DICOM 医学影像格式的 C++ 工具库：解析/读写/转换 DICOM 文件，
覆盖 DICOM 网络协议（C-ECHO/C-FIND/C-STORE）、多种压缩编码（JPEG/JPEG-LS/JPEG2000/RLE）。

- 上游：https://github.com/malaterre/GDCM
- 许可证：BSD-3-Clause
- 已适配版本：3.2.11、3.0.24（均 OHOS PC aarch64，静态库 14 个 `.a` + 14 个 CLI 工具）
- 版本间差异要点：3.0.24 无 `libgdcmrle`（RLE 源码进 gdcmMSFF）、消费方必须显式链 `socketxx`
  （gdcmMEXD 的 LINK_PRIVATE 依赖）、EXPAT include 路径上游已修（不需要 3.2.11 的那枚补丁）；
  `ctest -N` 注册数也不同（3.2.11 为 200，3.0.24 为 199）——照抄同族版本的清单会踩坑，
  详见各版本目录下的 `notes.md`
