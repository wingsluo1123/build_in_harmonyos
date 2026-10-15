# libgweather4 4.4.4 适配笔记

## 编译环境
- 构建系统: meson（上游 `meson.build`，`project('libgweather', 'c', ...)`）
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4（`/data/service/hnp/bin`，target aarch64-unknown-linux-ohos）
- 目标 profile: `ohos-aarch64`（os=OHOS, arch=armv8）
- 状态: 见文末「编译结束」段

## 上游身份与源码

| 项 | 值 |
|----|----|
| 上游仓库 | `https://gitlab.gnome.org/GNOME/libgweather` |
| GitHub 镜像 | `https://github.com/GNOME/libgweather`（tags API 本轮 403 rate-limit，改用 `git ls-remote --tags` 取证） |
| 版本存在性 | `refs/tags/4.4.4` 存在（tag obj `82bf8a14`，commit `b763fc4e`） |
| 官方 tarball | `https://download.gnome.org/sources/libgweather/4.4/libgweather-4.4.4.tar.xz`（HTTP 200，content-length 2843040，last-modified 2024-09-01） |
| sha256 | `7017677753cdf7d1fdc355e4bfcdb1eba8369793a8df24d241427a939cbf4283`（本机实算，64 位十六进制） |
| 语言实测 | R47 `lang-preflight`：`detected=c`，证据 `build_system=meson` + `manifest=meson.build project('libgweather', 'c',` + 源码统计 22 文件（c:20/bash:5/nodejs:1/python:1，主体 91%） |
| 许可 | GPL-2.0-or-later（meson project 声明；源码头 `SPDX-License-Identifier: LGPL-2.1-or-later`） |

## 依赖链（拓扑序，全部实测）

| 依赖 | meson 声明位置 | 硬/可选 | ohpcd 档案 | 制品仓发布 |
|------|---------------|--------|-----------|-----------|
| glib（gio-2.0 >= 2.68） | libgweather/meson.build:121 | 硬 | `archives/g/glib` 2.84/2.88 系列 | ✅ glib/2.84.0.1.1 等 8 个 |
| libsoup-3.0 >= 2.99.2 | libgweather/meson.build:118 | 硬 | `archives/l/libsoup3` 3.6.5-r1/r2/r3 | ✅ 3 个 |
| libxml-2.0 >= 2.6 | libgweather/meson.build:123 | 硬 | `archives/l/libxml2` 2.15.3/.1 | ✅ 2 个 |
| json-glib-1.0 | libgweather/meson.build:125 | 硬 | `archives/j/json-glib` 1.6.6/1.10.6/1.10.6.1 | ✅ 3 个 |
| **geocode-glib-2.0** | libgweather/meson.build:115 | **硬（上游）** | ❌ 无档案 | ❌ **0 配方** |
| meson >= 0.57（构建工具） | meson.build:5 | 硬 | `archives/m/meson` 1.5.1/1.11.0.1/1.11.1 | ✅ |
| ninja（构建工具） | — | 硬 | `archives/n/ninja` 1.12.1/1.13.2 | ✅ |

制品仓判定为双路取证：① `/api/registry` 全分页（offset 0..7100，total=7150，去重后 6316 条）geocode-glib **0 命中**；② 设备侧 `conan list "geocode-glib/*" -r=ohpcd` → `Found 0 pkg/version recipes`（R35 以 conan 侧为准）。

## 唯一硬阻塞：geocode-glib 未发布

上游 `libgweather/meson.build:115` 无条件 `dependency('geocode-glib-2.0')`——既没有 `required: false`，也没有对应的 `-D` 开关，meson setup 在本平台直接失败。

**§3.7 边界判定**：geocode-glib 在 ohpcd **既无 archives 档案也无发布**，但平台**已经存在依赖任务** `geocode-glib 3.26.4`（rawId=14281，activity=开源鸿蒙PC专项积分赛-依赖，status=claimed，claimer=`j669539`）。按 §3.7「先检索，别重复导入」，**不得重复导入**，属"缺发布"而非"缺任务"。

该参与者的在途 PR：**#12915**「【依赖项】feat(geocode-glib): 3.26.4 适配 HarmonyOS PC（libsoup3 flavour，libgweather 4.6.0 前置）」（全量扫 13782 个 PR 唯一命中；author=j669539，state=open，merged=0，ci_state=running，ai_review=completed，review_state=pending，updated_at=2026-09-27T11:25:32Z）。其合入前无法在配方里硬 requires。

