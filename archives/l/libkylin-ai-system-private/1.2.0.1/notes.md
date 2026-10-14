# libkylin-ai-system-private 1.2.0.1 — 适配笔记

## 上游
- 官方归档: Debian pool orig tarball
  `https://deb.debian.org/debian/pool/main/libk/libkylin-ai-system-private/libkylin-ai-system-private_1.2.0.1.orig.tar.gz`
  sha256 `f76dab05c377fde2342506ec61158ea016269b45ad4d218bfeadb1a55dfc8f90`（39350B，
  顶层目录 `libkylin-ai-system-private-1.2.0.1`，strip_root=True）
- 备选端点: gitee `https://gitee.com/openkylin/libkylin-ai-system-private`
  tag `debian/1.2.0.1-1`（repository/archive 端点需 curl UA，1.2.0.0 教训）；
  本版起主端点用 Debian（公网 HTTPS 无 UA 过滤，设备实测 200/Content-Length 39350），
  source() 已去掉 curl UA 头
- Debian 元数据: `libkylin-ai-system-private_1.2.0.1-1.dsc`（本机 Scout 证据留存）
- license: GPL-3.0-or-later（LICENSE 为 GPLv3；Debian d/copyright 即
  GPL-3.0-or-later，1.2.0.0 配方 license 字段漏写 or-later，本版已纠正，
  manifest.yaml 同步）

## 1.2.0.0 → 1.2.0.1 上游增量（全量 diff 实测，本机证据目录
## runs-v2/kylin-ai-document-qa-service-1.2.0.0/evidence/libkylin-ai-system-private-1.2.0.1/）
仅 3 个 CMakeLists 变化，其余全部逐字节一致（头文件 ×10、gdbus XML ×10、
grpc proto ×9、2 个 Functions/Generate.cmake、.clang-format、LICENSE）：
1. `cmake_minimum_required(VERSION 3.12)` → `3.14`（顶层 / ai-engine / ai-proto ×3）
   —— 设备 CI cmake 4.1.2 满足，无需任何配方侧处理
2. `install(TARGETS ... EXPORT ...)` 去掉 INTERFACE 库无效的
   ARCHIVE/LIBRARY/RUNTIME DESTINATION 子句（ai-engine、ai-proto）——
   INTERFACE 库无产物，对 conan 安装布局零影响
3. `write_basic_package_version_file(... COMPATIBILITY SameMajorVersion)` 加
   `ARCH_INDEPENDENT` —— 版本文件与架构解耦，对 header-library 正确且无害

## 补丁（3 个，0001 重锚行号 + 0002/0003 原样平移，与 knowledge/drafts/DRAFT-8959 同模式）
- 0001 ai-proto install 绝对路径越权 → `${CMAKE_INSTALL_PREFIX}`：
  改动内容与 1.2.0.0 补丁一致（目标行 `install(DIRECTORY protocols/usr/
  DESTINATION /usr)` 未变，仅位置从 43 行移到 41 行）；**@@ 头已按 1.2.0.1
  实际行号重锚（-40,4 → -38,4）**。CI round-1 实测：设备无 patch(1)/curl，
  Conan 2 patch_ng 按 hunk 头行号精确匹配、不做 GNU patch 式偏移搜索，
  沿用 1.2.0.0 行号的补丁直接 ConanException（经验仓过案
  build-system/libjpeg9-9f-conan2-hunk-exact-line-match.md：GNU patch
  --dry-run/git apply 通过不构成 Conan 可应用的反证）；重锚后按该条目
  自包含探针逐 hunk 验证（@@ 起点行内容与目标文件逐字节一致）
- 0002/0003 gdbus/grpc 宏硬编码路径变量化：目标文件两版逐字节一致、
  行号未变，原样复用（探针 @1/@14/@26、@14/@57 全过）
- 硬编码路径模式参考: knowledge/drafts/DRAFT-8959（kylin-ai 系列共享宏模板，
  OHOS 下必须变量化）

## 源码消费与 test_package
- recipe 结构与 1.2.0.0 完全一致（header-library、package_id clear、
  components KylinAiEngine/KylinAiProto + aiproto resdirs=share/kylin-ai）；
  source() 换 Debian URL 后无需 UA 头
- test_package 沿用 1.2.0.0 全套（glib/2.88.0.1 依赖 + KYLAI_GDBUS_CODEGEN /
  KYLAI_GDBUS_PROTOCOL_DIR / KYLAI_PROTO_CMAKE_DIR 注入 + gio/glib 绝对路径
  链接 + HMDFS 跨 app 读校验探针）；新增 2 个 1.2.0.1 增量断言：
  包内 share/KylinAiProto/cmake/ 下 KylinAiProtoFunctions.cmake（消费者
  include 的宏目录真实落包）与 KylinAiProtoConfigVersion.cmake（ARCH_INDEPENDENT
  版本文件生成安装）存在；assertion_count 8→10
- gdbus-codegen 实证: glib/2.88.0.1 包内 bin/gdbus-codegen 存在
  （.conan2/p/glib*/p/bin/，1.2.0.0 CI 已消费同一注入模式）

## 上游测试门禁
- NO_UPSTREAM_TESTS：tarball 无 test*/tests/ 目录，`grep -rnE
  "add_test|enable_testing|include\(CTest\)"` 全树 0 命中，debian/control 无
  测试入口；discovery 检查与证据路径已写入 test_package/MANIFEST.yml 头注
- 消费者冒烟 2 入口照旧（test_ai_engine 编译链接 + test_proto_gen 宏生成
  链路真实执行）承担全部验证

## 其他
- 蓝本 manifest 记 gdbus XML ×11 为笔误，实际两版均 10 个（清单 diff 一致），
  本版 manifest 按 ×10 记录；1.2.0.0 条目作历史记录保留不改
- 无第三方依赖（debian/control Build-Depends 仅 cmake）、无编译产物 →
  预计 CI 不超时，无需 build_timeouts 加行
