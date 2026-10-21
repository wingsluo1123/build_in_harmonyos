# Conan Verify Report — karchive 6.28.0

**Verdict**: PASS
**Reference**: `karchive/6.28.0@ohpcd/stable`
**Profile**: ohos-aarch64-full（真机 OHOS 6.0 aarch64，clang 15 / libc++ / cppstd=17）
**Date**: 2026-10-17

## G0: ✅ PASS
- 本包为 6.26.0.1（已合入）的增量升版，上游 6.28.0 仅提升 ECM 最低版本并
  调整 CMAKE_MODULE_PATH 写法，src/ 与 autotests/ 逐字节相同；已知风险条目
  （symlink 全域拒绝、KDEInstallDirs6 的 qtpaths 加载器路径、C++20 特性）
  的处置均已在配方内落实（见 notes.md「适配决策」）。

## G1: ✅ PASS
- ✅ name / version 声明（`karchive` / `6.28.0`）
- ✅ source() 方法（conandata.yml 提供 URL + sha256，镜像 URL 附理由注释）
- ✅ build() / package() / package_info() 方法
- ✅ 补丁应用调用（`apply_conandata_patches`，0001 C++17 兼容补丁）
- ✅ conandata.yml 完整（sources + patches 两段）
- ✅ test_package/ 存在，含 CMakeLists.txt、conanfile.py、test.cpp、MANIFEST.yml

## G2: ✅ PASS
- ✅ 真机 `conan create . -pr:h=ohos-aarch64-full -pr:b=ohos-aarch64-full
  --build="karchive/*" --user=ohpcd --channel=stable` 退出码 0
- 📄 真机构建日志 558 行，sha256 `14953e418972c9d5a5c95800d0f63ae4d5bbc195ca3aa3961847abc6fd065608`
  （平台规则禁止提交 conan-create.log，故不随档；关键行见下）
- ✅ 上游 CTest：`100% tests passed, 0 tests failed out of 3`（kfiltertest /
  klimitediodevicetest / kcompressiondevicetest）
- ✅ 消费者用例：`TEST SUMMARY: 4 passed, 0 failed`
- ⚠️ 说明（非阻塞）：karchivetest 直接全量驱动在该设备上因文件系统拒绝
  symlink(2)（上游 initTestCase 建 test3_symlink）按配方能力探测跳过并打印
  告警；symlink 可用的环境（CI 工位）会照常全量运行

## G3: ✅ PASS
- ✅ `lib/libKF6Archive.so`（5143104 B，ELF 64-bit LSB arm64），
  `lib/cmake/KF6Archive/` 与 `lib/pkgconfig/` 随档
- ✅ 无系统同名库冲突（R26；OHOS 系统内无 libKF6Archive）
- ✅ `lib/cmake/KF6Archive/KF6ArchiveConfigVersion.cmake` 中
  `PACKAGE_VERSION "6.28.0"` 与 recipe version 一致

## G4: ✅ PASS
- 包 ID `6dd5356c2d84a932438252879e0f79927cee0a3d`（OHOS 6.0 / armv8 /
  clang 15 / libc++ / cppstd 17 / Release / shared=True）

## L2: ⏭️ SKIP
- 无 bin/ 产物（纯库包，无 CLI），跳过 bin 冒烟

## L4: ✅ PASS
- 补丁在 pristine tarball 上 clean 应用（patch --dry-run 与实应用均已核验）

## L5: ✅ PASS
- `lib/` 有内容（见 G3），`include/` 14 个头文件
