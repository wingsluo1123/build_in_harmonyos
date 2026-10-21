# IRAF

IRAF 2.18.1 的 HarmonyOS PC / AArch64 原生 Conan 配方。保留 CL/ECL、
SPP/Ratfor/F2C 编译链、核心图像处理任务和 NOAO 天文处理包。

```sh
conan create archives/i/iraf/2.18.1 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

使用 Conan 的运行环境进入 `irafcl`、`cl`、`ecl`、`xc` 等命令；运行环境同时为
已安装的 `xc` 传播 zlib 的编译及链接元数据，并保留其运行期静态归档。启动器相对解析包目录，
临时文件默认位于 `$HOME/.cache/iraf/tmp`，也可通过 `TMPDIR` 指定可写目录。

自举构建及上游 `make test` 在 `build()` 内执行，随后 `test_package` 从安装包
验证版本、两个解释器、图像/FITS、SPP 编译和 ARM64 错误现场恢复。
具体证据、测试统计和使用边界见 [2.18.1/notes.md](2.18.1/notes.md)。
