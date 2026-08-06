# sipsak 0.9.7 HarmonyOS PC 适配说明

## 源码

- 版本：0.9.7
- 来源：官方 GitHub Release (nils-ohlmeier/sipsak 0.9.7)
- 校验：`conandata.yml` 中固定 SHA-256

## 构建方式

配方不运行旧版 Autotools，而是使用 Conan 构建环境中的 C 编译器直接编译
命令行程序所需的源文件。这样不依赖 OHOS CI 中缺失的 Autotools 工具，也不会
触发旧 `config.guess`、`config.sub` 或 `configure` 在 HMDFS 上的问题。

主要兼容选项：

- `-D_GNU_SOURCE`：声明 musl 提供的 GNU 扩展接口。
- `-fcommon`：保持 sipsak 0.9.7 旧源码中 tentative definitions 的链接语义。
- 显式 `HAVE_*` 和包版本宏：替代 `configure` 生成的配置头。
- Conan build-type 标志：分别支持 Debug、Release、MinSizeRel 和 RelWithDebInfo。

当前配方不修改上游源码，因此没有应用补丁。历史 Autotools 和源码补丁已移除，
避免让维护者误以为它们参与当前构建。

## 测试

上游包含两个基于 Check 框架的单元测试源文件：

- `tests/check_helper.c`
- `tests/check_md5.c`

OHOS 设备环境提供 Check 框架（/storage/Users/currentUser/usr/local）时，
配方会编译并运行上游 `tests/check_helper` 与 `tests/check_md5` 两个单元测试；找不到 Check 时才跳过。
`test_package/test_sipsak.sh` 使用 Bash 严格模式验证安装后的可执行文件存在，并确认
`sipsak --version` 输出版本 0.9.7。
