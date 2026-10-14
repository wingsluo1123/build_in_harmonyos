# DRAFT-waffle-1.8.3-vendored-meson-wrap-directory-and-uintptr-guard

> vendored meson 子项目按 wrap 的 directory 字段对齐解压目录 + vendored 头文件 stdint typedef 守护宏（含 python 注入 meson 时 ninja 内部命令与 PYTHONPATH 适配）

## 问题特征（真实日志片段/标记）

waffle 1.8.3 真机 compile 阶段被门禁逐轮揪出的四处可复现根因与两处环境故障：

- **目录不匹配（nodownload 拒绝）**：
  `ERROR: Subproject cmocka is buildable: NO ... Automatic wrap-based subproject downloading is disabled`（meson.build:273 为 dependency('cmocka', fallback:['cmocka','dep_cmocka'])）
- **vendored 头文件 typedef 重复定义**：
  `../src/subprojects/cmocka-1.1.2/include/cmocka.h:127:28 error: typedef redefinition with different types ('unsigned int' vs 'unsigned long')`，与 OHOS sysroot `aarch64-linux-ohos/bits/alltypes.h:63 typedef unsigned _Addr uintptr_t;` 冲突
- **symbolextractor 命令路径不存在（code=127）**：
  `FAILED [code=127] 执行 '<build-dir>/meson --internal symbolextractor ...'`，`/bin/sh: <build-dir>/meson: inaccessible or not found`
- **ninja 内部 python 子进程缺 PYTHONPATH**：
  `python3 -m mesonbuild.mesonmain --internal symbolextractor` 报 `ModuleNotFoundError: No module named 'mesonbuild'`（顶部 `meson setup` 已成功，形成落差）
- **环境资源故障（区别于配方方案）**：
  `Running /data/service/hnp/bin/clang --version gave [Errno 12] Out of memory`、`preflight.sh[319]: can't fork - try again`，均发生在真正编译前，属 worker fork/exec 资源耗尽。

平台能力：`chmod=0`、`jobs=1`、`local_mktemp=0/1`、SHELL=/bin/sh，vendored 环境无可写入/可执行脚本自由度的限制。

## 根因

1. 上游 waffle-1.8.3.tar.xz 自带 `subprojects/cmocka.wrap`（`[wrap-file] directory=cmocka-1.1.2`）；meson `wrap.py::_resolve()` 按该字段在 `subprojects/<directory>/` 查 `meson.build`，而配方此前把 vendored cmocka 解到 `subprojects/cmocka/`，目录名不一致导致 `wrap_mode=nodownload` 下判定 `buildable: NO`。
2. cmocka.c 在 `#include<cmocka.h>` 之前已 `#include<stdint.h>`，cmocka.h 兜底 `typedef unsigned int uintptr_t;` 与 OHOS sysroot `alltypes.h` 已定义的 `uintptr_t` 冲突（`typedef redefinition`）。
3. python3 -c 注入调用 `mesonmain.main()` 时把 `sys.argv[0]` 设为 "meson" 占位符；`mesonmain.main()` 用 `os.path.abspath(sys.argv[0])` 推断自身命令写入 ninja 规则，得到不存在的 `<build-dir>/meson`。
4. meson `set_meson_command` 据此记录 `[python,'-m','mesonbuild.mesonmain']`，ninja 派生全新 python 子进程运行内部工具；顶层 `meson setup` 靠 python3 -c 进程内 sys.path 注入不依赖 PYTHONPATH，故该落差未暴露，直到内部规则执行时才出现 ModuleNotFoundError。
5. fork OOM / can't fork 属共享真机瞬时资源/会话层故障（守则已覆盖：E491 forbid_3 Errno 12 须先有设备资源证据再改包），与配方方案严格区分。

## 修复方案（rec）

