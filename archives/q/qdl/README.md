# qdl

Qualcomm Download —— 与处于 **EDL（Emergency Download）** 模式的骁龙设备通信的
命令行工具：先上传 flash loader（Sahara 协议），再用 Firehose 协议按
`rawprogram*.xml` / `patch*.xml` 描述烧写镜像。上游是
[linux-msm](https://github.com/linux-msm)（Qualcomm 上游内核组织）维护的
[Bash-3-Clause](https://opensource.org/licenses/BSD-3-Clause) 项目。

qdl 提供三个可执行文件：

- **`qdl`** —— 主工具。与 VID `05c6`、PID `9008`/`900e`/`901d` 的 EDL 设备通信，
  支持 `flash <flashmap>`、`create-zip`、`ramdump`、`list` 等子命令，以及
  `--dry-run`（不碰设备，纯解析与摘要生成）与 `--create-digests`（生成要签名的
  VIP 摘要表）
- **`qdl-ramdump`** —— 从设备抓内存转储
- **`qdl-ks`** —— KeyStore 相关操作

- 上游：https://github.com/linux-msm/qdl
- 构建：Meson（`meson setup build && meson compile -C build`）
- 依赖：libusb-1.0（USB 传输）、libxml2（XML 描述解析）、libzip（zip 读写）；
  单元测试另需 cmocka
- 许可证：BSD-3-Clause
- 测试：meson 注册 6 条 —— 4 条 cmocka 单元测试（37 个用例）+
  2 条 bash 集成测试（VIP 表生成、flashmap dry-run）

## OHOS 适配

- **这是一个纯工具包**：上游只 install 三个可执行文件，内部
  `static_library('qdl_common', ...)` 没有 install 规则，也没有任何公共头。
  所以 `package_type = "application"`，`cpp_info` 只设 `bindirs`，
  并按 L0k 在软件级提供 `commands.json`。
- **构建工具**：真机没有 meson（`command -v meson` 为空、python3 也没有
  mesonbuild 模块），`tool_requires("meson/1.11.0")` 引入；同时要在
  `generate()` 里把这个包装脚本的 shebang 去掉（OHOS 上 conan 的
  Python `run()` 无法 execve 带 `#!` 的沙箱内脚本，否则 `Error 126`）。
- **依赖**：libusb-1.0 / libxml-2.0 / libzip 全部经 conan pkg-config 提供
  （制品仓已有 `libusb/1.0.27`、`libxml2/2.15.3.1`、`libzip/1.11.4`）；
  测试用的 `cmocka/2.0.2` 声明为 `test_requires`，不进包也不传给消费者。
- **归档器**：conan 的 MesonToolchain 不写 `ar`/`ranlib`，而 OHOS 上它们叫
  `llvm-ar`/`llvm-ranlib`，需从 c 编译器同目录推导绝对路径注入 native file。
- **版本号**：上游用 `git describe` 推版本，tarball 里没有 `.git`，不钉住的话
  `qdl --version` 会打印 `unknown-version`；配方显式写入 meson 的 `VERSION`
  选项，产物报 `qdl version 2.7`。
- **上游测试真实执行**：不裁剪 test/，`build()` 内跑 `meson test -v`，
  6 条测试的结果进入 `conan create` 日志。
- **唯一的上游改动**：两个 bash 集成测试用 `uname -s` 挑可执行文件名，只认
  `Linux*|Darwin*` 与 `CYGWIN*|MINGW*|MSYS*`，其余平台 `exit 1` —— 而
  HarmonyOS 的 `uname -s` 正是 `HarmonyOS`。补丁只往这个 case 里加
  `HarmonyOS*`，不动产物代码。

## References

- https://github.com/linux-msm/qdl
- https://github.com/openai/qdl — 上游文档里提到的同类实现之一
- https://www.qualcomm.com/ — EDL / Firehose / Sahara 相关背景
