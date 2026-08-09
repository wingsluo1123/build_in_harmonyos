# Xapers

## 简介

xapers 是一个个人论文/文献管理工具，基于 Xapian 提供本地文献索引、导入与检索能力。

## 基本信息

- **软件名称**: xapers
- **显示名**: Xapers
- **描述**: 个人论文/文献管理工具（Xapian 本地索引）
- **分类**: tool
- **官网**: https://finestructure.net/xapers
- **许可证**: GPL-3.0+
- **构建系统**: setuptools (Python)

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.9.0 | built | 2026-08-09 |

## OHOS 适配说明

- 纯 Python 包（py3-none-any），无 C 编译
- 运行依赖: xapian Python 绑定（xapian-core 1.4.26 + xapian-bindings 源码构建）、pybtex、pycurl、urwid
- 上游 0.9.0 发布未更新 version.py（仍为 0.8.2），已用补丁修正为 0.9.0
- 平台限制: xapian UUID 生成读 /proc/sys/kernel/random/uuid 无权限，上游测试套件 27/83 通过（basic 组 8/8 全过）
