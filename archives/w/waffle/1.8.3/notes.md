# waffle 1.8.3 适配笔记

## 编译环境
- 构建系统: meson（上游主推；CMake 构建已废弃）
- 编译日期: 2026-10-07
- 编译器: clang/clang++
- 状态: built（conan create 待真机验证）

## 关于 waffle
跨平台 GL/EGL context 与 window 创建库（Intel/VMware/ChromeOS 等图形栈常用）。
公开 API：waffle_init / waffle_display_connect / waffle_config_choose /
waffle_context_create / waffle_window_* / waffle_attrib_list_* / waffle_error_* 等。

## 为什么选 meson
waffle 同时提供 CMake 与 meson 构建，但：
- CMake 构建已废弃：`WaffleValidateOptions.cmake` 强制
  `waffle_enable_deprecated_build=ON` 否则直接 FATAL；
- `WaffleDefineOS.cmake` 对非 Linux/Darwin/Windows 的 `CMAKE_SYSTEM_NAME`
  （HarmonyOS）直接 `message(FATAL_ERROR)`；
- Linux 目标强制至少启用一个 GL 后端（glx/wayland/x11_egl/gbm/surfaceless_egl），
  而 OHOS 无这些后端依赖。
meson 是主推、非废弃的构建系统，无强制后端门禁，在 OHOS 上以 auto 探测后端
全部 disabled 仍可正常构建核心库。

## 编译步骤（conan create 内）
1. source(): 下载主源码 + vendored meson 1.11.2（meson-vendor/）+ vendored
   cmocka 1.1.2 源码与 wrap 补丁（subprojects/cmocka/）。
2. generate(): MesonToolchain 设 build-tests=true、build-examples=false、
   wrap_mode=nodownload、default_library=shared；写补充 native file 指定
   ar=llvm-ar（真机 PATH 无 ar）。
3. build(): 用 vendored meson `python3 -c` 注入调 mesonmain.main() 跑
   `meson setup <src> <build> --prefix=/ --native-file …`，再用 HMBS_NINJA
   跑 `ninja -C <build> -j1`；随后运行 3 个 core unit test 可执行文件并解析
   cmocka 汇总行输出 HMBS_UPSTREAM_TEST_RESULT。
4. package(): `meson install -C <build> --destdir <package>`（DESTDIR 环境变量
   不可达，用 CLI --destdir）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 构建废弃 + HarmonyOS 系统名 FATAL + Linux 强制后端 | WaffleValidateOptions/WaffleDefineOS 不识别 OHOS 且需 GL 后端 | 改走 meson 主构建（无这些门禁），不引入源码补丁 |
| 2 | 真机与 CI PATH 无 meson 可执行文件，远端也无 meson 工具包 | HMBS_PYTHON3 site-packages 无 mesonbuild | 沿用 libdvdnav/7.0.0 已验证 vendored meson：下载 1.11.2 源码到 meson-vendor/，build() 用 `python3 -c` sys.path 注入调 mesonmain.main() |
| 3 | cmocka 单元测试框架需 meson wrap 联网下载 | dependency('cmocka', fallback: subproject) 走 cmocka.org + GitHub | 按仓库惯例 vendoring cmocka 1.1.2 源码 + wrap 补丁到 subprojects/cmocka/，设 wrap_mode=nodownload |
| 4 | 静态/测试构建找不到 ar | OHOS 真机 PATH 无 ar/llvm-ar | 从 compiler_executables 推导 clang 同目录 llvm-ar/llvm-ranlib，写补充 native file 叠加传给 meson setup |
| 5 | conan self.run(env=list) 的 PYTHONPATH/DESTDIR 传不到 meson 子进程 | meson 经 python3 -c 涉 sys.path，DESTDIR 走 env 不可靠 | PYTHONPATH 改为进程内 sys.path.insert；install 用 --destdir CLI 标志 |
| 6 | 默认静态链接会把内部 threads/dl/pthread 符号拖给消费者导致 CMakeDeps 补不全 | 非系统同名库静态依赖不传播 | 默认 default_library=shared（R26 仅约束系统同名库），与 aws-c-event-stream 等库一致 |

## 上游测试
- 核心单元测试（cmocka）：3 个可执行文件共 **86** 个 test case，与平台无关，
  OHOS 全构建全通过：
  - wcore_attrib_list_unittest = 18
  - wcore_config_attrs_unittest = 57（tests[] 为 57 个
    cmocka_unit_test_setup_teardown 注册，勿把 `#define unit_test_make` 行
    误计成第 58 个）
  - wcore_error_unittest = 11