## §3.6 可退化移植（本次采用方案）

geocode-glib 在 libgweather 中**只支撑一个公开 API**：`gweather_location_detect_nearest_city()`（反向地理编码）。源码实测引用面唯一：

- `gweather-location.c:13` `#include <geocode-glib/geocode-glib.h>`
- `gweather-location.c:773-819` `_got_place()` 静态回调
- `gweather-location.c:837-865` `gweather_location_detect_nearest_city()` 公开入口

全库 `grep -rn "geocode" --include=*.c --include=*.h` 仅命中该文件；`find_nearest_city` / `find_nearest_city_full`（按距离检索，纯 `kdtree` + `libxml`，**不依赖 geocode-glib**）保持完整可用。

### 补丁（`patches/0001-optional-geocode-glib.patch`）

1. `meson_options.txt`：新增 `option('geocode_glib', type: 'feature', value: 'auto')`——默认 auto，有 geocode-glib 的构建行为与上游完全一致。
2. `meson.build:50`：`find_installation('python3', modules: ['gi'])` → 加 `required: false`。`py` 变量全树未被引用（上游只是借它确认 python3 存在，`gen_locations_variant.py` 只用标准库），而 OHOS 的 python3 3.12.9 **无 PyGObject**（设备实测 `ModuleNotFoundError: No module named 'gi'`），不改则 meson setup 失败。
3. `libgweather/meson.build:106-134`：把 `geocode_glib_dep` 改成 `dependency(geocode_glib_pc_name, required: get_option('geocode_glib'))`，并按探测结果 `add_project_arguments('-DHAVE_GEOCODE_GLIB=0/1')`。
4. `libgweather/gweather-location.c`：include 与 `_got_place()`、`gweather_location_detect_nearest_city()` 体用 `HAVE_GEOCODE_GLIB` 守卫；无 geocode-glib 分支仍创建 GTask 并 `g_task_return_new_error(..., G_IO_ERROR_NOT_SUPPORTED, ...)`。

### 降级边界声明（AGENTS.md §3.6 强制）

**降级范围**：`gweather_location_detect_nearest_city()` / `..._finish()` 的**在线反向地理编码能力**。符号仍导出、异步契约仍成立、错误码明确为 `G_IO_ERROR_NOT_SUPPORTED`，消费者（如 libgnome-desktop）在调用时会得到干净的不支持错误，而不是链接失败或崩溃。

**未降级（完整保留）**：Locations.xml 地点库加载与解析、locations-db 变体生成、按名检索最近城市、按经纬度距离检索最近城市（含机场关联）、命名时区、时区对象序列化、月相/日出日落计算、GWeatherInfo 预报对象生命周期、metar/nws/metno/owm/iwin 各后端预报 XML 解析。

**恢复条件**：`geocode-glib/3.26.4` 在 ohpcd 发布后，把配方 `default_options` 的 `geocode_glib` 改为 `True` 并删掉补丁即可全量恢复；补丁本身用 `feature` 选项驱动，不需要再改 C 代码。

## 设备侧实测事实

| 项 | 实测值 |
|----|--------|
| conan | 2.29.1，remote `ohpcd` Enabled: True |
| clang | 15.0.4，`/data/service/hnp/bin` |
| ninja | 1.13.1，`/data/service/hnp/bin` |
| **meson** | **不在 PATH** → 配方改用 `tool_requires("meson/1.11.1")` + `tool_requires("ninja/1.13.2")` |
| python3 | 3.12.9，`$HOME/usr/local/bin/python3`，**无 `gi` 模块** |
| g-ir-scanner | 不存在 → `-Dintrospection=false` |
| profile | `ohos-aarch64` 存在 |

## 配方级适配要点

