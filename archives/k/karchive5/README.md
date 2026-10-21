# karchive5

KDE Frameworks 5 的归档库（Qt5 轨道，包名 karchive5）。上游交付
libKF5Archive.so，提供 KArchive / KZip / KTar / KAr / KRcc 归档类，以及
KCompressionDevice 透明压缩过滤器（gzip、bzip2、xz/LZMA、zstd）。

- 上游主页：https://invent.kde.org/frameworks/karchive
- 上游源码：https://download.kde.org/Attic/frameworks/5.116/karchive-5.116.0.tar.xz
- 许可证：LGPL-2.0-or-later

## 版本

- 5.116.0：仓库中已存在的 KF5 归档版本，版本级 manifest 状态 built；
  source_url 使用国内镜像
  https://mirrors.bfsu.edu.cn/kde/Attic/frameworks/5.116/karchive-5.116.0.tar.xz。
- 5.116.0.1：R37 打包修复版本，上游源码与 sha256 不变（二者相同），仅配方
  变更。版本级 manifest 状态 built（配方定稿，设备回线后执行本轮
  conan create 并回填实测数字）。

## 依赖链

- qt5-qtbase/5.15.2.2：Qt5Core（已发布二进制绑定 zlib/1.3.1）
- zlib/1.3.1（5.116.0.1）或 zlib/1.3.1.1（5.116.0）：ZLib REQUIRED
- bzip2/1.0.8、xz/5.6.2、zstd/1.5.7：可选压缩后端，全部启用
- ecm/6.26.0：tool_requires

## 平台适配要点

- QT_MAJOR_VERSION=5 与 KF_IGNORE_PLATFORM_CHECK=TRUE：保持 Qt5 代码路径并
  绕过 KDE 平台白名单；KF_SKIP_PO_PROCESSING=ON 跳过翻译目录生成。
- OHOS 平台模块不定义 SONAME 标志：手动设置
  CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG=-Wl,-soname, 与
  CMAKE_PLATFORM_NO_VERSIONED_SONAME，避免 .so 缺少 DT_SONAME（W3/L5）。
- 压缩后端按 Conan 包消费；注入的 CMAKE_PROJECT_INCLUDE 把
  CMAKE_FIND_PACKAGE_PREFER_CONFIG 翻回 OFF，让上游 FindZLIB / FindBZip2 /
  FindLibLZMA 提供规范的 ZLIB::ZLIB、BZip2::BZip2、LibLZMA::LibLZMA 目标
  以及大写 *_FOUND 变量。
- zstd/1.5.7 的 libzstd.pc 硬编码 prefix=/usr/local：配方在探测前自行定义
  PkgConfig::LibZstd / LibZstd_FOUND，并用 pkg-config 包装器重定位 .pc。
- 非 PIC 链接墙：5.116.0 用 zlib/1.3.1.1（force=True）；5.116.0.1 改回
  zlib/1.3.1 并加 -Wl,--exclude-libs,ALL，避免改变 qt5-qtbase 的 package id。
- ECM_MODULE_PATH 手动注入；AUTOMOC/AUTORCC 指向 qtbase 的 bin/moc、bin/rcc；
  复制完整 mkspec 树，使 qplatformdefs.h 的 ../common/posix 相对包含可解析。
- 5.116.0.1 增加 portability 补丁 0001：沙箱拒绝 symlink()（EACCES）时跳过
  karchivetest 的 symlink 专项校验，其余归档读写照常执行；测试期还通过
  XDG_DATA_DIRS 注入含 zstd 条目的 shared-mime-info 数据库。

## 测试摘要

- 5.116.0：版本级 manifest 记录上游 CTest 5/5 通过（karchivetest、
  kfiltertest、deprecatedtest、klimitediodevicetest、
  kcompressiondevicetest），0 失败/0 跳过；test_package 覆盖 KZip 往返与
  GZip/BZip2/Xz/Zstd 过滤器，26/26 校验点通过。
- 5.116.0.1：2026-10-20 真机实测（记录见
  `5.116.0.1/manifest.yaml` 的 `test_results` 与
  `build-deps-wave2.log`）：CTest 实际注册 5 项，100% tests passed，
  0 failed out of 5；test_package 为 KTar/KZip/KCompressionDevice GZip
  往返测试，20 项断言全 PASS（TEST SUMMARY: 0 failure(s)），
  真机 `conan create` RC=0；l0/l1/l2/l4/l5 全部 pass。