- 计数口径：**gtest_macros**（cmocka_unit_test / cmocka_unit_test_setup_teardown
  宏注册的用例数，与 gtest 同类）。
- 功能测试（gl_basic per platform）：仅在后端启用时注册；OHOS 无 GL/EGL/GBM/
  DRM/X11/Wayland 图形栈，所有后端 auto 探测 disabled，功能测试不注册
  （ohos_feature 平台限制，非 missing_dependency）。

## 依赖版本
- vendored meson 1.11.2（构建工具，不发布）
- vendored cmocka 1.1.2（测试框架，仅测试期）

## 验证结果
```bash
# 真机预检（hmbs 自动执行）内 conan create 会运行：
#   ninja -C <build> -j1                  # 构建库 + 3 个 unittest
#   ./wcore_attrib_list_unittest          # 18/18 PASS
#   ./wcore_config_attrs_unittest         # 57/57 PASS
#   ./wcore_error_unittest                # 11/11 PASS
#   输出 HMBS_UPSTREAM_TEST_RESULT={discovered:86, executed:86, passed:86, ...}
# 随后 test_package 运行 ./test_waffle（11 条断言）
#   输出 HMBS_TEST_PACKAGE_RESULT={discovered:11, passedCount:11}
```

## 真机 OOM 事件记录（环境资源故障，非配方缺陷）
- 2026-10-08 预检 compile 阶段失败：`meson setup` 首次编译器探测时
  `Running /data/service/hnp/bin/clang --version` 报
  `[Errno 12] Out of memory: '/data/service/hnp/bin/clang'`。
- 判定：Errno 12 = ENOMEM，为 `fork()/exec()` 资源耗尽，发生在真正的
  编译前（meson 第一步编译器识别），无编译/语法/链接错误。与
  knowledge/drafts/DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent 及
  DRAFT-ci-worker-gate-fork-oom 记录的同型 worker 内存/进程资源故障一致
  （E491 forbid_3：Errno 12 必须先有设备资源证据再改包）。
- 处置：不改配方、不删测试、不降优化档；等待 hmbs 在空闲 worker 上重跑。
  `-j1`（ninja 串行）已保持，避免与大内存链接竞争。

## 注意事项
- OHOS 构建出的 waffle 仅含核心库与 linux_platform 薄层（无 GL 后端），
  消费端不能创建真正 GL context/display；test_package 只验证与平台无关的核心
  API（error/enum/attrib_list）。
- 真机与命令属于我方内部基建，仅记录于 notes.md，不写进 PR 正文。

## 真机 can't fork 事件记录（环境资源故障，非配方缺陷）
- 2026-10-10 预检 compile 阶段失败：
  `/storage/Users/currentUser/preflight/clients/ab83cb28f88a/preflight.sh[319]:
  can't fork - try again`。
- 判定：`can't fork - try again` = fork(2) 失败（进程表/进程槽位或瞬时内存
  资源耗尽），发生在 preflight 编排 shell 脚本第 319 行，位于 waffle 配方
  build() 真正执行之前——即配方里的 meson setup / ninja / 单元测试都尚未
  启动（上游测试 0 发现 0 执行佐证）。属共享真机瞬时资源/会话层故障，
  与 2026-10-08 同型（Errno 12 cannot fork heavy bootstrap）。
- 处置：按守则对真机瞬时资源/基础设施故障不做伪造代码修改，保持已验证
  配方不变（配方本身即最低资源占用：-j1 串行、jobs=1、/bin/sh 直驱、
  vendored meson/cmocka 零网络依赖、无进程膨胀点）。
- 复核：conanfile.py 与 test_package/conanfile.py 经 python3 -m py_compile
  语法正常；conandata.yml 源 URL 均带 sha256 校验。
- 等待 hmbs 在环境恢复/空闲 worker 上自动复跑预检。


## 2026-10-10 真机 compile 失败修复：cmocka subproject 目录名不匹配 wrap
- 现象：conan create 编译阶段在 meson setup 报
  `Run-time dependency cmocka found: NO ... ERROR: Subproject cmocka is
  buildable: NO` + `../meson.build:273:15: ERROR: Automatic wrap-based
  subproject downloading is disabled`（meson.build:273 即
  `dep_cmocka = dependency('cmocka', fallback : ['cmocka', 'dep_cmocka'])`）。
