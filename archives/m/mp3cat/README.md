# mp3cat

MP3 流处理工具，用于拼接、清洗和分片 MP3 流。

## 功能

- **流清洗**：从输入流中提取有效 MP3 帧，丢弃非帧数据
- **目录分片**：将 MP3 流按指定大小分片写入目录（current.mp3 + 时间戳文件）
- **尾部读取**：从 mp3dir 目录的 current.mp3 尾部开始读取（live stream 模式）
- **详细模式**：`-v` 输出帧解析详情到 stderr

## OHOS 适配

- 原始 Makefile 硬编码 `cc`，通过补丁改为 `$(CC)` 支持编译器覆盖
- 原始 Makefile 不支持 `DESTDIR`，通过补丁添加以支持 staging 安装
- 原始代码不支持 `--version`/`--help`，通过补丁添加以满足 smoke test 门禁
- 终端工具静态链接（R26），避免动态库依赖问题
- R33: conanfile.py 中编译器路径从 `self.conf.get()` 获取

## 依赖关系

- 编译依赖：无
- 运行依赖：无（静态链接，无动态库依赖）

## 参考资料

- 源码：https://github.com/tomclegg/mp3cat
- 许可证：GPL-2.0-or-later
