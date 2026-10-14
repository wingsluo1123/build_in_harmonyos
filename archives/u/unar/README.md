# unar

Universal Archive Reader（MacPaw/XADMaster）—— 支持 7z、zip、tar、gzip、bzip2、rar、cab、xz、arj、lzma 等 60+ 种归档格式的解包与列表命令行工具（Objective-C 2.0 / GNUstep）。

- 上游: https://github.com/MacPaw/XADMaster
- 许可证: LGPL-2.1
- 构建系统: GNU make（Makefile.linux）

## 产物

| 文件 | 说明 |
|------|------|
| bin/unar | 解包工具（`unar -o <dir> <archive>`） |
| bin/lsar | 归档列表工具（`lsar <archive>`） |
| lib/libtzguard.so | 加载期时区兜底库（OHOS 无系统时区数据时设 TZ=UTC；必须作为首个 DT_NEEDED 先于 libgnustep-base.so 加载） |

## 版本

| 版本 | 状态 |
|------|------|
| 1.10.8 | 适配中 |

## 平台适配要点（OHOS）

- musl 无 getpass()/REG_STARTEND → 补丁 0001/0002
- XADRegex regexec 需 NUL 终止输入（musl 堆越界读导致 tar.gz 识别失败）→ 补丁 0002
- gnustep-base 加载期固化时区状态（OHOS 无 TZ/localtime/zoneinfo）→ libtzguard.so + 补丁 0003/0004

详见 `1.10.8/notes.md`。
