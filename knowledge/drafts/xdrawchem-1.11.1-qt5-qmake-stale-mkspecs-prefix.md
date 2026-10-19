# Qt5 包内 qmake 模块描述指向已消失的构建目录：`QT += <module>` 全部 Unknown module(s)

> Draft: `DRAFT-XDRAWCHEM-1111-QT5-QMAKE-STALE-MKSPECS-PREFIX`
> Stem: `xdrawchem-1.11.1-qt5-qmake-stale-mkspecs-prefix` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-XDRAWCHEM-1111-QT5-QMAKE-STALE-MKSPECS-PREFIX
- **严重度**: 2
- **类别**: build-system|qmake|qt5|conan|path
- **触发工具**: qmake|conan
- **阶段**: build

## 错误特征

用 qmake 构建一个依赖 Qt5 模块包的 conan 配方时（xdrawchem 1.11.1 实测）：

```
qmake xdrawchem.pro -spec linux-clang ...
Cannot read /home/u/.conan2/p/b/qt5-qa31db92296d5b/b/mkspecs/modules-inst/qt_lib_bootstrap_private.pri: No such file or directory
Cannot read .../qt_lib_core.pri: No such file or directory
...                                       # 共 48 条同类警告
Project ERROR: Unknown module(s) in QT: core gui xml network widgets printsupport
```

注意 `svg` **不在** Unknown 列表里——因为配方已通过 `QMAKEMODULES` 提供了重写后的
`qt_lib_svg.pri`；这恰好说明"只修外部模块（qtsvg）不修 qtbase"是不够的。

## 根因

Qt5 模块包（qt5-qtbase / qt5-qtsvg …）在 conan 缓存里是**就地安装**后再打包的，
包内 qmake 元数据保留了构建期前缀：

```
$ tail -6 <qtbase-pkg>/mkspecs/modules/qt_lib_core.pri
QT_MODULE_BIN_BASE       = .../p/b/qt5-qa31db92296d5b/b/bin
QT_MODULE_INCLUDE_BASE   = .../p/b/qt5-qa31db92296d5b/b/include
QT_MODULE_LIB_BASE       = .../p/b/qt5-qa31db92296d5b/b/lib
include(.../p/b/qt5-qa31db92296d5b/b/mkspecs/modules-inst/qt_lib_core.pri)
QT.core.priority = 1

$ cat <qtbase-pkg>/bin/qt.conf
[Paths]
Prefix=.../p/b/qt5-qa31db92296d5b/b/p          # 同样是构建期路径
HostPrefix=.../p/b/qt5-qa31db92296d5b/b/p
```

`.../p/b/<hash>/b` 是 conan 的构建目录，打包后即被清理。于是：

1. `include(...)` 目标不存在 → 每个模块一条警告，`QT.<module>` 的 includes/libs
   解析不出有效值 → `Unknown module(s) in QT`；
2. `QT_INSTALL_BINS` → `<stale>/bin` → `QMAKE_RCC/MOC/UIC` 指向不存在的可执行文件
   （生成的 Makefile 把 `<stale>/bin/rcc` 写成 qrc 依赖，即使过了 configure 也会在
   make 阶段炸）；
3. 命中 `QT_MODULE_LIB_BASE` 的链接路径与产物 RUNPATH 一并写入失效目录。

## 修复（rec_approach: copy-rewrite-pri-via-qmakemodules-plus-qtconf）

在配方 `build()` 里组装一个"清洁的 qmake 视野"：

```python
_STALE_PREFIX_RE = re.compile(r"/[^\s\"'()]*?/p/b/[^/\s\"'()]+/[bp](?=/|$|\s|\"|')")

for dep_name in ("qt5-qtbase", "qt5-qtsvg"):           # 每个 Qt5 模块包都要
    pkg = self.dependencies[dep_name].package_folder
    for sub, target in (("mkspecs/modules", modules_dir),
                        ("mkspecs/modules-inst", modules_inst_dir)):
        for pri in os.listdir(os.path.join(pkg, sub)):
            content = read(pri)
            write(target/pri, _STALE_PREFIX_RE.sub(pkg, content))
build_env.define("QMAKEMODULES", modules_dir)          # 优先于 Qt 安装内条目

# 修正 qt.conf（不可带 [EffectivePaths] Prefix=..，否则找不到 mkspec）
write(qt_conf, f"[Paths]\nPrefix={qtbase}\nHostPrefix={qtbase}\nSysroot=\n")
qmake -qtconf qt_conf app.pro -spec linux-clang \
      "QMAKE_RCC={qtbase}/bin/rcc" "QMAKE_MOC={qtbase}/bin/moc" "QMAKE_UIC={qtbase}/bin/uic"
```

三个关键点：

| 关键点 | 为什么 |
|---|---|
| 正则必须以 `/` 起锚 | 否则 `include(/…/b/…)` 的 `include(` 会被连带吃掉，生成的 `.pri` 变 `…/b/…)`，仍报 Unknown module(s)（qpdfview 0.5.0 实撞） |
| `QMAKEMODULES` 而不是改包内文件 | QMAKEMODULES 目录同名 `.pri` 优先，无需改动 conan 缓存包（并发构建安全、不改动依赖包完整性） |
| 残留 "Cannot read" 警告可接受 | qmake 仍会遍历 Qt 安装内 `modules/` 目录；不影响模块解析，属噪音 |

## 先例

- `archives/q/qconf/2.5` —— 同问题的完整解法（含 qt.conf + 工具变量兜底）
- `archives/b/baka/2.0.4`、`archives/q/qpdfview/0.5.0` —— 外部模块（qtsvg/qtx11extras）
  的 .pri 改写
- `archives/q/qt5-qtsvg/5.15.2` —— 反向做法（直接改 qtbase 包内文件）作兜底参考

## 验证

```bash
qmake -qtconf <fixed>.conf <app>.pro -spec linux-clang
# 期望：无 "Project ERROR: Unknown module(s)"
grep -n '^CXXFLAGS' Makefile          # -I 指向真实 package 目录
make -j1 && readelf -d bin/<app> | grep -E 'RUNPATH|NEEDED'
# 期望：RUNPATH 不含 .conan2/p/b/ 构建期路径
```
