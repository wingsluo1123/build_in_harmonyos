# osdclock

X On-Screen Display 时钟：以 `strftime(3)` 格式把当前时间画在 X 根窗口上（经 libxosd）。

- 上游版本：0.5（2001，Jon Beckham）
- 上游主页：<http://leftorium.net/software.phtml>（站点已停，源码取自 Debian pool 的原始发布副本，见 0.5/conandata.yml 说明）
- 许可：GPL-2.0-or-later
- 构建系统：makefile（上游自带手写 Makefile，无 configure/CMake）
- 适配状态：见 [0.5/manifest.yaml](0.5/manifest.yaml)

## 构成

| 文件 | 说明 |
|------|------|
| `commands.json` | 命令行工具声明（R38） |
| `manifest.yaml` | 软件级元数据（依赖、适配要点、版本索引） |
| `0.5/conanfile.py` | Conan 配方（make 驱动 + 补丁 + 安装） |
| `0.5/conandata.yml` | 源码 URL/sha256 + 两个 portability 补丁声明 |
| `0.5/patches/` | 0001 libxosd 2.2.14 API 适配；0002 aarch64 getopt 返回值类型修复 |
| `0.5/test_package/` | 真实执行二进制的 5 条用例 / 9 条断言（无需 X server） |

## 依赖

`libxosd/2.2.14`（唯一在发行的 XOSD 实现，经 `cpp_info.requires` 传递
`libx11/6.4.0` + `libxext/6.4.0` + `libxinerama/1.1.5` + `xorgproto/2025.1`），
另按运行期 `DT_NEEDED` 闭包显式声明 `libxcb/1.16` + `libxau/1.0.11` + `libxdmcp/1.1.5`。
全部为 ohpcd 已发布 OHOS armv8 二进制，不依赖编译环境预编译 X11 栈。

## 用法

```bash
conan install --requires=osdclock/0.5 -pr=ci/conan/profiles/ohos-aarch64
osd_clock -F '%H:%M' -c green -t -o 20     # 需要可达的 X server
osd_clock -h                               # 查看全部选项
```
