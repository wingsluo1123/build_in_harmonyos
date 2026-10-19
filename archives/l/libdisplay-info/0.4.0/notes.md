# libdisplay-info 0.4.0 适配笔记

## 编译环境
- 构建系统: meson（>= 0.57）
- 编译日期: 2026-10-16
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos)
- 状态: built（conan create 通过，本地 W3 门禁通过）
- 依赖: hwdata/0.411（构建期数据依赖，提供 pnp.ids）

## 编译步骤

```bash
# 1. 依赖检查（W0）：本包不需要库依赖，仅构建期数据包 hwdata
conan download hwdata/0.411 -r=ohpcd --only-recipe     # 命中

# 2. 手动编译（探索阶段，验证上游测试）
#    meson 用 native file：c/cpp/ar/ranlib/strip 全部绝对路径；hwdata.pc 由配方生成
meson setup build <src> --native-file ohos-native.ini -Dbuildtype=release -Dwrap_mode=nodownload
ninja -C build                                    # 28 targets 全部成功
meson test -C build                               # 上游测试，见下

# 3. Conan 配方验证（G2：干净源码 + test_package）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| `di_info_get_make/model/serial` 返回 NULL；调用方进程 `exit` 阶段收到 SIGTRAP（exit 133） | 上游用 `open_memstream()` 收集字符串（`memory-stream.c`、`info.c` 的 `encode_ascii_*`）；本平台 C 库内存流不可用：`fclose()` 返回 EBADF（-9）并丢弃缓冲区。可稳定复现的最小现象是 `open_memstream` + `fputs` + `fclose` → `fclose` 返回 -9/EBADF、`*sizeloc` 归零、缓冲区内容丢失（裸最小程序自身退出码 0）；进程级 SIGTRAP/exit 133 出现在补丁前上游 34 个 `print-*` 用例（日志 mtest.log）与带多次流操作的复现变体中，故适配判据以 EBADF + 内容丢失为准 | 补丁 `0001`：`memory-stream.c` 改为进程内自增长缓冲（`realloc`）并提供 `memory_stream_puts/printf/vprintf`；`log.c`/`info.c`/`include/log.h`/`include/edid.h`/`edid.c` 的 FILE* 汇改为该缓冲 |
| `di-edid-decode` 输出 `MHz ()`（DTD 尺寸丢失），上游 print/decode 参考输出对不上 | CLI 自己的 `join_str()`（`di-edid-decode/edid.c`）同样用 `open_memstream()` 拼字符串，同样被问题 1 破坏 → 返回空串 | 补丁 `0001` 同时把 `join_str()` 改为两遍制（先量长度再 `malloc` + 拷贝） |
| `meson setup` 报 `File /usr/share/hwdata/pnp.ids does not exist` | 上游 `dependency('hwdata', native: true)` 未命中后回退到发行版路径 `/usr/share/hwdata/pnp.ids`（OHOS 无此文件） | `requirements()` 用制品仓已有的 `hwdata/0.411`；`generate()` 里写 `hwdata.pc`（conan 的 PkgConfigDeps 生成物只有 prefix/bindir，没有 `pkgdatadir`，而 hwdata 包内自带的 .pc 把打包机绝对路径写死），`pkgdatadir` 指向 `self.dependencies["hwdata"].package_folder/share/hwdata` |
| `meson test` 的 34 个 `decode-*` 用例集体失败（差集恰为夹具 `.diff` 内容） | 上游 harness 用 GNU 专属的 `patch <目标文件> <diff>` 调用形式；本平台 `patch` 是 toybox 实现，既不吃位置参数形式，取的名字也与 GNU 相反（toybox 取 `+++`、GNU 取 `---`），夹具差异实际未被套用 | 补丁 `0002`：把 diff 头部路径改写为 `ref` 并改用 `patch -p0 -i`（GNU/toybox 通用），`.diff` 正确套用后 `meson test` 68/68 |
| `dependency('hwdata', native: true)` 在交叉构建下找不到 .pc | meson 的 `pkg_config_path` 是 **built-in option**（写在 `[built-in options]`），native:true 依赖在交叉构建里读的是 `build.pkg_config_path` | `MesonToolchain.build_pkg_config_path = generators_folder`（MesonToolchain 默认置 None） |
| `meson setup` 报 `Unknown compiler(s): clang` / `Unknown linker(s): llvm-ar` | OHOS 沙箱 hmmac 限制：python 子进程无法按 PATH 执行裸命令名，meson 探测裸名失败 | `conan_meson_native.ini` 的 `[binaries]` 注入 c/cpp/ar/ranlib/strip 绝对路径（`_inject_meson_archiver()`） |
| 新构建的 `.so` 无法被加载 | 鸿蒙要求 ELF 带 `.codesign` | `package()` 内 `binary-sign-tool -selfSign 1` 自签名，并用 `llvm-readelf -SW` 校验 `.codesign` 恰好一处 |
|------|------|----------|
> 上游 `test/edid-decode-check.sh` 用 GNU 形式的 `patch <ref> <diff>` 套用参考差异；
> 本平台 `patch` 为 toybox 实现（不支持目标文件位置参数，且取 `+++` 名而非 GNU 的 `---` 名），
> 夹具差异实际未被套用。补丁 `0002` 把调用改为 `patch -p0 -i`（头部路径改写为 `ref`），
> 两种实现都能正确套用 → `meson test` 从 36/68 变为 **68/68**。

## 源码修改

2 个补丁：

**`patches/0001-memory-stream-portable.patch`（8 个文件）**：

- `memory-stream.c` / `include/memory-stream.h`：内存流由 `open_memstream()` 改为进程内自增长缓冲，
  新增 `memory_stream_puts/printf/vprintf/is_empty`；
- `log.c` / `include/log.h`：`struct di_logger` 的输出汇由 `FILE *` 改为 `struct memory_stream *`；
- `info.c`：`encode_ascii_byte/string()` 及 `di_info_get_make/model/serial()` 改用缓冲接口，
  `_di_edid_parse()` 的失败信息汇随之改类型（`include/edid.h`、`edid.c`）；
- `di-edid-decode/edid.c`：`join_str()` 改为两遍制缓冲拼接。

**`patches/0002-meson-test-harness-portable.patch`（1 个文件）**：

- `test/edid-decode-check.sh`：把夹具差异的应用方式从 GNU 专属的
  `patch <目标文件> <diff>` 改为可移植的 `patch -p0 -i`，并在应用前把 diff 头部路径
  改写为目标文件 `ref`（否则 toybox 取 `+++` 名、GNU 取 `---` 名，行为不一致）。
  **只改调用方式，不改任何断言、夹具或参考输出**——同一份 `.diff`、同一份 `.ref`、
  同一个 `diff -u` 比较。

两个补丁都不含平台宏（无 `__OHOS__` / `#ifdef` 分支），是通用可移植性改写；
在内存流与 GNU patch 正常的平台上行为与上游一致。

