# xdrawchem 1.11.1 适配笔记

## 编译环境

| 项 | 值 |
|----|----|
| 设备/平台 | HarmonyOS PC（aarch64，OHOS 6.0），原生（非交叉）构建 |
| 编译器 | clang 15.0.4（`/data/service/hnp/bin/clang++`，`-spec linux-clang`） |
| 构建系统 | **qmake**（上游 `xdrawchem.pro`，in-source build） |
| conan | 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64` |
| 编译日期 | 2026-10-16 |
| 状态 | built（conan create + test_package 全绿，未 upload） |

## 依赖（W0 结论：全部已发布，无需先适配依赖）

| 依赖 | 版本 | 提供方 | 用途 |
|------|------|--------|------|
| qt5-qtbase | 5.15.2.2 | 制品仓已发布 | Qt5Core/Gui/Widgets/Network/Xml/PrintSupport + qmake/moc/rcc/uic |
| qt5-qtsvg | 5.15.2 | 制品仓已发布 | `QT += svg`（Qt5Svg，图形导出） |
| openbabel | 3.2.1 | 制品仓已发布 | `PKGCONFIG += openbabel-3`（分子格式读写/2D-3D） |
| （传递）zlib / dbus / expat / libxml2 / eigen / rapidjson | — | 制品仓已发布 | qt5-qtbase 与 openbabel 的依赖链 |

> W0 前置检查（适配前）：`bash ci/scripts/preflight_check.sh xdrawchem/1.11.1 --deps "…"`
> → 3 个直接依赖全部 `[OK] 已发布`，版本号 `xdrawchem/1.11.1` 未被占用。

## 源码

- 上游：<https://gitlab.com/yamanq/xdrawchem>（Debian/Ubuntu 打包的上游原名，`debian/copyright` 的 `Source:` 字段与 `debian/watch` 的 `searchmode=plain` 均指向该 GitLab 仓库；GitHub 镜像 `bryanherger/xdrawchem` 只有 1.10.2-1 及 v2.0rc* 标签，**无 1.11.1**）
- tag：`v1.11.1`（2024-05-29）
- 归档：`https://gitlab.com/yamanq/xdrawchem/-/archive/v1.11.1/xdrawchem-v1.11.1.tar.gz`
- sha256：`4e90e37e713dbd45f53c545c4adedb41154bb6881515c850c1af9c7979f8224b`

## 编译步骤（实际执行）

```bash
# 1) 语言预检（R47）
ohc-run.py lang-preflight xdrawchem 1.11.1 --src $BUILD_SRC_DIR   # detected=cpp，c↔cpp 兼容族

# 2) 配方构建（qmake 在 conan create 内执行）
conan create archives/x/xdrawchem/1.11.1 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

`build()` 内部等价命令：

```bash
qmake -qtconf <修正后的 qt.conf> xdrawchem.pro -spec linux-clang \
      CONFIG+=release PREFIX=<package_folder> QMAKE_STRIP=true \
      QMAKE_RCC=<pkg>/bin/rcc QMAKE_MOC=<pkg>/bin/moc QMAKE_UIC=<pkg>/bin/uic
