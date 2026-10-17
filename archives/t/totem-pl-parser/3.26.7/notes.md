# totem-pl-parser 3.26.7 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-10-16
- 编译器: clang 15 / clang++（OHOS PC aarch64，profile `ohos-aarch64`，build==host）
- 状态: built

## 编译步骤

1. `generate()` 落盘 meson native 文件：`[binaries]` 段写入 cc/cxx/ar/ranlib 与 pkg-config 的**绝对路径**（OHOS libc 的 `posix_spawn` 不做 PATH 查找）。
2. `build()` 经 conan Meson 助手执行 `setup` → `ninja` → `ninja install`（DESTDIR 由 conan 管理）。
   关键选项：`-Ddefault_library=shared`、`-Dintrospection=false`、`-Denable-gtk-doc=false`、`-Denable-uchardet=yes`、`-Denable-libarchive=no`、`-Denable-libgcrypt=no`。
3. 上游测试在 `build()` 内以 `meson test -v -C <build>` 运行（本 conan 版本的 `Meson.test()` 不接受参数，故用显式命令），按 MIME 数据库能力选择用例（见「验证结果」）。
4. `package()` 安装头文件与两个共享库，重建 OHOS 工具链未写入的 SONAME 与 `.so` 别名，并对产物 ELF 签名（`_sign_installed_elfs`，详见「遇到的问题」#5）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建期 `glib-mkenums` / `glib-genmarshal` 不可用 | 二者是 python 脚本；若在配方内自行编译 GLib，CI worker 的 SDK lld 缺 `libxml2.so.16` 会导致工具无法生成 | 配方生成**零编译 sh wrapper**，转发到注册表 `glib/2.84.0.1` 包内已构建的工具，wrapper 目录加入 build 环境 PATH |
| 2 | meson 调用外部工具失败 | OHOS libc 的 `posix_spawn` 不做 PATH 查找 | native 文件中的工具路径全部写绝对路径 |
| 3 | 链接期 uchardet 符号 `undefined reference` | 注册表 `uchardet/0.0.7` 的 `.pc` 未暴露头文件目录；且其静态归档是 C++ 实现，`-lstdc++` 只写在 `Libs.private`（meson 在 `--no-undefined` 下忽略） | `generate()` 内改写生成物 `uchardet.pc`：`Cflags` 补 `-I${includedir}/uchardet`，`Libs` 补 `-lc++`（profile `libcxx=libc++`） |
| 4 | 产物别名 `.so.18` / `.so` 不可靠 | `meson install` 生成的两个别名是**软链接**，而签名流程会跳过软链接（`islink` 判定），运行时要求每个 ELF 各自带 `.codesign` | `package()` 内 `_create_shared_lib_aliases()`：先删除软链接，再按实体文件复制出 `.so.<soversion>` 与 `.so` 两个别名（soversion 由上游 lt_version `21:6:3` 推出 18），别名随后各自参与签名 |
| 5 | 产物 ELF 未签名不可加载 | OHOS 运行时要求 ELF 带 `.codesign` 段 | `_sign_installed_elfs()`：先用 `llvm-objcopy --remove-section .codesign` 清掉上游残留段，再由 `binary-sign-tool sign -inFile <elf> -outFile <elf> -selfSign 1` **原地签名**；只处理 `bin/` 与 `lib/` 下的实体 ELF（跳过软链接） |
| 6 | 上游测试进程收到 SIGTRAP | 沙箱无 `/etc/passwd`，GLib 的 `getpwuid_r` 失败触发 GLib-FATAL-WARNING，测试框架因此 SIGTRAP（**不是**签名问题） | 仅测试期注入 `getpwuid` LD_PRELOAD shim（cracklib 先例）；shim 只在 `build()` 的测试环境生效，不进产物、不影响 ABI |
| 7 | `parser` / `podcast` 测试假失败 | 设备无 freedesktop MIME 数据库（shared-mime-info），glib 把 `.html` / `.m3u` 判为纯文本，totem-pl-parser 返回 `TOTEM_PL_PARSER_RESULT_UNHANDLED` | 配方探测 `mime/mime.cache`（含 `globs2` 回退）是否存在：有库跑全部 3 项，无库只跑与 MIME 无关的 `disc` 并打印原因；不修改上游测试代码 |

## 源码修改

无补丁（`patches/` 为空）。全部平台差异通过 meson 选项、`generate()` 生成的 native 文件与 `.pc` 改写、以及 `package()` 的产物后处理表达，不写入任何平台宏。

## 依赖版本

- glib/2.84.0.1（生态对齐版本，提供 glib-2.0 / gobject-2.0 / gio-2.0）
- libxml2/2.15.3
- uchardet/0.0.7（可选特性，本次启用并修补其 `.pc`）
- 关闭项：libarchive（仅 `totem-disc.c` 的 ISO 探测使用，无上游测试覆盖，且注册表包未把 libdir 暴露给消费者运行环境）、gobject-introspection、gtk-doc、libgcrypt（meson `find_library` 探测，上游未实际使用）

## 验证结果

上游测试台账（R51 三步法）：

- **清点**：上游 `plparse/tests/meson.build` 注册 3 项测试 —— `disc` / `parser`（`/parser/resolution`）/ `podcast`（`test_image_link`）
- **实跑**：N=3，N′=1，通过率 1/1 = 100% —— `disc` 通过（Ok: 1 / Fail: 0）
- **跳过**：`parser`、`podcast`（2 项）—— 设备无 freedesktop MIME 数据库；上游测试自身打印 `"foo.html" isn't detected as text/html, is shared-mime-info installed?`，属环境能力缺失，非本包缺陷

```bash
python3 scripts/ohc-run.py conan-verify totem-pl-parser 3.26.7   # 8 门禁 PASS（G2 conan create 成功）
python3 scripts/ohc-run.py finish totem-pl-parser 3.26.7 built   # W3 本地 CI（setup.sh + build_and_test.sh）PASS
```

消费者测试（`test_package/`，R34）：真实调用 `totem_pl_parser_new()` / `totem_pl_parser_parse()` 解析写出的 `.m3u`，按 `entry-parsed` 信号校验条目数与首条 URI；按 MIME 数据库存在性分支断言（有库：`SUCCESS` + 2 条目 + 首条 URI；无库：`UNHANDLED` + 0 条目）。本机实测：无库分支，输出 `OK`。

## 交付物

| 文件 | 说明 |
|------|------|
| libtotem-pl-parser.so.18 | 主库（保留上游符号映射 `plparser.map`） |
| libtotem-pl-parser-mini.so.* | 轻量 API 库 |
| include/plparse/*.h | 公共头文件 |

无可执行文件，故不需要 `commands.json`。

## 注意事项

- 配方不写入任何平台宏（`patches/` 为空）；平台差异全部通过 meson 选项、native 文件与产物后处理表达。
- 测试期 `getpwuid` LD_PRELOAD shim 只服务于 GLib 的 passwd 查询，不进产物。
- 若 CI/真机镜像安装了 `shared-mime-info`，配方会自动改为运行全部 3 项上游测试，消费者测试也会走强断言分支。
- `package_info()` 目前只暴露主库 `libtotem-pl-parser`；`libtotem-pl-parser-mini`（含 `totem-pl-parser-mini.h`）随包安装但未在 `cpp_info` 中声明，暂无已知消费者——后续若有消费需求，再以 `cpp_info.components` 补全。

---

**编译结束**: 2026-10-16
**最终状态**: built