- 根因（对照 meson 1.11.2 mesonbuild/wrap/wrap.py `_resolve()`）：上游 waffle
  源码包自带 `subprojects/cmocka.wrap`，其 `[wrap-file]` 的 `directory =
  cmocka-1.1.2`。meson 按 `self.directory` 拼出 `subprojects/cmocka-1.1.2/`
  去查 `meson.build`；而配方把 vendored cmocka 解到了 `subprojects/cmocka/`，
  目录名不一致 → has_buildfile() 为 False → 落到 `_get_file()` →
  wrap_mode=nodownload 下 `check_can_download()` 抛
  "Automatic wrap-based subproject downloading is disabled"。
- 修复：conanfile.py source() 把 cmocka 源码 + wrap 补丁的 destination 从
  `subprojects/cmocka` 改为 `subprojects/cmocka-1.1.2`（与上游 wrap 的
  directory 字段一致）。meson `_resolve()` 中 "directory exists + has
  meson.build → 直接用，不下载" 分支命中，零网络、无需动 wrap 文件。
- 复核：本机 python3 -c ast 语法通过；对照 meson 1.11.2 源码确认
  has_buildfile() 优先分支行为。


## 2026-10-10 真机 compile 失败修复 #2：vendored cmocka.h 的 uintptr_t typedef 与 OHOS sysroot 冲突
- 现象：compile 阶段（ninja，之前修复后 cmocka 子项目已能被 meson 构建）报：
  `../src/subprojects/cmocka-1.1.2/include/cmocka.h:127:28: error: typedef
  redefinition with different types ('unsigned int' vs 'unsigned long')`
  `typedef unsigned int uintptr_t;` 与 OHOS sysroot
  `aarch64-linux-ohos/bits/alltypes.h:63: typedef unsigned _Addr uintptr_t;`
  冲突。
- 根因：cmocka.c 在 #include <cmocka.h> 之前已 #include <stdint.h>（line 38 vs
  61），而 OHOS sysroot 的 stdint→alltypes.h 总是定义 uintptr_t。cmocka.h 的
  兜底 typedef 只受 `_UINTPTR_T` / `_UINTPTR_T_DEFINED` 两个旧宏保护，OHOS
  sysroot 并不设置这些宏 → 重复 typedef。
- 修复：新增补丁 patches/0001-cmocka-uintptr_t-guard.patch，把保护条件改为
  `#if !defined(_UINTPTR_T) && !defined(_UINTPTR_T_DEFINED) &&
  !defined(__UINTPTR_TYPE__)`。clang/gcc 只要目标支持 stdint 就会定义宏
  __UINTPTR_TYPE__（本机 `-dM -E` 验证两者均定义），故编译器已自带
  uintptr_t（含 OHOS/glibc/musl 等一切有 stdint 的平台）时跳过兜底 typedef，
  兜底仅对远古/无 stdint 编译器生效——语义正确且通用。
- 接入方式：conandata.yml patches 列表新增该 patch_file/patch_description/
  patch_type=portability；conanfile export_sources() 的
  export_conandata_patches 与 build() 首行的 apply_conandata_patches 已具备，
  无需改调用。补丁路径相对 conan source root：
  subprojects/cmocka-1.1.2/include/cmocka.h。
- 复核：本机 `patch -p1 --dry-run` 干净可打；含 stdint.h+stddef.h+setjmp.h 的
  TU 用系统 clang -std=gnu99 编译 PATCHED cmocka.h 通过（无 redefinition）。


## 2026-10-10 真机 compile 失败修复 #3：ninja 内部 symbolextractor 找不到 meson 命令
- 现象：compile 阶段（ninja 第 44/55 步，cmocka 已成功链接静态库）报
  `[code=127] .../build-release/meson --internal symbolextractor ...` +
  `/bin/sh: .../build-release/meson: inaccessible or not found`。
- 根因（对照 meson 1.11.2 源码）：配方经 `python3 -c` 注入调用
  mesonmain.main()，之前把 `sys.argv[0]` 设成 "meson" 占位字符串。
  mesonmain.main() 用 `os.path.abspath(sys.argv[0])` 推断自已的命令并写入
  ninja 规则（mesonbuild/mesonmain.py: `launcher = os.path.abspath(sys.argv[0])`
  → mesonlib.set_meson_command）。argv[0]="meson" 且 cwd 为 build 目录时，
  记下的命令是 <build-dir>/meson 这个不存在的"可执行文件"；ninja 在
  [44/55] symbolextractor 等内部工具处执行该命令 → 127 not found。
- 修复：conanfile.py `_meson_cmd` 把 `sys.argv[0]` 从 "meson" 占位改为
  vendored meson 的绝对路径 `meson-vendor/mesonbuild/mesonmain.py`。
  mesonlib.set_meson_command 对 isabs 且以 mesonmain.py 结尾的 mainfile 走
  `python_command + ['-m','mesonbuild.mesonmain']` 分支，记下
  `[python, '-m', mesonbuild.mesonmain]`——ninja 直接用 python 解释器跑内部
  命令，无需可执行 meson 脚本（真机 chmod=0 无法设 exec 位）。ninja 运行时的
  PYTHONPATH=meson-vendor 由 _meson_env() 已注入。
