# mystiq 20.03.23 适配笔记

## 编译环境
- 构建系统: qmake（顶层 `mystiq.pro`，`TEMPLATE = app`）
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，ohos-sdk 26.0.0.18，musl libc）
- 目标: HarmonyOS PC aarch64（`ohos-aarch64` profile，os=OHOS/6.0，arch=armv8，libc++）
- 状态: built

## 编译步骤

本包不改上游源码，全部适配在配方层完成：

1. `requirements`: `qt5-qtbase/5.15.2.2`（注意 5.15.2 是 `-no-widgets -no-dbus` 构建，不可用）、
   `qt5-qtdeclarative/5.15.2`、`qt5-qtmultimedia/5.15.2`。
2. `build()` → `_prepare_qt5_root()`：在 `build_folder/qt5-root` 建合并前缀（R49 私有前缀）：
   - `bin/` 从 qtbase 复制（qt.conf 依赖可执行文件真实路径，符号链接会被解析回原包）；
   - `include/ lib/ plugins/ qml/` 符号链接合并三包（`.prl` 不链接）；
   - `mkspecs/` 复制 qtbase 全量后叠加 declarative/multimedia 的 `modules`、`modules-inst`；
   - **重写 `.pri`/`.prl` 内的 conan 构建目录绝对路径**（形如 `.../.conan2/p/b/qt5-qXXXX/b`），
     改为对应依赖的 `package_folder`，并把 `include(<pkg>/mkspecs/modules-inst/...)` 指向合并树副本；
   - 生成 `qt5-root/bin/qt.conf`（`Prefix=<root>`，`TargetSpec=linux-clang`）。
3. 构建命令：
   ```bash
   "<qt5-root>/bin/qmake" mystiq.pro -spec linux-clang
   make -j2 QMAKE_STRIP=""
   ```
4. `package()`：`bin/mystiq` + `presets.xml`/`constants.xml`（DATA_PATH 为空时按可执行文件同级查找）
   + desktop/icon/appdata/man。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 解压失败：`Compressed file ended before the end-of-stream marker was reached` | 内置 urllib 下载 GitHub tarball 被截断（833,780 字节 ≠ 完整 896,299 字节） | 用 `curl -sSL` 重新下载并补齐 sha256（`cfb84fae…`）后重跑 init-build |
| 2 | `qmake` 报 `libQt5OpenGL.prl does not define QMAKE_PRL_TARGET` / `Unknown module(s)` | conan 包内 `.pri`/`.prl` 记录的是**构建时**绝对路径（构建目录已被 conan 清理） | 配方内统一重写 `.pri`/`.prl` 前缀到 `package_folder`（`_prepare_qt5_root`） |
| 3 | 重写脚本把依赖包内 `.prl` 清成 0 字节 | `sed > 符号链接路径` 会跟随链接、先截断目标源文件 | 修法：`lib` 阶段跳过 `.prl`，单独生成临时文件再 `os.replace`；已被清空的包用 `conan remove` + 重新 `conan install` 恢复 |
| 4 | `qt.conf` 用相对 `Prefix=..` 时 `QT_INSTALL_PREFIX` 解析成 `bin/build/qt5-root` | qmake 相对可执行文件目录解析 Prefix | `qt.conf` 写绝对路径 |
| 5 | 鸿蒙测试编译报 `undefined symbol: typeinfo for NotificationService` / `undefined symbol: main` | `.pro` 漏 `services/notificationservice.cpp`；`.cpp` 漏 `QTEST_MAIN` | 补 SOURCES 与 `QTEST_MAIN(TestOhosPlatform)` |
| 6 | `conan create` 报 `get() got an unexpected keyword argument '20.03.23'` | conandata `sources` 用了版本层，代码却直接 `**self.conan_data["sources"]` | `sources` 改为无版本层（与 acetoneiso 先例一致） |
| 7 | `conan create` 应用补丁失败：`source/target file does not exist: b'a/tests/testohosplatform/...'` | 新增测试目录在源码树中不存在，patch 无法创建目录 | 改为配方附加源码：`ohos-tests/` 随 `export_sources()` 分发，`build()` 中 `copy` 到 `tests/testohosplatform`；`patches` 置空 |
| 8 | W3 `L0 gate failed: stub_test_method` / `no_test_sources` | test_package 用 `subprocess` 而非 `self.run`，且缺 `.sh` 测试源 | 新增 `test_package/test_mystiq.sh`，`test()` 改为 `self.run(sh … , env="conanrun")` |
| 9 | W3 `JC gate failed: junk files detected` | `junk_check.sh` 无 `pr.diff` 时回退 **full 模式扫全仓**，命中 main 上其他包的遗留状态文件（cloog/kcachegrind/kics/libbfio/libdazzle/oscpack/reflex/thc 共 9 个），与本包无关 | 以 `JUNK_PR_DIFF=<本包 pr.diff>` 走 prdiff 模式验证：`Junk Files: 0`、`涉及软件数: 1（合规）`；同时清理本包由 conan-verify 留下的镜像备份/`.orig` 残留、补丁备份目录与 test_package 的 conan 生成脚本 |
| 10 | `build_and_test.sh` / `conan-verify` 运行后 `conandata.yml` 被改写为 `url: [镜像地址, 官方地址]` 列表 | 工具的 E017 镜像注入后"恢复"逻辑保留了镜像项，属工具侧缺陷 | 提交前必须把 `sources.url` 还原为**单条官方 https** 并重新 `git add`；已用官方源复跑 `conan create`（EXIT=0）与 W3（EXIT=0）验证 |

