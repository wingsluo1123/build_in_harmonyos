# libpsl 0.23.3 鸿蒙 PC 升级说明

## 版本与源码

- 这是上游真实发布的 0.23.3，不是下游自造修订号。官方发布资产 SHA-256 为 `93941f85a1e7bd593fa94f299233cb5dfc91cd144fd9a78a6ceb75001c5b03be`。
- 旧官方 main 仅有 0.21.5 与 0.21.5.1，本任务为看板精确分支 `upgrade/libpsl-0.23.3`。
- 从旧版 Conan 配方继承 libidn2/2.3.7.1、libunistring/1.0 依赖与 OHOS Autotools 配置。0.23.3 的 `configure.ac` 已将 `--enable-builtin=libidn2` 标记为弃用，候选改为 `--enable-builtin`，运行时仍明确选用 libidn2。

## 许可证

- 上游 README/COPYING 指明主体 MIT。`src/psl-make-dafsa` 和 `src/lookup_string_in_fixed_set.c` 另受 `src/LICENSE.chromium` 条款约束。Conan 包中复制 LICENSE 与 LICENSE.chromium，不把例外文件错标成 MIT。

## 私有原生验证

- 2026-10-14 授权 `10.62.201.39:2222` 全新私有根 a721：先核对设备清单与固定 SSH 指纹；源码归档和四份候选文件均独立逐字节回读一致。原生 Conan create RC0。
- 构建内 `make check` 两组上游套件分别 3/3 和 5/5，通过率 8/8，零跳过、零失败；安装包消费者实际编译、链接和运行，验证 `com` 公共后缀、`example.com` 非公共后缀、拒绝 `.com` Cookie 域。原始日志 49,585 字节，SHA-256 `ad68d4c9207010dd235a93b32f43708a9907fb8d59c1ef6fa9b35dae044e9c6d`。
- 该验证仅是私有目标原生 Conan；尚无正式 W3、平台 CI、PR 人工审查、合并或积分。配置过程有一次 `error: write on a pipe with no reader` 探针输出，但最终配置、完整测试和 Conan create 均 RC0；需以正式 CI 日志复核。

## 提交边界

仅提交本版本的 conanfile.py、conandata.yml、manifest.yaml、notes.md 和 test_package 下三个源文件；不得包含源码解压目录、下载缓存、私有目标日志或手写 CI 回执。