1. **`AR/AS/STRIP/NM/RANLIB` 环境变量污染**：CI worker 导出的是 `llvm-*` 名但这些不在 PATH 上，meson 探测后会 abort。在 `generate()` 里 `os.environ.pop()` 掉并用 `shutil.which()` 取真实工具（与 libsoup3/glib 配方同解法）。
2. **禁止 strip**：OHOS loader 校验 `.codesign` 段内嵌哈希与文件内容是否一致，strip 改写 `.so` 会导致哈希失配、dlopen 报 `Permission denied`（libsoup3/3.6.5-r3 踩过）。`tc.strip = None`。
3. **glib .pc 注入**：`PkgConfigDeps` 只生成 glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0/gthread-2.0.pc。libgweather 还要探测 `gmodule-2.0`，且 gnome module 工具（`glib-mkenums`、`glib-compile-schemas`、`glib-compile-resources`）需要从 glib 包 `bin/` 按绝对路径 pin 进 meson native file 的 `[binaries]`。
4. **`-lintl`**：`PkgConfigDeps` 生成的 `glib-2.0.pc` 的 Libs 缺 `-lintl`，而 libgweather 经 `glib/gi18n-lib.h` 的 i18n 宏直接引用 `g_libintl_bindtextdomain`，链接会报 undefined symbol。用 glib 包内官方 `glib-2.0.pc`（改 prefix）覆盖 generators 版本。同时剥掉 `Requires.private`（libpcre2-8/zlib 不在本包 PkgConfigDeps 输出里，pkg-config 会报 not found）。
5. **运行时数据**：`Locations.xml`（约 30 MiB）+ `locations-db` + 编译后的 `org.gnome.GWeather4` gsettings schema 都是运行期必需，`package_info()` 导出 `GSETTINGS_SCHEMA_DIR`、`LIBGWEATHER_LOCATIONS_PATH`、`LD_LIBRARY_PATH`。
6. **共享 glib 硬约束**：`libsoup3/3.6.5-r3` 硬 pin `glib/2.84.0.1.1` shared（静态内嵌 GObject 副本会导致双类型系统 SIGABRT），libgweather 必须对齐同一 shared glib，否则同进程内再次出现双副本。
7. **必须给打包的 `.so` 签名（`.codesign`）**：meson 产物没有 `.codesign` 段，OHOS loader 在符号查找之前就拒绝加载，症状极具误导性——链接成功、符号确实已导出（`llvm-readelf --dyn-syms` 可见）、文件也确实在磁盘上，但运行时报
   `Error loading shared library libgweather-4.so.0: (needed by ./test)` + 一串 `Error relocating ...: symbol not found`。
   已按已合入的 `wavpack/5.9.0` 形状实现 `_sign_shared_libs()`：`llvm-objcopy --remove-section .codesign`（无该段属新构建正常情况，不 abort）→ `binary-sign-tool sign -selfSign 1`（失败必须抛）。
8. **GSettings schema 必须自己编译**：meson.build 设了 `glib_compile_schemas: true`，但 tarball 只带 `org.gnome.GWeather4.gschema.xml` / `.enums.xml` 两个源文件，`meson.install()` 只复制它们，**从不生成 `gschemas.compiled`**。GSettings 只认编译产物，消费者首次触发库内设置即 `GLib-GIO-FATAL-ERROR: No GSettings schemas are installed on the system`（SIGTRAP）。已加 `_compile_gsettings()`（`_inject_glib_tools` 已把 glib 包自带的 `glib-compile-schemas` 放上 PATH），产出物缺失即抛错。

## 测试

- **上游测试已在配方 `build()` 内真实执行**（不是"另建 build 目录跑一遍"）：
  `generate()` 设 `tests=true`（`meson_options.txt` 默认也是 true），
  `build()` 调 `_run_upstream_tests()`，按上游 CI 同口径**单次**执行
  `meson test -C builddir --print-errorlogs --no-suite=style --timeout-multiplier 4`，
  target 名从上游 `libgweather/tests/meson.build` 的 `gweather_tests` 列表解析，不硬编码。
- 上游注册点实测：`grep -c g_test_add_func libgweather/tests/*.c` → test_libgweather **7**
  + duplicates **2** + timezones **3** + metar **1** = **13** 个用例，分布在 4 个 meson target：
  `test_libgweather`(7) / `duplicates`(2) / `timezones`(3) / `metar`(1)；
  另加 `data/meson.build` 的 2 个 lint 入口（xmllint `Valid Locations file`、
  pylint `pylint-gen-locations-variant`）⇒ **上游用例合计 15**。
