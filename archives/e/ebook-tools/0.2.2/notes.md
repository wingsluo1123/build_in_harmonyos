# ebook-tools 0.2.2 — 适配笔记

## 平台
- 目标: OpenHarmony PC (aarch64)
- 构建系统: CMake（上游 `cmake_minimum_required(VERSION 2.4.0)`）

## 源码（R39 官方直链，本机实测）
- URL: `https://downloads.sourceforge.net/project/ebook-tools/ebook-tools/0.2.2/ebook-tools-0.2.2.tar.gz`
- 实测: HTTP 200 / 46889 字节 / sha256 `cbc35996e911144fa62925366ad6a6212d6af2588f1e39075954973bbee627ae`
- ⚠ 主域 `sourceforge.net` 本机 DNS 解析失败（`Could not resolve host`），但
  `downloads.sourceforge.net`（官方下载端点，属 sourceforge 官方）解析正常，
  直链实测 200；未使用任何镜像前缀、未使用 Debian 池货源。
- 产物形态: `libepub.so`（4 个 .c 编译）+ `bin/einfo`（CLI）+ `bin/lit2epub`（sh 脚本）
  + 头文件 `epub.h / epub_shared.h / epub_version.h`；共 11 个 c/h 文件。

## 依赖（W0 已核 ohpcd 已发布）
- `libxml2/2.15.3.1`（OPF/OCF 的 XML 解析）—— `conan download --only-recipe` 实测命中
- `libzip/1.11.4`（EPUB 容器就是 zip）—— 同上
- preflight 在 conanfile 生成前报「未找到依赖声明」属预期，配方落地后复跑。

## 关键适配点（不改源码、零补丁）
1. **CMake 4 兼容**：上游 min 2.4.0 在 CMake 4.x 直接 fatal ⇒ `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
   （与 `archives/l/libzip/1.11.4` 同法，实证可用）。
2. **依赖接线**：上游 `find_package(LibXml2 REQUIRED)` / `find_package(LibZip REQUIRED)`；
   `cmake/FindLibZip.cmake` 是「LIBZIP_LIBRARY/LIBZIP_INCLUDE_DIR 缓存即 FOUND」的老写法，
   CMake 内置 `FindLibXml2` 走 find_path/find_library ⇒ 配方直接把两组缓存变量预置成
   conan 依赖的真实路径（libxml2 的 `include/libxml/parser.h`、`lib/libxml2.so`；libzip 的
   `include/zip.h`、`lib/libzip.so`），同时经 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 把依赖目录
   注入 `CMAKE_PREFIX_PATH`/`CMAKE_FIND_ROOT_PATH`（MODE 置 BOTH）。
   两条都为绕开 ohos.toolchain 把 FIND_ROOT_PATH_MODE 设成 ONLY 的问题（命令行 cache 盖不住普通 set）。
3. **交叉编译**：自发现 `ohos.toolchain.cmake` + 裸 `cmake -B/-S`，绕开 conan_toolchain 在
   `os=OHOS` 下的 `CMAKE_SYSTEM_NAME` 映射问题（ML-0035）。同 libzip 配方。
4. **签名**：`package()` 内对 `lib/*.so*` 与 `bin/` 下 ELF（einfo）做 XPM 自签
   （`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`）。
5. **上游零测试**：无 `tests/`、无 `enable_testing/add_test/ctest`、`debian/rules` 无测试段、
   README 无测试说明 ⇒ 上游无可执行测试（R51 清点证据见 PR 正文）。
   功能验证改为 test_package 现场往返：libzip 构造最小 EPUB → `epub_open` 解析 →
   `epub_get_metadata(EPUB_TITLE)` 读回比对 → `epub_get_ocf_file("mimetype")` 读回比对 →
   错误路径（不存在文件返回 NULL），另执行打包的 `einfo -h`（验签名与运行时链接）。

## 状态
- conan-verify：G0-G4 + L2/L4/L5 全部通过（配方干净构建自包含）
- finish 本地 CI 模拟（W3）：通过，`.ci-result.json` exit_code=0
- 上游测试：N_static=0（无 tests/、无 ctest/enable_testing/add_test、debian/ 无测试段）
- 消费者测试：test_package 1 个程序 / 8 项断言全过，另执行打包的 einfo -h
- W4 独立审计：verdict=pass（P0/P1=0，P2/P3 均为建议项）
---

**编译结束**: 2026-10-08 18:29
**最终状态**: built
