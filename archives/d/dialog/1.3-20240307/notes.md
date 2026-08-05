# dialog 1.3-20240307 — 适配笔记

## 基本信息
- **软件**: dialog (display dialog boxes from shell scripts)
- **版本**: 1.3-20240307
- **构建系统**: autotools (configure + make)
- **源码**: https://invisible-mirror.net/archives/dialog/dialog-1.3-20240307.tgz
- **SHA256**: 339d311c6abb240213426b99ad63565cbcb3e8641ef1989c033e945b754d34ef

## 依赖
- ncurses 6.4 (system-installed via cmd-pkgs, static library + bundled headers)

## 适配要点

### 1. config.sub OHOS 平台识别 (E007)
dialog 的 config.sub 不识别 `ohos` 操作系统。补丁 `0001-config.sub.patch` 在 OS 验证列表中添加 `ohos*`，在 kernel-OS 组合验证中添加 `linux-ohos*-`。

### 2. HMDFS umask 077 权限问题 (E007)
configure 脚本和生成的 config.status 使用 `umask 077 && mktemp` 创建临时目录，在 HMDFS 上导致权限拒绝。在 `build()` 方法中，使用 `replace_in_file` 在运行 configure 之前移除 `umask 077`。

### 3. ncurses 依赖处理
ncurses 未发布到 Conan 制品仓，通过 cmd-pkgs 安装静态库 (`libncursesw.a`)，并打包 ncurses 头文件 (`ncurses-headers.tar.gz`)。创建 `libncurses.a -> libncursesw.a` 软链接以匹配 dialog 的 `-lncurses` 链接。

### 4. 构建三元组
传递 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos` 避免 config.guess 调用（config.guess 无法检测 HarmonyOS）。

## 编译选项
- `--with-ncurses`: 使用 ncurses 库
- `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`: 显式构建三元组

## 测试结果
- `make check`: PASS (create-rc test with 5 sample RC files)
- `dialog --version`: PASS (Version: 1.3-20240307)
- `conan create`: PASS (G2 验证通过)
- `test_package`: PASS (dialog --version)
