# atkmm 2.28.4 适配笔记

## 基本信息

- **上游**：https://gitlab.gnome.org/GNOME/atkmm（tag 2.28.4）
- **类型**：ATK 无障碍工具包的官方 C++ 绑定（GNOME mm 系）；gtkmm 3.24.x 的直接依赖
- **ABI**：atkmm-1.6（pkg-config 名 `atkmm-1.6`，产物 `libatkmm-1.6.so`）
- **构建系统**：meson
- **许可**：LGPL-2.1-or-later

## 依赖（上游 atkmm-2.28.4/meson.build 实测 L109/L112/L119/L122）

| 依赖 | 上游要求 | 仓内版本 | 满足 |
|---|---|---|---|
| atk | >= 2.12.0 | atk/2.38.0.1.1 | ✅ |
| glibmm-2.4 | >= 2.46.2 | glibmm/2.66.9（2.4 ABI 线） | ✅ |
| sigc++-2.0 | 随 glibmm-2.4 传递 | libsigc/2.10.8 | ✅ |
| mm-common | 仅 maintainer-mode 需要 | 不需要 | — |

**ABI 说明**：atkmm-1.6（本包）与 atkmm-2.36（既有 `atkmm/2.36.4`，glibmm-2.68 线）
ABI 不兼容且 pkg-config 名不同，二者作为**不同 conan 版本并存**；
gtkmm 3.24.11 要求 atkmm-1.6，故必须有本包。atk 选用 2.38.0.1.1 与
gtk/3.24.43 保持同一版本，避免 GTK3 依赖图出现双 atk。

## 适配要点

1. **maintainer-mode=false**：官方 tarball 是 `meson dist` 产物，生成绑定已在
   `untracked/` 预生成（解包后全量 415 个文件），不需要 mm-common/gmmproc/m4。
2. **build-documentation=false**：doxygen/dot/xsltproc 在 OHOS worker 缺失。
3. **wrap_mode=nodownload**：禁止 meson 拉取 subprojects wrap，依赖全部由
   Conan PkgConfigDeps 提供。
4. **gmmprocdir 变量注入**：上游 meson.build L122
   `glibmm_dep.get_variable(pkgconfig: 'gmmprocdir')` 在 maintainer-mode 分支之外
   **无条件执行**，而 glibmm/2.66.9 的 `glibmm-2.4.pc` 未定义该变量 →
   generate() 中向生成的 `glibmm-2.4.pc` 追加
   `gmmprocdir=${libdir}/glibmm-2.4/proc`。（pangomm-2.46.5 同款技法）
5. **extra_defs 库链接路径（本包首轮 G2 失败点）**：上游
   `codegen/extradefs/meson.build` L7 用
   `cpp_compiler.find_library('glibmm_generate_extra_defs-2.4')` 查找该库；它位于
   glibmm 包的 `lib/`（`~/.conan2/p/glibma1451e20554ba/p/lib/`）而不在编译器默认
   搜索路径，报错：
   `ERROR: C++ shared or static library 'glibmm_generate_extra_defs-2.4' not found`。
   修复：generate() 中把 glibmm 的 libdir 经 conf 注入
   `tools.build:sharedlinkflags` / `tools.build:exelinkflags`（`-L<libdir>`），
   使 MesonToolchain 写入 native 文件的 cpp_link_args
   （atkmm-2.36.4 / pangomm-2.46.5 同款技法）。修复后 G2 全绿。
6. **.so 签名**：原生 OHOS worker meson install 改写 rpath 后需 binary-sign-tool
   重签（E135，与 glibmm/pangomm 同款处理）。

## 上游测试情况（R51 三步法申报）

**1) 清点**（tarball 解包目录实测）：

```sh
$ find . -type f | wc -l          → 415
$ ls tests                        → No such file or directory
$ find . -maxdepth 2 -type d -name "test*"   → （无输出）
$ grep -rn "\btest(" --include=meson.build . | wc -l   → 0
```

**2) 运行**：注册测试数 0 → 无测试对象可运行，N′ = 0（非"没环境"，是上游确无测试）。
GNOME mm 系 tarball 不带 meson 测试，与 atkmm 2.36.4、pangomm 2.46.5/2.50.1 一致。

**3) 申报**：上游注册测试 **0** 项；通过率 **N/A（无测试可跑）**。

消费者验证由 `test_package/test.cpp` 承担（**13 项断言**）：`Atk::init()` 绑定初始化、
版本宏 3 项（2/28/4）、`Glib::wrap(AtkObject*)` 绑定包装非空、`set_name/get_name`
往返、`get_role()`、`Atk::StateSet` 工厂+状态增删查 5 项、`Atk::Relation`
工厂+类型往返 2 项。实测输出 `atkmm consumer test: PASS (13 checks)`。

## R40 适配完整性说明

atkmm 是**纯 C++ 绑定库**：由 gmmproc 生成的包装代码逐 API 映射 atk C 接口，
上游实现本身即全平台无关，不含平台条件编译分支、无平台后端、无设备访问路径。
故对 OHOS 而言不存在需替换的平台代码，"编译通过即适配完成"；
本包未加入任何 stub / `return 0` 占位实现（无 `#ifdef __OHOS__` 补丁），
非"空壳绕过"。

## 结果

- conan-verify：G0-G4 + L2/L4/L5 **全部通过**（reports/conan-verify-report.md）
- W3 本地 CI 模拟：**PASS**（`.ci-result.json` exit_code=0；reports/w3-local-ci.log）
- test_package：编译+链接+运行全通过（13/13 checks）
- W4 独立审计：**pass**（P0/P1/P2/P3 全 0；reports/audit-result.json）

## 结束标记

**最终状态**：适配完成 —— conan create 成功、test_package 13/13 通过、W3 本地 CI
模拟通过、W4 独立审计 pass，PR 已提交。编译结束。
