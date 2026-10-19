# libdisplay-info

EDID (Extended Display Identification Data) and DisplayID parsing library.

## Description
纯 C 库，把显示器的 EDID/DisplayID 二进制块解析成结构化数据（厂商/型号、
时序、色度、HDR 静态元数据、CTA-861 扩展块等）。上游与 `di-edid-decode`
命令行工具同属一个 meson 工程，本归档只发**库**（`libdisplay-info.so`、
头文件、`libdisplay-info.pc`）；命令行工具由
[`libdisplay-info-tools`](../libdisplay-info-tools/README.md) 单独成包，
两包不共享任何文件（该工具包目前只有 0.3.0；0.4.0 的 CLI 归属需另行适配
`libdisplay-info-tools/0.4.0`，本包只发库、不发布 `bin/`）。

## Project URL
https://gitlab.freedesktop.org/emersion/libdisplay-info

## License
MIT

## HarmonyOS 适配说明

### 构建信息
- **版本**: 0.4.0（上游最新稳定版，wlroots 0.20.x DRM backend 要求 ≥ 0.4.0）
- **构建系统**: meson
- **编译器**: clang 15.0.4 (aarch64-linux-ohos)
- **依赖**: `hwdata/0.411`（构建期数据依赖，提供 `pnp.ids` 厂商 ID 表，
  数据被编进库中，运行时不需要）
- **补丁**: 2 个（`0001-memory-stream-portable.patch` 内存流可移植化、
  `0002-meson-test-harness-portable.patch` 测试 harness 夹具应用可移植化，见下）

### 适配要点
| 问题 | 根因 | 处理 |
|------|------|------|
| `di_info_get_make/model/serial` 返回 NULL，且调用方进程在退出时收到 SIGTRAP | 上游用 `open_memstream()` 收集字符串；本平台 C 库的内存流实现不可用——`fclose()` 返回 EBADF 并丢弃内容 | 补丁改为进程内自增长缓冲（`memory-stream.c`），不再依赖该 C 库设施 |
| `meson setup` 报 `File /usr/share/hwdata/pnp.ids does not exist` | 上游 `dependency('hwdata', native: true)` 未命中后回退到发行版路径 | 用制品仓已有的 `hwdata/0.411`，并在 `generate()` 里写一份带 `pkgdatadir` 的 `hwdata.pc`（conan 合成的 .pc 没有该变量） |
| meson 探测裸名编译器/归档器失败 | OHOS 沙箱无法按 PATH 执行裸命令名 | `[binaries]` 注入 c/cpp/ar/ranlib/strip 绝对路径 |
| 新构建的 `.so` 无法加载 | 鸿蒙要求 ELF 带 `.codesign` | `package()` 内 `binary-sign-tool` 自签名并用 `llvm-readelf` 校验唯一 `.codesign` |
| 上游 34 个 `decode-*` 测试集体失败 | harness 用 GNU 专属的 `patch <目标文件> <diff>`；本平台 toybox patch 未套用夹具差异 | 补丁 `0002` 改为 `patch -p0 -i`（头部路径改写为目标文件），GNU/toybox 通用 → 68/68 |

### 与 `libdisplay` 0.3.0 的关系
`archives/l/libdisplay/` 是同一个上游工程的另一条归档（包名 `libdisplay`，
0.3.0，用补丁内置 pnp.ids）。本包沿用上游/制品仓既有包名 `libdisplay-info`
（`libdisplay-info/0.3.0` 已在制品仓发布），0.4.0 为该包名的版本升级，
并改用制品仓的 `hwdata` 数据包替代"数据文件随配方携带"的旧做法。

### 使用方式
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libdisplay-info 0.4.0

export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig
cc your_program.c $(pkg-config --libs --cflags libdisplay-info) -o your_program
```

### 验证结果
- `conan create`（ohos-aarch64 profile）：通过，test_package 10 项断言全绿
- 上游测试：`meson test` **Ok: 68 / Fail: 0**（共 68 项 = 34 夹具 × 2 harness，全部通过；
  补丁 `0001` 修内存流后 `print-*` 34/34 通过，补丁 `0002` 把 harness 的 patch 调用
  改为可移植写法后 `decode-*` 34/34 通过；另以 `patch_ng` 独立复核 33/33 唯一夹具输出
  与参考逐字节一致，详见 `0.4.0/reports/test-report.md`）
