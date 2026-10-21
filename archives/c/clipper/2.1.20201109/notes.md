# clipper 2.1.20201109 适配笔记

## 软件识别
- **项目**: CCP4 clipper（晶体学计算库），Kevin Cowtan 开发
- **主页**: http://www.ysbl.york.ac.uk/~cowtan/clipper/
- **仓库**: https://ccp4forge.rc-harwell.ac.uk/ccp4/clipper
- **上游版本**: tag `2.1`（Debian 版本号 2.1.20201109 = 上游 tag 2.1）
- **语言**: C++17，纯 C++（无 Fortran 代码，尽管可选 --enable-fortran）
- **许可证**: GPL-2.0+
- **注意**: 与 Angus Johnson 的多边形裁剪库 Clipper2 完全不同

## 源码获取
- 上游仓库: ccp4forge.rc-harwell.ac.uk/ccp4/clipper
- Tag: 2.1
- 下载地址: https://ccp4forge.rc-harwell.ac.uk/ccp4/clipper/-/archive/2.1/clipper-2.1.tar.gz
- 文件结构:
  - CMakeLists.txt + cmake/source.cmake
  - clipper/{core,contrib,cns,phs,mmdb,ccp4,minimol,cif}/
  - config.h.cmakein

## 依赖
- **libccp4c** (libccp4/8.0.0) — CCP4 核心 C 库，输出 libccp4c.so + cmake-config
- **mmdb2** (mmdb/2.0.22) — 大分子坐标库，输出 libmmdb2.a
- **sfftw** (fftw/2.1.5) — FFTW2 单精度版 --enable-float --enable-type-prefix，输出 libsfftw.a + libsrfftw.a

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-15
- 编译器: clang/clang++ 15.0.4 (OHOS)

## 编译选项
- CMAKE_SYSTEM_NAME=Linux（OHOS 不可识别，fallback Linux）
- CMAKE_POLICY_VERSION_MINIMUM=3.5（CMake 4.x 兼容）
- BUILD_SHARED_LIBS=OFF（静态库）
- CMAKE_CXX_FLAGS="-DFFTW2_PREFIX_S"（强制使用 srfftw.h 单精度头文件）
- CMAKE_PREFIX_PATH 包含三个依赖的安装路径

## 源码修改
| # | 文件 | 问题 | 修改 |
|---|------|------|------|
| 1 | config.h.cmakein | CMakeLists.txt typo (FFTW2_DEFINTIONS 少 I) 导致宏未注入 | 添加 #define FFTW2_PREFIX_S |
| 2 | clipper/core/fftmap.cpp | fftw_real 类型在 sfftw.h 中被覆盖为 double | float* dummy = nullptr |
| 3 | clipper/core/fftmap_sparse.cpp | 同上 | float* dummy = nullptr |
| 4 | clipper/core/fftmap.cpp | 依赖仓库 fftw/2.1.5 为 double 构建，float 缓冲直传 double FFTW ABI 读垃圾写越界 | 变换调用点插入 double 精度临时缓冲转换层（0002 补丁） |
| 5 | clipper/core/fftmap_sparse.cpp | 同上（稠密 in-place 3D 与稀疏按行两条路径） | 同上（0002 补丁） |

### 0002 补丁根因与方案
- **根因**: 依赖仓库 fftw/2.1.5 是「s 前缀文件名的 double 构建」——sfftw.h 中 FFTW_ENABLE_FLOAT 未定义（`typedef double fftw_real`）、导出符号为无前缀 double（nm 实证 sfftw 符号数=0）。上游 autotools 的 SINGLE_FFTW2 检测（m4/fftw.m4，`float a; fftw_real *p = &a;` 链接测试）会拒绝该包，但 CMake 构建缺少该检测，导致 clipper 的 float 缓冲被 double FFTW 按 double 读写：谱数据全错 + 越界写 2 倍。
- **方案**: 保持 clipper::ffttype=float 与包 API/存储布局不变，在 fftmap.cpp（FFTmap_p1::fft_h_to_x/fft_x_to_h）与 fftmap_sparse.cpp（FFTmap_sparse_p1_hx::fft_h_to_x / FFTmap_sparse_p1_xh::fft_x_to_h）的全部变换调用点插入 double 精度临时缓冲转换层；clipper 的归一化约定（x_to_h 除以网格尺寸、h_to_x 无 post-scale）保持原样。
- **验证**: 独立 double 精度 DFT 参考实现证明稠密/稀疏两方向变换数值精确；上游 18 个 check_PROGRAMS 实跑（见 test_package/MANIFEST.yml），test.csh 的 5 个 stdin 用例输出与上游 test.log 参考输出数值等价，maketestdata 内嵌自测试 Test core OK / Test contrib OK。
- **关键经验**: Xmap::fft_from/fft_to 默认走 Sparse 后端（Xmap_base::default_type_ = Sparse，xmap.cpp:127），FFT 修复验证必须覆盖 FFTmap_sparse_p1_hx/xh，仅测 FFTmap_p1 不充分。

## 编译步骤
```bash
cmake -DCMAKE_SYSTEM_NAME=Linux -DBUILD_SHARED_LIBS=OFF \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DCMAKE_CXX_FLAGS="-DFFTW2_PREFIX_S" \
      -DCMAKE_PREFIX_PATH="libccp4;mmdb;fftw" ..
make -j1
make install DESTDIR=staging
```

## 编译产物
8 个静态库:
- libclipper-core.a, libclipper-contrib.a, libclipper-cns.a, libclipper-phs.a,
  libclipper-mmdb.a, libclipper-ccp4.a, libclipper-minimol.a, libclipper-cif.a
头文件: include/clipper/*.h, include/clipper/{core,contrib,cns,phs,mmdb,ccp4,minimol,cif}/*.h
pkg-config: lib/pkgconfig/clipper.pc

## 上游测试
上游测试体系 = examples/Makefile.am 的 18 个 check_PROGRAMS + test.csh 运行脚本 + test.log 参考输出
（automake 未定义 TESTS，make check 仅构建）。真实执行结果（详见 test_package/MANIFEST.yml）：
- 运行级通过 7 程序 10 次运行：rfltest(sg=1/146)、symtest(sg=1/19/210) 输出与上游 test.log
  数值等价（仅 libm 显示精度差异）；mtztest、sgtest(530 设置)、ccad、sktest、maketestdata
  （Test core OK / Test contrib OK）全部 exit 0
- 构建级验证 9（cmaplocal/diffmap/maptest/ffttest/cnstest/cns2mtz/sftest/phstest/ciftophs）：
  上游未分发其运行输入数据（全树仅 testfile.mtz），与上游 make check 验证级别一致
- 排除 2：ftndemo（OHOS 无 Fortran 编译器）、cctbxtest（cctbx 依赖不在仓库）

## 验证结果
- conan download mmdb/2.0.22 --only-recipe: RC=0
- conan download libccp4/8.0.0 --only-recipe: RC=0
- conan download fftw/2.1.5 --only-recipe: RC=0
- make -j1: RC=0, 8/8 静态库编译通过

## 状态: built (本地编译通过，待 conan-verify/finish 闭环)
---

**编译结束**: 2026-10-15 16:17
**最终状态**: built
