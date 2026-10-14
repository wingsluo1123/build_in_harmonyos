- **三方库名称**：libskk
- **上游版本**：1.1.1
- **上游仓库地址**：https://github.com/ueno/libskk
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 35 | 上游 `make check` 的 8 个 GLib TAP 测试目标；按 8 个 `tests/*.log` 中 `ok N` 行计数。 |
| 集成测试 | 0 | 上游未单列集成测试目标。 |
| 其他测试 | 0 | 无其他测试目标。 |
| **合计** | **35** | 8 个目标各自用例数：basic 22、cdb-dict 1、context 2、file-dict 1、rom-kana 1、rule 4、skkserv 1、user-dict 3。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 35 | 不变 | 真机执行 `make check`，8 个目标全部通过，未改上游测试。 |
| 集成测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test_package.c`：通过公开 C API 创建 context、输入罗马字，校验假名输出和 preedit；5 项断言。 |
| **合计** | **36** | **+1** | 35 个上游用例 + 1 个消费者用例。 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

## 验证结果

- 编译状态：通过（HarmonyOS 真机 `conan create` 退出码 0）
- 上游测试用例通过率：35/35（100%）；失败 0。8 个 `make check` 目标通过，Automake 汇总 PASS 8、FAIL 0、SKIP 0、ERROR 0。逐目标用例数见上表；没有失败项，因此无失败原因。
- 新增测试用例通过率：1/1（100%）；消费者测试 5/5 项断言通过。

## 补充说明

- 上游归档地址：`https://github.com/ueno/libskk/releases/download/1.1.1/libskk-1.1.1.tar.xz`；配方固定 SHA-256：`2d4c15976d459ef0004ce1c0e47506c7859d0b6f4fb104ed837f3326d235bb56`，真机 `conan create` 下载时按该值校验。
- 平台制品库中已有并使用 glib/2.84.0、libgee/0.20.8.2、json-glib/1.6.6、libxkbcommon/1.6.0、libintl/0.26.1；构建工具 vala/0.56.18、gettext/0.22.5.1 也已存在。gettext 仅作为构建期工具提供 `msgfmt`，不进入包的运行时依赖；libintl 是目标端 gettext/NLS 运行库。
- 官方 release 压缩包已包含生成后的 `configure`、`aclocal.m4` 与 `Makefile.in`；配方直接运行 `configure`，不调用或依赖 `autoreconf`、`autopoint`、`aclocal` 或 `automake`。
- The libtool export-symbol list is resolved from the configured source directory through `$(abs_srcdir)`, so it remains reachable from Conan's out-of-tree build.
- gettext 仅提供可能重编 NLS catalog 所需的 `msgfmt`，libintl 提供 external gettext 的目标端运行库。HarmonyOS 配置关闭 FEP、文档和可选 GObject Introspection。`libskk` 以静态库形式构建：平台 libgee 的共享制品内含静态 GLib，为避免第二份 GType 注册；包通过 `LIBSKK_DATA_PATH` 指向安装的规则数据。
- 上游 `po/`、日文翻译及 NLS 规则保持启用；`ja.po` 编译安装为 `share/locale/ja/LC_MESSAGES/libskk.mo`。
- `make check` 用例数取自真机测试构建目录 8 个 TAP 日志：`grep -h '^ok [0-9]' "$TEST_LOG_DIR"/*.log | wc -l`；结果 35。Automake 汇总为 8/8 个目标通过。
- 验证命令：在干净独立 `CONAN_HOME` 且基础 PATH 不含 autopoint 的环境中，执行 `conan create archives/l/libskk/1.1.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -c tools.build:jobs=2 --user=ohpcd --channel=stable`；gettext build requirement 提供 `msgfmt`，release 包自带生成文件，配方不运行 autotools 生成器；libintl 提供目标端翻译运行库。
