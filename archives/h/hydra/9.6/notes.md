# hydra 9.6 适配笔记

## 构建环境

- 构建系统: Autotools
- 编译日期: 2026-07-15
- 编译器: clang / clang++
- 平台: HarmonyOS PC (aarch64)
- 状态: built

## 源码与依赖

- 源码: https://github.com/vanhauser-thc/thc-hydra/archive/refs/tags/v9.6.tar.gz
- SHA-256: `c839e5c64ef60185c69a07a9a59831bd2cfe9ac2eac0c4d9e87fdf38dbf04c40`
- 依赖: `openssl/1.1.1w`、`zlib/1.3.1`

## Conan 配方

配方通过 `AutotoolsToolchain` 传递 OHOS 交叉编译环境，先执行
`configure --disable-xhydra --nostrip`，再执行 `make` 和 `make install`。图形界面被禁用，
安装阶段不调用上游硬编码的宿主 `strip`。
缺少 libssh、libidn、ncurses 等可选库时，上游配置脚本会禁用对应模块。

## 验证

`test_package/test.sh` 运行 `hydra -h` 与 `pw-inspector -h`，并检查两个工具的
版本输出。软件仅应用于合法、已授权的安全测试。
