# minidraw ee0989e954 适配笔记

## 编译环境
- 构建系统: header-only（single-file 库，无 build 系统，MINIDRAW_IMPLEMENTATION）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built

## 编译步骤

minidraw 是单头文件路径式 2D 图形库（David Reid）。核心文本 API（UTF-8/UTF-16/UTF-32
转换、BOM、端序交换）与后端无关，可在 OHOS PC 上用 clang 独立编译：

1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing`
   — 配方为 header-only（变体 A），仅打包 `minidraw.h` 到 include/，无编译产物。
2. test_package/test.c 以消费者视角 `#define MINIDRAW_IMPLEMENTATION` 调用
   `md_utf8_to_utf16le`/`md_utf16le_to_utf8`/`md_utf8_to_utf32le`/端序交换/BOM 检测。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 conan create 失败：test.c:9 `minidraw.h` not found | 生成的 test_package/conanfile.py 用 `self.source_folder` 拼 include 路径，指向源码目录而非已安装包 include | 改用 `self.dependencies["minidraw"].cpp_info.includedirs` 从安装包 include 取路径 |
| 2 | package() 后包内无文件（"No files in this package!"） | header-only 模板 copy() 的 `dst="include"` 相对路径落到配方目录 | 显式 `dst=os.path.join(self.package_folder,"include")` |
| 3 | test.c 引用 `MD_VERSION` 未定义 | 上游头未提供该宏 | 修正测试输出为固定版本字符串 |
| 4 | upstream tests 依赖 GTK/Cairo/Pango | minidraw_testcommon.c 经 minidraw_app.h 引入 GTK; OHOS 无 GTK/pango/cairo | 按 R51 申报不可运行，由 test_package 消费者测试覆盖核心文本 API。详见 MANIFEST.yml |

## 源码修改

无补丁（patches/ 为空，header-only 库无需适配改动；核心文本 API 在 OHOS 原样可用）。

## 验证结果

- conan-verify: G0-G4 全 PASS（G1 配方完整性 / G2 conan create / G3 系统同名隔离 / G4 产物完整性）
- HarmonyOS 专项测试：两次独立运行均 exit 0，输出 `OK: all minidraw consumer checks passed`
- W3 本地 CI：JC_RESULT=pass、L0=pass、Pass rate 100% (1/1)

## 交付物

header-only 库，无 bin/lib 产物。交付 `archives/m/minidraw/ee0989e954/`（conanfile.py + conandata.yml + test_package/ + manifest/notes）。

## 注意事项

- 上游 Cairo/Pango 图形后端在 OHOS 不可用，本次只验证无后端文本 API 子集；图形渲染后端留待生态就绪后适配。
- 集成测试需 /data/service/hnp/bin/clang（OHOS 工具链），网络下载需 NO_PROXY 或镜像。

---

**编译结束**: 2026-09-28 23:29
**最终状态**: built
---

**编译结束**: 2026-10-15 20:16
**最终状态**: published

## r02 补充（rule12 E2E）

分析端 rule12 审查：r01 鸿蒙特有测试仅有纯断言类，缺真实端到端消费者用例。
r02 在同一 worktree 与既有 PR #13612 内补齐：

- 新增 `test_package/test_e2e.c`：自实现 `md_backend_custom` 软件光栅化后端，
  真实走通 `md_init → md_gc_init → md_gc_clear → md_gc_rectangle/md_gc_fill
  → md_gc_move_to/md_gc_line_to/md_gc_stroke → md_gc_get_image_data → 逐像素
  内容校验（背景白、矩形红、线段蓝覆盖 ≥20px）→ md_gc_uninit/md_uninit`。
- 首跑失败（missing procs.uninit → SIGSEGV exit 139）：补齐 `sw_api_uninit`
  回调后同一 task_id 内修复重跑，exit 0，全部断言通过。
- 两次独立运行日志与 SHA-256 已留档（e2e-run1.log / e2e-run2.log）。
