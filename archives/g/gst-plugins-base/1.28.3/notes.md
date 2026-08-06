# gst-plugins-base 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码 tarball 并验证 sha256
2. 运行 init-build 初始化构建环境
3. 使用 meson 配置 + ninja 编译
4. 关键 meson 选项: -Diso-codes=disabled, -Dorc=disabled, -Dgl=disabled, -Dexamples=disabled, -Dvorbis=disabled, -Dtheora=disabled, -Dogg=disabled, -Dnls=disabled, -Dtests=disabled, -Dintrospection=disabled, -Dtools=disabled

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python 脚本无法在 HMDFS 上直接执行 | HMDFS 不支持 shebang 行 | Patch 0001: find_program→files+python3 模式调用 meson-pkg-config-file-fixup.py 和 extract-release-date-from-doap-file.py |
| 2 | gettext/ngettext 未定义 | OHOS 无 gettext 库 | 在 MesonToolchain c_args 中定义 -Dgettext(x)=(x) 和 -Dngettext(s,p,n)=((n)==1?(s):(p)) 宏 |
| 3 | glib2 子包 .pc 文件缺失 | Conan PkgConfigDeps 只生成 glib-2.0.pc | 在 generate() 中创建 gobject-2.0.pc, gio-2.0.pc, gmodule-2.0.pc 等 wrapper .pc 文件 |
| 4 | gstreamer .pc 文件缺失 | Conan PkgConfigDeps 未生成 gstreamer .pc 文件 | 在 generate() 中创建 gstreamer-1.0.pc 及子包 .pc 文件 |
| 5 | AR/AS/STRIP/NM/RANLIB 环境变量指向不存在的 llvm-* 工具 | CI worker 导出的环境变量与 PATH 不匹配 | 在 generate() 中清除这些环境变量，用 shutil.which() 从 PATH 解析正确路径 |

## 源码修改

- patches/0001-fix-python-script-execution.patch: 修复 meson.build 中 Python 脚本执行（find_program→files+python3）

## 依赖版本

- gstreamer/1.28.3 (已在 conan 本地缓存)
- glib2/2.88.0 (已在 conan 本地缓存)

## 验证结果

```bash
# conan create 验证
conan create archives/g/gst-plugins-base/1.28.3/conanfile.py
# → 验证通过，包进入本地 conan 缓存
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (Meson + MesonToolchain + PkgConfigDeps) |
| conandata.yml | 源码 URL + sha256 + 补丁声明 |
| test_package/ | 测试包 (调用 gst_audio_format_to_string 等真实 API) |
| patches/0001-fix-python-script-execution.patch | HMDFS Python 脚本执行修复 |

## 注意事项

- gstreamer/1.28.3 必须先 conan create 成功（本包依赖它）
- gettext stub 方式与 gstreamer 配方一致
- glib2 子包 .pc 文件创建方式与 gstreamer 配方一致
---

**编译结束**: 2026-08-06 18:09
**最终状态**: built
