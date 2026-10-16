# zram-init

zram-init 是一个 POSIX shell 脚本工具，用于在 Linux 系统上创建（setup）与释放（release）
zRAM 压缩内存块设备，可作为 swap 或 tmpfs（/tmp、/var/tmp 等）使用。它通过 `modprobe zram`
加载内核模块，按配置设置磁盘大小、文件系统与挂载点，并在退出时按逆序安全释放。

## 软件构成

纯 shell 项目，无任何 C/C++ 源码：

- `sbin/zram-init.in` — 主脚本模板（GNU Make 替换占位符后生成 `zram-init`）
- `man/zram-init.8.in` — 手册页
- `modprobe.d/zram.conf` — 内核模块配置样例
- `zsh/_zram-init` — zsh 补全脚本
- i18n po 文件、systemd/openrc 服务单元（本适配不启用）

## OHOS 适配要点（13.3）

- **构建**：手写 GNU Makefile（非 autotools）。`conanfile.py` 直接调用
  `make GETTEXT=FALSE SYSTEMD=FALSE OPENRC=FALSE MODIFY_SHEBANG=FALSE`：
  鸿蒙无 gettext/systemd/openrc 基础设施；保留 `#!/usr/bin/env sh` shebang。
- **打包**：toybox 无 `install -D`，`package()` 显式复制
  （bin/zram-init、share/man/man8、share/zsh/site-functions、res/modprobe.d 样例）。
- **测试**：上游无测试套件；test_package 提供 13 项功能等价断言
  （布局检查 + `sh -n` 语法校验 + `sh zram-init -h` Usage 输出验证）。

## 上游

- https://github.com/vaeth/zram-init （GPL-2.0-only）
