# vtgamma

vtgamma — 为 Linux 虚拟控制台（VT）与 xterm 类图形终端模拟器做伽马校正的工具
（单文件纯 Perl 脚本，无 C/C++ 源码）：按给定伽马值生成 256 级颜色斜坡并应用
到终端调色板，修正终端颜色与显示设备的伽马偏差。上游 0.5（归档文件日期
2023-09-14），许可证 Public Domain（上游 LICENSE 声明放弃版权）。

## 功能
- `vtgamma <gamma>`：对 16 色调色板按单一伽马值生成斜坡并应用（xterm 类终端走
  `rgb:` 转义，Linux 虚拟控制台走 `PIO_CMAP` ioctl）
- `vtgamma <red> <green> <blue>`：按 RGB 三分量分别指定伽马值
- `vtgamma <palette> [<gamma>...]`：基于具名调色板（vga / ubuntu / gruvbox 等）
  生成斜坡
- `-r` 反向（读取/还原）；`-e` 扩展处理；`-l` 相关开关见 `vtgamma -h` / man page

## HarmonyOS PC (arm64) 适配说明
- 纯 Perl 脚本包：上游归档无任何构建系统，配方**直接文件安装**
  （脚本 → `bin/vtgamma`，man page → `share/man/man1/`，LICENSE → `licenses/`），
  不做 configure/make，保证 Conan 包可重定位。
- 脚本 shebang 由上游写死的 `#!/usr/bin/perl -w` 改写为 `#!/usr/bin/env perl`：
  HarmonyOS PC 系统 perl 位于 `/data/service/hnp/bin/perl`（hnp 包管理路径），
  绝对路径在目标机不成立；改写后运行期从 PATH 解析解释器，配合配方声明的
  Conan 运行时依赖 `perl/5.42.2`（VirtualRunEnv 将其 `bin/` 加入 PATH）。
- `build()` 在改写前断言上游 shebang 与预期一致，上游漂移时构建显式失败，
  不会静默发出未适配脚本。
- 正常工作路径需要真实 VT/终端（ioctl 操作控制台），自动化环境只能覆盖到
  脚本安装形态 + Perl 语法校验（`perl -c`），终端调色板效果需真机确认。

## 安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- vtgamma 0.5
```

## 验证
```bash
vtgamma 1.0          # 期望: rc=0（真实终端下重设伽马 1.0 调色板）
vtgamma 0.45 0.45 0.45   # 期望: rc=0（RGB 分量伽马）
perl -c $(command -v vtgamma)   # 期望: syntax OK
```

## 参考资料
- 上游仓库: https://github.com/kilobyte/vtgamma
- man page: `vtgamma.1`（随包安装于 `share/man/man1/`）