- **真机实测结果（设备 3QC0124C11000071，2026-10-08 23:35 CST，CI 同源闸
  `ci/conan/build_and_test.sh` rc=0 / Pass rate 100% / `conan create passed`）**：

  | 层级 | 实测 |
  |---|---|
  | meson test 条目 | 注册并执行 **5**（4 g_test + 1 lint）：**Ok=4 / Fail=1** |
  | 13 个 g_test 用例 | **10 通过** / **1 跳过**（`location-names`，缺 `fr_FR.UTF-8` locale，上游自带 `g_test_skip`）/ **2 归因失败**（`named-timezones-deserialized`、`timezones`） |
  | lint `Valid Locations file` | **通过**（`/data/service/hnp/bin/xmllint` 存在，故该入口**会**注册） |
  | pylint 入口 | **未注册 ⇒ 未执行**（目标机无 `pylint`，`find_program(required:false)` 探测失败） |
  | metar | **通过**（60.33s，设备具备出网） |

  ⇒ 15 项中实跑 **14**：11 通过、1 跳过、2 归因失败、1 未注册。
- **判定为什么要两个源对账**（本轮踩到的坑，已写进配方）：被 SIGABRT 中止的
  `timezones` target 在 **TAP 流里不产生 `not ok` 行**——只读 `meson-logs/testlog.txt`
  会把 meson 自己判 `Fail` 的一跑报成「0 failed / 100% 通过」（2026-10-08 22:44
  的设备日志实测到该矛盾）。故配方捕获 meson stdout 的 `Ok:`/`Fail:`/`Summary of
  Failures` 作 target 级唯一判据，TAP 只作 case 级，再用 `g_test_add_func` 注册点
  核算「TAP 未上报」的用例并逐条点名（registered 13 − TAP 11 = 2）。
  归因表按 **meson target 名 + 日志签名**双重校验：签名不匹配即当移植缺陷抛错，
  防止归因表掩盖真回归。
- **通过率口径与归因（按 §8.6）**：

  | target | 用例数 | 真机实测 | 归因 |
  |---|---|---|---|
  | `test_libgweather` | 7 | 6 通过 + 1 跳过（locale） | — |
  | `duplicates` | 2 | 2 通过 | — |
  | `timezones` | 3 | 1 通过 + **2 失败** | 平台缺 `/usr/share/zoneinfo` 文件树，见下 |
  | `metar` | 1 | 1 通过（60.33s） | 无出网的 sandbox 上归因为网络，见下 |

- **`metar` 的网络依赖（具体技术原因，非笼统"平台不支持"）**：
  该用例唯一数据源是在线地址 `METAR_SOURCES` =
  `https://aviationweather.gov/data/cache/stations.cache.xml.gz`
  （`libgweather/tests/metar.c:16`），用 libsoup3 直接 GET，并对响应码断言
  `g_assert_cmpint (soup_message_get_status (msg), >=, 200)` / `< 300`
  （`metar.c:273-274`）。
  **真机（3QC0124C11000071）实测：通过，60.33s**——设备具备到该主机的出网，
  早期笔记里「`ping 114.114.114` → `Network unreachable` ⇒ 结构上不可跑」的结论
  **已按实测撤回**（当时的探针跑在不带出网的会话/路径上，不代表本次执行环境）。
  **无出网的 CI sandbox** 上该断言仍不成立，故配方保留网络归因：失败时按日志签名
  （`aviationweather.gov` / `metar.c` / `stations.cache.xml`）校验后放行并写明原因，
  签名不符则当移植缺陷抛错。恢复条件：执行环境具备到 aviationweather.gov 的出网能力。
- 上游 `test_libgweather` 里的 `test_weather_loop_use_after_free` 会真调
  `gweather_info_update()` 并起 5 秒 `g_main_loop`，靠 `g_assert_not_reached()`
  验证 `updated` 信号**没有**被发出——它属于 UAF 回归防护，不是联网用例。
- `test_location_names` 断言法语译文，需要 `fr_FR.UTF-8` locale；上游自己写了
  `g_test_skip("Locale fr_FR.UTF-8 is not available")` 兜底（`test_libgweather.c:156`），
  所以缺 locale 时是 skip 而不是 fail，不影响通过率分母口径。
- `test_package` 两个真实消费者二进制（`test_libgweather4` / `test_detect_degraded`），
  经 `VirtualRunEnv` + `env="conanrun"` 运行（默认 `self.run()` 没有传递依赖的
  `LD_LIBRARY_PATH`，会假报失败）。

### 推送闸门证据（§6.0b，最终树，设备 3QC0124C11000071）

