# lv 4.51-10.1 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-07-18
- 编译器: clang 15.0.4
- 状态: built

## 软件简介
lv (Leap View) 是一个强大的多语言文件查看器，类似于 less/more，支持多种编码。

## 编译步骤
1. init-build: 下载源码，初始化构建环境
2. configure: ./configure --prefix=/ --enable-static --disable-shared
3. make: 编译成功，生成 lv 二进制
4. package: 安装二进制和 lv.hlp 帮助文件

## 遇到的问题
- HMDFS 不支持硬链接，lgrep 改为符号链接
- 源码在 src/ 子目录中，configure 脚本位于 src/ 下
- lv.hlp 位于源码根目录，不在 src/ 中

## 依赖
- ncurses: 系统预装