## 源码修改

无源码补丁（`patches: []`）。上游 tarball sha256 保持官方原值；
鸿蒙相关测试以 `ohos-tests/` 随配方分发，不修改上游文件。

## 依赖版本

| 依赖 | 版本 | 类型 |
|---|---|---|
| qt5-qtbase | 5.15.2.2（rrev `760fc7d9`） | 构建期链接 + 运行期（Core/Gui/Widgets/Network/DBus/Test/OpenGL） |
| qt5-qtdeclarative | 5.15.2（rrev `9d2bf9bc`） | 构建期链接 + QML 运行时 |
| qt5-qtmultimedia | 5.15.2（rrev `20294ed3`） | 构建期链接 + 运行期 |
| ffmpeg / ffprobe | 运行期外部 CLI（`>= 3.0.0`，建议 `ffmpeg/7.1.5`） | 下游部署注入，不在本包链接 |
| sox | 运行期可选（仅"音频变速"） | 可选 |

## 验证结果

```bash
# 上游测试（OHOS aarch64，offscreen QPA）
tests/testversioncompare  : 5 passed（含 init/cleanup），用例 3/3 PASS
tests/testupdateinfoparser: 3 passed（含 init/cleanup），用例 1/1 PASS
# 鸿蒙特有测试
tests/testohosplatform    : 5 passed（含 init/cleanup），用例 3/3 PASS
# 包级
conan create              : EXIT=0，test_package 启动 mystiq 存活 6s
conan-verify              : G1/G2/G3/G4 PASS
W3 build_and_test.sh      : JC/L0/L1/L4/L5 PASS（L2 skip：GUI 应用无 --version/--help）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `packaging/mystiq-20.03.23-release.tar.gz` | 1.6 MB | conan 包目录打包（bin + share） |
| `packaging/mystiq-20.03.23-debug.tar.gz` | 1.6 MB | 未 strip 产物（OHOS 加载器要求） |

## 注意事项

1. qt5-qtbase **5.15.2** 是 `-no-widgets -no-dbus` headless 构建，mystiq 必须用 **5.15.2.2**。
2. `qt5-qtmultimedia/5.15.2` 包内无 `qml/QtMultimedia` QML 插件，`qml/main.qml` 的
   `import QtMultimedia 5.10` 运行时可能告警；转码/探测走外部 ffmpeg/ffprobe，主功能不受影响。
3. 只有 offscreen/minimal/vnc QPA 插件可用（无 xcb/wayland），真实窗口渲染未验证。
4. ffmpeg 7.1.5 不支持 mystiq 用到的 `-sameq`/`-deinterlace`/`-vol` 等旧参数（LGPL 构建亦无 libx264），
   若要完全等价旧行为可部署 `ffmpeg/4.4.8`。
5. `make` 必须带 `QMAKE_STRIP=""`：OHOS 加载器拒绝 strip 后的 ELF。
---

**编译结束**: 2026-10-17 23:01
**最终状态**: built
