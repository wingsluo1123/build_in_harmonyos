# Serd

## 简介
Serd 是 David Robillard 开发的轻量级 RDF 序列化库，用于读写 RDF 数据格式。

## 功能概述
- 支持 Turtle, N-Triples, JSON-LD 格式
- 提供 serdi 命令行工具进行格式转换
- 高性能流式处理

## OHOS 适配
- 构建系统：meson (default_library=static)
- 上游 `meson test` 在 `build()` 阶段运行
- 静态库方式打包，作为 sord 的前置依赖

## 依赖
- zix/0.8.1-git (基础工具库)

## 功能验证
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib
serdi --version  # 输出: serdi 0.32.9
```

## 参考
- 官网：https://drobilla.net/software/serd
- 源码：https://gitlab.com/drobilla/serd
