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
---

**编译结束**: 2026-08-12 08:51
**最终状态**: built
