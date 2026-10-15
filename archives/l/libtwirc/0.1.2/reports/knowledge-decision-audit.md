# 知识判定审计 — libtwirc 0.1.2（task_id: libtwirc-0.1.2-r01-bootstrap-and-adapt-pc3-32-20260927T094559Z）

## 快照信息
- 快照绝对路径: /storage/Users/currentUser/tianyi/build_in_harmonyos/.knowledge-snapshots/libtwirc-0.1.2-r01-bootstrap-and-adapt-pc3-32-20260927T094559Z
- repository: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git
- ref: main, HEAD: c611f7d61b422eda200fc49481cf0d404e63f10c
- 稀疏目录: knowledge（graph 545 条目, doc 541 条目, drafts 若干）
- 只读: procedural_only_fs_ignores_chmod（本机 FUSE 类挂载忽略权限位，只读由流程保证）

## 扫描范围
- 正式 `knowledge/graph/E*.kv`（545）与 `knowledge/doc/E*.md`（541）
- `knowledge/drafts/*.{md,kv}` 与根目录 `DRAFT-*` 配对（libharu/libfreenect 等）
- 索引 `knowledge/graph/index.tsv`
- 关键词: soname, DT_SONAME, Wl,-soname, SOVERSION, build-shared/static, hand-written, raw makefile, no configure, autotools 模板, manual compile, no-build-family, 单翻译单元

## 候选 1：上游无 configure/Makefile/CMakeLists（仅有手写 build-shared/build-static 脚本），conan-init 生成 autotools 模板不可用
- error_signature（本轮实测）: conan-init 输出“conanfile.py 模板不可用（autotools），跳过” → G1 首查缺 export_sources；探索编译需直接 clang 调用
- 命中条目: `knowledge/drafts/DRAFT-arduinospritzcipher-1.2.0-no-build-family-manual-compile.{kv,md}`（无构建族 → conan-init 误判 autotools → 配方内手动 cc -c + ar/llvm-ar 编译）
- 逐字段适用性验证：
  | 字段 | DRAFT-arduinospritzcipher | libtwirc 0.1.2 | 适用 |
  |---|---|---|---|
  | trigger_tool | conan-init\|conan-verify\|ohc-run.py | conan-init 误判 autotools；conan-verify G1 | ✅ |
  | error_signature | configure.*no such file\|No configure script\|autotools 模板 | autotools 模板跳过 + 手写脚本无 configure | ✅ |
  | root_cause | 无构建族被猜成 autotools | 同族：仅手写 shell 脚本无标准构建系统 | ✅ |
  | rec_approach | no-build-family-manual-compile-recipe（conf 取编译器 + 直接编译 + ar + 装头文件） | conanfile.py 手写 custom：conf 取 clang + 单 TU 编译 + ar/shared + 装头文件 | ✅ |
  | affected_scope | 所有无构建系统但需编译的源文件库 | libtwirc 属此类 | ✅ |
- 结论: **等价命中 → reuse_existing（路径 A）**；本轮适用性验证逐字段通过（上表），不创建草稿

## 候选 2：共享库缺 DT_SONAME → W3 L5a `soname_gate_failed`
- error_signature（本轮实测）: `[fail] L5a: libtwirc.so 缺少 DT_SONAME` / `L5_RESULT=fail: soname_gate_failed`
- 命中条目: `knowledge/graph/E383.kv|doc/E383.md`（OHOS 共享库缺 SONAME → soname_gate_failed）+ 根目录 `knowledge/DRAFT-libharu-2.3.0-missing-dt-soname.{kv,md}`（同一 error_signature 族）与 `knowledge/DRAFT-libfreenect-...-versioned-symlink`（HMDFS 无软链）
- 逐字段适用性验证：
  | 字段 | E383 / DRAFT-libharu | libtwirc 0.1.2 | 适用 |
  |---|---|---|---|
  | error_signature | soname_gate_failed\|no SONAME\|L5_RESULT=fail: soname_gate_failed | 完全一致 | ✅ |
  | root_cause | OHOS 缺 CMake 平台模块致 SONAME_FLAG 空 / 构建未传 -Wl,-soname | 手写脚本直接 clang -shared 未传 -Wl,-soname | ✅（同族：链接时未注入 SONAME） |
  | rec_approach | 注入 -Wl,-soname（CMake 变量或直接 target link option） | conanfile.py 链接命令行 `-Wl,-soname,libtwirc.so` | ✅（同族修复，机制略异不构成新知识） |
  | verification_cmd | readelf -d <lib>.so \| grep SONAME | llvm-readelf -d lib/libtwirc.so 复验 | ✅ |
- 结论: **等价命中 → reuse_existing（路径 A）**；机制差异（手写脚本 vs CMake）不新增跨库知识，不创建草稿

## knowledge_decision（最终）
- `knowledge_decision: reuse_existing`（路径 A）——两个候选均等价命中现有知识（DRAFT-arduinospritzcipher 无构建族手动编译；E383/DRAFT-libharu 共享库 SONAME 族）
- 未命中基线噪声/共享框架/控制器/知识图谱完整性/网络设施等禁止走路径 B 的类别
- 无 new_draft；不在当前库 worktree 创建草稿；不写正式 E###/索引/其他库目录

## 依赖项说明
- libtwirc 无第三方编译依赖（仅系统 libc），无依赖项分类；`issue_action: none` 保持