# xsetroot 1.1.3 适配笔记

## 任务与结论

- 软件: xsetroot（X.Org 根窗口属性设置工具）
- 版本: 1.1.3（与上游 `PACKAGE_STRING` = "xsetroot 1.1.3" 一致）
- 分支: feat/xsetroot-1.1.3（R40/L0n）
- 构建系统: autotools（上游 tarball 自带预生成 `configure`，Autoconf 2.71）
- 依赖: libx11/6.4.0 + libxmu/1.3.1.1 + libxcursor/1.2.3 + xorgproto/2025.1
- 产物: bin/xsetroot + share/man/man1/xsetroot.1 + licenses/COPYING
- 结论: **built**。`conan create` 全绿；上游无测试套件，故按 TEST_QUALITY_SPEC
  「上游无测试」分支由 test_package 提供覆盖（4 用例 / 23 项检查，0 失败）。
- 语言预检（R47）: detected_language=c（autotools；源码 1 个 .c，主体 100%）

## 版本号与源码来源

上游 X.Org individual release（官方 x.org 发布源，R39/PF7 合规）：

```
https://www.x.org/releases/individual/app/xsetroot-1.1.3.tar.xz
sha256 6081b45a9eb4426e045d259d1e144b32417fb635e5b96aa90647365ac96638d1
```

## W0 依赖发布检查（R35 口径：conan install，不依赖 conan list）

| 依赖 | 结果 |
|---|---|
| libx11/6.4.0 | ✅ Install finished successfully |
| libxmu/1.3.1.1 | ✅（首次缺 libxext/6.4.0.1 binary，`--build=missing` 后成功并已入缓存） |
| libxcursor/1.2.3 | ✅ Install finished successfully |
| xorgproto/2025.1 | ✅ Install finished successfully |
| **xbitmaps** | ❌ **制品仓完全无此包**（`conan list xbitmaps/*` → no matching recipe references） |

### 依赖版本坑位记录

- 仓库 recipe 目录是 `archives/l/libxmu/1.3.1/`，但其 `conanfile.py` 与制品仓的
  实际可解析版本是 **`1.3.1.1`**。若按目录名写 `libxmu/1.3.1` 会直接
  `Unable to find 'libxmu/1.3.1' in remotes`。**以制品仓可用版本为准**（R35）。
- 该 recipe 目录内 `version = "1.3.1"` 与制品仓 `1.3.1.1` 不一致，属历史遗留；
  本包不依赖 `libxmu/1.3.1` 而使用 `1.3.1.1`。
- libxmu 的 recipe 已导出 `libXmuu.so`（`pkg_config_name` 生成 `xmuu.pc`），
  因此 xsetroot 的 `PKG_CHECK_MODULES(... xmuu ...)` 可满足（实测缓存内
  `lib/pkgconfig/xmuu.pc` 存在）。

## 探索阶段定位的真实问题

### 问题 1：xbitmaps 未发布（唯一真实缺口）

`xsetroot` 的 `configure.ac` 第 41 行：

```
PKG_CHECK_MODULES(XSETROOT, [xmuu x11 xbitmaps xcursor xproto >= 7.0.25])
```

但 OHOS 制品仓**没有任何 xbitmaps 版本**（`conan list xbitmaps/* -r=ohpcd` →
"There are no matching recipe references"）。

关键判断（源码级核验，非猜测）：

```
$ grep -n 'bitmap' xsetroot.c
47:#include "X11/bitmaps/gray"
```

即 xsetroot 对 xbitmaps 的**唯一**需求是 `#include <X11/bitmaps/gray>`——
一个**编译期数据文件引用，不是链接库**。

上游 xbitmaps-1.1.3 的包性质（实测）：

| 项 | 值 |
|---|---|
| `.c` / `.cc` / `.cpp` 源文件数 | **0** |
| `.h` 头文件数 | **0** |
| 内容 | 纯 XBM 数据文件 + `Makefile.am` / `configure.ac` / `xbitmaps.pc.in` |
| 安装布局 | `bitmapdir = $(includedir)/X11/bitmaps` |

**处置方案**：采用仓库中**已合并先例** `archives/m/motif/2.3.8` 的同一做法——
在配方内附带 canonical 数据文件 shim，并把其 include 根加入 `CPPFLAGS`：

