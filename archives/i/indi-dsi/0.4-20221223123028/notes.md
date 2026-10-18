# indi-dsi 0.4-20221223123028 适配笔记

## 任务背景

- 平台任务 id **7465**（主榜「开源鸿蒙PC专项积分赛」10 火种），分支 `feat/indi-dsi-0.4-20221223123028`。
- 与 indi-rtklib(12501)/indi-starbook-ten(12504)/indi-maxdomeii(12496)/indi-starbook(12503) 同族（indi-3rdparty 2022 快照驱动），四雷修复方案、L1e 修复模式全套复用。

## 真实身份

Meade DSI/DSI II/DSI III（Pro & Color）相机的 INDI 驱动**可执行程序**（非库），INDI::CCD 子类。
源码 11 编译单元：dsi_ccd.cpp（INDI::CCD 驱动壳）+ DsiDevice.cpp（61KB，USB bulk 协议层）+ DsiDeviceFactory + DsiPro/DsiProII/DsiProIII + DsiColor/DsiColorII/DsiColorIII（型号变体）+ DsiTypes + Util（tokenize_str 助手）+ NamedEnum.h；首连经 fx2 固件上传（meade-deepskyimager.hex 随包安装），download_fx2.cpp 仅 APPLE 编译。

## 源码与依赖

- Debian `indi-dsi_0.4+20221223123028.orig.tar.gz`（82679 B），sha256 `32c8ce7f3848abecebddc105567ab1875628a1c365c2a9981594927b44bae612`（dsc 校验一致）。
- CMakeLists：`find_package(CFITSIO/INDI/ZLIB/USB1 REQUIRED)` 四个外部查找；cmake_minimum_required 3.0。
- 依赖：`libindi/2.2.2.1` + `cfitsio/4.6.4` + `libusb/1.0.27` + `zlib/1.3.1.1`，全已发布。**源码树无 libnova 引用**（INDI::CCD 链不传递 libnova，与 INDI::Dome/Telescope 不同——grep 全树零命中）。

## 四雷命中与修复（同族方案复用）

| 雷 | 命中情况 | 修复 |
|---|---|---|
| FindINDI 版本正则 | cmake_modules/FindINDI.cmake:215 老正则 | 0001 = libfli/2.0-20221221182632 0001 逐字 |
| CMakeCommon 锁 C++14 | cmake_modules/CMakeCommon.cmake:11 | 0002 = 同族 0002 同款 |
| 驱动 1.x API（雷4） | **极轻**：上游 master 与本快照逐文件对比，dsi_ccd.cpp 仅两处 `IUSaveText(&BayerT[2], ...)`→`BayerTP[2].setText(...)`（2.2.2 的 CCD::BayerTP 已 Property 化）；DsiDevice.h 大重构为纯 USB 层自洽头（不含 INDI 引用、其 .cpp 与 master 逐字一致），无需跟随 | 0003 = 两处 master 回移（打完与 master 逐字节一致） |
| INDI_INCLUDE_DIR 层级 | 配方层 | 注入 `<libindi包>/include/libindi` + `INDI_ROOT=<包根>` |

## 新变体（本包首次记录）

1. **静态 cfitsio 的链接闭包**：OHOS cfitsio 为静态库（libcfitsio.a），nm 实测含未定义 zlib 符号（deflate 系）；快照 `find_package(ZLIB REQUIRED)` 结果从不进链接行 → `CFITSIO_LIBRARIES` 注入时把 libz.a 追加在 libcfitsio.a 之后（FindCFITSIO 短路口径采信该列表，保链接序）。
2. **FindUSB1 双通道注入**：模块无短路分支但 find_path/find_library 对预置变量天然空转 → `USB1_INCLUDE_DIR=<libusb>/include/libusb-1.0`（模块自检 `<libusb.h>` 裸引用所需子目录）+`USB1_LIBRARY=...so`；另 DsiDevice.h 带前缀引用 `<libusb-1.0/libusb.h>` 且快照无 `include_directories(${USB1_INCLUDE_DIR})` → 包 include 根走 `extra_cxxflags -I`。
3. **绝对安装路径改写**：快照把 udev 规则装到 /lib/udev/rules.d、固件装到 /lib/firmware（绝对路径，conan 打包会写出包外）→ 配方注入包内相对路径 `RULES_INSTALL_DIR=share/udev/rules.d` + `FIRMWARE_INSTALL_DIR=share/firmware`。**⚠️ 后经第 1 轮真机证伪：注入被上游无条件 set() 遮蔽失效，须 0004 守卫配合（见下节）**。

