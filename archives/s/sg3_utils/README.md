# sg3_utils

SCSI generic (sg) 工具集与 `libsgutils2` 库，为 HarmonyOS PC 适配。

- 上游：<https://sg.danny.cz/sg/sg3_utils.html>（官方 GitHub 仓库 <https://github.com/doug-gilbert/sg3_utils>）
- 许可证：GPL-2.0-or-later
- 构建系统：CMake（上游 1.44 起与 Autotools 并存）

## 提供的产物

| 类别 | 内容 |
|---|---|
| 库 | `libsgutils2.a` / `libsgutils2.so`（`-lsgutils2`），头文件 `include/scsi/*.h`（19 个） |
| 工具 | 84 个可执行文件：72 个 `sg_*`（`sg_inq`、`sg_vpd`、`sg_dd`、`sg_raw`、`sg_format`、`sg_turs`、`sg_luns`…）+ 12 个历史别名/脚本（`sginfo`、`sgm_dd`、`sgp_dd`、`scsi_*`、`rescan-scsi-bus.sh`） |
| 声明 | 软件级 `commands.json`（tool 类型，R38） |

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.49 | built | 首发适配：CMake 平台判定补丁，恢复真实 sg v4/bsg pass-through |

## 鸿蒙适配要点

1. **必须打补丁 0001**：上游 `CMakeLists.txt` 只把 `CMAKE_SYSTEM_NAME == "Linux"` 视为 Linux——
   HarmonyOS 会静默落入 `PT_DUMMY` 降级分支：pass-through 全部空转，且
   `if (SG_LIB_LINUX AND NOT PT_DUMMY)` 分支的 13 个 `SG3_UTILS_LINUX_ONLY` 工具 + `sg_scan`
   共 14 个直接不构建。补丁把 HarmonyOS/OHOS 并入 Linux 分支；OHOS sysroot 具备
   `scsi/sg.h`、`linux/bsg.h` 等内核头，**是真实实现不是桩**，14 个工具实测全部产出。
2. **静态库安装缺失**：上游 `install(TARGETS)` 未声明 `ARCHIVE DESTINATION`，静态库不会进包；
   配方在 `package()` 从构建目录补齐，并归一库名 `libsgutils2.a`。
3. **测试**：上游 `ttesting/` 20 个用例（4 项实跑通过、2 项 t10.org 数据漂移、14 项需 `/dev/sg*`），
   另补 9 项鸿蒙专项/消费者断言（含真实 PT 分支回归守门）。详见版本目录 `notes.md`。

## 用法

```python
# conanfile.py
def requirements(self):
    self.requires("sg3_utils/1.49")
```

```bash
# 工具在 conanrun 环境的 PATH 中
sg_inq --version
sg_vpd --page=0x00 /dev/sg0
```
