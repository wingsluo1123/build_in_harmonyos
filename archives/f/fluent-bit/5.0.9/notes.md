# fluent-bit 5.0.9 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-07-29}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

### 编译经验记录（manifest knowledge_gained 段，2026-07-30）

1. 鸿蒙 musl 缺 `<fts.h>`（BSD 文件树遍历库），chunkio 用 `fts_open`/`fts_read`/`fts_close`，需提供空 stub。
2. 鸿蒙 musl 缺 openssl/sqlite3 头文件，但 fluent-bit 核心源（`flb_hmac`/`flb_crypto`/`flb_sqldb.h`）无条件编译，需提供空声明 stub。
3. 鸿蒙 musl 缺 `pthread_cancel`，需链接期空 stub。
4. monkey 子项目生成头文件 `mk_core_info.h`/`mk_info.h`/`mk_env.h` 用 `${PROJECT_BINARY_DIR}/include/monkey/` 路径，但 `mk_getopt.h`/`mk_scheduler.h` 用 `<mk_core/...>` 和 `<monkey/...>` 尖括号包含，需在顶层 CMakeLists.txt 加 `include_directories(BEFORE ${CMAKE_BINARY_DIR}/include/{,monkey/})`。
5. `flb_blob_db.c` 的 `#else` 分支（`FLB_SQLDB=Off`）缺 `stdint`/`cfl_sds`/`flb_config` include，且 `flb_blob_db_file_part_get_next` 签名与 `.h` 声明冲突（缺 `int *part_count` 参数）。
6. `flb_http_client.c` 缺 `#include <flb_upstream_node.h>`，导致 `flb_upstream_node` 类型不完整。
7. OHOS 零依赖策略：关闭所有需外部库的可选子系统（TLS/HTTP/AWS/SQLDB/Kafka/Lua/WASM 等）+ 关闭所有需外部依赖的 input/output/filter 插件，绕过 R36 雍塞。
8. GitHub 源 tarball 下载不稳定（反复超时/损坏），`codeload.github.com` 直连可用但需后台 `nohup` + 轮询避免 bash 超时。
9. conan 2.x `apply_conandata_patches` 只扫 `patches:` 段，但会把 `.tar.gz` 也当 patch 解析；stub bundle 应放自定义 `stubs:` 段，由 `build()` 手动解包。
10. conan 2.x `export_conandata_patches` 需 `patch_file` 字段值含路径前缀（如 `patches/xxx.patch`），非纯文件名。
11. ohc-run.py E017 预防逻辑会临时把 GitHub URL 注入 `ghfast.top` 镜像，跑完恢复；配方 `conandata.yml` 应写原始 GitHub URL。
12. `refresh-patch --auto` 会按源文件拆分单文件 patch 成多个小 patch 并删原文件；放 `{work_dir}/.edit-tracker.json`（`edited`/`added` 空列表）可让 `has_tracker=True`，`get_tracked_files=[]`，跳过拆分保留现有补丁。
13. conan 2.x `self.run(env=...)` 的 `env` 参数是 conan 环境文件名（如 `"conanbuild"`），非 `KEY=VALUE` list；注入环境变量应用 `os.environ["KEY"] = "VALUE"` 让子进程继承。
14. test_package 对 APPLICATION recipe 需 `self.cpp_info.bindirs = ["bin"]` 在 `package_info()` 建广播，否则 test_package 查不到安装的二进制。
15. `/dev/fd/` 在本沙箱环境权限拒，bash 进程替换 `< <(cmd)` 必失败，需改临时文件管道。
16. `/usr/local/bin/zsh` 实为 bash 仿链接，build_and_test.sh 的 zsh 特有语法（`${=VAR}`、`*.so*(N)` glob qualifier）必失败，需改 bash/zsh 通用的写法。


{需要特别注意的点；无则删除此节}
## 对话记录

### 对话 #1 — fluent-bit 5.0.9 编译 (2026-07-30)

**用户**: 编译 fluent-bit 5.0.9 (C++) 为 OpenHarmony 平台配方，发布到 ohpcd 制品仓。

**AI**: 遵循 SKILL.md openharmony-compile-agent v11.4 流程：
1. W0 依赖检查 — 所有可选依赖在 ohpcd 未发布，但 fluent-bit 所有依赖可选，可用 CMake 零外部依赖编译绕过 R36
2. W1 同步 main — 创建 `feat/fluent-bit-5.0.9` 分支
3. W2 init-build — `--no-download` 模式生成构建上下文
4. Step2 AI 编译 — 关闭所有可选子系统 + 提供 openssl/sqlite3/fts stub + 修 monkey include 路径 + flb_blob_db/flb_http_client 源码补丁
5. conan-verify — G1/G0/G2/G3/G4 + L2/L4/L5 全 PASS
6. finish — refresh-patch（用 .edit-tracker.json 跳过拆分）+ W3 本地 CI 模拟通过 + 知识整理

**结果**: fluent-bit 5.0.9 二进制（19MB，arm64 musl）成功编译，conan-verify 全通过，status=published。

### 对话 #2 — refresh-patch 拆分问题 (2026-07-30)

**问题**: finish 的 Step 1 refresh-patch 把单文件 patch 拆成 31 个小 patch 并删原文件，导致 conan-verify 找不到 patch。

**解决**: 在 work_dir 放 `.edit-tracker.json`（`edited`/`added` 空列表），让 `has_tracker=True`，`get_tracked_files=[]`，refresh-patch 走"无变更保留现有补丁"路径跳过拆分。

### 对话 #3 — build_and_test.sh zsh 语法 bug (2026-07-30)

**问题**: `/usr/local/bin/zsh` 实为 bash 仿链接，build_and_test.sh 的 zsh 特有语法（`${=VAR}`、`*.so*(N)` glob qualifier、`< <(cmd)` 进程替换）必失败。

**解决**: 改成 bash/zsh 通用的写法（`${VAR}`、`*.so*` + `[ -f ] || continue`、临时文件管道）。
---

**编译结束**: 2026-07-30 22:58
**最终状态**: published
