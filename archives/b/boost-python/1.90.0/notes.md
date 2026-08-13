# boost-python 1.90.0 适配笔记

## 定位

独立 Boost.Python 编译组件依赖包，作为 eigenpy 3.13.0（Issue #2008）的 R36 前置依赖。

- 上游：Boost 1.90.0（https://www.boost.org/doc/libs/1_90_0/libs/python/），BSD/BSL-1.0
- 归档：`archives/b/boost-python/1.90.0/`
- 分支：`feat/boost-python-1.90.0`
- 状态：built（未发布）

## 依赖关系

- `requires("boost/1.90.0.3")`：普通 Boost 头文件与已发布 OHOS AArch64 二进制（官方确认已发布 ohpcd）。
  boost/1.90.0.3 不提供 Boost.Python 专属头文件、libboost_python312.so 或 Boost::python312 —— 由本包补齐。

## 构建方案

### 为何不用 b2 / 官方 CMake

- b2 (Boost.Build) 与 OHOS 不兼容（E035/E099/E153），无法构建 Boost.Python 编译组件。
- Boost 官方 CMake 构建（BOOST_INCLUDE_LIBRARIES 含 python）依赖 `boost-1.90.0-cmake.tar.xz`
  （github release），CI/本机网络不可达；经典 `boost_1_90_0.tar.bz2` 无顶层 CMakeLists。

### 正式方案（conanfile.py build()）

- 源码：官方 `boost_1_90_0.tar.bz2`（SHA256 `49551aff...`，conandata.yml 校验）。
- 按官方 `libs/python/CMakeLists.txt` add_library 源文件清单直接编译：
  **27 个唯一核心源文件**（CMakeLists 29 行 src/ 引用，object_protocol.cpp 与 object_operators.cpp
  各重复一次；`grep -c 'src/'` = 35 = 29 + 6 numpy 条件块）。Boost.NumPy（6 文件）为可选，
  eigenpy 不依赖 `boost::python::numpy`，不编译。
- 编译参数：`-std=c++14 -fPIC -shared -O2 -DNDEBUG -DBOOST_PYTHON_DYN_LINK`，
  include = 源码根 + boost/1.90.0.3 头 + Python 3.12 dev 头；链接 libpython3.12.so；
  `-Wl,-soname,libboost_python312.so`。
- 输出：`lib/libboost_python312.so`，NEEDED 仅 `libpython3.12.so.1.0` / `libc++_shared.so` / `libc.so`
  （无 glibc / manylinux / libstdc++ 依赖，file 确认 aarch64 OHOS ELF）。
- Python ABI：cp312（`python_abi` option 进 package ID，防止跨 Python 版本复用）。

### 头文件安装

- Boost.Python 专属头位于官方源码树**顶层** `boost/python.hpp` 与 `boost/python/`
  （218 个 .hpp），`package()` 安装到 `include/boost/`。
- 不重复打包 boost/1.90.0.3 已提供的普通 Boost 头；专属头引用的 108 个普通 boost 头
  （config/mpl/preprocessor/iterator 等）全部由 boost/1.90.0.3 提供，经核对 0 缺失。
- 两包共装无文件冲突（1.90.0.3 无任何 boost/python* 文件与 libboost_python312.so）。

### Python 依赖

