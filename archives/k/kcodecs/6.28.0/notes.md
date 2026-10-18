# kcodecs 6.28.0 notes

## Scope

KDE Frameworks 6.28.0 baseline of kcodecs (string/text codecs library,
`libKF6Codecs.so`), delivered as `kcodecs/6.28.0`. Depends on qtbase/6.11.1
(Qt6Core), ecm/6.28.0 (ECM build tool) and libiconv/1.17 (legacy charset
fallback).

## 6.26.0.1 → 6.28.0（本版差异）

| 项目 | 6.26.0.1（前版） | 6.28.0（本版） |
|---|---|---|
| 上游源码 | kcodecs-6.26.0.tar.xz（`ee1fe3bd…bcb4`） | kcodecs-6.28.0.tar.xz（`b0a9ae34…a4d8`，2,477,088 字节） |
| ecm | ecm/6.26.0 | ecm/6.28.0（6.28 源码 `find_package(ECM 6.28.0)`） |
| qtbase / libiconv | qtbase/6.11.1、libiconv/1.17 | 相同 |
| patches 0001/0002/0004/0005 | — | 与 6.26.0.1 逐字节一致 |
| patch 0003 | 适配 6.26.0 树 | 按 6.28.0 树重新生成（上游删除了 `<stdio.h>` include 与 `Q_OS_WIN` 块，命中原 hunk 上下文） |
| DT_SONAME 注入（`-Wl,-soname,`） | 已含 | 保留（配合纯名制品，见下） |
| **CMAKE_PLATFORM_NO_VERSIONED_SONAME** | 无 | **新增 = ON（设备 HMDFS 拒 symlink）** |

## Adaptations