make -j1
make install                   # 上游 INSTALLS: bin/xdrawchem + share/xdrawchem/{ring 内容, doc/}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Project ERROR: Unknown module(s) in QT: core gui xml network widgets printsupport`，并伴随 48 条 `Cannot read <stale>/mkspecs/modules-inst/qt_lib_*.pri` | qt5-qtbase/5.15.2.2 与 qt5-qtsvg/5.15.2 包内 `mkspecs/modules/*.pri`（及 `bin/qt.conf` 的 `[Paths] Prefix`）记录的是**构建期** conan 私有前缀 `.../p/b/<hash>/b`，随构建目录清理而失效；qmake 据此解析 `QT += core …` 与 rcc/moc/uic 路径 | `_setup_qmake_modules()`：把两个包 `mkspecs/{modules,modules-inst}/*.pri` 复制到构建目录，用正则把构建期前缀整体改写为真实 package 目录，经 `QMAKEMODULES` 暴露（QMAKEMODULES 目录优先，覆盖包内失效条目）；另生成修正 `qt.conf`（Prefix/HostPrefix=真实 package）以 `-qtconf` 加载，并显式钉住 `QMAKE_RCC/QMAKE_MOC/QMAKE_UIC`。参照 `archives/q/qconf/2.5` 先例 |
| 2 | `qt5-qtsvg/5.15.2` 与 `qt5-qtbase/5.15.2.2` 版本冲突（`qt5-qtsvg` 精确 `requires qt5-qtbase/5.15.2`） | 5.15.2 为 `-no-widgets` 构建（无 Qt5Widgets），xdrawchem 需要 Widgets | 配方内 `self.requires("qt5-qtbase/5.15.2.2", override=True)`（`archives/b/baka/2.0.4` 同解；5.15.2.x 为补丁版本，API/ABI 兼容） |
| 3 | 编译到 `http.cpp` 中断：`calling 'debug' with incomplete return type 'QDebug'`（10 处 error） | Qt 5.15 的 `qlogging.h` 只前置声明 `QDebug`（其头注释明写 "In order to use the qDebug() stream, you must #include<QDebug>"），`http.cpp` 大量使用 `qDebug() << …` 却既未包含 `<QDebug>`，也不经其他 Qt 头间接引入 | 补丁 `0002-xdrawchem-http.cpp.patch`：`http.cpp` 增加 `#include <QDebug>`（全仓仅此 1 个 TU 受影响，`make -k` 全量枚举确认） |
| 4 | 产物为 `-O0 -g3` 的 12MB 调试二进制，与 conan `build_type=Release` 不符 | 上游 `xdrawchem.pro` 无条件 `CONFIG += debug` + `QMAKE_CXXFLAGS_DEBUG += -O0 -g3`；qmake 的 `.pro` 在命令行赋值**之后**求值，`CONFIG-=debug` 命令行覆盖无效（实测） | 补丁 `0001-xdrawchem.pro.patch` 移除硬编码 `CONFIG += debug`；配方按 `self.settings.build_type` 显式传 `CONFIG+=release` / `CONFIG+=debug` |
| 5 | `openbabel-3.pc` 的 `prefix`/`libdir` 指向构建期目录，`PKGCONFIG += openbabel-3` 探测失败 | openbabel 包内 `.pc` 未做 prefix 改写 | `generate()` 用 Conan `PkgConfigDeps` 重新生成 `.pc`，并以 `set_property("openbabel", "pkg_config_name", "openbabel-3")` 对齐上游探测名；`PKG_CONFIG_PATH` 指向 generators 目录（PkgConfigDeps 不自动注入） |
| 6 | `make -j>1` 报 jobserver mkfifo 错误 | HMDFS 不支持 mkfifo | `make -j1`（仓内 Qt 应用先例一致） |
| 7 | `conan create` 构建成功，但 test_package 全部 FAIL：`bin/xdrawchem: Operation not permitted`（execve 返回 EPERM，而非 EACCES） | 上游 `install_target` 规则末尾带 `-$(STRIP) <安装后的二进制>`，qmake 生成的 Makefile 里 `STRIP = strip` → **安装期把二进制 strip 了**；OHOS 加载器拒绝 stripped ELF（实测：同一份二进制 `strip` 前后，未 strip 可正常交给动态加载器，strip 后 execve 直接 `Operation not permitted`）。注意环境变量 `QMAKE_STRIP` 与 `make QMAKE_STRIP=` **都无效**——Makefile 里的变量名是 `STRIP`，必须在 **qmake 命令行**传 `QMAKE_STRIP=true` 才会写进 Makefile（实测 `STRIP = true`） | qmake 命令行加 `QMAKE_STRIP=true`（`archives/b/baka/2.0.4`/`acetoneiso` 采用"不用 make install、直接 copy"的等价思路） |
| 8 | test_package 的 TC-04（断言二进制 DT_NEEDED 含 Qt5Widgets/libopenbabel）在 `conan test` 下恒 FAIL 且诊断输出为空，同一命令在交互 shell 里却正常 | `conan test` 注入的运行环境 PATH 中 `/system/bin` 排在 `/data/service/hnp/bin` **之前**，`grep` 命中 **toybox grep 0.8.12**（`/system/bin/grep`）；toybox grep 对二进制文件默认跳过，`-a` 亦不生效，故恒不命中且返回非 0（交互 shell 因 PATH 里 HNP 优先而取 GNU grep，看不到该现象）。`command -v grep` → `/system/bin/grep` 是判定铁证 | 测试脚本放弃 `grep -a`：改用 `tr -d '\000' < 二进制` 去 NUL 后由 **bash 内建 `case`** 做子串匹配（只依赖 toybox `tr`），5/5 PASS（知识草稿 xdrawchem-1.11.1-toybox-grep-binary-skip） |