| 闸 | 命令/判据 | 结果 |
|---|---|---|
| ① 语法+静态 | `python3 -m py_compile conanfile.py` + `python3 -m pyflakes conanfile.py` | ✅ 通过，无输出 |
| ①+ 解析器离线回归 | 用**设备真实日志**喂 `_parse_meson_stdout` / `_parse_upstream_testlog` | ✅ `Ok=4/Fail=1/failed=[libgweather:timezones]` 解析正确；TAP 带/不带 `- ` 分隔符两种形态均正确 |
| ② 配方门禁（设备侧 `conan-verify`） | `python3 scripts/ohc-run.py conan-verify libgweather4 4.4.4`（2026-10-09 03:39–03:46） | ✅ `rc=0`，`G0/G1/G2/G3/G4 全 PASS`，verdict `PASS`，`conan create` 成功（内部含 `Calling generate()` / `Calling build()`），`reports/conan-verify-report.md` 已产出 |
| ③ CI 同源（设备侧） | `CI_PACKAGES=archives/l/libgweather4/4.4.4 JUNK_PR_DIFF=<19 文件 pr.diff> zsh ci/conan/build_and_test.sh`（2026-10-09 03:25–03:32，**含本文件与 MANIFEST/知识草稿的最终树**） | ✅ `rc=0`；`检查模式: prdiff (19 个文件)`；`G0/KC/JC=pass`、`L0/L1/L5=pass`、`L2=skip`、`L4=warn`（补丁含 sed，已知告警）、`Pass rate 100.0%`、`All packages built and tested successfully`；实测口径与 23:35 那轮完全一致（`Ok=4 Fail=1`、`10 passed / 1 skipped / 2 failed with attribution`，metar 60.32s） |

> 上一版（2026-10-08 23:28–23:35 CST）那轮闸③在**本文件写入之前**运行，故上表以
> 2026-10-09 03:32 / 03:46 两轮为准——它们覆盖的才是待推送的最终树。

设备通道纠正：早期「设备无工具链 / uid2000 不能执行 ELF / 闸2闸3 物理不可跑」的结论
**已推翻**——探针当时跑在裸 `hdc shell`（`HOME=/root`，PATH 不同）上；`agent_mailbox`
worker 会话内 `conan 2.29.1 / python3 / clang 15.0.4(aarch64-ohos) / cmake / ninja / meson`
齐全，且能执行用户 ELF。OP-3 闸门**在 mailbox worker 里可跑**，本轮就是这么跑绿的。

推送序列（按 AGENTS §8.3，顺序不可乱）：三闸全绿 → push（新 head 解 CI 去重）→
`/rebuild` → 等 CI 绿 → `/ai review` → 清零全部意见（含 2 条 rule11 伴生线程）→ 提审。

### 上游测试二进制的 DT_RPATH（打开 tests=true 带来的连带问题）

打开 `tests=true` 后，meson 会额外构建 `libgweather/tests/*` 与
`libgweather/tools/*` 共 7 个可执行文件，它们链接 `libgweather_static` 及
glib/libsoup3/libxml2/json-glib。这些 `.so` 只存在于 conan 包目录，
而 **OHOS musl loader 忽略 `LD_LIBRARY_PATH`**（见下节），测试程序会在进入
`main()` 前就 `Error loading shared library` 退出。
故 `generate()` 里把每个依赖包的 `libdir` 以 `-Wl,-rpath` 注入
`tc.c_link_args`，并加 `-Wl,--disable-new-dtags` 强制 lld 产出老式 `DT_RPATH`
（musl dynlink 只认 `DT_RPATH`，不认默认的 `DT_RUNPATH`）。
形状与已合入的 `gmime/3.2.15`、`pan/0.165`、`uhttpmock/0.11.0` 一致。

### OHOS musl loader 忽略 LD_LIBRARY_PATH → 消费者必须自带 DT_RPATH

