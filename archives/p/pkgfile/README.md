# pkgfile

## 简介

pkgfile 是 Arch Linux 生态的 `.files` 元数据浏览器：它把各仓库的 alpm `.files`
数据库（「包 → 文件列表」）转换成本地按仓库分片的缓存，从而支持反查
「某个文件属于哪个软件包」。典型用途是 shell 的 command-not-found 钩子
（`extra/command-not-found.*`）。

常用命令：

```sh
pkgfile --update                 # 拉取并转换仓库 .files 到本地缓存
pkgfile <file>                   # 反查某个文件属于哪个包（默认 -s）
pkgfile --list <pkg>             # 列出包内文件
pkgfile --search --verbose <file># 输出 repo/pkg 版本号 + 命中路径
```

## OHOS 适配

- 构建系统：Meson（`meson.build`），语言标准 **C++20**。
- 产物：`bin/pkgfile`（`package_type = application`，无库/头文件）。
- 版本 25：
  - `configure()` 把 `compiler.cppstd` 抬到 20（CI profile 固定 17，会覆盖上游
    `default_options: cpp_std=c++20`）。
  - OHOS 上启用 `_LIBCPP_ENABLE_EXPERIMENTAL` 并链接 `libc++experimental.a`
    （libc++ 15004 默认不暴露 `std::format`）。
  - 补丁 0001：`-Ddaemon=false` 关闭 `pkgfiled` 守护进程（依赖 libsystemd，
    OHOS 无 systemd 生态，ohpcd 亦无 libsystemd 制品）。
  - 补丁 0002：`-Dman_pages=false` 关闭 man 页生成（依赖 pod2man/perl）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| pcre | 8.45 | 上游 `dependency('libpcre') >= 8.30`（PCRE1，静态） |
| libarchive | 3.8.7 | 读写 alpm `.files` 归档 |
| curl | 8.15.0.1 | 下载仓库元数据（shared） |
| gmock / gtest | 1.17.0 | 仅 `test_requires`，用于上游 `unit_tests` |
| meson / ninja / pkgconf | 1.11.0 / 1.12.1 / 3.0.5 | 仅构建期 |

pthreads 由 meson 内建 `dependency('threads')` 处理，无需 conan 包。

## 功能验证

```sh
# 版本与帮助
pkgfile --version          # pkgfile v25
pkgfile --help

# 离线端到端（test_package 使用的同款流程）
pkgfile --config=<pacman.conf> --cachedir=<cache> --update
pkgfile --config=<pacman.conf> --cachedir=<cache> --search <file>
pkgfile --config=<pacman.conf> --cachedir=<cache> --list <pkg>
```

完整的消费者测试见 `25/test_package/test_pkgfile.sh`（16 个断言点，完全离线）。

## 状态

- `25`：**真机 shadow CI 单包验证通过**（`status: built`）。
  - 门禁：G0/KC/JC/L0/L1/L2/L4/L5 全 pass，`Build Summary: Total 1, Success 1 (100%)`
  - 上游单元测试：`meson test unit_tests` → `1/1 OK, Ok: 1, Fail: 0`（11 个 gtest 用例）
  - 消费者测试：`test_package/test_pkgfile.sh` 离线端到端 16 项断言全通过
  - 产物：`bin/pkgfile` 338432 B，sha256 `a32f83b24425b22624caeb025844e032720557add09b060db2caf60ae327ab14`
  - 详见 `25/reports/device-verification.md`；适配问题全表见 `25/notes.md`
- 未适配项：`pkgfiled` 守护进程（依赖 systemd/libsystemd，有意关闭）；
  27 个 python 集成用例（测试夹具平台假设，见 `25/test_package/MANIFEST.yml`）

## 参考

- 主页：https://github.com/falconindy/pkgfile
