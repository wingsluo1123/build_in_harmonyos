# rmlint

[![GitHub stars](https://img.shields.io/github/stars/sahib/rmlint)](https://github.com/sahib/rmlint)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue)](https://www.gnu.org/licenses/gpl-3.0)

## 简介

rmlint 是一个极快的文件系统清理工具，能够发现并移除：

- **重复文件** 和重复目录
- **未剥离调试符号的二进制文件**（non-stripped binaries）
- **损坏的符号链接**
- **空文件和空目录**
- **用户/组 ID 损坏的文件**

## 特性

- 性能极快（相比同类工具如 fdupes 有显著优势）
- 支持多种哈希算法（SHA1, SHA256, SHA512, xxHash 等）
- 偏执模式（Paranoia mode）：不信任哈希值时进行逐字节对比
- 多种输出格式（JSON, CSV, shell 脚本等）
- 支持缓存和重放
- 支持 BTRFS 特性

## 构建系统

SCons（Python 构建系统）

## 依赖

- glib >= 2.64（必需）
- scons（构建工具）
- （可选）libelf, json-glib, GTK3, gettext

## 版本

- v2.10.3 (Ludicrous Lemur) - 最新稳定版