# chayang 0.1.0 适配笔记

## 编译环境
- 构建系统: meson (C11)，设备原生 build=host
- 编译日期: 2026-10-16
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，取自 profile 的
  `tools.build:compiler_executables`）
- Conan: 2.29.1；profile `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / Release）
- 状态: built（本地 conan-verify + CI 同构门禁通过，尚未平台 upload）

## 上游信息
- 上游: https://git.sr.ht/~emersion/chayang，tag `v0.1.0`
  （`af4cbddfdf6508393fc73f85a3805a49bdf99cba`，deref `fc98f97db88c890fb4589f3d2a090f3b0ce81f62`）
- tarball: `https://git.sr.ht/~emersion/chayang/archive/v0.1.0.tar.gz`
- sha256: `61aa0e2955e8b5cf321ef14a5fd72f0e953da51a390d456e929b74fc5efcb74a`（10508 bytes，本机实测）
- 许可证: MIT；形态: 单文件 C11 的 wlroots 客户端（`zwlr-layer-shell` +
  `wp_viewporter` + `wp_single_pixel_buffer_manager_v1` 全屏调光）
- 包类型: `application`（桌面 CLI 工具）

## 编译步骤（已固化为 conanfile.py）

```bash
conan create archives/c/chayang/0.1.0 \
  -pr:h=<root>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<root>/ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方内部顺序：
1. `source()`：下载 chayang v0.1.0 + wayland 1.24.0 源码（后者仅用于编译静态 scanner）
2. `generate()`：MesonToolchain（`default_library=static`，R26）；写出
   `fixed_pkgconfig/{wayland-scanner.pc,wayland-protocols.pc}`，把依赖包 `.pc`
   复制改写 prefix 后置顶 `pkg_config_path`；native file 注入 `llvm-ar`/`llvm-ranlib`
3. `build()`：先编译 **静态 wayland-scanner**，再 `meson setup` / `meson compile` /
   `meson test`
4. `package()`：`meson install`，随后 **`chmod 755` + 重新签名**（见问题 1）
5. `package_info()`：`bindirs = ["bin"]`

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| wayland | 1.24.0 | `libwayland-client` + `wayland-client.h`/`wayland-cursor.h`；同时是静态 scanner 的源码版本 |
| wayland-protocols | 1.36 | `stable/viewporter`、`stable/xdg-shell`、`staging/single-pixel-buffer-v1` XML |
| libffi | 3.4.4 | `wayland-client.pc` 的 `Requires.private: libffi` 会被 `pkg-config --cflags` 解析，需实际安装 |
| meson | 1.11.0 | 构建系统（`tool_requires`；设备无系统 meson） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 安装后的 `bin/chayang` 执行报 `Operation not permitted`（rc 126/127） | 安装期 meson 就地改写 ELF（把 RUNPATH 的构建机绝对路径替换为占位符；实测 strip=False、`.symtab`/`.debug_*` 仍在、安装前后仅差 155 字节），使链接器写入的 `.codesign` **失效**（任何 ELF 改写——install 期该改写/strip/objcopy——都会）；鸿蒙内核拒绝执行没有有效 `.codesign` 的 ELF（E077）。A/B 实测：未 strip（43456B）可执行；`strip` 后（21752B）不可执行；`llvm-objcopy --remove-section .codesign` 单删该段也不可执行 | `package()` 中 `chmod 755` 后用 `binary-sign-tool sign -selfSign 1` **重新签名**（E077 四步流程 / E472 先例；仓库 1900+ 配方同款）。签名后实测 `chayang -h` 退出 0、`chayang -d <非法值>` 退出 1 |
| 2 | `dependency('wayland-scanner')` 找到的制品仓 scanner 执行报 `Operation not permitted`（rc 126） | **两个独立缺陷**：① 该二进制是 meson 安装产物，`.codesign` 已被安装期 ELF 改动作废（E077）；② 其 DT_NEEDED 内嵌构建机绝对路径 `…/.cache/conan2/p/expat*/p/lib/libexpat.so`（本机不存在）且需 `libxml2.so.16`。实测：单独重签名后即暴露真实错误 `Error loading shared library …/expat…/libexpat.so`、`libxml2.so.16`、`xmlNewValidCtxt: symbol not found` | 不修补制品仓包，改从 wayland 1.24.0 源码 `-static` 编译只依赖 libc 的 scanner，写 `wayland-scanner.pc` 交给 meson（`DRAFT-ohos-static-tool-bypass-dlopen-limit`；lavalauncher / wayland-protocols 1.47 先例） |
| 3 | `meson: inaccessible or not found` | 设备无系统 meson | `build_requirements()` 加 `tool_requires("meson/1.11.0")`（仓库 121 处先例） |
| 4 | meson 报 `Package libffi was not found` | `wayland-client.pc` 的 `Requires.private: libffi` 会被 `pkg-config --cflags` 解析；libffi 是纯传递依赖，conan 记为 "Skipped binary" 不安装其 `.pc` | `self.requires("libffi/3.4.4")` 提升为直接依赖（hyprpicker/lavalauncher 先例） |
| 5 | 依赖 `.pc` 的 prefix 不可用（wayland 为 `/`；wayland-protocols 指向构建机缓存路径） | 制品仓 `.pc` 由 meson 以 `prefix=/` 生成；wayland-protocols 1.36 未在 `package()` 内修正 | 复制依赖 `.pc` 到 `fixed_pkgconfig` 并改写 prefix/libdir/includedir，置顶 `pkg_config_path`；`wayland-protocols.pc` 由本配方整份重写（kwayland 先例） |
| 6 | 自写的 `wayland-scanner.pc` 被依赖 `.pc` 复制循环覆盖，meson 仍解析到不可执行的 scanner | 复制循环把 wayland 包的 `wayland-scanner.pc` 也拷了进来 | 复制循环跳过 `wayland-scanner.pc` / `wayland-protocols.pc` 这两个本配方自写的文件 |
| 7 | `[paths] pkg_config_path` 触发 meson 1.11 弃用告警 | meson 1.11 起 `[paths]` 弃用，`pkg_config_path` 已是 built-in option | 删掉手工 `[paths]` 注入，依赖 `MesonToolchain.pkg_config_path`（写入 `[built-in options]`） |

## 源码修改

无。上游 `meson.build` / `main.c` 未做任何修改（`conandata.yml` 的 `patches: {}` 为空）。
所有适配（静态 scanner、`.pc` prefix 修正、ELF 重签名、tool_requires）都在配方的
`generate()` / `build()` / `package()` 内完成，不触碰上游源码。

## 上游测试清点与归因（R51）

- 清点方法：读 `meson.build`（无 `test()` / `benchmark()` / `subdir('test')`）
  + 实际执行 `meson test`。
- 实测输出：`No tests defined.`（`build()` 内执行，见 conan create 日志）
- **TOTAL=0 / PASS=0 / FAIL=0 / SKIP=0 / NOT_RUN=0**。上游无测试目标，不存在被跳过或
  被"改为通过"的用例；未改断言、未删用例、未跳套件。

## 消费者测试（test_package，R34）

`test_package/src/test_chayang.sh` 对 **已安装的 `bin/chayang`** 断言（**TOTAL=9**）：

| # | 断言 | 结果 |
|---|------|------|
| 1 | `bin/chayang` 存在 | PASS |
| 2 | `bin/chayang` 有可执行位 | PASS |
| 3 | ELF 含上游串 `usage: chayang` | PASS |
| 4 | ELF 含上游串 `invalid -d value` | PASS |
| 5 | ELF 含上游串 `failed to connect to display` | PASS |
| 6 | `DT_NEEDED` 含 `libwayland-client.so.0` | PASS |
| 7 | **实际运行** `chayang -h` → 退出 0 + `usage: chayang [-d seconds]` | PASS |
| 8 | **实际运行** `chayang -d notanumber` → 退出 1 + `invalid -d value` | PASS |
| 9 | **实际运行**（unset `WAYLAND_DISPLAY`/`XDG_RUNTIME_DIR`）→ 退出 1 + `failed to connect to display` | PASS |

**TOTAL=9　PASS=9　FAIL=0　SKIP=0　NOT_RUN=0**

- 断言 7–9 是真实执行（`self.run(..., env="conanrun")` → 由 conanrun 提供
  `LD_LIBRARY_PATH` 解析 `libwayland-client.so.0`），断言被测二进制的真实输出与退出码，
  非空壳、非只看退出码。
- L1e 破坏性反向验证（移走 `bin/` 后重跑本测试）已确认测试**确实依赖被测产物**。
- 注：断言 7–9 依赖问题 1 的重签名修复；修复前这三条在本机被 EPERM 阻断（SKIP）。

## 验证结果

### conan-verify（`ohc-run.py conan-verify`，exit 0）

| 门 | 结果 |
|----|------|
| G0 预构建风险评估 | PASS |
| G1 配方完整性 | PASS |
| G2 conan create（干净构建） | PASS |
| G3 系统同名库隔离（R26） | PASS |
| G4 产物完整性 | PASS |
| L2/L4/L5 | 报告内跳过（工具侧 "无 cache 路径"，未取到 package_id）→ 由 CI 同构门禁覆盖 |

### CI 同构门禁（`ci/conan/build_and_test.sh`，exit 0）

| 门 | 结果 |
|----|------|
| G0 根目录白名单 | pass |
| KC 知识库质量 | pass |
| JC 杂项文件 | pass |
| L0 质量门禁 a–q | pass（L0i 依赖在制品仓：wayland/1.24.0、wayland-protocols/1.36、libffi/3.4.4、meson/1.11.0；L0j 首发布无冲突；L0k commands.json 有效；L0m 目录结构合规） |
| L1 测试执行验证 | pass（`upstream tests + test_package executed`） |
| L1e 破坏性反向验证（R34） | pass（`Negative test confirmed — test genuinely depends on chayang`） |
| L2 冒烟 `--version/--help` | **skip**（chayang 用 `getopt("hd:")`，不实现长选项，二者均退出 1；脚本内为非阻塞 warn） |
| L4 补丁静态安全扫描 | pass（无补丁） |
| L5 产物基线 | pass（`bin/ has content`） |
| Pass rate | 100.0% (1/1) |

## 复现命令

```bash
# conan-verify
porting run --workspace <worktree> --expect-branch feat/chayang-0.1.0 \
  --job-id <job-id> --task-id t_chayang6433 -- \
  python3 $F/scripts/ohc-run.py conan-verify chayang 0.1.0 \
    --profile <root>/ci/conan/profiles/ohos-aarch64 --project-dir <worktree>

