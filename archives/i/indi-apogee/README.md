# indi-apogee（INDI Apogee 相机 / 滤光轮驱动）

INDI 第三方驱动，支持 Apogee（阿普奇）CCD 相机（`indi_apogee_ccd`）与独立滤光轮
（`indi_apogee_wheel`）。两个可执行文件都是标准 INDI 驱动：把
`<getProperties version="1.7"/>` 写到 stdin，就会把设备属性定义输出到 stdout。

- 官网: https://github.com/indilib/indi-3rdparty
- 源码: Debian pool 的 orig 包 https://deb.debian.org/debian/pool/main/i/indi-apogee/
  （上游 Apogee SDK 为闭源，社区版由 Debian 维护）
- 许可证: LGPL-2.1-or-later

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.9-20221223184417 | built | 2026-10-03 | 源码取自 Debian orig 包；4 个补丁（2 个 cmake_modules + 2 个属性 API 迁移） |

## 编译注意事项

- **驱动源码里没有 `main()`**：入口由 libindi 的 `libs/indibase/indidrivermain.c` 提供并编进
  `libindidriver`。该 `main` 只认 `-v`，随后阻塞在 `eventLoop()` 读 stdin，stdin EOF 时
  `exit(1)` —— 拿退出码或 `-v` 当探针是错的，正确探针是喂 `getProperties` XML 再看 `<def...>`。
- **属性 API 要分两类**：驱动自己声明的属性用裸 C 结构体（libindi 2.2.2 完整保留该 C API，
  无需改动）；从基类继承的属性（`TemperatureNP` / `FilterSlotNP` / `FilterNameTP`）在 libindi 2.x
  已是 `INDI::PropertyNumber`/`PropertyText` 对象、旧名 `TemperatureN`/`FilterSlotN` 已删除，
  需要迁移补丁（`patches/0003`、`patches/0004`，内容取自上游 indi-3rdparty 的同名迁移）。
- `-I<libapogee3>/include` 必须显式补：libapogee3 只暴露 `include/libapogee`（其公有头互相
  扁平 include），而上游源码写 `<libapogee/Xxx.h>`。
- `INDI_DATA_DIR` 必须显式钉住：`FindINDI.cmake` 靠 `find_path(drivers.xml)` 推导，制品仓的
  libindi 不装该文件，否则 XML 会被装进 `INDI_DATA_DIR-NOTFOUND`。
- `CMAKE_POLICY_VERSION_MINIMUM=3.5` 必须走 configure 命令行 `-D`（写入 toolchain 无效）。
- **ELF 自签名（E077）**：产物是 `bin/` 下的可执行文件，HarmonyOS 内核只执行带有效
  `.codesign` 的 ELF，未签名报 `Operation not permitted`（`chmod` 无效），配方在 `package()`
  里用 `llvm-objcopy` + `binary-sign-tool -selfSign` 处理。
- **运行期依赖的 `.so` 必须来自「已重签的副本」，光挂依赖 `libdir` 没用**：两个二进制动态
  链接 libindi（真机实测缺的就是 `libindidriver.so.2` / `libindiAlignmentDriver.so.2`），
  但 HMDFS 上未签名（或签名失效）的共享库无法 `mmap(PROT_EXEC)`，依赖包 `libdir` 里那批
  `.so` 都没有有效签名 —— 挂上路径只会让 loader 更早撞上坏候选，报
  `Error loading shared library <so>: (needed by ...)`（**不带 errno**，极易误诊成路径问题）。
  可行做法是**自包含 staging**：把二进制与全部依赖 `.so` 的已重签副本放进同一目录，再把这个
  目录**前置**到 `LD_LIBRARY_PATH`。`test_package` 就是这么做的
  （`~/.cache/indi-apogee-test-stage`，由 `test.sh` 自己前置）。消费者运行这些二进制时同样需要。
- 无真实 Apogee 硬件：`test_package` 只验证 INDI 协议层往返，不连接设备。
