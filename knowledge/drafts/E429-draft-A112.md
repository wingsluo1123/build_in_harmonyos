# E429: aarch64 char 无符号 + getopt_long 返回值承接错误导致选项循环死锁

## 基本信息
- **严重度**: 2（🟡medium）
- **类别**: portability
- **来源**: osdclock 0.5 适配（feat/osdclock-0.5，HarmonyOS PC / OHOS aarch64）
- **贡献者**: A112（草稿）

## 错误特征
```
comparison of constant -1 with expression of type 'char' is always true|char c; while \(\(c = getopt_long|always true \[-Wtautological-constant-out-of-range-compare\]
```

## 根因
aarch64/ARM 上 char 默认无符号：getopt/getopt_long 返回 -1 存入 char 变 255，与 -1 比较恒真，选项循环永不退出（程序在 xsd 初始化前空转）。x86 上 char 有符号，故上游与 Debian 补丁集都不需要修。

## 推荐方案
承接 getopt/getopt_long 返回值的变量必须是 int（clang 判据 -Wtautological-constant-out-of-range-compare）；回归测试加 timeout，打补丁前后 rc 124(悬死)→1。

## 关联
- 配方: `archives/o/osdclock/0.5/conanfile.py`、`patches/`
- 测试: `archives/o/osdclock/0.5/test_package/test_osdclock.sh`

> 本文件为草稿配套文档（R31/W5：E###.kv ↔ doc/E###.md 配套），待主编审核后 promote 为正式条目。
