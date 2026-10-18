# scrot

scrot (SCReenshOT) is a simple command line screen capture utility using
imlib2 to grab and save images. Upstream:
https://github.com/resurrecting-open-source-projects/scrot

Works in X11-based environments only.

## 已适配版本

| Version | Status | Date |
|---------|--------|------|
| 2.0.0 | built | 2026-10-17 |

## 构建说明

- 构建系统：autotools (configure + make)
- 构建命令：`./configure --prefix=/ && make && make install`
- 上游 2.0.0 无测试套件（无 tests/ 目录，Makefile.am 无 TESTS，
  无 `make check` 目标），build() 不调用上游测试
- test_package 执行 headless-safe 探针：
  `scrot --version` / `scrot --help`，均无需 X display
- Conan profile：ohos-aarch64

## 依赖

| Dependency | Version | Source |
|-----------|---------|--------|
| libx11 | 6.4.0 | conan registry (ohpcd) |
| libxcomposite | 0.4.6 | conan registry (ohpcd) |
| libxfixes | 6.1.0 | conan registry (ohpcd) |
| libxrandr | 1.5.5.1 | conan registry (ohpcd) |
| imlib2 | 1.9.1 | conan registry (ohpcd) |

> 注意：上游 deps.pc 要求 imlib2 >= 1.11.0 且需要 X 支持；
> 仓库内唯一含完整配方的 imlib2 是 1.9.1（--without-x 构建）。
> 版本/X 支持缺口已在 2.0.0/notes.md 如实记录，待真机预检给出机器证据。
