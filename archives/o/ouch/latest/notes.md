# ouch latest 适配笔记

## 编译环境
- 构建系统: Cargo (Rust, edition 2024, rust-version 1.93.0)
- 编译日期: 2026-07-03
- 编译器: clang/clang++ 15
- 状态: built

## 软件信息
- 软件: ouch (A command-line utility for easily compressing and decompressing files and directories)
- 版本: 0.8.0 (latest)
- 语言: Rust
- 许可证: MIT
- 上游: https://github.com/ouch-org/ouch

## 下载
- search-url 找到的 savannah URL 返回 404，软件不存在于 Savannah
- 通过 GitHub API 搜索找到真实仓库: https://github.com/ouch-org/ouch
- 使用 GitHub tarball: https://github.com/ouch-org/ouch/archive/refs/tags/0.8.0.tar.gz
- SHA256: 72ed23c0b2aa51b1b33d3251ddae14cf2bb07a24035d1593c06fc97070e4edf0

## 编译步骤

1. init-build 下载源码（SSL 证书问题，使用 curl -k 手动下载 + --no-download 模式）
2. `cargo build --release` 编译

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | search-url savannah URL 404 | search-url 启发式匹配错误 | 通过 GitHub API 搜索找到 ouch-org/ouch 真实仓库 |
| 2 | SSL 证书验证失败下载 tarball | OHOS 系统 CA 证书路径问题 | 使用 curl -k 手动下载，init-build 使用 --no-download 模式 |
| 3 | 链接器找不到 -lstdc++ | Rust 在 aarch64-unknown-linux-ohos 目标上默认链接 -lstdc++，但 OHOS 系统只有 libc++ (E050/E212) | 在 OHOS SDK lib 目录创建 libstdc++.so 链接器脚本: `echo 'INPUT(-lc++_shared)' > libstdc++.so`，设置 RUSTFLAGS 包含该目录 |
| 4 | conan create 下载 GitHub 源码超时 | GitHub 下载速度慢 (E017) | 在 conandata.yml 中使用 ghfast.top 加速镜像 URL |
| 5 | test_package 使用 Conan 1.x API (deps_cpp_info) | conan-init 生成的模板使用旧 API | 改用 Conan 2.x API: `self.dependencies["ouch"].package_folder` |

## 源码修改
- 无源码修改（纯环境变量和链接器脚本适配）

## 依赖版本
- Rust 1.96.1 (harmonybrew OHOS 适配版)
- clang 15.0.4
- OHOS SDK 26.0.0.18

## 验证结果

```bash
$ ouch --version
ouch 0.8.0

$ cargo test --release
36 passed, 1 failed
```

- conan-verify 8 道门禁全部通过
- 失败测试: `tar_hardlink_pack_and_unpack` — OHOS 硬链接创建权限被拒绝，非代码问题

## 产物信息
| 文件 | 大小 | 说明 |
|------|------|------|
| ouch | 5.4MB | ELF 64-bit aarch64, PIE, Full RELRO |

## 知识图谱
- E212 (草稿): Rust 链接器在 OHOS 上默认 -lstdc++ 但系统只有 libc++
- E050 (命中): OHOS HMDFS 符号链接限制
- E017 (命中): GitHub 下载慢

---

**编译结束**: 2026-07-03 10:24
**最终状态**: built
