# wiki-tui 0.9.2 — 鸿蒙PC (aarch64-linux-ohos) 适配笔记

## 软件简介

wiki-tui 是终端 Wikipedia 浏览器 TUI（Rust / ratatui + crossterm 界面，
wiki-api 后端：reqwest + scraper 解析）。上游 <https://github.com/Builditluc/wiki-tui>，
v0.9.2 为 Rust workspace：根包 `wiki-tui`（bin）+ `wiki-api`（库）+
`wiki-api-macros`（proc-macro），Cargo.lock 锁定 368 个 crate。
上游无顶层 tests/ 目录，唯一测试是 wiki-api/src/search.rs 的内联 #[test]
（Namespace display/from_string 往返，1 处）。

## 适配要点（详见 conanfile.py 文档注释与 manifest.yaml knowledge_gained）

1. **Rust 工具链**：`tool_requires("rust-toolchain/1.97.1")`（仓库内 conan 包，
   rust-lang 官方最小 dist + OHOS aarch64 标准库）。二进制未带 OHOS code
   signature，构建期复制 cargo/rustc/librustc_driver-*.so 并用
   `binary-sign-tool sign -selfSign 1` 自签名；rustc 以
   `--sysroot=<包目录>` 显式指定（签名副本搬离包目录后 rustc 推导不到
   sysroot，E0463）。
2. **cargo 运行期共享库**：cargo 动态链接 libssl.so/libcrypto.so/libz.so
   （实测 NEEDED）。Harmonybrew bottle CDN 会轮换旧版（本任务实测 404），
   改用 cbindgen 0.28.0 方案：`tool_requires` openssl/3.5.8.1 +
   zlib/1.3.2.1，构建期把静态 PIC 归档重链为私有 .so（clang -shared
   --whole-archive），注入 LD_LIBRARY_PATH（OHOS loader 忽略 DT_RUNPATH）。
   零 CDN 依赖、零系统前缀污染。
3. **TLS**：patches/0001 将 wiki-api 的 reqwest 切到 `default-features=false,
   features=["rustls-tls"]`——wiki-api 仅用 Client::get().send().text()，
   纯 Rust TLS 即可，应用层零 OpenSSL 依赖。补丁改了 Cargo.toml 的 feature
   声明，故不用 --locked，cargo 从 rsproxy sparse 镜像重解析 rustls 依赖族
   更新 Cargo.lock（上游其余钉版不变）。
4. **测试**：`cargo test --release --workspace --exclude wiki-api-macros
   --lib --bins`：
   - 最小 dist 不含 rustdoc → doctest 无法编译，用 --lib --bins 排除；
   - wiki-api-macros 是 proc-macro crate，其 lib 测试二进制在 OHOS 上 exec
     时对宿主 proc-macro 动态库重定位失败（exit 127），排除之（构建不受影响）；
   - workspace 根执行需 --workspace 才会跑 wiki-api 的内联测试。
   实测（真机）：1 passed / 0 failed（HMBS_UPSTREAM_TEST_RESULT marker）。
5. **test_package**：真实执行交付的 bin/wiki-tui，4 项断言：--version 报
   0.9.2、--help 列出 --language、--config-path 输出真实路径（非 TUI 纯
   IO 路径）、未知参数非零退出。CI 破坏性负测试（挪走 bin/）通过。

## 验证结果

- conan-verify（G1/G2/G3）：通过（conan create 干净构建 + 真实测试执行）
- W3 本地 CI 模拟：通过（conan create + test_package 4/4 断言 + L0-L5 门禁）
- 交付物：bin/wiki-tui（自签名），LICENSE 随包
---

**编译结束**: 2026-10-17 19:57
**最终状态**: built
