# Wt 4.14.0 — 适配笔记

## 任务
- 任务卡 #12000（j669539），taskBranch=feat/wt-4.14.0
- Emweb C++ Web Toolkit 4.14.0 → OpenHarmony PC aarch64

## 依赖面（W0 核验通过，三件全发布）
- boost/1.91.0.1.1（program_options/thread 组件 + headers + asio 头）
- zlib/1.3.1.1（wthttp HTTP deflate）
- openssl/3.5.7（ENABLE_SSL）

## 关键适配决策
1. **WtFindBoost 非标准查找**：Wt 自带 cmake/WtFindBoost.txt 包装
   find_package(Boost 1.66 COMPONENTS program_options thread)，命中
   IMPORTED 目标后转 Boost::<comp>——conan CMakeDeps 原生兼容。
   Boost>=1.69 不加 system 组件；WT_CPP17_FILESYSTEM_IMPLEMENTATION=std
   绕开 filesystem 组件。
2. **CMake>=4 worker 坑**（libsoundio 48c47b83 先例）：OHOS 时
   CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64。
3. **最小依赖面**：HARU/PANGO/SQLITE/POSTGRES/FIREBIRD/MYSQL/OPENGL/
   UNWIND/SAML/LIBWTTEST/LIBWTDBO 全 OFF + CMAKE_DISABLE_FIND_PACKAGE_*
   五连（PNG/GLEW/OpenGL/HPDF/Asciidoctor），阻断可选查找。
4. **测试策略**：上游 testsuite 需 Wt::Test harness（已随 LIBWTTEST 关闭）
   与网络服务场景，CI 沙箱不可行；test_package 端到端替代——真实
   WServer + wthttp 连接器在 127.0.0.1 服务页面，socket 级取页断言
   HTTP 状态行 + 应用标记（HELLO_WT_OK）。
5. **OHOS 签名**：libwt/libwthttp 打包后 binary-sign-tool 重签
   （libsoundio/ki18n 先例机制）；test 可执行文件同款处理。

## 交付链
conan create RC=0 → 双签 commit → push fork feat/wt-4.14.0 →
跨仓 PR（head=j669539:feat/wt-4.14.0）→ /rebuild + /ai review →
bind-pr #12000。