## 第 1 轮真机 FAIL@G2 与修复（2026-10-14，install 阶段）

**失败**：configure/编译/链接全过后，package() 的 cmake.install() 把 udev 规则写绝对路径 /lib/udev/rules.d → EPERM（设备无 root）；xml 另落字面量 `INDI_DATA_DIR-NOTFOUND/` 目录（非致命错误布局）。

**根因①（机制性注入失效）**：上游 CMakeLists 对 RULES_INSTALL_DIR/FIRMWARE_INSTALL_DIR 做**无条件普通 set()**——CMake 普通变量优先于同名非 FORCE cache 变量，conan 工具链（CACHE STRING）注入被完全遮蔽。**"不改上游"在此类上游手上机制性无效**。修复：**0004 补丁**给两个 set() 加 `if(NOT DEFINED)` 守卫（有注入用注入、无注入回退系统默认），注入保留不变。

**根因②（PATH 类型锚定）**：FindINDI 的 `find_path(INDI_DATA_DIR drivers.xml ...)` 只搜系统路径 → NOTFOUND。注入相对值 `share/indi` 时，**find_path 把变量定型为 PATH，CMake 将相对 PATH 值锚定到构建目录**（WSL 实证：cache 里变成 `<build>/share/indi`，xml 逃逸出包）。修复：配方注入**绝对路径** `INDI_DATA_DIR=<自身 package_folder>/share/indi`（不越包边界；绝不可指 libindi 包——install 会写进依赖包）。

**彩排升级（堵盲区）**：初版彩排在链接阶段即停（预期失败）从未到达 install——install 期缺陷只有真机能暴露。现在彩排加"假二进制骗过 TARGETS 安装"步骤：`touch <build>/indi_dsi_ccd` 后 `cmake --install --prefix <tmp>`，验证四件套（bin/xml/udev/firmware）全部落进 prefix 正确位置、零 /lib 泄漏——本修复已实测通过。

**知识图谱 E540 误匹配备录**：G2 失败时引擎命中 E540（runner-path-prepend），建议查 PATH/工具链；日志证伪（编译器检查与 11 .o 全过），属误匹配。

## 彩排验证（WSL，2026-10-14）

- patch_ng（strip=0, fuzz=False）链式应用 0001-0003 全 OK；dsi_ccd.cpp 与上游 master **逐字节一致**。
- 对真 OHOS 包头+库 configure（全注入按配方）：`Found CFITSIO`（带 libz.a）/ `Found INDI 2.2.2` / `Found ZLIB 1.3.1` / `Found USB1` 全命中；FindUSB1 的 `USB1_HAS_LIBUSB_ERROR_NAME` 链接自检失败属 x86_64↔aarch64 预期（真机 aarch64 全对齐会成功，fallback 路径编译亦过）。
- 编译：**11 个 .o 全过零错误**；链接 x86_64←aarch64 .so 失败**属预期**（同族彩排口径）。
- Layer1 x86_64 实跑（纯 std 无需 stub）：tokenize_str 六组断言（默认混合/连续/前导/尾随/空/自定义分隔符）**全 PASS，rc=0**。

## test_package 设计（R34/R51）

- **上游确无测试用例（R51 声明，附清点证据）**：源码包全树 34 文件仅驱动源码 + CMake/打包/文档 + udev 规则 + 固件，无 tests/ 目录、无 ctest/gtest 注册。
- **Layer 1（自研探测）**：vendor 编译包内 `src/Util.cpp`，test_dsi.cpp 六组断言覆盖 tokenize_str 分隔符语义（该函数被 DsiDevice.cpp:178 真实调用，属驱动公共助手）；纯 std 零外部依赖。
- **Layer 2（L1e 锚点）**：`bin/indi_dsi_ccd` 存在性硬断言（缺失抛 ConanException）+ `--help` best-effort（捕获返回码 warn；EPERM/126 属环境限制）——沿用同族验证生效模式。