- 本包 `files/X11/bitmaps/gray`（87 字节）
- 与上游 `xbitmaps-1.1.3/gray` **逐字节一致**：
  `sha256 b4df654f97ba9474c0d2b2f762c4db3d8613559447828a27f0bcfa2a0fcfc2aa`
  （本包 shim、上游 gray、motif 先例 shim 三者 sha256 相同）
- 注入方式：`toolchain.extra_cflags.append(f"-I{exports}/files")`

**为何不走「依赖项」路径**（诚实说明）：`xbitmaps` 有 **0 个 C/C++ 源文件**，
若作为独立包适配，R47 语言预检很可能判非 C/C++ 主体而直接终止为
`env_unsupported`，反而拿不到依赖附加 0.5 分。相比之下 motif 已验证的数据 shim
方案零代码风险、不引入新包，是更稳的选择。

### 问题 2：OHOS 沙箱无法运行 conftest（Autotools 交叉编译模式）

沿用仓库内 X.Org 包已验证的模式（`libxcursor` / `libxmu`）：以
`--host=aarch64-linux-ohos` 走**交叉编译模式**。若用原生 `--build == --host`
模式，autoconf 的 C-compiler works check 会尝试**运行** conftest 二进制，
而 OHOS 沙箱无法执行它。

### 问题 3：上游 configure 的 `umask 077`

上游 `configure` 在创建辅助目录时用 `umask 077`，在 OHOS worker 上会导致这些
目录对随后执行的 `make` 不可读。处置与 libxcursor 一致：在构建目录内生成一份
`configure` 副本，把 `umask 077` 替换为 `umask 022` 后执行（副本生成前先校验
`umask 077` 恰好出现 2 次，契约变化则显式报错，避免静默失效）。

### 问题 4：上游无测试套件（需走「上游无测试」分支）

核验证据：

```
$ grep -n 'TESTS\|check_PROGRAMS' Makefile.am   → 无输出
$ ls | grep -iE 'test|check'                    → 无 test/ check/ 目录
源码树仅 1 个 .c 源文件 + man page
```

故本包属 `TEST_QUALITY_SPEC` 的「上游无测试」分支：适配后由 `test_package/`
提供覆盖，并在 `test_package/MANIFEST.yml` 中 `upstream_tests_exist: false`
显式申报（避免被误判为漏装上游测试）。**未删除任何上游文件**。

## 补丁清单

**本包无补丁**（`patches: []`）。上游 `xsetroot.c` 零修改。

xbitmaps 缺口以**配方内置数据文件**（构建输入）解决，不是源码补丁，
故 `patches` 为空、`patches_applied: []`。R8 平台宏约束不适用（无补丁）。

## 配方关键决策

| 决策 | 理由 |
|---|---|
| `package_type = "application"` | 产物是命令行程序，不是库 |
| `cpp_info.bindirs=["bin"]` / `libdirs=[]` / `includedirs=[]` | 显式声明产物形态 |
| `exports_sources = "files/*"` | shim 数据文件必须随配方源码导出（`export_conandata_patches()` 不会复制它） |
| `validate()` 限定 Linux/OHOS（R32） | 非 Linux 家族不支持 |
| 依赖走 6.4.0 track | 与已合并的 libxmu/libxcursor/libxi 配方一致；1.8.13 track 无对应 binary |
| `--disable-docs` | X.Org `XORG_DEFAULT_OPTIONS` 默认开启文档构建，产物不需要 |
| 无 `options`（shared/fPIC） | 应用包无可链接产物，不适用 |

## 测试：上游无测试 → 补全消费者用例（R51 三步法）

### 1. 清点（附证据）

| 测试类型 | 数量 | 来源 |
|---|---|---|
| 上游单元测试 | **0** | `Makefile.am` 无 `TESTS` / `check_PROGRAMS`；无 test 目录 |
| 上游集成测试 | 0 | 上游无 |
| 上游其他测试 | 0 | 上游无 |

**上游 N = 0**。

### 2. 运行

上游**无测试可运行**（无可运行入口）。按 TEST_QUALITY_SPEC「上游无测试」分支
处理：**不伪造上游测试**，改为由 test_package 提供真实消费者覆盖。

### 3. 回填

见 PR 描述统计表（上游 0 → 适配后 4 用例，+4）。

### 补全的消费者用例（4 个具名用例 / 23 项检查）