真机证据（同一份日志）：`LD_LIBRARY_PATH` 已包含全部依赖包目录，但**只有位于 conan 包目录里的 4 个库**报 `Error loading shared library`，而系统路径 `/storage/Users/currentUser/usr/local/lib` 里的 glib/gobject/gio/gmodule/gthread/intl 全部正常解析。这个「按目录整齐分裂」的形态就是 LD_LIBRARY_PATH 被忽略的指纹，不是缺符号。
修法（同已合入的 `uhttpmock/0.11.0`、`pan/0.165`）：`test_package` 的 `build()` 里遍历依赖取 `package_folder + cpp_info.libdirs`，加
`-Wl,--disable-new-dtags -Wl,-rpath,<每个目录>`。两个 flag 都要：lld 默认产 `DT_RUNPATH`，而 musl dynlink 只认老式 `DT_RPATH`；`CMAKE_BUILD_RPATH` 无效是因为 conan toolchain 设了 `CMAKE_SKIP_RPATH`。
设备回读确认：修复后同一条命令的 `Error loading` 从 4 条降到 1 条（剩下的那条是自己没签名的 `libgweather-4.so.0`），修完签名后归零；`llvm-readelf -d` 回读 `RPATH_COUNT=1 RUNPATH_COUNT=0`。

## 知识候选

- 标题：构建期 ctypes dlopen 依赖会让 CI 与设备结果不一致（改用纯标准库实现）
- 真实错误：CI-010 上 `FAILED: [code:1] data/Locations.bin` /
  `Permission denied: .../p/lib/libglib-2.0.so.0`；设备本地同配方全绿
- 根因：`tools/gvariant_ctypes.py` 在**构建期** `dlopen("libglib-2.0.so.0")`。
  CI worker 镜像里只有未签名的 conan glib 副本，OHOS loader 校验 `.codesign`
  哈希后拒绝加载 → shim 的候选路径列表耗尽。换 glib 版本或 pin 都不能根治：
  能不能 dlopen 取决于**构建机的镜像状态**，不是配方属性
- 修复：新增 `tools/gvariant_pure.py`，用**纯标准库**自行序列化 GVariant normal
  form（无 gi、无 ctypes、无 dlopen）。`GW_GVARIANT_BACKEND` 保留 ctypes 分支
  作为逐字节交叉验证
- 布局规则来源（不是猜的）：① 上游 `gweather-db.h:39 Db_ref_get_offset_size()`
  的查表实现，证明 framing 表宽度由**值的总字节数**决定而非最大已存 offset；
  ② 真 GLib 2.88.1 逐字节实测 1092 种 struct 形状 + 12 组宽度边界向量
- **验收方式（可复用，勿再用自写 readback.c）**：`gweather-db.h` 只依赖 glib，
  可脱离 libgweather 单独编译。把它的 accessor 原件接上纯串行器的产物，
  8868 条记录逐字段 diff 与上游 generator 自身算出的值完全相同
- 反例：`g_variant_get` 的格式串必须与类型**成员数**一致（`((ss)ss(dd)ssqyqqaqaq)`
  是 12 个成员）。我曾写成 13 个（含多余的 `q`）且给两个 `aq` 数组用了只对
  tuple 有效的 `v`，`g_variant_get` 直接 SIGBUS

- 标题：`Meson.configure(env=...)` 在 Conan 2.29 不是合法 kwarg
- 真实错误：`TypeError: Meson.configure() got an unexpected keyword argument 'env'`
- 根因：`Meson` helper 的 `configure()` 没有 env 形参；即使想给 meson 传环境变量
  也要走 `self.buildenv_info`（已在 `generate()` 里注入过 `GW_GVARIANT_DIR`）
- 适用范围：任何用 `Meson(self).configure(...)` 的配方；**写完务必真机跑一遍**
  ——本机上 pyflakes/py_compile 都过，只有 `conan create` 才炸

- 标题：GNOME meson 库在缺 PyGObject 目标上的 `find_installation(modules:['gi'])` 硬失败
- 真实错误：meson setup 阶段 `python3 -c "import gi"` 失败 → `Could not find valid Python installation`
- 根因：上游把「确认 python3 存在」写成对 PyGObject 的硬要求，而绑定变量 `py` 全树未使用
- 修复：加 `required: false` 而不是删变量
- 适用范围：任何 GNOME meson 项目在无 PyGObject 的目标上（先 `grep -rn "find_installation" --include=meson.build` 确认绑定变量确实未被引用）

