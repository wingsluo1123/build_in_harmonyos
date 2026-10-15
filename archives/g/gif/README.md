# gif

GIF 图像格式编码/解码库（上游：giflib 5.2.2，https://sourceforge.net/projects/giflib/）。

## 已适配版本

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|---------|------|
| 5.2.2 | built | makefile | 纯 Makefile；补丁 0001 修正 OHOS head 负数偏移 |

## 使用

Conan 包 `gif/5.2.2`：

```python
self.requires("gif/5.2.2")
```

库：`gif`（libgif）；头文件：`gif_lib.h`；CMake 目标：`gif::gif`；
pkg-config：`giflib`。

## 适配要点

- 上游为纯 Makefile（无 configure），编译器/归档器经 Conan conf
  `tools.build:compiler_executables` 获取，flags 走 make 命令行。
- 上游回归套件（tests/makefile）需先构建工具；包只发布库与头文件。
- OHOS `head` 不支持 GNU `--bytes=-N`，补丁用 `wc -c` + `dd bs=1` 保持截断语义。
