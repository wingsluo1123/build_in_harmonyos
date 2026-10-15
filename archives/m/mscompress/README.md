# mscompress

**Microsoft "compress.exe/expand.exe" 兼容的 LZ77 压缩/解压工具**

mscompress 是 Microsoft compress.exe 格式的压缩/解压实现，提供两个命令行程序：

- `mscompress` — 使用 LZ77 算法压缩文件，输出可用 Microsoft expand.exe 或 msexpand 解压
- `msexpand` — 解压 Microsoft compress.exe 压缩的文件（如 Win 3.x 安装文件）

## 用法

```bash
mscompress file.txt          # 生成 file.txt_
msexpand < file.txt_ > out   # 解压回原始内容
```

## 构建

- 构建系统：autotools（configure.ac + Makefile.am），需 `autoreconf -fiv` 生成 configure
- 版本：0.4
- 许可证：GPL-2.0
- 源码：https://github.com/stapelberg/mscompress （tag 0.4，commit 988955729c1537f441e746a41b8977db860e4d65）

## OHOS 适配

- 零外部依赖（纯 libc），双 CLI 程序打包为 application
- `--build/--host=aarch64-unknown-linux-ohos` 显式传入（config.guess 不识 HarmonyOS）
- tool_requires `automake/1.18` + `libtool/2.5.4`（CI 最小镜像缺 automake 工具链）
- 上游 `test.sh` 往返测试直接复用为 HarmonyOS 专项测试
