# rmap 1.2 适配笔记

## 编译环境
- 构建系统: autotools（上游 configure；配方采用 direct compiler driver）
- 编译日期: 2026-10-11
- 编译器: clang（OHOS SDK 26.0.0.18 / clang 15，aarch64-linux-ohos）
- 状态: published

## 编译步骤

上游 configure 面向宿主构建（autoconf 宏缺失、-lgd 探测不适合交叉），配方 build() 直接驱动编译器：

```bash
# 1) conan install 拉取 gd/2.3.3.2 工具链（CMakeDeps 提供 include/lib 路径）
# 2) build() 内编译驱动：
clang -DPACKAGE="rmap" -DVERSION="1.2" -DGD_GIF -I<src> -I<gd>/include -O2 -c main.c rmap.c
clang -I<src> -I<gd>/include -o rmap main.o rmap.o -L<gd>/lib -lgd -lm
# 3) 配方验证（8 门禁）
python3 $SKILL/scripts/ohc-run.py conan-verify rmap 1.2   # G1/G2/G3 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | main.c 报 `use of undeclared identifier 'PACKAGE'/'VERSION'` | 源码依赖 autoconf 生成的宏 | 编译参数补 `-DPACKAGE="rmap" -DVERSION="1.2"` |
| 2 | 链接报 `unable to find library -lpng/-ljpeg` | conan 制品 gd/2.3.3.2 未启用 PNG/JPEG 支持（nm 证实无 gdImagePng 符号，有 gdImageGif） | 去掉显式 `-lpng -ljpeg`，编译加 `-DGD_GIF` 走上游 GIF 输出分支（rmap.c 的 GD_GIF 优先路径） |
| 3 | 测试运行报 `Couldn't open rmap.colors` | CLI 运行需源码树数据文件（矢量地图+配色） | earth.rez/rmap.colors 打入包内 share/rmap，测试显式传 `--datafile/--colorfile` |
| 4 | W3 L0k 门禁失败 | 产物为 CLI 可执行文件，缺软件级 commands.json | 补 archives/r/rmap/commands.json（type=tool） |

## 源码修改

无补丁（patches/ 为空、源码零改动）。配方通过 exports_sources 声明空驱动（build() 直接驱动编译器，属配方资产）。

## 依赖版本

- `gd/2.3.3.2`（ohpcd 已发布；静态库 libgd.a，无 PNG/JPEG 特性）

## 验证结果

```bash
$ python3 $SKILL/scripts/ohc-run.py conan-verify rmap 1.2
✅ 配方验证通过: rmap 1.2 → 可标记 status: published
# G1 PASS / G2 PASS(conan create + test_package 实测渲染) / G3 PASS / L2·L4·L5 PASS
# 报告: archives/r/rmap/1.2/reports/conan-verify-report.md

# test_package 实测（G2 门禁内自动执行）
INFO: rendered GIF 320x160, 6xxxx bytes
PASS: rmap consumer test (render/geometry/determinism)
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/rmap` | CLI 可执行（OHOS aarch64 ELF，动态链接 musl） |
| `share/rmap/earth.rez` | 矢量地图数据（运行必需） |
| `share/rmap/rmap.colors` | 默认配色文件（运行必需） |

## 注意事项

- **GIF 而非 PNG**：conan 制品 gd 包未编译 PNG 支持，编译走 `-DGD_GIF`；GIF 为上游 rmap.c 原生优先支持的输出格式，非适配降级。
- **运行时数据**：rmap 启动即读 rmap.colors/earth.rez，部署时须保证 share/rmap 数据文件随行（包内已含）。
- 上游站点（sourceforge distfiles）已 404，源码经 FreeBSD distcache 权威镜像获取，sha256 与 FreshPorts distinfo 一致。

## 适配实测（2026-10-11）

- 依赖：gd/2.3.3.2（制品仓已发布）；gd 制品包无 PNG 支持（无 gdImagePng 符号，有 gdImageGif），编译加 `-DGD_GIF` 走 GIF 输出路径
- main.c 需 `-DPACKAGE="rmap" -DVERSION="1.2"`（autoconf 宏）
- 运行需源码树数据文件 earth.rez（矢量地图）+ rmap.colors（配色），已打入包内 share/rmap
- conan-verify：G1/G2/G3 PASS（test_package 渲染 320x160 GIF + 确定性断言通过）

---
**编译结束**: 2026-10-11 11:29
**最终状态**: published

## 人工审查整改记录（2026-10-12，PR #15292）

pc-pr-review 判 `VERDICT=FAIL`（13 条规则 12 条 PASS），命中两项：

- **rule1（PR 模板格式）**：PR 描述「验证结果」中该字段写作「鸿蒙特有测试通过率」，
  平台校验器按 `templates/积分赛事PR模板.md` 的字段名「**新增测试用例通过率**」取值 →
  取到 None → FAIL。整改：PR 正文按模板逐字对齐三字段——`编译状态：通过` /
  `上游测试用例通过率：0/0` / `新增测试用例通过率：1/1（100%）`，
  并补齐「适配后测试用例统计」的单元/集成行（0，不变），合计 1（+1）。
- **rule11（评审意见已解决）**：diff 评论「⚠ test_package 需复核」1 条未解决。
  整改：逐条复核 test_package 后四段式回复（被测对象/执行链/校验内容/复核修正）
  并标记 resolved。
- **rule6/rule7（复审前置）**：本次 push 后重新评论 `/ai review`（AI 检视需覆盖最新
  提交）与 `/rebuild`（CI 为评论触发型），由审查方对新 SHA 复判。

**本轮自查发现并修正的申报口径错误**：`test_package/MANIFEST.yml` 与 `manifest.yaml`
的鸿蒙特有测试 description 此前写作「PNG 签名/IHDR」，与实际实现不符——
`test_package/test_rmap.cpp` 校验的是 **GIF8 签名 + 逻辑屏幕描述符（宽高 320x160）**，
build 走 `-DGD_GIF`（gd 制品无 PNG 支持，见上「GIF 而非 PNG」节）。两份元数据文案
本次更正为 GIF 口径，消除申报与实测不一致。本轮无代码逻辑改动：test_package 源码、
conanfile.py、补丁（空）均未改动。
