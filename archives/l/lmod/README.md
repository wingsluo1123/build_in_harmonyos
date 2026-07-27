# Lmod — Lua 环境模块系统

Lmod 是一个基于 Lua 的环境模块系统，用于动态管理 Unix/Linux 系统的用户环境变量。
它兼容传统 TCL 模块文件，并支持软件层级（Software Hierarchy）功能。

**上游仓库**: https://github.com/TACC/Lmod  
**文档**: https://lmod.readthedocs.io/  
**许可证**: MIT

## 功能特点

- 完全兼容 TCL 模块文件（Environment Modules TCL 格式）
- 内建软件层级（Software Hierarchy）支持，自动管理编译器/库的匹配
- 支持 bash、zsh、csh、tcsh、fish 等主流 Shell
- 提供 `module` 命令的统一接口
- 支持 Spider Cache 加速模块查询

## 版本

- 9.2.5 — 当前版本
