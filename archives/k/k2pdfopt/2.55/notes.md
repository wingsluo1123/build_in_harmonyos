# k2pdfopt 2.55 适配笔记

## 编译环境
- 构建系统: makefile（配方内置自写 Makefile 驱动）
- 编译日期: 2026-10-13
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS API 20)
- 状态: built（本地 conan create + test_package 全链路通过）

## 上游情况
- 官方源码: https://www.willus.com/k2pdfopt/src/k2pdfopt_v2.55_src.zip（GPL-3.0）
- 上游无可用构建系统：CMakeLists.txt 主体被注释，依赖系统 pkg-config mupdf；
  按 readme_k2src.txt 的编译模型（willuslib -> k2pdfoptlib -> k2pdfopt.c）自写构建。
- 上游钉死 MuPDF 1.23.7；本适配使用制品仓已有的 mupdf/1.25.1。
- 上游无自动化测试套件（无 make check/ctest）。

## 编译步骤
1. conan download 拉取 mupdf/1.25.1、libpng/1.6.58、zlib/1.3.1.1（R36 依赖预检）
2. conandata.yml 双源：k2pdfopt 官方 zip（strip_root）+ mupdf 1.25.1 GitHub tarball
3. 打补丁（见下）后自写 Makefile 编译全部源文件，链接静态归档：
   `libmupdf.a libmupdf-third.a libmupdf-threads.a libpng16.a libz.a -lm`
   （JPEG 符号由 libmupdf-third.a 内置，无需单独 libjpeg）
4. conan create + test_package：运行 k2pdfopt 将内嵌单页 PDF 转换为 k2out.pdf
   并断言 %PDF- 头 —— 本地真机（aarch64 OHOS）实测转换成功（8 words）

## 关键补丁
- 0001 willuslib/willus.h：禁用 DjVu/GOCR/Leptonica/Tesseract（制品仓无对应包；
  k2pdfopt 的 PDF/文本核心功能不受影响）
- 0002 k2pdfoptlib/k2ocr.c：
  - `k2ocr_tess_status` 移出 `HAVE_TESSERACT_LIB` 条件块（k2ocr_show_envvar 无 Tesseract 时仍引用）
  - `k2ocr_multithreaded_ocr` 内 `ocrwords_multithreaded_ocr` 调用以 `#ifdef HAVE_TESSERACT_LIB` 包裹
  - OCRTESSINITINFO typedef 相应移出条件块
- 0003 mupdf-1.25.1/source/fitz/stext-device.c：重打上游 willus mod
  （结构收集分支后补 `else dev->flags = 0;`）——k2pdfopt mupdf_mod 对 1.23.7 的
  唯一实质逻辑修改；1.25.1 中该处代码位置不变，diff 极小
- mupdf_mod/font-win32.c：1.23.7 文件未修改，直接对 1.25.1 头文件编译，
  提供非 Windows 平台 `pdf_install_load_system_font_funcs` 空实现
  （1.25.1 已删除该符号，willuslib 仍引用）

## 排错记录
- 源码为 CRLF 行尾：python 按 bytes 替换补丁点，diff 补丁保留 \r
- 链接期 undefined `pdf_install_load_system_font_funcs`：用 k2 自带
  mupdf_mod/font-win32.c（1.23.7 实现）补上
- libpng/zlib 需静态链接（shared=False），避免与系统库同名动态冲突（R26）
- CI L0c 门禁：test_package/ 需有测试源文件 —— 新增 run_test.sh
  （转换 test.pdf 并断言 %PDF- 头），conanfile.py test() 改为调用该脚本

**编译结束**: 2026-10-13 17:12
**最终状态**: built

## CI 修复记录（2026-10-13 第二轮）

- PR #15597 首轮 CI 失败：L0c no_test_sources（test_package 无 .sh/.py/.c 测试源文件）
- 修复：新增 test_package/run_test.sh；本地完整 CI（setup.sh + build_and_test.sh 定向 k2pdfopt/2.55）全绿：
  L0 pass / L1 pass（含 L1e 破坏性反向验证）/ L4 pass / L5 pass / L2 skip（CLI 无 --version，非阻塞）
- test_package 实测：单页 PDF 转换成功（1 pages, 8 words → k2out.pdf，%PDF- 头校验通过）
---

**编译结束**: 2026-10-14 07:35
**最终状态**: built

## CI 修复记录（2026-10-14 第三轮，CI #90582）

- PR #15597 第二轮 CI 失败（类别未知）：conan-build-test 14400s 无输出超时。
- 根因：k2pdfopt 转换完成后打印 "Press <ENTER> to exit." 并阻塞读 stdin；
  CI stdin 为常开管道，永远等不到 EOF → 测试实际已成功（k2out.pdf 已生成）但进程挂死。
- 修复：run_test.sh 对 k2pdfopt 调用加 `< /dev/null`（stdin 重定向）+ `timeout 300` 兜底。
- 本地完整 CI 复验全绿：conan create + test() 正常退出，L0/L1(含L1e)/L4/L5 pass，L2 skip（CLI 无 --version，非阻塞）。