Same adaptation set as the 6.18.0/6.26.0 recipes, plus the device symlink fix:

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during the Conan build;
  `BUILD_FUZZERS=OFF` keeps oss-fuzz helper targets out.
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` (new in 6.28.0): HMDFS (the device
  user volume) rejects `symlink()` with EPERM, so the versioned
  `libKF6Codecs.so.6` symlink chain CMake creates after linking fails the
  device build. Libraries are emitted under their plain name instead
  (kwidgetsaddons 6.28.0 / kcolorpicker / expat precedent).
- `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG = -Wl,-soname,` injected on OHOS:
  native builds stay in CMake's `Generic` platform module (no
  `Platform/HarmonyOS`), which has no soname rule, so without the flags the
  resulting `libKF6Codecs.so` would lack `DT_SONAME` (CI L5a) and consumers
  would record an absolute build-machine path in `DT_NEEDED` (L5c). Together
  with the point above, the library bakes a real `DT_SONAME=libKF6Codecs.so`
  under its plain name. Both variable flavors (`tc.variables` +
  `tc.cache_variables`) are set: cache variables reach
  `-DCMAKE_TOOLCHAIN_FILE` configures, plain variables cover preset-based
  ones.
- `ecm_install_po_files_as_qm(poqm)` disabled (patch 0001): the Qt Linguist
  tools component is not part of the OHOS qtbase package.
- libiconv fallback (patches 0002/0003): qtbase on OHOS is built without ICU,
  so `QStringDecoder` cannot decode some RFC2047 legacy charsets. The patches
  add an iconv-based decode fallback (`decodeWithIconv`) wired in via
  `KCODECS_ICONV_LIBRARY` when libiconv is present.
- ECM_MODULE_PATH set manually and `conan_cmakedeps_paths.cmake` written by the
  recipe because the CMakeDeps-generated ECMConfig.cmake does not propagate
  ECM_MODULE_PATH and qtbase uses `cmake_find_mode=none`.
- `/system/lib64` prepended to LD_LIBRARY_PATH for cmake/ctest runtime so the
  compatible `libc++_shared.so` wins over the sandbox one (kconfig 6.26.0 /
  bluez-qt 6.28.0 precedent).

## 上游测试适配（沿用 6.26.0 引入的各点，补丁逐字节一致）

1. `kencodingproberunittest` does not link `KF6::Codecs`, so
   `target_compile_features(KF6Codecs PUBLIC cxx_std_20)` is not propagated
   and it compiles with `-std=c++17`, breaking `std::span` usage in
   `nsCodingStateMachine.h`. Patch 0004 adds an explicit
   `target_compile_features(kencodingproberunittest PRIVATE cxx_std_20)`
   (CMake-only change, no test source touched).
2. `kcharsets.cpp` uses `std::string_view <=> std::string_view` which the OHOS
   libc++ (clang 15 toolchain) does not implement. Patch 0005 replaces it with
   `compare() <=> 0` (built-in integer spaceship), preserving the
   `std::strong_ordering` return type.
3. `parseEncodedWord`'s `maybeCharset` is a `QByteArrayView`; the iconv-fallback
   `conversionCharset` needs an explicit `QByteArray(maybeCharset)` conversion
   (patch 0003, regenerated for 6.28.0).

## Verification

- 上游 tarball SHA256 本地复核：
  `b0a9ae34b389c6460adad5323d21bb9e43638acb58da9685f8dc8d821c38a4d8`
  （2,477,088 字节）。conandata 列出官方源 + 南京大学镜像 + 阿里云镜像：
  download.kde.org 经 Mirrorbits 重定向，选中的镜像可能带损坏的 TLS 证书
  （设备网络实测 mirrors.bfsu.edu.cn 失败），三 URL 列法保证任一权威镜像先
  应答都落到同一 sha256 固定的官方 tarball。
- 五个补丁在 6.28.0 源码树上经 patch_ng 链测全部干净应用，产出树与目标树
  逐字节一致（patch 头为 `--- a/…` / `+++ b/…` 规范形态）。
- 设备 `conan-verify`（`scripts/ohc-run.py conan-verify kcodecs 6.28.0`，
  ohos-aarch64 profile，2026-10-17）：
  - 首轮（00:34–00:39）：G0/G1 通过；G2 在链接期失败 —
    `CMake Error: failed to create symbolic link '../bin/libKF6Codecs.so.6':
    Permission denied`（HMDFS 用户卷拒绝 `symlink()`）。修复 =
    `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`（kwidgetsaddons 6.28.0 同款首轮
    故障、同款修复）。
  - 二轮（00:42–00:46）：G0–G4、L2/L4/L5 全门禁 PASS。
  - 终轮（最终字节：test.cpp 注释与 conandata 头注更新后，00:52–00:55）：
    `VERIFY_RC=0`，全门禁 PASS（`conan-verify-report.md` 随档）。
  - 上游 CTest（conan create 内，BUILD_TESTING=ON）：**6/6 passed**
    （`base45test`、`codectest`、`kemailaddresstest`、`kcharsetstest`、
    `kencodingproberunittest`、`kencodingprobertest`）。
    `rfc2047test` 运行期排除（`ctest -E "^rfc2047test$"`）：其 "working-QP"
    行需要 ICU 提供的 `ISO-8859-15` 编码器，OHOS qtbase 无 ICU，KCodecs 回退
    System codec，属环境限制、非 kcodecs 回归（kconfig 6.26.0 排除清单先例）；
    用例仍编译（二进制链接成功）。
  - `test_package`：**1/1 passed**，且直接运行输出 PASS×3 — base64 往返、
    quoted-printable 往返、RFC2047 解码（真实 API 调用）。
  - 包 id：`546f25c40e62843f04e563647cb09d4d09d8b48c`。
- 制品 ELF 证据（设备 llvm-readelf）：`lib/libKF6Codecs.so` 为单文件（无版本化
  软链）；`DT_SONAME = libKF6Codecs.so`；`GNU_RELRO` 段存在；`GNU_STACK` RW
  （NX）；消费者 `test_kcodecs` 的 `DT_NEEDED = libKF6Codecs.so`（可重定位、
  无构建机绝对路径）。

---

**编译结束**: 2026-10-17 00:56
**最终状态**: built

## 对话记录

### 对话 #1 — 2026-10-17

- 目标：交付 `kcodecs/6.28.0`（KF6 6.28 闭包版本），分支 `feat/kcodecs-6.28.0`
  （= 卡面 taskBranch）。
- 配方自 6.26.0.1 继承：版本号三处（conanfile `version`、conandata patches
  键、manifest）+ ecm 升 6.28.0；补丁仅 0003 因上游上下文变化重新生成
  （regenerated via a/b 目录 + 逐处断言替换 + `diff -u --label`），其余四个
  逐字节沿用 6.26.0.1。
- 设备首轮命中 HMDFS symlink EPERM（G2 build 链接期），按 kwidgetsaddons
  6.28.0 先例以 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`（双变量形态）修复，
  二、三轮全绿（详见 Verification）。
- 离线检视 / MR / CI 记录：见下方追加条目（随流程推进补记）。