## 源码修改

补丁由 `ohc-run.py refresh-patch --auto` 生成（探索阶段直接改 `$BUILD_SRC_DIR` 源码，未手写 patch）：

| 补丁 | 文件 | 改动 | 类型 |
|------|------|------|------|
| `0001-xdrawchem.pro.patch` | `xdrawchem.pro` | 删除硬编码 `CONFIG += debug`（-2 行） | portability |
| `0002-xdrawchem-http.cpp.patch` | `xdrawchem/http.cpp` | 增加 `#include <QDebug>`（+2 行） | portability |

> 无 `__OHOS__` 等平台宏（R8/PF5 合规）；无共享系统前缀注入（R49/PF6 合规）。

## 验证结果

```bash
# conan-verify（G0-G4 + L2/L4/L5）与 conan create + test_package
conan create archives/x/xdrawchem/1.11.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...
# → Build succeeded；test_package CASE SUMMARY: total=5 passed=5 failed=0 → PASS
```

> **W3 本地 CI 的 L2 冒烟结果为 `[warn] L2: xdrawchem --version/--help failed (non-blocking)` /
> `L2_RESULT=skip`**：CI 的 L2 直接 execve 包内二进制而**不注入 conanrun 的
> `LD_LIBRARY_PATH`**，二进制 RUNPATH 只含 qt5-qtbase 的 lib 目录 → 加载器缺
> `libopenbabel.so.8`/`libQt5Svg.so.5`/`libxml2.so.16` 等而失败。L2 在 CI/W3 中显式
> 标注 non-blocking（`L0_RESULT=pass`、`.ci-result.json` exit_code=0），不影响流水线。
> 等价断言由注入 conanrun 环境的 `test_package` TC-01/TC-02/TC-03 实跑覆盖
> （`xdrawchem --version` exit=0，输出 `XDrawChem 1.11.0`）。

`test_package` 用例（**实质执行被测包**，非空壳；R34）：

| 用例 | 断言 | 结果 |
|------|------|------|
| TC-01 | `xdrawchem --version` 输出含 `XDrawChem` | PASS |
| TC-02 | `xdrawchem --help` 输出含 `Usage:` 与 `xdrawchem` | PASS |
| TC-03 | 【鸿蒙特有】可执行文件为 OHOS aarch64 ELF（`e_machine=0xB7`）且在本机执行成功 | PASS |
| TC-04 | 二进制 DT_NEEDED 含 `libQt5Widgets` 与 `libopenbabel`（非空壳/错链） | PASS |
| TC-05 | 上游运行期数据随包安装：`share/xdrawchem/xdrawchemrc` + `share/xdrawchem/doc/index.html` | PASS |

### 上游测试（R51 三步法）

1. **清点**：上游 v1.11.1 归档 `find . -iname "*test*"` **0 命中**；顶层仅
   `SPECS/ doc/ icons/ ring/ ring_cml/ translation/ xdrawchem/`，无 `tests/`；
   `xdrawchem.pro` 只有 `TEMPLATE=app` 与 `INSTALLS`，**无 `check`/`test` 目标**；
   无 CTest / pytest / meson 注册 → **上游确无自动化测试套件**。
