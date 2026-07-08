# mp3cat 0.5 适配笔记

## 编译环境
- 构建系统: makefile（纯手写 Makefile，无 configure 脚本）
- 编译日期: 2026-06-30
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

mp3cat 使用纯手写 Makefile，无 autotools 的 configure 脚本。编译流程：

```bash
# 1. 修改 Makefile 支持 CC/CFLAGS/LDFLAGS 变量和 DESTDIR（补丁 0001）
# 2. 修改 mp3cat.c 添加 --version/--help 支持（补丁 0002）
# 3. 静态链接编译
make CC=clang CFLAGS='-O2' LDFLAGS='-static' -j1
# 4. 安装到 staging
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络无法直连 github.com | 使用 ghfast.top 镜像 + curl 下载 |
| 2 | /tmp 只读 | 鸿蒙 E002：/tmp 为只读文件系统 | 使用 $TMPDIR |
| 3 | Makefile 硬编码 cc | 原始 Makefile 用 `cc -o mp3cat *.c` | 补丁 0001：改为 `$(CC) $(CFLAGS) -o mp3cat *.c $(LDFLAGS)`，添加 DESTDIR |
| 4 | 二进制动态链接 | 默认编译为动态链接 | 使用 `LDFLAGS=-static` 静态链接（R26 终端工具） |
| 5 | test_package 用 Conan 1.x API | 模板生成代码用 `deps_cpp_info` | 重写为 Conan 2.x VirtualRunEnv + test.sh |
| 6 | L2 smoke test 失败 | mp3cat 不支持 `--version`/`--help` | 补丁 0002：添加 `--version` 和 `--help` 支持 |
| 7 | conandata.yml patches 格式错误 | 多了一层嵌套 | 修正为 Conan 2.x 标准列表格式 |
| 8 | R33 合规：编译器路径 | conanfile.py build() 硬编码 `clang` | 改用 `self.conf.get("tools.build:compiler_executables:c", "clang")` |

## 源码修改

### 补丁 0001-Makefile.patch
- **文件**: Makefile
- **类型**: portability
- **内容**: `cc` → `$(CC)`，添加 `CC?=`/`CFLAGS?=`/`LDFLAGS?=`，install 目标添加 `$(DESTDIR)` 前缀

### 补丁 0002-mp3cat.c.patch
- **文件**: mp3cat.c
- **类型**: feature
- **内容**: 添加 `--version`（输出 "mp3cat 0.5"）和 `--help`（输出用法到 stdout），exit(0)

## 依赖版本

无外部依赖。纯 C 程序，仅依赖标准库。

## 验证结果

```bash
# 静态链接
$ file mp3cat
mp3cat: ELF executable, 64-bit LSB arm64, static, not stripped
$ readelf -d mp3cat
There is no dynamic section in this file.

# 功能测试
$ mp3cat --version → "mp3cat 0.5"
$ mp3cat - - < dirty.mp3 > clean.mp3  # 流清洗：1351→834字节
$ mp3cat --size 500 - /tmp/mp3dir < stream.mp3  # 目录分片

# Conan 验证（8道门禁全部通过）
G0 ✅ G1 ✅ G2 ✅ G3 ✅ G4 ✅ L2 ✅ L4 ✅ L5 ✅
```

## 产物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| bin/mp3cat | ELF binary (static) | 主程序，MP3流处理 |
| bin/mp3log | shell script | 日志记录脚本 |
| bin/mp3log-conf | shell script | 日志配置脚本 |
| bin/mp3dirclean | shell script | 目录清理脚本 |
| bin/mp3http | shell script | HTTP流脚本 |
| bin/mp3stream-conf | shell script | 流配置脚本 |

## 注意事项

1. mp3cat 的 `--tail` 模式设计为 live stream tailing，会持续监听文件增长
2. 静态链接是必须的（R26 终端工具）
3. `--version`/`--help` 为补丁添加的功能，原始代码不支持
4. R33: conanfile.py 中编译器路径必须从 `self.conf.get()` 获取
5. R38: 软件级目录需创建 commands.json（CLI 工具声明）

---

## 结束标记

最终状态: published
编译结束
