# pango 1.56.4.1 编译笔记（HarmonyOS PC · xft 后端补全）

## 定位
同一上游版本 1.56.4 的适配修复。在保持 pango-1.0 / pangocairo-1.0 / pangoft2-1.0
三个原有产物不变的前提下，新增构建并暴露 Xft 后端 libpangoxft-1.0.so + pangoxft.pc，
供下游（如 sxmo-dwm）消费。

## 关键改动

1. **版本号**：1.56.4 → 1.56.4.1（同一上游 tarball，修复类按 R37 加后缀）
2. **xft 后端开启**：`tc.project_options["xft"] = "enabled"`（原来是 `"disabled"`）
3. **新增依赖**：`self.requires("libxft/2.3.8")`（xft 后端头文件与 xft.pc 来自它）
4. **暴露产物**：
   - `self.cpp_info.libs` 追加 `'pangoxft-1.0'`
   - `--alias-pc` 列表追加 `'pangoxft=pango,xft,freetype2,fontconfig'`（转发型 .pc）
5. **conandata.yml**：patches 键从 `"1.56.4"` 改为 `"1.56.4.1"`（与 `apply_conandata_patches(self)` 匹配）
6. **上游测试真实执行集成**（build() 末尾 `_run_upstream_tests()`）：
   - 编译并运行上游 tests/ 中 8 个无条件测试（无字体/X11 显示依赖）：
     test-coverage / testboundaries / testboundaries_ucd / testcolor /
     testscript / testlanguage / testmatrix / testtabs
   - 数据文件（*BreakTest.txt、boundaries.utf8）复制到运行目录
   - 运行时闭包：依赖 cpp_info libdirs（相对路径转绝对）+ LD_LIBRARY_PATH；
     libthai 词典经 LIBTHAI_DICTDIR 指向包内 share/libthai（conan 包 prefix 空
     导致内嵌 "//share/libthai" 不可达）
   - glib TAP 判定：exit 0 且无非 SKIP "not ok" 行
7. **test_package 运行时修复**（`_runtime_env()`，实验定位）：
   - 本机即 OHOS arm64（host=build 同 profile），交叉产物原生可运行，
     此前"OHOS 跳过运行"系缺库报错的错误归因
   - 根因一：libxft 预编译包自带 .codesign 签名无效 → OHOS 加载器
     对 exec 映射拒绝（dlopen → Permission denied）→ 复制依赖 so 至
     conanhome/tmp-runtimelibs 并统一剥旧签名 + selfSign 重签
   - 根因二：libXft 预编译二进制 DT_NEEDED libxml2.so.16，但 0 个 xml
     符号引用（构建污染）且 conan 图无 libxml2 → patchelf 剥离该 NEEDED
   - 运行时闭包 = 重签库目录 + conanrunenv LD_LIBRARY_PATH + LIBTHAI_DICTDIR

## 补丁保留
0001-include-fcfreetype.patch 原样保留——xft 打开后 FcFreeTypeQueryAll 的调用路径仍走。

## 验证清单
- `conan create` 退出码 0（W3 内嵌强制重建，2026-10-18 04:08，reports/conan-create.log
  归档自 .ci_logs/conan_build_pango_1.56.4.1.log 最终轮）
- 上游测试 8/8 PASS（TAP 合计 29 ok / 0 not ok，逐项 3+1+6+3+1+2+10+3，
  证据在 conan-create.log「上游测试 …: PASS」行；testboundaries_ucd 的
  /text/break/line 为条件性 SKIP——上游在启用 libthai 时跳过该数据集，属预期）
- test_package 探针 2/2 真实运行 exit=0（test.c 泰文断言全过 + test_xft.c
  头可达/符号注册/版本一致）
- `libpangoxft-1.0.so` 存在于 package_folder/lib
- `pangoxft.pc` 由 alias-pc 机制生成
- 老三个 .so 仍在
- NEEDED 含 libXft / libfontconfig / libfreetype / libpango-1.0
- pkg-config --libs pangoxft 返回 -lpangoxft-1.0
- 下游 C 文件编译链接通过
- 未执行的上游用例：依赖 fontmap 渲染/字体的 15 个 testsuite 测试
  （test-itemize/test-shape/test-layout/test-font* 等，build-testsuite 选项
  门控且需字体环境），无字体依赖的 8 个无条件测试已全部真实执行

## 状态
built（真机 conan create + 上游测试 8/8 + test_package 运行 2/2 通过）
---

**编译结束**: 2026-10-18 04:05
**最终状态**: published
