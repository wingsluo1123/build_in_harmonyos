# Sord

## 简介
Sord 是 David Robillard 开发的轻量级 RDF 内存存储库，提供快速 RDF 数据存储和查询功能。

## 功能概述
- RDF 内存存储
- 快速 RDF 查询
- 提供 sordi 命令行工具进行 RDF 查询
- 基于 serd 的 RDF 序列化

## OHOS 适配
- 构建系统：meson (default_library=static)
- 上游 `meson test` 在 `build()` 阶段运行
- 静态库方式打包，作为 lilv 的前置依赖

## 依赖
- zix/0.8.1-git (基础工具库)
- serd/0.32.9-git (RDF 序列化库)

## 功能验证
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib
sordi --version  # 输出: sordi 0.16.22
```

## 参考
- 官网：https://drobilla.net/software/sord
- 源码：https://gitlab.com/drobilla/sord