- 标题：Locations.bin 生成器去掉 PyGObject（纯 ctypes 实现 GLib.Variant）
- 真实错误：`gen_locations_variant.py:7 from gi.repository import GLib` → `ModuleNotFoundError: No module named 'gi'`，ninja 在 221 个目标里的 `data/Locations.bin` 上中止
- 根因：OHOS 上 PyGObject **彻底不可用而非「没装」**：制品仓有 `pygobject/3.58.0` 且能装上，但 `import gi` 死在动态链接期（`ImportError: Error relocating .../gi/_gi.cpython-312-aarch64-linux-ohos.so: PyType_Ready: symbol not found`）；旁证 `ctypes` 本身可用、只有 Python C 扩展加载不了 → 目标 CPython 3.12.9 ABI 不匹配，加包/换解释器都修不了
- 修复：`tools/gvariant_ctypes.py` 用 ctypes 直连被测库自己链接的同一个 `libglib-2.0.so.0`，用 GLib 自己的 `g_variant_new_tuple`/`g_variant_new_array` 构造（**不能用 GVariantBuilder**：遇 tuple 内含 `y`(byte) 槽位即返回 NULL，而 location 记录的 `level` 字段正是 byte）；字节取自 `g_variant_get_normal_form`
- 附带两个真实 bug：`g_variant_new_dict_entry` 原型是 `(GVariant *key, GVariant *value)` 两个独立指针，**不接受 children 数组**（传错会在 GLib 里 abort 成 `g_variant_type_info_check: (0 <= index && index < 24)`）；`{...}` 用 tuple 构造会让外层 `a{sq}` 报 `g_variant_new_array: assertion 'is_of_child_type' failed`。self-test 必须按族分开覆盖，否则只测 tuple/array 会漏掉 dict-entry。
- 验证：真机生成成功，`a{sq}`/`a{s((ss)as)}`/root 全部 `is_normal_form: True`，magic `3031444274684757` = `0x5747687442443130`，与 `gweather-private.c` 的 `db_world_get_magic` 断言一致；消费者断言 Sydney `Australia/Sydney`、London `Europe/London` 坐标与时区全部正确。

- 标题：meson `glib_compile_schemas: true` 不等于会产出 `gschemas.compiled`
- 真实错误：`GLib-GIO-FATAL-ERROR: No GSettings schemas are installed on the system`（SIGTRAP）
- 根因：该选项只在源码树内配合 gnome 模块工具生效；发布 tarball 里 `install_data()` 只复制源 `.gschema.xml`，`meson.install()` 同样只复制 → 包内永远缺编译产物
- 修复：`package()` 阶段显式调用 glib 包自带的 `glib-compile-schemas <packaged schema dir>`，并校验产物存在
- 适用范围：任何用 GSettings 的 GNOME 库在「源码树外消费打包产物」的场景（包管理/conan 打包），源码树内跑 `meson test` 通常不复现

- 标题：world 节点没有名字是上游设计，别把它当回归
- 真实症状：自写测试里 `g_ascii_strcasecmp (gweather_location_get_name (world), "World")` → `GLib-FATAL-CRITICAL: g_ascii_strcasecmp: assertion 's1 != NULL' failed` + SIGTRAP
- 根因：`Locations.xml` 根 `<gweather format="1.0">` **没有 `<name>`/`<_name>` 子元素**；生成器 `get_name()` 返回 `('', '')`；C 侧 `gweather_location_get_name()` 用 `EMPTY_TO_NULL` 把空串映射成 NULL（`gweather-location.c:296`）。上游自己的测试也只 `g_assert_nonnull(world)`，从不断言 world 名字
- 反例：world 的直接子节点是 **region** 不是 country——XML 实测 9 个 `<region>` / 245 个 `<country>`，country 全部嵌套在 region 内；生成器 `levels = {gweather:0, region:1, country:2, ...}`。在 world 层按 country 计数只会数到 region
- 适用范围：任何按 Locations.xml/同类层级数据写断言的消费者测试；断言前先读数据格式本身，并对照上游测试断言了什么

---

**编译结束**: 2026-10-09 03:46 CST（设备 3QC0124C11000071，`conan create` + 上游
`meson test` 5 条目 Ok=4/Fail=1(归因) + test_package 30 断言全过；三闸同日 03:32/03:46
在最终树上全绿：`conan-verify` G0–G4 PASS、`ci/conan/build_and_test.sh` rc=0 /
Pass rate 100%）
**最终状态**: 本地三闸全绿、待推送进入 §8.3 审计序列（push → /rebuild → CI 绿 →
/ai review → 清零意见 → 提审）；平台任务 13221 `claimed`，PR #13996 open