**上游测试资产改动范围**：仅 `test/edid-decode-check.sh` 的 patch 调用一行（补丁 `0002`）；
`test/edid-print-check.sh` 与全部夹具（`.edid/.ref/.diff/.print`）**零改动**，断言与阈值未放宽。
补丁 `0001` 的对象是库源码（`memory-stream.c`、`info.c`、`log.c`、`include/*.h`）与
CLI 源码（`di-edid-decode/edid.c` 的 `join_str()`）；`di-edid-decode` 属于
`libdisplay-info-tools` 包，本包只发库。

## 依赖版本

- hwdata/0.411（`pnp.ids`，构建期数据依赖，编译进库）
- meson / ninja / pkg-config：平台自带（meson 1.12.1 / ninja 1.13.1 / pkg-config 0.29.2）
- 无其他库依赖（运行时仅 libc/libm）

## 上游测试（R51）

- **清点**：`test/meson.build` 注册 34 个 `test_cases` × 2 个 harness（`print-*`、`decode-*`）= **68 项**
  （`cta-timings` 在清单里出现两次；唯一 `.edid` 夹具 33 个，其中 31 个带 `.diff`）。
  上游无 Python/ctest 测试，全部为 meson + shell harness 的参考输出比对。
- **执行**：真机 `meson test -C build`（release，native file 与 CI profile 同源）。
- **结果**：`Ok: 68 / Fail: 0`（**全部通过**）。
- **过程**：补丁 `0001` 之前为 `0/68`（34 个 `print-*` 全部 SIGTRAP）；补丁 `0001` 后为
  `36/68`（`print-*` 34/34 通过），剩余 32 项 `decode-*` 失败原因单一且已定位——
  harness 的 `patch <目标文件> <diff>` 是 GNU 专属调用，本平台 toybox patch 未套用夹具；
  补丁 `0002` 改为 `patch -p0 -i`（头部路径改写为目标文件）后 **68/68**。
- **交叉复核**：另用 conan 自带 `patch_ng` 独立套用全部 `.diff` 并逐字节比对，
  33/33 个唯一夹具输出与参考一致（`cta-timings` 在 meson 清单中重复登记一次）。

## 验证结果

```bash
# conan create（干净源码，含 test_package）—— 通过
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing
...
ok: all-zero EDID rejected
ok: truncated EDID rejected
ok: valid EDID parsed
ok: di_info_get_edid() returned an EDID
ok: no failure message for a valid EDID
ok: manufacturer = 'ACR'
ok: product = 0x1616
ok: make = 'Acer Technologies'
ok: model = 'P1276'
ok: serial = 'JGG110015900'
test_libdisplay_info: all checks passed

# 上游测试（见上节）
meson test -C build   # Ok: 68 / Fail: 0（含补丁 0002 的 harness 调用可移植化）
```

## 注意事项

- 本包只发库（`lib/`、`include/`、`lib/pkgconfig/libdisplay-info.pc`）；
  同一 meson 工程构建出的 `bin/di-edid-decode` 在 `package()` 里被删除，
  该命令行工具由 `libdisplay-info-tools` 包单独提供（同一个文件不设两个属主；
该工具包当前版本为 0.3.0，0.4.0 的 CLI 需另行适配该包，本 PR 不涉及）。
- `hwdata` 是构建期数据依赖（数据被编进 `pnp-id-table.c`），运行时不需要它。
- `archives/l/libdisplay/`（0.3.0，包名 `libdisplay`）是同上游的另一条归档；
  本包沿用制品仓既有的 `libdisplay-info` 包名（0.3.0 → 0.4.0 版本升级），
  并取消了旧做法（数据文件随配方携带 + 联网下载）。
---

**编译结束**: 2026-10-16 16:33
**最终状态**: built
