# ncurses 6.5 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-07-31
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build ncurses 6.5
   ```

2. 平台检测补丁（E160）：config.guess/sub 不识别 HarmonyOS，在 build() 阶段用 sed 注入 `HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl` 与 `ohos*)` 匹配。

3. configure（禁用共享库，静态编译——R26 系统同名库强制静态）：
   ```bash
   TMPDIR=/data/storage/el2/base/haps/entry/files/.ncurses-tmp \
   /system/bin/sh ./configure \
     --without-shared \
     --without-debug \
     --without-ada \
     --without-manpages \
     --without-tests \
     --without-cxx-binding \
     --enable-widec \
     --enable-overwrite
   ```
   注意：`--without-shared` 是 OHOS 安全要求（R26），共享库可能被 LD_LIBRARY_PATH 劫持系统 libncursesw.so.6 致 zsh 崩溃。未使用 `--enable-symlinks`（HMDFS 不支持软链接，会致 `make install` 失败）。

4. 编译：
   ```bash
   make -j1
   ```

5. 安装到 staging：
   ```bash
   autotools.install()  # Conan 调 make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识引用 |
|---|------|------|----------|----------|
| 1 | config.guess 不识别 HarmonyOS | upstream config.guess 无 OHOS case | sed 注入 `HarmonyOS|HongMeng) UNAME_SYSTEM=Linux` | E160 |
| 2 | `make preinstall` 测试失败 | HMDFS noexec，configure 尝试跑未生成的 Makefile | sed 改 `make preinstall` 为 `true` | — |
| 3 | configure 临时文件创建失败 | HMDFS 不允许在 cwd 写 `./confXXXXX` | TMPDIR 重定向到 sandbox `/data/storage/el2/base/haps/entry/files/.ncurses-tmp` | — |
| 4 | HMDFS 不支持软链接 | `--enable-symlinks` 会让 `make install` 创建 libcurses.a → libncurses.a 等链接失败 | 不使用 `--enable-symlinks`（默认禁用），靠 `--enable-overwrite` 直接安装头文件到顶层 include/ | — |

## 源码修改

无补丁文件（平台检测与 configure 补丁在 build() 阶段用 sed 动态注入，非持久补丁）。

## 依赖版本

- ncurses 6.5 上游源码（GNU mirror）
- 无 Conan 库依赖（ncurses 是底层系统库，自身无三方库依赖）

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion ncursesw
# 6.5

# 静态库符号验证
nm libncursesw.a | grep initscr
# 0000000000000000 T initscr

# 消费者测试（test_package/test_ncurses.c）
# initscr() 返回值检查 + printw/endwin 安全调用，headless 环境不段错误
./test_ncurses
# ncurses API test PASSED
```

## 交付物

| 文件 | 说明 |
|------|------|
| libncursesw.a | 静态库（widec） |
| libpanelw.a | panel 库 |
| libmenuw.a | menu 库 |
| libformw.a | form 库 |
| include/*.h | 头文件（--enable-overwrite 安装到顶层） |

## 注意事项

1. **必须 `--without-shared` 静态编译**（R26 + OHOS 安全）：共享库可能被 LD_LIBRARY_PATH 劫持系统 libncursesw.so.6 致 zsh 崩溃，所有终端不可用。
2. **不得使用 `--enable-symlinks`**：HMDFS 不支持软链接，`make install` 创建符号链接会失败。
3. **TMPDIR 必须重定向到 sandbox**：HMDFS tmpfs（hmmac=use_task）阻塞 configure 临时文件创建，重定向到 `/data/storage/el2/base/haps/entry/files/.ncurses-tmp`（HMFS hmmac=inherit_parent 允许跨 subshell 写临时文件）。
4. **E160 平台检测**：config.guess/sub 需 sed 注入 HarmonyOS case，upstream 不识别 OHOS。