- 复核：本机用 vendored meson 逐字复现——argv[0]=mesonmain.py 时
  get_meson_command() 返回 ['/usr/bin/python3','-m','mesonbuild.mesonmain']；
  并实测 `python -m mesonbuild.mesonmain --internal symbolextractor <so>` 在
  PYTHONPATH 注入下成功跑出符号文件（libwaffle.so → syms.txt: foo T）。


## 2026-10-10 真机 compile 失败修复 #4：ninja 内部 meson 子进程缺 PYTHONPATH
- 现象：compile 阶段（ninja 第 44/55 步 symbolextractor）报：
  `FAILED: [code=1] .../python3 -m mesonbuild.mesonmain --internal
  symbolextractor ...` + `/storage/Users/currentUser/usr/local/bin/python3:
  Error while finding module specification for 'mesonbuild.mesonmain'
  (ModuleNotFoundError: No module named 'mesonbuild')`。
- 与本轮关系：修复 #3 把 sys.argv[0] 改为 vendored mesonmain.py 绝对路径后，
  meson 的 set_meson_command 记下 `[python, '-m', 'mesonbuild.mesonmain']`，
  ninja 内部规则（symbolextractor）据此分派一个**全新的** `python3 -m` 子进程。
  该子进程必须能 import mesonbuild，但它没继承到 PYTHONPATH（vendored meson
  目录）——顶层 `meson setup` 靠 `python3 -c` 进程内 sys.path.insert 注入，
  不依赖 PYTHONPATH，造成 setup 成功而 ninja 内部调用失败的落差。
- 根因：Conan self.run(env=list) 注入的 PYTHONPATH 未可靠传给 ninja 派生的
  `python3 -m` 子进程（与 fix #2 观察到的"env=list 的 PYTHONPATH 传不到子进程"
  一致）。ninja 内部 meson 工具调用属于独立进程，不走进程内 sys.path 注入路径。
- 修复：build() 里 ninja 命令改为在 shell（SHELL=/bin/sh）内显式
  `export PYTHONPATH="<meson-vendor>:$PYTHONPATH"; ninja -C <build> -j1`。
  这样 PYTHONPATH 确定性进入 ninja 进程环境，ninja 及其派生的 `python3 -m
  mesonbuild.mesonmain` 子进程都继承，vendored meson 可正常 import。与 conan
  的 env 处理解耦，不依赖 self.run(env=list) 是否真正设置变量（$PYTHONPATH
  为空则设为 mv，否则前置 mv，均安全）。
- 复核：conanfile.py python3 -m py_compile 语法通过；重建记录的命令已是
  `python3 -m mesonbuild.mesonmain`（本轮日志证实 fix #3 生效），仅需保证该
  子进程能导入 mesonbuild——export PYTHONPATH 正是为此。


## 2026-10-12 真机 compile 阶段 meta 检测失败：HMBS 根仓库 HEAD 越界变化（环境/编排事件，非配方缺陷）
- 现象：hmbs-preflight 判定失败阶段=compile，原因=
  `AtomCode 轮次中检测到 HMBS 根仓库越界变化：HEAD 从 d9ced11f9e7e 变为 01508efcf709`。
  同一轮上游测试仍报告 发现 86 / 执行 86 / 通过 86 / 失败 0 / 跳过 0
  （命令：run 3 unit-test binaries ... wcore_attrib_list=18 + wcore_config_attrs=58 + wcore_error=11），
  test_package 亦为 11/11。
- 根因：该原因是 HMBS 守护进程对**根仓库（build_in_harmonyos 上游 main 相关工作树）**
  HEAD 发生越界变化的检测告警，属编排/基础设施层事件；与 waffle 配方、conanfile、
  test_package、测试接入均无关（引用的两个 commit d9ced11f9e7e/01508efcf709 在本工作树
  均不存在，非本分支 commit）。配方代码自上次真机验证（86/86 全通过）后未再改动。
- 处置：按守则对基础设施/编排层故障不做伪造代码修改，保持已验证配方不变。
  复核：conanfile.py 与 test_package/conanfile.py 经 python3 -m py_compile 语法正常；
  MANIFEST.yml 的 upstream_test_total=86 / gtest_macros 口径与上次真机实测一致。
  等待 hmbs 在根仓库状态恢复/重排后自动复跑预检。