## MateBook 真机验证项

1. 拉分支 `feat/indi-dsi-0.4-20221223123028`，确认 HEAD。
2. remote 预检（conan ohpcd remote 存在；libindi/2.2.2.1、cfitsio/4.6.4、libusb/1.0.27、zlib/1.3.1.1 均可 download）。
3. `python3 scripts/ohc-run.py conan-verify indi-dsi 0.4-20221223123028`（仓内副本）。
4. 通过后 `finish indi-dsi 0.4-20221223123028 built`。
5. 真机产物留本地当证据（已合并配方不含 reports/.ci-result.json）。

## 风险表

| 风险 | 等级 | 应对 |
|---|---|---|
| 静态 libcfitsio.a 链接闭包遗漏其他外部符号 | 低 | nm 实测仅 zlib 系外部未定义（无 curl/BZ2/pthread）；真机链接失败再按符号补 |
| FindUSB1 自检在真机失败导致宏路径变化 | 低 | 自检仅影响错误字符串 fallback；真机 aarch64 对齐链接会成功 |
| udev/固件装包内 share/ 与 W3 包内容检查 | 低 | share/ 为标准路径；udev 规则对 OHOS 仅参考用，固件为运行时资产 |
| L1e 误判（executable-only） | 低 | Layer2 硬断言锚定，同族四包验证模式 |
| JC 门禁（.staging-verified/.build-closed 不得跟踪） | 低 | 沿用同族合规口径 |

## 第 2 轮真机全绿（2026-10-15，9205a6cd19）

conan-verify 全绿（exit 0）：G0（E092 已处理）/G1（全声明+MANIFEST 在位）/G2（11 .o 零错误、链接成功、install 通过）/G3（纯可执行包无 lib/）/G4（⚠ 无法找到程序包 ID，警告级判 PASS）/L2/L4/L5（无 cache 路径跳过）全 PASS。

- **package() install 落点**（prefix 四件套，零 /lib 绝对路径泄漏，0004 守卫生效）：`bin/indi_dsi_ccd`、`share/indi/indi_dsi.xml`、`share/udev/rules.d/99-meadedsi.rules`、`share/firmware/meade-deepskyimager.hex`（另 `src/Util.cpp`、`src/Util.h` 随包）。
- **test_package**：Layer1 六组断言全过（mixed_delims 3 / consecutive 2 / leading 1 / trailing 1 / empty 0 / custom_colon 3 tokens，`PASS: tokenize_str public helper exercised (6 assertion groups)`）；Layer2 bin 硬断言 PASS；`--help` 未签名 exec EPERM rc=126（已知环境行为），**打包签名后 rc=1 真实输出 Usage 横幅**（EPERM 假设再度闭环）。
- **L1e sabotage 判真实**：移走 bin/ 后测试立刻失败（`[ok] L1e: Negative test confirmed — test genuinely depends on indi-dsi`）。
- **finish**：第 1 遍 step8 预检缺 3 项 → 补齐（verify-build PASS → PackageBuilder 打包签名 159MB+debug 57MB+.packaged → tarball 解包独立 exec 验证 → .staging-verified）→ 第 2 遍 step8 四项全绿、step5b 红（框架误报，全局，不修）；HANDOFF EXIT_REASON finish_success / EXIT_CODE 0（**可标记 published**）。gen_summary 崩溃不计退出码（框架 bug）。
- **.ci-result.json**：exit_code=0，integrity_hash `feff942b9684d2d1`（step W3_local_ci，2026-10-15T09:00:18）。
- 过程备录：W3 首跑 JC 三红系本地 origin/main 落后（libdazzle .staging-verified 被跟踪带入 + 增量 533 包），update-ref 刷新 origin/main 后归零复跑全绿（只动引用未提交）；真机部署位 conan 缓存包内二进制已签名，EPERM 消失。
- 证据（test-report.md / packaging/.packaged 等）随第 3 轮收尾提交；step5b 红随 PR 如实声明。