1. **目录对齐**：conanfile.py `source()` 中把 vendored cmocka 源码与 wrap 补丁的 destination 从 `subprojects/cmocka` 改为 `subprojects/cmocka-1.1.2`。meson `_resolve()` 命中 `subprojects/cmocka-1.1.2/meson.build` 即直接用、不下载。
2. **typedef 守护宏**：新增 `patches/0001-cmocka-uintptr_t-guard.patch`，把 cmocka.h 保护条件改为 `#if !defined(_UINTPTR_T) && !defined(_UINTPTR_T_DEFINED) && !defined(__UINTPTR_TYPE__)`，并接入 conandata.yml `patches:`（conanfile 的 export/apply_conandata_patches 已就绪）。clang/gcc 在支持 stdint 的目标上都定义 `__UINTPTR_TYPE__`（`-dM` 已验证），故编译器已自带 `uintptr_t`（OHOS/glibc/musl）时语义正确且通用地跳过兜底 typedef。
3. **命令路径**：把 `_meson_cmd` 的 `sys.argv[0]` 改为 vendored meson 的绝对路径 `meson-vendor/mesonbuild/mesonmain.py`。按 `set_meson_command` 逻辑，此时记下 `[python, '-m', mesonbuild.mesonmain]`，ninja 直接用 python 解释器跑内部命令（无需可执行 meson 脚本，适配 chmod=0）。已复现 get_meson_command 返回 `['/usr/bin/python3','-m','mesonbuild.mesonmain']`，并实测 `python -m mesonbuild.mesonmain --internal symbolextractor <so>` 成功输出符号文件。
4. **PYTHONPATH 继承**：在 build() 的 ninja 命令串内显式 `export PYTHONPATH="<meson-vendor>:$PYTHONPATH"`（SHELL=/bin/sh），使 PYTHONPATH 确定性进入 ninja 进程并被其 `python3 -m` 子进程继承，与 conan 的 env 处理解耦。
5. **环境故障**：对 fork OOM / can't fork，按守则不伪造配方改动，-j1 串行、jobs=1、vendored 零网络依赖维持最低资源占用，仅在 notes.md 记录证据等待环境恢复复跑。

## 禁止策略

- 禁止以删除测试、伪造同类、改动 wrap 的 `directory` 字段来绕开 `nodownload` 门禁。
- 禁止把 vendored 头文件的兜底 typedef 直接删除破坏其它无 stdint 平台；必须用 `__UINTPTR_TYPE__` 等守护宏语义跳过。
- 禁止把 ninja 内部命令硬编码成假路径掩盖 ModuleNotFoundError；必须经 PYTHONPATH 注入使 `python3 -m mesonbuild.mesonmain` 可解析。
- 禁止把 fork OOM / can't fork 环境资源故障当配方缺陷改包（守则 E491 forbid_3：先有设备资源证据）。

## 与相近条目的边界（查重）

查重命中表全部条目均为相邻异因：编译器头缺失、编译器 ICE、autotools、golang、readonly-tmp 等。本条目则覆盖 meson wrap 目录对齐与 vendored 头文件全架构类型守护，并串起 `set_meson_command` 记录命令与 `PYTHONPATH` 子进程继承两条通用问题。增量成立：无既有条目覆盖 meson wrap 目录对齐与 vendored 头文件全架构 stdint typedef 守护及 python 注入下 ninja 子进程命令/PYTHONPATH 适配这一组合。

## 适用判断

当满足以下任一条件时直接采纳本条目方法：(a) 用 vendored meson 构建且源码包自带 `subprojects/*.wrap`；(b) vendored 头文件内含 stdint typedef 兜底且目标为 OHOS/glibc/musl sysroot；(c) 以 `python3 -c` 注入调用 meson 且平台 chmod=0/只读无可执行脚本；(d) ninja 内部规则报 `ModuleNotFoundError: No module named 'mesonbuild'` 或 `<build-dir>/meson: not found`。对 meson setup 阶段 `Errno 12`/`can't fork` 则判为环境资源故障，不套用配方方案。
