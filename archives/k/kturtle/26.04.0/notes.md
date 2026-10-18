# kturtle 26.04.0 适配笔记（OHOS PC aarch64）

## 基本信息

- 软件：kturtle 26.04.0（KDE Gear 教育应用，Qt Widgets 桌面程序，C++/CMake）
- 上游：https://download.kde.org/stable/release-service/26.04.0/src/kturtle-26.04.0.tar.xz
  （官方源被拒/镜像失败，改用 USTC 镜像下载，sha256 见 conandata.yml）
- 交付物：bin/kturtle（可执行）+ share/（desktop/knsrc/metainfo）→ R38：commands.json 已建（软件级）
- 模式：KDE CMake（ECM），KDE Gear 应用先例参考 archives/k/kwrited

## R51 上游测试清点（三步法申报）

| 项 | 结果 | 证据 |
|---|------|------|
| 上游测试目录 | **无** autotests/tests 目录 | `ls kturtle-26.04.0` 全树清点，仅 scripts/if-test.turtle（Turtle 演示脚本，非测试套件） |
| ctest 注册 | **0** | 顶层/src CMakeLists.txt 无 enable_testing/add_test/ecm_add_test/BUILD_TESTING 任何引用 |
| 上游运行 | N/A | 上游确无测试（KDE Gear 小型交互式教育应用惯例） |
| 适配后测试 | test_package 真实执行 bin/kturtle --help（offscreen QPA，加载全 Qt6/KF6 闭包 + KAboutData 用法输出断言），通过 | conan-verify G2/L2 日志（bg-67） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | KF6 发布件 DT_NEEDED 烙死绝对/相对路径 | CI 发布 worker 布局烙进二进制 | 绝对：默认缓存补齐路径（逐字节 rm+cp）；相对：test_package cwdroot 模式 |
| 2 | 发布库 dlopen Permission denied | **内容改写使 .codesign 签名失效**（HMDFS 加载期校验，R1） | 恢复原始字节（remove-c+重下/rm+cp），禁内容级修补 → 沉淀知识库拓展四件套 |
| 3 | conan 缓存 DB 与磁盘不一致（os.utime 报错） | 缓存清理 rm -rf 中断 | 受影响包 remove-c + conan download 重建 |
| 4 | CONAN_HOME 隔离后绝对 NEEDED 永远断链 | 隔离缓存脱离烙死路径 | 终版回归默认缓存 + 全量重下 29 包，verify 全绿 |
| 5 | qtbase 变体死墙 | 6.11.1.3 变体引发 KF 全量重建 | qtbase 钉 6.11.1（KF 二进制 package_id 命中实证），PrintSupport/DBus 源码可选化裁剪 |
| 6 | 幻影文件（-f 可见读失败）把好目标 rm 成空洞 | HMDFS 目录项与数据不一致 | 修复脚本强制「源先读验证再 rm+cp」（cpfrom） |

## 源码修改

patches/ 共 4 个（refresh-patch --auto 生成，conandata.yml 已登记）：
PrintSupport 与 DBus 可选化（顶层与 src CMakeLists.txt、mainwindow.cpp、
interpreter.cpp）——OHOS 无 CUPS/无桌面 DBus 会话，默认裁剪，可通过开关启用。

## 依赖版本

qtbase/6.11.1（全图归一）、ecm/6.26.0、kio/6.26.0、knewstuff/6.29.0.1、
kxmlgui/kconfigwidgets/ki18n/kiconthemes/kio 等 6.26.0 系、ktextwidgets/kcodecs/
kcompletion/sonnet 6.18.0 系、kpackage/6.26.0.1、qtsvg/6.11.1、zstd/1.5.7.1。
override 口径见 conanfile.py requirements() 注释（kcoreaddons/ki18n override-only、
qtsvg override-only）。

## 验证结果

```bash
# conan-verify（默认缓存，29 包全量重下后）
#   G0-G4 + L2/L4/L5 全过，G2 全新编译 kturtle + test_package 真实执行：
OK: bin/kturtle --help executed cleanly (Qt6/KF6 closure loaded, KAboutData usage printed)
# rc=0（bg-67）
# 知识库拓展四件套实测（archives/k/kturtle/26.04.0/knowledge-extension/）：
#   reproduce.sh rc=0 —— R1(签名)/R2(无签名三方式全PASS)/R3(EPERM) 矩阵全符合
#   detect-hmdfs-exec-integrity.sh 真缓存体检 A=63 B=0 C=9 D=27
#   repair-hmdfs-cache.sh fill → FILLED 3 → 复检 C=0（闭环）
```

## 注意事项

- **禁止对本机缓存内已签名发布件做内容级修补**（patchelf/python 字节替换）——
  会使 .codesign 失效，加载期 Permission denied；唯一出路是恢复原始字节。
  详见 knowledge-extension/README.md 与 knowledge/drafts/
  hmdfs-signed-elf-byte-rewrite-exec-denied.md（草稿）。
- HMDFS 禁原地覆盖（EPERM）→ rm 后再 cp；幻影文件需先读验证。
- 相对 NEEDED（`../../bin/…`）按进程 CWD 解析，不吃 LD_LIBRARY_PATH；
  test_package 的 cwdroot 方案已内置（三环境兼容：硬链 → /bin/cp → copyfile）。
- 依赖装默认缓存 `~/.cache/conan2`（发布件烙死路径所在），勿用隔离 CONAN_HOME。
---

**编译结束**: 2026-10-17 21:30
**最终状态**: published
