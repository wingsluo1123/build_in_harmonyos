# ---------------------------------------------------------------------------
# xnnpack_project_include.cmake — OHOS/Conan glue for XNNPACK
# 位置: archives/x/xnnpack/0.0-git20241108.4ea82e5/xnnpack_project_include.cmake
#
# 通过标准 CMake 变量 CMAKE_PROJECT_XNNPACK_INCLUDE 在 XNNPACK 顶层
# project() 调用结束时被 include（主配方 generate() 传绝对路径）。
#
# 为什么需要它：XNNPACK 的 CMakeLists.txt 对每个依赖都写成
#     IF(NOT TARGET <dep>) ... IF(NOT XNNPACK_USE_SYSTEM_LIBS) 下载并
#     ADD_SUBDIRECTORY(...) ELSE() FIND_LIBRARY(<dep>/lib) ENDIF() ENDIF()
# 也就是说，只要在它检查之前就把同名 target 建好，XNNPACK 就会整段跳过。
# 而 XNNPACK_USE_SYSTEM_LIBS=ON 又会跳过顶部那一整块“配置期下载”
# （ExternalProject 直连 github.com/gitlab.arm.com，CI worker 网络不可达）。
# 两者结合 ⇒ configure 全离线，依赖来自 Conan 包 + vendor 源码树。
#
# 这里定义的 target 名字必须与 XNNPACK CMakeLists 里检查的完全一致：
#   cpuinfo / fxdiv / pthreadpool / kleidiai(关闭) / gtest
# ---------------------------------------------------------------------------

# ── cpuinfo / fxdiv：制品仓里的 Conan 包（已做 OHOS 适配）──────────────────
find_package(cpuinfo CONFIG REQUIRED)
find_package(fxdiv CONFIG REQUIRED)

# CMakeDeps 生成的 target 名带命名空间，XNNPACK 期望的是裸名。
add_library(cpuinfo INTERFACE)
target_link_libraries(cpuinfo INTERFACE cpuinfo::cpuinfo)

add_library(fxdiv INTERFACE)
target_link_libraries(fxdiv INTERFACE fxdiv::fxdiv)

# ── pthreadpool：vendor 源码，构建为静态库（见 conandata.yml 的说明）──────
# 上游默认值是 "default"（跟随 BUILD_SHARED_LIBS）；这里固定 static，使它
# 的对象在 XNNPACK 为 shared 时被整体链入 libXNNPACK.so，为 static 时以
# 独立的 libpthreadpool.a 形式随包安装并在 package_info 的组件里声明。
set(PTHREADPOOL_LIBRARY_TYPE "static" CACHE STRING "" FORCE)
set(PTHREADPOOL_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PTHREADPOOL_BUILD_BENCHMARKS OFF CACHE BOOL "" FORCE)
# pthreadpool 的 FXdiv 下载块判据是 IF(NOT DEFINED FXDIV_SOURCE_DIR)（不是
# target 检查），所以必须给它一个值才能保住“全离线”；上面已建好 fxdiv
# target，它随后的 IF(NOT TARGET fxdiv) 会把 ADD_SUBDIRECTORY 整段跳过，
# 因此这个路径只用于压掉下载分支，不会被真正读取。
set(FXDIV_SOURCE_DIR "${XNNPACK_FXDIV_SOURCE_DIR}" CACHE PATH "" FORCE)
add_subdirectory("${XNNPACK_PTHREADPOOL_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/pthreadpool")

# ── FP 收缩：必须关闭（OHOS/aarch64 上的数值正确性前提）────────────────────
# XNNPACK 的标量 f32 路径把 FMA 写成普通表达式：
#     src/xnnpack/simd/f32-scalar.h: xnn_fmadd_f32(a,b,c) { return (a*b)+c; }
# 而 f32-scalar.h **不定义** XNN_SIMD_HAS_NATIVE_FMA（只有 f32-neon.h /
# f32-avx2.h / f32-fma3.h 等架构头定义它）。于是 f32-vgelu-scalar-rational-12-10-div.c
# 里 `#if XNN_SIMD_HAS_NATIVE_FMA` 取 0 分支 ⇒ 用**未启用 FMA 的标定常数**
# （vmax_abs_x=5.1158981323，注释写明"该值是插值恰好返回 ±1.0f 的第一个浮点数"）。
# 但 aarch64 上 clang 默认 -ffp-contract=on，会把 `(a*b)+c` 收缩成 fmadd ⇒ 实际
# 用的是 FMA 算术、却按非 FMA 常数标定 ⇒ 在 clamp 点插值不再恰好返回 ±1.0f，
# 残余 ~3.6e-7 被 0.5*|x| 放大后超出 GELU 的绝对容差（10*FLT_EPSILON=1.192e-6）。
# 真机实测：`f32-vgelu-test` 73 条断言失败（y=-1.672e-6 vs y_ref=-0，容差 1.192e-6），
# 单文件加 -ffp-contract=off 重编后同一二进制 66/66 全过。
# x86/SSE2 基线没有 FMA 指令、不会收缩，所以上游 CI 看不到这个问题；aarch64 上
# 必须显式关闭收缩，才能让"未启用 FMA 的标定"与实际算术一致。
# 关闭后 NEON 等架构头里的真 FMA intrinsic 不受影响（intrinsic 不是表达式收缩）。
if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
  add_compile_options("$<$<COMPILE_LANGUAGE:C,CXX>:-ffp-contract=off>")
endif()

# ── googletest：vendor 源码，仅供 XNNPACK_BUILD_TESTS 使用 ────────────────
# XNNPACK 的测试段是 IF(NOT TARGET gtest) → FIND_PACKAGE(GTest REQUIRED)，
# 建好 gtest/gtest_main 及其 GTest:: 别名后即整段跳过（googletest 的 CMake
# 在 add_subdirectory 时会定义 GTest::gtest / GTest::gtest_main）。
# 版本 = 上游 cmake/DownloadGoogleTest.cmake 钉的同一 revision（1.15.2，见
# conandata.yml 的说明：1.14.0 会让 ±inf 断言假失败）。
# 注意 BUILD_GMOCK 必须保持 googletest 的默认 ON：XNNPACK 的部分测试目标
# （CMakeLists.txt:1735 的 *-test）显式链接 GTest::gmock，关掉会在 generate
# 阶段报 `Target "f32-vtanh-test" links to: GTest::gmock but the target was
# not found`（真机实测 2026-10-06）。
if(XNNPACK_OHOS_VENDOR_GTEST)
  set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
  add_subdirectory("${XNNPACK_GOOGLETEST_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/googletest")
endif()
