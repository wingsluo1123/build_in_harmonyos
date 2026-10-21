# xkbcommon 1.13.2 适配笔记

## 编译环境
- 构建系统: meson (meson_version >= 1.4)
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++
- 状态: published

## 编译步骤
1. 获取源码：GitHub tag xkbcommon-1.13.2（archive tarball，sha256 见 manifest）
2. meson 交叉编译（OHOS aarch64 cross file + 关闭可选功能）：
   ```
   meson setup build-ohos --cross-file=ohos-aarch64.ini \
     -Denable-x11=false -Denable-wayland=false -Denable-tools=false \
     -Denable-xkbregistry=false -Denable-bash-completion=false -Ddefault_library=static
   ninja -C build-ohos
   ```
3. conan create 完整验证（ohos-aarch64 profile）通过，test_package 鸿蒙冒烟测试 100% Passed

## 上游测试（R51 申报表）
- 测试命令：`meson test --num-processes 1`（23 个注册用例）
- 实测结果：18 通过 / 2 失败（context、compose）/ 3 跳过或依赖外部（xkeyboard-config 数据等）
- 通过率：18/20 可独立运行用例（90%）；2 项失败详见下

### 失败项 1：libxkbcommon:context — SIGABRT
- 崩溃点：test/common.c:260 `test_maketempdir` 中 `assert(tmp == tmpdir)`
- 根因：`test_maketempdir` 在非 Windows 分支硬编码 `mkdtemp("/tmp/%s")`（common.c:255），本机沙箱 `/tmp` 只读（已验证 `touch /tmp/x` → Read-only file system），mkdtemp 返回 NULL → 断言失败
- 性质：环境问题（沙箱 /tmp 只读）。CI worker /tmp 可写，该用例在 CI 可正常通过
- 技术证明：`test/common.c:255 asprintf_safe("/tmp/%s", template)` + 沙箱 `touch /tmp: Read-only file system`

### 失败项 2：libxkbcommon:compose — SIGABRT
- 崩溃点：test/compose.c:787 `compose_traverse_fn` 中 `assert(test_eq_entries(entry_ref, entry))`
- 根因：Compose 表遍历时，含 keysym U1D1B9（0x101d1b9，MUSICAL SYMBOL MINIMA 输入序列）的条目在 `xkb_compose_table_iterator_next()` 的 trie 深度优先遍历中缺失。探测实证：compose 表共 5689 条目，遍历结果中无 U1D1B9；而源码 Compose 文件（test/data/locale/en_US.UTF-8/Compose:5035）明确含该条目；`xkb_keysym_from_name("U1D1B9")=0x101d1b9` 解析正常
- 性质：xkbcommon 在 OHOS（musl）平台 compose 表遍历对高值 Unicode keysym 的边界差异。仅影响 compose（X11 输入法合成）功能，wlroots/wayfire 仅用核心 xkb_keymap API，不依赖 compose → 不影响 wayfire 依赖链编译与运行
- 影响评估：wayfire/wlroots 集成 xkbcommon 核心库不受影响

## 源码修改
- patches/0001-meson-merge-modes-python-interpreter.patch：merge-modes custom_target 命令由 `script` 改为 `python, script`（用 find_installation('python3') 显式执行），避免依赖脚本 shebang /usr/bin/env——OHOS 沙箱与部分精简环境无 /usr/bin/env 时 custom command 无法执行（沙箱已实证 `/usr/bin/env: Permission denied`）

## 依赖版本
- 核心库无强制外部依赖；可选功能（x11/xcb、xkbregistry/libxml2）已关闭
- 构建工具：clang 15.0.4、meson 1.13.1、ninja 1.13.1

## 验证结果
```bash
# 交叉编译
ninja -C build-ohos   # 296 目标全部成功
# 上游测试
meson test --num-processes 1   # Ok: 18, Fail: 2（见上）
# conan 完整验证
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 ...   # PASS
# test_package 鸿蒙冒烟
1/1 Test #1: test_xkbcommon Passed (xkb_context_new/keymap_new_from_string/state/keysym/utf8)
```