2. **实跑**：无可运行的上游测试；改为消费者视角 `test_package`（上表 5 条，全部实跑）。
3. **如实回填**：上游用例数 0/0（无测试），新增/自带用例 5/5（100%）。未修改上游任何测试。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/xdrawchem` | Qt5 + Open Babel 图形应用（OHOS aarch64 ELF，未 strip，2,587,264 字节 ≈2.5 MB） |
| `share/xdrawchem/{xdrawchemrc,*.qm,COPYRIGHT.txt,…}` | 上游运行期数据（`ringdir` 的 `ring/*` 按 qmake 语义平铺于此，RINGHOME 即本目录） |
| `share/xdrawchem/doc/*` | 上游帮助文档（`index.html` + 48 个资源） |

## 注意事项

- **上游版本串与 tag 不一致**：tag 为 `v1.11.1`，但 `defs.h` 的 `XDC_VERSION` 仍是
  `"XDrawChem 1.11.0"`（上游未同步）。`--version`/`--help` 与窗口标题都打印 1.11.0，
  属上游既有行为，不做修改。
- **`RINGHOME` 编译期即固定**为 `<package_folder>/share/xdrawchem`（`.pro` 的
  `DEFINES += RINGHOME=…$${PREFIX}/share/xdrawchem`，配方传 `PREFIX=package_folder`）。
  与 Conan 包目录一致，故包自包含；同时 `main.cpp` 会把
  `applicationDirPath().replace("bin","ring/")` 赋给 `RingDir`（翻译/rc 文件查找路径），
  该路径在 Conan 布局下不存在，程序回退 `preferences.Defaults()`，不影响启动与绘图。
- **`-png` 导出在无显示环境下不可用**：`-png` 走 GUI 渲染路径（`QPixmap`/`QWidget::paintEngine`），
  `QT_QPA_PLATFORM=offscreen` 下 `save PNG failed`；此外上游为该开关赋值 `outfile = arg`（把
  `-png` 自身当输出文件名，未取下一个参数），属上游既有缺陷，未纳入本次适配范围（不影响
  编译、打包与 `--version`/`--help`）。测试不以 PNG 导出为判据。
- `make -j1` 为本环境硬约束（HMDFS 无 mkfifo）。
- **R40「需人工确认适配完整性」标注**：xdrawchem 属 Qt5 桌面 GUI 应用，本次验收覆盖
  CLI（`--version`/`--help`）、ELF 架构（`e_machine=0xB7`）、真实 DT_NEEDED
  （Qt5Widgets/libopenbabel）与运行期数据安装；**GUI 端到端（窗口系统/输入事件/绘图渲染、
  分子格式读写、NMR/IR 工具、PNG 导出）未在本环境验证**，需由人工在有显示会话的 OHOS PC
  上确认（窗口/输入栈本身由已发布的依赖包 qt5-qtbase 承担，本配方职责为正确链接与打包）。
  status 因此为 `built`（未 publish）。

## 提交流程说明（PF9 免检留痕）

本 PR 的首个提交同时包含**软件级**文件 `archives/x/xdrawchem/{manifest.yaml,README.md,commands.json}`：

- `ARCHIVE-SPEC v3.0 §2.1` 将软件级 `manifest.yaml` / `README.md` 列为必须项；`commands.json`
  为 tool 类型的条件必填项，`CI 门禁 L0k` 从软件级目录读取它（`ci/conan/build_and_test.sh`
  的 `CONANFILE_DIR="$(dirname "$CONANFILE")"` + `PKG_SOFTWARE_DIR="$(dirname "$CONANFILE_DIR")"`
  两行，等价于取版本目录的上一级）。若缺此文件，CI 的 L0k
  会直接 `[fail] L0k: CLI tool detected but commands.json missing`。
- 但 `scripts/ohc/preflight.py` 的 **PF9 分支/路径闸**要求 archives 下变更路径深度 ≥5
  （必须落在 `archives/<字母>/<包>/<版本>/` 内），软件级文件必然命中该闸（本机复跑
  `run_preflight(., "origin/main", "HEAD")` 的唯一 finding 即此三文件），属该闸的**假阳性**
  ——PF9 的设立目的是防 "No packages to build"，而带版本目录一起提交不会触发该 CI 报错；
  `submission.py` 自身的 W2 原子性校验亦显式放行软件级文件
  （`f.startswith(software_archive_root) and f.count("/") <= 3`）。
- 处置（与 `archives/a/anacron/2.3`、`archives/g/guile/2.2.7.2`、`archives/d/das-watchdog/0.9.0`
  等先例一致）：保留软件级文件于提交内，创建 PR 时使用文档化逃生口
  `OHC_PREFLIGHT=0`（等价 `--no-preflight`），并在 PR 正文披露本项；PF1–PF8 已逐项人工复核
  （单包/无归档件/test 实质执行/依赖全部已发布/补丁无平台宏/无共享前缀注入/官方 https 源/
  settings 与 commands.json schema 合规）。
- 另：`packaging/` 已由 `ARCHIVE-SPEC v3.0 §2.3` 废弃，但 `submission.py:_check_packaging_present`
  对 built 状态仍要求 `packaging/*.tar.gz`；本目录下按该陈旧自检生成了
  `packaging/xdrawchem-1.11.1-ohos-aarch64.tar.gz`（内容为该 conan 包实体，`.gitignore` 已忽略、
  不入 PR、不上传制品仓），仅供本地 submit 自检通过。
---

**编译结束**: 2026-10-16 21:03
**最终状态**: built
