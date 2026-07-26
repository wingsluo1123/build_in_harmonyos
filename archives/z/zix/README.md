# Zix

## 简介
Zix 是 David Robillard 开发的轻量级 C 基础工具库，提供 LV2 生态共用的常用数据结构和系统工具。

## 功能概述
- B-tree / tree 数据结构
- Ring buffer 环形缓冲区
- Semaphores 信号量
- Filesystem 文件系统操作
- Thread 线程支持
- Allocator 内存分配器
- String / digest 工具

## OHOS 适配
- 构建系统：meson (default_library=static)
- 上游 `meson test` 在 `build()` 阶段运行
- 硬链接相关测试可能因 OpenHarmony 平台限制失败，不影响作为 LV2 生态依赖库使用

## 依赖
- 无外部必需依赖（threads 由系统提供）

## 功能验证
```bash
pkg-config --modversion zix-0  # 输出: 0.8.1
```

## 参考
- 官网：https://drobilla.net/software/zix
- 源码：https://gitlab.com/drobilla/zix
