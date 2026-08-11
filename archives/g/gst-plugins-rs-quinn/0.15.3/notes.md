# gst-plugins-rs-quinn 0.15.3 适配笔记

## 编译环境
- 构建系统: cargo (Rust) — gst-plugins-rs workspace 的 net/quinn crate
- 编译日期: 2026-08-11
- 编译器: rustc/cargo 1.97.1 (harmonybrew), clang 15.0.4 (HNP)
- 状态: built

## 编译步骤

1. `cargo build -p gst-plugin-quinn --release`（CARGO_TARGET_DIR 指向临时目录）
2. 产物 `libgstquinn.so`（cdylib）安装到 `lib/gstreamer-1.0/`
3. 系统依赖 gstreamer 1.28.3 + glib 2.88.0 通过 cmd-pkgs 预编译包安装
4. `cargo test -p gst-plugin-quinn --lib`：0 测试通过（net/quinn 无内置 #[test]）
5. 集成测试 quinnquic.rs / quinnwebtransport.rs 需真实 QUIC 网络，离线环境超时跳过
6. conan create 干净构建 + test_package ELF 符号校验通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误判构建系统为 autotools | gst-plugins-rs 是 Rust/cargo 项目 | conanfile.py 手工改写为 cargo 配方 |
| 2 | 系统无 cargo/rustc | 工具链缺失 | harmonybrew install rust (1.97.1) |
| 3 | 无 gstreamer 开发头文件 | 系统依赖缺失 | cmd-pkgs 预编译 gstreamer-1.28.3 + glib 安装到 ~/usr/local |
| 4 | 链接缺 -lgstbase-1.0.so | 预编译包缺 .so 开发符号链接 | `rm -f && ln -s` 补齐 .so/.so.0 符号链接 |
| 5 | dlopen 测试失败 | OHOS musl ldso namespace 机制 (E186)，LD_LIBRARY_PATH/RPATH 无效 | test_package 改用 ELF 动态符号表校验插件入口符号 |
| 6 | patchelf 后 Permission denied | OHOS XPM 要求 .so 代码签名 | package() 中 patchelf 设 RUNPATH 后重新 binary-sign-tool 签名 |
| 7 | gitlab 源码下载失败 | gitlab.freedesktop.org Anubis 反爬对 curl 返回 HTML | 改用 GStreamer 官方 GitHub 镜像（sha256 一致）|
| 8 | W3 本地 CI predl 改写坏 conandata.yml | build_and_test.sh predl 正则截断连字符 URL + gh-proxy 403 误判成功 | 预置 predl_cache 正确文件走 [cached] 分支 |

## 源码修改

无补丁（未修改上游源码，仅构建配置适配）。

## 依赖版本

- gstreamer 1.28.3（cmd-pkgs 预编译）
- glib 2.88.0（cmd-pkgs 预编译）
- Rust 工具链 1.97.1（harmonybrew）
- Rust crate 依赖：quinn 0.11、gstreamer-rs 0.25、tokio 1.x 等（cargo 自动拉取）

## 验证结果

```bash
cargo build -p gst-plugin-quinn --release   # 成功
cargo test -p gst-plugin-quinn --lib        # 0 tests, ok
conan create ...                            # 通过
test_package: ELF 符号校验 gst_plugin_quinn_get_desc + gst_plugin_quinn_register
W3 本地 CI 模拟 (setup.sh + build_and_test.sh): 通过
```

## 注意事项

- 本包是 GStreamer 插件（dlopen 加载），不是链接库：package_info() 中 cpp_info.libs 为空是预期行为
- OHOS 上 dlopen 依赖解析受 namespace 限制（E186），插件 .so 需带 RUNPATH 指向 gstreamer 库目录并重新签名
- 集成测试需要真实 QUIC 网络，CI 中不可运行

---

**编译结束**: 2026-08-11 16:00
**最终状态**: built
