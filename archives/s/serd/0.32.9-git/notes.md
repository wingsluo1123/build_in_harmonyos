# 编译记录: serd 0.32.9-git

**编译开始**: 2026-07-27
**最终状态**: built (上游 meson test 运行)

---

## 编译环境

- 构建系统: meson + ninja
- 编译器: clang (aarch64-linux-ohos)
- 目标平台: aarch64 (OpenHarmony)
- 源码: serd-0317806.tar.gz (git 0317806)

## 源码完整性

| 项 | 值 |
|----|----|
| URL | https://gitlab.com/drobilla/serd/-/archive/0317806/serd-0317806.tar.gz |
| SHA-256 | 4cec57d40ff913a4530043ffc6e37f80b758f08fb807ac8d73b832d31f336a78 |
| 大小 | 380829 bytes |

## 许可证

ISC (Copyright 2011-2025 David Robillard <d@drobilla.net>)

## 编译步骤

1. `meson.configure()` + `meson.build()` — 编译 libserd-0.a 和 serdi
2. `meson.test()` — 运行上游测试套件 (node, reader, writer, env, string, uri)
3. `meson.install()` — 安装 libserd-0.a、serdi、serd-0.pc、include/serd-0/serd/*.h

## 依赖

- zix/0.8.1-git (基础工具库)

## 验证结果

```bash
$ pkg-config --modversion serd-0
0.32.9
```

---

**编译成功** ✓