- 制品仓无独立 Python 3.12 开发包配方（python/*、cpython/* 均 0 条）；唯一 Python 系配方
  `cpython-tkinter/3.12.9` 不打包 dev 头/libpython，运行时 sysconfig 自发现。
- 本包采用同款自发现机制（sysconfig + /proc/self/maps + prefix find），不硬编码绝对路径；
  运行时 libpython3.12.so 由设备 Python 3.12.9 提供（NEEDED 为 libpython3.12.so.1.0）。

## CMake target

- `cmake_file_name = boost_python`，`cmake_target_name = boost_python::python312`，
  别名 `Boost::python312`（供 jrl-cmakemodules target_link_boost_python 消费）。
- `cpp_info.requires = ["boost::headers"]` 关联 boost/1.90.0.3 headers 组件。
- 消费者测试（test_package）：find_package(boost_python CONFIG) + 显式 find_package(Boost)，
  链接 boost_python::python312 与 Boost::headers；两包共装无 BoostConfig/组件/target/include 冲突。

## 验证结果

- conan create（干净构建）：exit=0；conan-verify：G0-G4 全过，exit=0。
- test_package：3 断言全过（add(2,3)==5、add(-1,1)==0、greet()=='hello-from-boost-python'）。
- W3 本地 CI 模拟：setup.sh + build_and_test.sh 通过（L0/L1/L4/L5 pass，L2 skip 无 bin/）。
- finish：built（未 published）。

## 已知限制

- 消费者需显式 `find_package(Boost CONFIG REQUIRED)`（传递依赖下 CMakeDeps 对 boost 的 include
  生成为空，本包测试中已显式声明规避；这是 CMakeDeps 传递依赖行为，非本包缺陷）。
## 与 eigenpy 集成结论（2026-08-11 实测）

- 实测：与 boost/1.90.0.3 共享 `cmake_file_name="Boost"` 时，Conan CMakeDeps 不会把
  boost-python 的组件并入 Boost config（eigenpy 的 `find_package(Boost COMPONENTS python312)`
  无法命中 python312）。因此本包采用独立 `cmake_file_name="boost_python"`。
- 消费者（含 eigenpy）需显式 `find_package(boost_python CONFIG REQUIRED)` 获得
  `boost_python::python312`（别名 `Boost::python312`），并显式 `find_package(Boost)` 获得
  普通头（Boost::headers）。eigenpy 侧可通过 CMAKE_PROJECT_INCLUDE 注入一行实现，不改上游源码。
- 已实测：eigenpy 3.13.0 真实 CMake 配置（注入 find_package(boost_python)）+ 完整构建通过，
  libeigenpy.so NEEDED 含 libboost_python312.so。
## OHOS ELF 签名（PR #5100 CI 修复，2026-08-12）

- OHOS dlopen 强制要求 ELF code signature：未签名的 `test_ext.so` 在 test_package 的
  Python import 阶段报 `ImportError: ... Permission denied`（CI 真实证据），本地 display-sign
  与签名后 import 实验证实根因。
- 修复：复用 boost/1.90.0.3 已验证的 OHOS 原子签名模式
  （`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`，
  临时副本 → 签名 → 恢复原权限 → 原子替换 → 清理）：
  - 包内共享库：主 conanfile.py `package()` 完成所有文件复制后，对 `libboost_python312.so` 签名；
  - 消费者扩展：test_package `test()` 在 `self.run()` 导入前，对 CMake 实际生成的
    `test_ext.so` 签名。
- 签名失败将导致 OHOS 构建/测试明确失败（`ConanInvalidConfiguration`），不静默忽略。
- 测试断言数量保持不变（add(2,3)==5、add(-1,1)==0、greet() 字符串，共 3 项）。
## 链接器适配（PR #5100 二次 CI 修复，2026-08-12）

- 根因：OHOS SDK 默认链接器 `ld.lld`（LLD 15.0.4）的 NEEDED 含 `libxml2.so.16`；
  CI 沙箱缺失该库，链接阶段报 `Error loading shared library libxml2.so.16: needed by lld`
  → `clang: linker command failed` → conan create exit=1（package()/签名/test 均未执行）。
- 对照实验：`ld.bfd`（binutils 2.45，`/data/service/hnp/bin/ld.bfd`）NEEDED 仅 `libc.so`，
  干净环境（env -i）下 `--version` 与最小 OHOS AArch64 共享库链接均成功；LD_LIBRARY_PATH 无污染。
- 修复：本包链接显式使用结构化解析的 `ld.bfd`：
  - 主配方 `build()`：clang++ 增加 `-fuse-ld=<解析到的 ld.bfd>`（仅本包构建，不写入
    cpp_info.sharedlinkflags，不传播下游）；
  - test_package `generate()`：CMakeToolchain 设置 `CMAKE_MODULE_LINKER_FLAGS` 与
    `CMAKE_SHARED_LINKER_FLAGS` = `-fuse-ld=<ld.bfd>`（test_ext.so 为 MODULE target，
    MODULE linker flag 真实生效）；
  - 解析顺序：compiler executable 目录 → `shutil.which("ld.bfd")` → `/data/service/hnp/bin`
    → binutils 2.45 目录；找不到抛 `ConanInvalidConfiguration`，不静默回退损坏的 lld。
- 签名修复保留：package() 最后签名 `libboost_python312.so`；test() 导入前签名 test_ext.so；
  签名后恢复权限；断言数量不变（3 项）。
- 边界：bfd 路径仅作为构建期 `-fuse-ld` 参数，不进入下游公开链接参数；未修改 ci/、scripts/、
  profile；未复制 libxml2 入包；未设置全局 LD_LIBRARY_PATH。
## OHOS dlopen 权限根因与 0755 策略（PR #5100 终审，2026-08-12）

- 根因：签名前/后 test_ext.so 与 libboost_python312.so 权限为 0770（owner/group 可读写执行，
  other 无任何权限）。CI 运行用户与文件 owner/group 不同时，dlopen 走 other 路径 → EACCES
  （`ImportError: ... Permission denied`）。
- 实测（本机 HMDFS）：HMDFS/SELinux 忽略 POSIX chmod（chmod 600→660、644→660、755→770、
  777→770，E046），且文件 owner 被映射为 20001006 与运行用户不同；本机运行用户属于
  group 1006（文件 gid），故本机 group 位可访问而 CI 用户不可。
- 修复：对最终可加载的 OHOS ELF 共享库统一使用确定性权限 **0o755**（不再采用
  `original_mode | 0o111`，该写法在 0770 下结果为 0771 且无法覆盖 other 位）。
  签名流程（copy2 → 删 .codesign → selfSign → chmod 0o755 → os.replace → chmod 0o755 →
  stat 验证严格等于 0755，否则抛 ConanInvalidConfiguration 失败）中，签名是最后一个
  ELF 内容变更步骤，chmod 不改变 ELF 内容。
- 两个文件（主配方 libboost_python312.so、test_package test_ext.so）应用相同规则；
  EXE/SHARED/MODULE 三处 ld.bfd 修复保留。
- 边界：本机 HMDFS 无法达成 0755（E046 平台限制）；远端 CI 路径同样位于
  /storage/Users/currentUser，不能假设 CI 中 chmod 会生效——0755 仅为 best-effort
  请求，签名有效性以 .codesign 段 + display-sign 为准，不因 HMDFS 返回 0770 判定失败。
## HMDFS 跨身份真实加载：TMPDIR 暂存方案（PR #5100 修复终版，2026-08-12）

- E046 已真实确认：HMDFS/SELinux 忽略 POSIX chmod（chmod 600→660、644→660、755→770、
  777→770），且文件 owner 被映射为 20001006 与运行用户不同；远端 CI 路径同样位于
  /storage/Users/currentUser，不能假设 CI 中 chmod 会生效。
- 结论：0755 仅为 best-effort 请求，不因 HMDFS 返回 0770 判定失败；签名有效性以
  .codesign 段 + display-sign self-sign 为准（不再做"最终 mode 必须等于 0755"的硬失败检查）。
- 真实运行方案：test_package test() 将当前产物暂存到本轮 TMPDIR 独立运行目录：
  1. tempfile.mkdtemp(dir=os.environ["TMPDIR"]) 创建 boostpy-run-* 目录（进程自己拥有）；
  2. 系统 cp 复制 test_ext.so、libboost_python312.so（取自 package_folder/lib）、
     consumer_test.py（不使用 shutil.copy2，其依赖 E046 下无效的 chmod）；
  3. 复制后逐项验证：ELF magic、SHA256 一致、.codesign 存在、display-sign self-sign、
     os.R_OK/os.X_OK；若 cp 后签名失效则按原子流程重新签名并再次 display-sign；
  4. PYTHONPATH / LD_LIBRARY_PATH 首位为运行目录（保留 conanrun 其余环境）；
  5. 从运行目录执行 consumer_test.py，输出 test_ext.__file__ 必须解析到 TMPDIR 运行目录；
  6. 真实执行 add(2,3)==5、add(-1,1)==0、greet() 3 项断言；
  7. finally 中清理运行目录。
- 验证结果（本机 conan create exit=0）：test_ext.__file__ =
  /storage/Users/currentUser/boostpy-run-mrorcq25/test_ext.so；3 断言全部通过；
  包内 libboost_python312.so：aarch64 ELF、NEEDED 仅 libpython3.12/libc++_shared/libc、
  .codesign 存在、display-sign self-sign。
## 原生（非 HMDFS）运行暂存目录选择（PR #5100 修复，2026-08-13）

- 偏离根因：CI 进程中 conan 运行环境会把 TMPDIR 覆盖为 $HOME/tmp（HMDFS，决定性证据：
  CI 日志 `make: jobserver mkfifo: /storage/Users/currentUser/tmp/...`），而进程原生 TMPDIR
  （CI 环境变量 `TMPDIR=/data/storage/el2/base/cache`，ext2 分区）才是非 HMDFS 目录。
  旧实现直接信任 `os.environ["TMPDIR"]`，导致 ELF 暂存落在 HMDFS，跨身份 dlopen EACCES
  （ctypes.CDLL(libboost_python312.so) Permission denied）。
- 修复：`_pick_native_base()` 按候选顺序探测真实可写/可读/可执行且非 HMDFS 的基座：
  1. `OHPC_NATIVE_TMPDIR` 环境变量（可选显式指定）；
  2. `/data/storage/el2/base/cache`（nuclei 使用的 ext2 cache）；
  3. `/data/storage/el2/base/haps/entry/files`（argo/kubo 使用的 ext2）；
  4. 当前 TMPDIR，仅当其真实路径不以 /storage/Users 开头。
  每候选执行真实探针：创建任务专属子目录 → 写读探针文件 → chmod 0755 →
  R_OK/X_OK 验证；第一个通过者即最终基座；全部失败则报 blocked，不回退 $HOME/tmp。
- 实测：本机与 CI 均命中 `/data/storage/el2/base/cache`；run_dir =
  /data/storage/el2/base/cache/boostpy-run-*；test_ext.__file__ 与 /proc/self/maps
  证明两个 ELF 均从该原生目录动态加载；3 项消费者断言全部通过。
- 边界：包内 libboost_python312.so 在 test_package 中只验证（ELF magic/.codesign/
  display-sign/SHA256），绝不重签；test_ext.so 由 test_package 签名；主 conanfile.py
  的构建与签名逻辑未改动。
---

**编译结束**: 2026-08-13 11:03
**最终状态**: built

## Python 解释器安全域（E212）与用户域解释器选择（PR #5100 修复，2026-08-13）

- E212 实证：HNP Python（/data/service/hnp/bin/python3.12）运行于 hnp_file 安全域，
  不能加载 /data/storage/el2/base 下 hishell_hap_data_file 标签的用户生成 .so——
  CI 中 ctypes.CDLL(libboost_python312.so) 报 Permission denied（与 Unix 权限、
  TMPDIR、.codesign 均无关；普通 chmod/TMPDIR 方案不能修复 HMMAC 标签拒绝）。
- 对照实验（本机，同一组已签名 .so、相同 native run_dir /data/storage/el2/base/cache）：
  - 用户域 Python（$HOME/usr/local/bin/python3，3.12.9，安全域 u:r:hishell_hap:s0）：
    ctypes.CDLL + import test_ext + 3 项断言全部通过（exit=0）；
  - HNP Python 本机不可用（仅 CI 环境），由 E212 知识条目与远端 CI 证据确认其限制。
- 修复：test_package 选择用户域 Python 3.12（_pick_test_python）：
  1. OHPC_TEST_PYTHON 环境变量显式覆盖；
  2. $HOME/usr/local/bin/python3 默认；
  校验存在/可执行/版本 3.12；禁止静默回退 /data/service/hnp/bin/python3.12。
  CMake Python3_EXECUTABLE 与 consumer_test 执行使用同一解释器；consumer_test.py
  输出 sys.executable 供 CI 审计；包内库仍只验证不重签。
