# inotify — OpenHarmony 编译档案

## 软件简介
inotify 是一个 C 语言库（libinotifytools）和一套命令行程序（inotifywait/inotifywatch），用于提供 Linux inotify 文件系统事件监控接口。上游仓库为 inotify-tools/inotify-tools。

## 功能概述
- inotifywait：等待文件系统事件
- inotifywatch：统计文件系统事件频率
- libinotifytools：C 语言库，简化 inotify 接口使用

## OHOS 适配要点
- conanfile.py 手写极简 Makefile 直接编译（CI/真机缺 aclocal，上游 autotools 链不可用），未运行上游 configure
- 依赖 Linux inotify 内核接口，OHOS 内核兼容
- 已知限制：OHOS 无 fanotify_init()/fanotify_mark() 实现，fanotify 路径已由 shim 禁用；上游测试中的 fanotify 用例按 ohos_feature 如实上报

## 依赖关系
- 无外部依赖（仅依赖 libc/libc++）

## 参考资料
- [inotify-tools GitHub](https://github.com/inotify-tools/inotify-tools)
- [inotify(7) man page](https://man7.org/linux/man-pages/man7/inotify.7.html)
