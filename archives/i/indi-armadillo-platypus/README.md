# indi-armadillo-platypus

## 软件描述
indi-armadillo-platypus 是 INDI 生态中面向 **Lunatico Astro（西班牙）设备** 的驱动集：一个 CMake 工程产出 **6 个独立驱动的可执行文件**，覆盖旋转器、圆顶/屋顶控制器与调焦器。

| 可执行文件 | 设备/类别 | 基类 |
|---|---|---|
| `indi_seletek_rotator` | Seletek 旋转器 | `INDI::Rotator` |
| `indi_dragonfly_dome` | DragonFly 圆顶 | `INDI::Dome` |
| `indi_dragonfly` | DragonFly 控制器 | 辅助设备（Auxiliary） |
| `indi_beaver_dome` | Beaver 圆顶 | `INDI::Dome` |
| `indi_armadillo_focus` | Armadillo 调焦器 | `INDI::Focuser` |
| `indi_platypus_focus` | Platypus 调焦器 | `INDI::Focuser` |

配套数据文件 `share/indi/indi_lunatico.xml`（6 条 `<driver>`，供 INDI 客户端/`indiserver` 发现），以及 Linux 下的 udev 规则 `99-armadilloplatypus.rules`（USB 设备 `16C0:09B1` 权限）。

## 功能概述
- **旋转器**：Seletek 旋转角控制与同步
- **圆顶/屋顶**：DragonFly 与 Beaver 圆顶的开合、park/unpark、与望远镜联动（slaving）
- **调焦器**：Armadillo / Platypus 的绝对/相对位置移动、同步与温度补偿（共用 `arm_plat_focuser_common.*` 命令层）
- **连接方式**：走 INDI 自带串口/USB 连接插件
- **设备发现**：`indi_lunatico.xml` 声明全部 6 个驱动，交由 `indiserver` 动态加载

## OHOS 适配

### 构建方式
- **CMake 源码构建**：源码取自 **indi-3rdparty 单体仓库**（驱动位于 `indi-armadillo-platypus/` 子目录），pin 到 commit `945fbe12…`（与制品仓 `libindi 2.2.2.1` 同代；与同快照兄弟驱动 indi-aok / indi-talon6 / indi-maxdomeii 同一 commit 与 sha256）
- **必须保留整棵仓库树**：子目录 `CMakeLists.txt` 会把 `../cmake_modules` 追加进 `CMAKE_MODULE_PATH`
- **只构建本驱动目录**：`cmake.configure(build_script_folder="indi-armadillo-platypus")`（该目录内含 6 个驱动源文件）

### 关键攻坚点
1. **多驱动包的消费者校验**：6 个 bin 逐一做 AArch64 ELF 审计；`indi_lunatico.xml` 的 6 条 `<driver>` 与 `bin/` **逐一对应**（多/少都判失败）；6 个 bin 各自做 DT_NEEDED 闭包审计
2. **绝对路径安装变量需重定向**：上游把 `RULES_INSTALL_DIR` 硬编码为 `/usr/lib/udev/rules.d/`（会写穿包前缀、宿主机该目录不可写）→ 按同族 `archives/l/libfli` 的既有做法重定向进私有前缀 `lib/udev/rules.d`，产物不丢
3. **Linux 守卫需走 Linux 路径**：上游 udev 安装被 `if (CMAKE_SYSTEM_NAME MATCHES "Linux")` 守卫，而 CMake 无 HarmonyOS 平台（E092）→ `CMAKE_SYSTEM_NAME=Linux`（同族 libfli 先例）才能触发该安装
4. **`INDI_DATA_DIR` 必须预置为相对路径**：否则 `find_path` 解析出 libindi 包的绝对路径，`indi_lunatico.xml` 会被装进依赖包（同 indi-talon6 / indi-maxdomeii 的坑，复用 DRAFT-24001 结论）
5. **libnova 头目录注入**：indi 头链间接包含 `<libnova/utility.h>`，上游不传其头目录 → `extra_cflags/extra_cxxflags` 注入（**值内不嵌引号**，按同族 libfli 写法）
6. **DT_NEEDED 需含 `libindiclient`**：`find_package(INDI)` 默认组件为 `driver + align` → 补丁请求 `client` 组件，否则 musl loader 解析 `tty_write_string` 等符号失败
7. **`package_info()` 注入运行期搜索路径**：libindi 静态优先发布，驱动动态链接其 `.so` → 注入 `LD_LIBRARY_PATH`

### 与 Linux 的差异
- 无源码级差异（INDI 驱动跨平台）；差异集中在**打包与运行环境**：数据文件落点需预置、udev 规则需重定向进包、libindi 的 `.so` 搜索路径需显式注入
- 宿主不允许从用户数据目录（$HOME，构建/包目录所在处）执行二进制（实测把系统自带的 busybox 复制到该目录同样报 Permission denied），消费者校验会把这类情况按具名环境信号记为 SKIP

## 依赖关系
- **构建/运行期**：`libindi/2.2.2.1`、`libnova/0.16`（均已合入制品仓）
- 上游 Debian 打包仅额外声明 `libnova-dev`；本驱动的 CMakeLists **未 find_package** 其它库（无 cfitsio/zlib/gphoto 需求）

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.0-20221226082641 | built | 2026-10-07 | indi-3rdparty 单体仓多驱动包范式 + udev 规则重定向 |

## 参考资料
- 上游仓库: https://github.com/indilib/indi-3rdparty
- 厂商: https://lunaticoastro.com