# CI 同构门禁（JUNK_PR_DIFF 限定到本包变更文件：worktree 的 origin/main 是旧 tip，
# JC 的 incremental 模式会把大量历史改动一并扫入；等价于 CI 上以 PR diff 为准的 prdiff 模式）
porting run --workspace <worktree> --expect-branch feat/chayang-0.1.0 \
  --job-id <job-id> --task-id t_chayang6433 -- \
  env CI_PACKAGES=archives/c/chayang/0.1.0 CI_REPO_ROOT=<worktree> \
      CONAN_PROFILE=<root>/ci/conan/profiles/ohos-aarch64 \
      JUNK_PR_DIFF=<changed-files-list> \
  zsh $F/ci/conan/build_and_test.sh
```

## 证据路径（本机）

| 内容 | 路径 |
|------|------|
| conan-verify 输出 | `$HOME/.local/share/ohpc-porting/runs/chayang-verify-*/output.log`（最新一次） |
| conan create 原始日志 | `archives/c/chayang/0.1.0/reports/conan-create.log`（ignored，按需重生成） |
| conan-verify 报告 | `archives/c/chayang/0.1.0/reports/conan-verify-report.md` |
| CI 同构门禁输出 | `$HOME/.local/share/ohpc-porting/runs/chayang-ci-*/output.log`（最新一次） |
| init-build / lang-preflight | `$HOME/.local/share/ohpc-porting/runs/chayang-initbuild-*/output.log`；语言判定 detected=c / build_system=meson |

## 注意事项

- 静态 scanner 依赖 SDK 自带 `libexpat.a`
  （`/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`）；按"SDK → 依赖包内"顺序查找，
  找不到显式抛 `ConanException`，不静默降级。CI 机器缺该路径会失败。
- 静态 scanner 的 wayland 版本必须与 `requires` 的 wayland 版本一致，配方内已加显式校验。
- **`.codesign` 必须在所有 ELF 改动作业之后写入**；`package()` 里先 `meson.install()`
  （会 strip）再签名，顺序不可颠倒（E077 四步流程顺序不可变）。
- `binary-sign-tool` 缺失时配方显式报错（不静默产出不可执行的产物）。

## 发现与知识

- ✅ **命中既有条目 E077（复用，不新开草稿）**：鸿蒙只执行带有效 `.codesign` 的 ELF，
  且 `llvm-strip` / `objcopy` / `patchelf` 会使其失效。本轮的具体触发点是
  **meson 安装期就地改写 ELF（RUNPATH→占位符）使签名失效** → 应用类（`package_type=application`）
  配方必须在 `package()` 末尾重新签名，否则产物在设备上完全不可执行。
  **误导性症状**：execve 阶段报 `Operation not permitted`/`Permission denied`，
  不含 `codesign` 字样，极易误判为 dlopen/权限/HMDFS 问题（本轮先误判过，
  靠 A/B 实验——未 strip 可执行 / strip 后不可执行 / 只删 `.codesign` 段即不可执行——定位）。
  该"meson install 期 ELF 改写失效签名"的触发点在 E077 正文只隐含提到，可作为图谱补充候选。
- ✅ `pkg-config --cflags` 会解析 `Requires.private`：仅作传递依赖被 conan 记为
  "Skipped binary" 的包不会安装 `.pc`，会让 meson 的 `dependency()` 失败；解法是提升为
  直接 requires（hyprpicker/lavalauncher 既有经验命中）。
- ✅ 制品仓 `wayland` 包的 scanner 有两个独立缺陷（失效签名 + DT_NEEDED 内嵌不存在的
  构建机绝对路径且缺 `libxml2.so.16`）；只重签名仍不可用 —— 故必须从源码静态重建工具。
  （`DRAFT-ohos-static-tool-bypass-dlopen-limit` 适用范围命中；新增"该 DRAFT 的适用场景
  包含制品仓工具签名失效"这一判据，可作图谱补充候选。）
- ✅ CI L0i 的依赖提取只看 AST 常量字符串参数，`"wayland/" + CONST` 拼接会被静默漏检；
  依赖引用写字面量才能被门禁覆盖（本轮实测发现并修正）。