| 用例 | 类型 | 内容 |
|---|---|---|
| HC-1 | consumer_e2e | 包内 `bin/xsetroot` 是 ELF64/EM_AARCH64 且可执行；未知选项时打印上游 usage 横幅并以状态 1 退出（对照 `xsetroot.c:73-96`） |
| HC-2 | consumer_e2e | 真实执行 `xsetroot -version`：上游在 `XOpenDisplay` **之前**处理该选项（`xsetroot.c:135-138`），打印 `PACKAGE_STRING` 并 exit 0 → **无 X 服务器也能真实断言程序可运行** |
| HC-3 | consumer_e2e | 执行 `xsetroot -help`，断言 usage 横幅列出上游完整选项集（-bitmap/-cursor/-cursor_name/-xcf/-mod/-gray/-solid/-name/-display/-def），证明功能全部编入而非空壳 |
| HC-4 | **harmony_specific** | 自解析包内 ELF 的 DT_NEEDED：非空且不含绝对路径（机器私有 Conan 缓存路径泄漏 = 制品不可跨机消费） |

### 统计口径：按「具名用例数」，不按断言数

PR 描述「适配后测试用例统计」表：单元测试 0→0、集成测试 0→0、
鸿蒙特有测试 0→4；合计 **0 → 4（+4）**。用例内部的 ok/FAIL 行（23 项）只是
各用例的检查项，不单独计数。

### 防空壳的结构性保障（R34 / L1e）

- `test_package/conanfile.py` 的 `test()` 用 `self.run` 真正执行包内二进制；
  `can_run()` 为假时**直接抛 AssertionError**（不允许静默跳过）。
- HC-2 是**真实运行**并断言 `PACKAGE_STRING`，非空壳打印。
- HC-3 断言上游完整选项面，证明功能已编入。
- L1e 负向预期：`mv` 走包内 `bin/` 后 HC-1.1 找不到可执行文件 → 立即失败。

### 测试器自带纯标准库 ELF 解析器（环境语义可迁移性）

`test_xsetroot.py` 自行解析 ELF（`_Elf` 类：节表 + 动态表 + DT_NEEDED），
**不调用 nm / readelf / strings**。原因有实际教训：同批次的 indi-beefocus 包
首轮 CI 因 `FileNotFoundError: 'nm'` 失败——CI worker 的 PATH
（`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:...`）不保证提供 binutils。
本包从一开始就避免该环境假设。

## 验证结果

```console
$ python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight xsetroot 1.1.3 --src <src>
  ✅ 语言匹配: task=cpp, detected=c — 继续适配主流程

$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
  ...
  == 4 cases, 0 failed ==
  == 23 checks, 0 failures ==
  RESULT: PASSED
  rc=0
```

| 项 | 结果 |
|---|---|
| `conan create` 退出码 | 0 |
| 上游测试 | 上游无测试套件（0 个）→ 无可运行入口，按规范走「上游无测试」分支 |
| 上游测试修改 | 0 处 |
| test_package 用例 | 4/4 通过 |
| test_package 检查项 | 23/23 通过 |
| 产物 | `bin/xsetroot`、`share/man/man1/xsetroot.1`、`licenses/COPYING` |

## 复现命令

```sh
cd archives/x/xsetroot/1.1.3
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 踩坑与注意事项

1. **libxmu 版本以制品仓为准**：目录名 `1.3.1` 但可解析版本是 `1.3.1.1`；
   写 `libxmu/1.3.1` 会 `Unable to find ... in remotes`。
2. **`conan list` 不能判 binary 是否存在**（R35）：`libxmu/1.3.1.1` 的 recipe
   存在但 binary 需 `--build=missing` 才成；必须用 `conan install` 判定。
3. **不要用 binutils 做测试断言**：CI worker 未必提供 nm/readelf/strings。
4. **X.Org app 必须交叉编译模式**：`--build == --host` 会尝试运行 conftest 而失败。

## 遗留与后续

- 无待办阻断项。
- `xbitmaps` 若日后被正式适配并发布到制品仓，可移除本包的 `files/` shim，
  改回 `self.requires("xbitmaps/1.1.3")`。
- 潜在路径 B 素材（本轮不提交，先保路径 A）：「X.Org app 系适配模式」
  （交叉编译模式 + umask 修正 + xbitmaps 数据 shim 三件套）具备提炼为通用
  新 SKILL 的形态，可与 indi-beefocus 的四件套一并沉淀。
