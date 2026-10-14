# gocr

GOCR/JOCR — OCR（光学字符识别）引擎。本仓适配的是 **OSRA 项目发布的上游 patched 快照**
（`gocr-0.50pre-patched-2`），其中 `src/gocr.c`/`src/gocr.h` 增加了 OSRA 需要的
`__thread job_t *OCR_JOB, *JOB` 线程局部钩子。

## 组件

- **gocr**：命令行 OCR 工具（读 PNM/PCX 图像，输出文本）
- **libPgm2asc**（`libPgm2asc.a`）：OCR 库，供调用方喂入内存位图并取回识别结果。
  这是 OSRA 2.2.4 的硬依赖（`configure.ac` 中以 `-lPgm2asc` 探测 `job_init`/
  `job_init_image`/`pgm2asc`/`job_free_image`/`decode` 等符号）。

## 上游

- 源码分发（本仓采用）：<https://sourceforge.net/projects/osra/files/gocr-patched/>
- 原始项目：<http://jocr.sourceforge.net>

## 适配要点（OHOS / aarch64）

- `make` 只编 CLI；库需 `make libs`。
- 上游手写 `Makefile.in` 无 VPATH 支持 → conan 侧 in-source 构建。
- `configure` 的 `umask 077` 临时目录在 HMDFS 上不可写（E011）→ 打补丁改 `umask 022`。
- `--without-netpbm`：PNG/JPEG 输入依赖外部转换器，OSRA 走库 API 不需要。
- 头文件平铺安装（OSRA 以 `<pgm2asc.h>`/`<gocr.h>` 包含且自行 `extern "C"` 包裹）。

详细编译步骤、上游测试实跑（4/6 全等，字符准确率 95.38%）与踩坑见
[`0.50pre-patched-2/notes.md`](0.50pre-patched-2/notes.md)。

## License

GPL-2.0-or-later（见源码包 `COPYING`）。
