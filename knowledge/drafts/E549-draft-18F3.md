# E549: 老 XOSD 客户端对 libxosd 2.2.14 的 xosd_init() 7 参 API 漂移

## 基本信息
- **严重度**: 2（🟡medium）
- **类别**: linking
- **来源**: osdclock 0.5 适配（feat/osdclock-0.5，HarmonyOS PC / OHOS aarch64）
- **贡献者**: 18F3（草稿）

## 错误特征
```
too few arguments to function call, expected 7, have 6|xosd_init|number_lines
```

## 根因
osd_clock 0.5（2001）针对 xosd 0.7.0 编写，而唯一在发行的 libxosd 2.2.14 把 xosd_init() 扩到 7 参（新增 number_lines）。仅补第 7 参不够：xosd_display() 有 0 <= line < number_lines 校验，而该程序在 line 1 上绘制。

## 推荐方案
xosd_init 补第 7 参 number_lines=2（保留 line 1 绘制语义），并把 deprecated xosd_uninit() 换成 xosd_destroy()。

## 关联
- 配方: `archives/o/osdclock/0.5/conanfile.py`、`patches/`
- 测试: `archives/o/osdclock/0.5/test_package/test_osdclock.sh`

> 本文件为草稿配套文档（R31/W5：E###.kv ↔ doc/E###.md 配套），待主编审核后 promote 为正式条目。
