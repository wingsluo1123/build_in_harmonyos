# 编译记录: sord 0.16.22-git

**编译开始**: 2026-07-27
**最终状态**: built (上游 meson test 运行)

---

## 编译环境

- 构建系统: meson + ninja
- 编译器: clang (aarch64-linux-ohos)
- 目标平台: aarch64 (OpenHarmony)
- 源码: sord-c9b049b.tar.gz (git c9b049b)

## 源码完整性

| 项 | 值 |
|----|----|
| URL | https://gitlab.com/drobilla/sord/-/archive/c9b049b/sord-c9b049b.tar.gz |
| SHA-256 | 560bfd76aa87d248e6ea21c2d5100da4354aa0abbf3a0824af3163407a31eb1c |
| 大小 | 286929 bytes |

## 许可证

ISC (Copyright 2011-2025 David Robillard <d@drobilla.net>)

## 编译步骤

1. `meson.configure()` + `meson.build()` — 编译 libsord-0.a 和 sordi
2. `meson.test()` — 运行上游测试套件 (test_sord)
3. `meson.install()` — 安装 libsord-0.a、sordi、sord-0.pc、include/sord-0/sord/*.h

## 依赖

- zix/0.8.1-git (基础工具库)
- serd/0.32.9-git (RDF 序列化库)

## 验证结果

```bash
$ pkg-config --modversion sord-0
0.16.22
```

---

**编译成功** ✓
