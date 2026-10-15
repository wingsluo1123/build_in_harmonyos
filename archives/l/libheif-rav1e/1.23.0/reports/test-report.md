# test-report — libheif-rav1e 1.23.0

- 软件: libheif-rav1e
- 版本: 1.23.0
- 交付面: 上游 libheif 1.23.0 树内 CMake MODULE 目标 `heif-rav1e` → `lib/libheif/libheif-rav1e.so`
- 平台: HarmonyOS PC（aarch64, OHOS 6.0, clang 15.0.4, conan 2.29.1 OHOS 适配版）
- 日期: 2026-09-27

## 1. 本地构建验证（W3）

```
$ conan create archives/l/libheif-rav1e/1.23.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable -c tools.build:jobs=4
```

- 内树 rav1e 0.7.1 构建产物（主配方 build() 日志）：
  - `librav1e.a` size=76268686（sha256 随构建目录变化：内嵌含绝对路径的 debuginfo，
    两次实测 `e367886a…` / `b7bedbfa…`；内容等价性由插件链接 + 运行期编码成功证明）
  - `rav1e.h` size=47349 sha256=9e2b7ea4f1026023819f7be17901070a39e83010240fc447b27b261f1186ef04
- CMake configure 以 `RAV1E_INCLUDE_DIR`/`RAV1E_LIBRARY` 钉住内树产物；构建目标 `heif heif-rav1e`。
- 包内 ELF 由 `binary-sign-tool` 装后重签（OHOS）。

## 2. 消费者测试（test_package，R34）

`conan create` 自动编译并运行 `test_libheif_rav1e`（链接打包产物 `libheif::libheif`，
`env="conanrun"`）。**15/15 项检查通过**：

```
libheif-rav1e 1.23.0 consumer check
  heif_get_version() = 1.23.0
  [ok]   host libheif version fingerprint is 1.23.0
  [ok]   heif_init() succeeds (host loads plugins)
  LIBHEIF_PLUGIN_PATH = <pkg>/lib/libheif
  [ok]   LIBHEIF_PLUGIN_PATH exported by this package (runenv_info)
  delivered plugin: <pkg>/lib/libheif/libheif-rav1e.so
  [ok]   delivered artifact <plugin_path>/libheif-rav1e.so exists and is non-empty
  have_encoder(AV1)=1 have_decoder(AV1)=0 have_encoder(HEVC)=0
  [ok]   heif_have_encoder_for_format(AV1)==1 (libheif-rav1e.so loaded and registered)
  [ok]   negative control: heif_have_decoder_for_format(AV1)==0 (no dav1d/aom in this package)
  [ok]   negative control: heif_have_encoder_for_format(HEVC)==0 (no x265 in this package)
  [ok]   heif_image_create(128x128 RGB)
  [ok]   heif_image_add_plane + heif_image_get_plane (interleaved RGB)
  [ok]   heif_context_alloc()
  [ok]   heif_context_get_encoder_for_format(AV1) returns the rav1e encoder
  heif_encoder_get_name() = Rav1e encoder v0.7.1
  [ok]   encoder is owned by rav1e (heif_encoder_get_name() contains 'rav1e')
  [ok]   heif_context_encode_image(AV1) through the rav1e plugin succeeds
  [ok]   encoded AVIF bitstream written to disk is non-empty
  [ok]   heif_deinit() then heif_init() again succeeds (reference-counted lifecycle)
RESULT: 15/15 checks passed
```

要点：宿主 `heif_init()` 运行时 `dlopen` 了交付的 `libheif-rav1e.so` 并注册 AV1 编码器
（`heif_have_encoder_for_format(AV1)==1`），编码器归属 rav1e（`heif_encoder_get_name()` =
`Rav1e encoder v0.7.1`），并真实编码一张 128x128 图进 rav1e 编码器、写出非空 AVIF。
这是**功能验证**，不是空壳（R34）。

## 3. 上游测试（R51 三步法第 2 步，HMBS 标记）

内树构建的 rav1e 0.7.1 在 test_package 阶段真跑（官方源重下、OHOS aarch64）：

```
$ cargo test --release --target aarch64-unknown-linux-ohos --workspace --tests --no-fail-fast
```

| 测试 target | 结果 |
|------------|------|
| ivf unittests | 3 passed / 0 failed / 0 ignored |
| rav1e lib unittests（含 quickcheck 属性测试展开） | 436 passed / 0 failed / 0 ignored |
| rav1e bin unittests | 0 tests |
| tests/binary.rs（CLI 集成，真实编码） | 10 passed / 0 failed / 0 ignored |
| tests/doctests.rs | 3 passed / 0 failed / 0 ignored |
| **合计** | **452 passed / 0 failed / 0 ignored（100%）** |

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "cargo-test",
  "discovered": 452, "executed": 452, "passed": 452, "failed": 0, "skipped": 0}
```

### 3.1 libheif 上游 CTest/Catch2 套件（真跑）

在独立的 testing-preset 测试构建（`<build>/upstream-tests`）里编译并运行上游 `tests/`：

```
$ ctest --output-on-failure          # 38 个可执行测试，100% tests passed
```

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "catch2+ctest",
  "unit": "test_case", "passed": 212, "failed": 0, "skipped": 0, "executed": 212}
```

| 项 | 数量 |
|----|------|
| 主 N（libheif Catch2 `TEST_CASE` 注册面） | 217 |
| 本配置编译出的 ctest 可执行文件 | 38 |
| **N′（真跑用例）** | **212**（PASS 212 / FAIL 0 / SKIP 0） |
| NOT_RUN | 5（2×上游 `#if 0` + 1×tiffdecode `#if` 守卫 + 2×zlib gated） |

开关与做法见 notes.md 6.2；逐可执行文件的 Catch2 汇总行见构建日志
（`ctest-upstream.log` / `upstream-tests-ledger.tsv`）。

## 4. 安全基线 / 产物检查

- 包内 `lib/libheif/libheif-rav1e.so`（+ VERSION/SOVERSION 软链）、`lib/libheif.so[.1]`、
  `lib/librav1e.a`、`include/rav1e.h`、`include/libheif/*.h`、`lib/pkgconfig/libheif.pc`、
  `lib/cmake/libheif/*` 均已生成。
- 插件 `DT_NEEDED` 为无斜杠的 `libheif.so.1`（因显式 `CMAKE_SYSTEM_NAME=Linux` 让宿主带
  SONAME），运行期由 `conanrun` 的 `LD_LIBRARY_PATH` 解析。
- 无 `__OHOS__` 平台宏注入（R8/PF5）；无源码补丁（`patches: {}`）。

## 5. 结论

`conan create` 端到端通过：内树 rav1e 构建 → 宿主 + 插件编译/链接 → 消费者功能测试
（15/15）→ 上游 rav1e cargo test（452/452）→ libheif 上游 CTest/Catch2 套件真跑
（N′=212，PASS 212 / FAIL 0 / SKIP 0，NOT_RUN 5）。`.ci-result.json` 由 `finish` W3 写入
exit_code=0。
