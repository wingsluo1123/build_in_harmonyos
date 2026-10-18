# wlc

wlc 是 Weblate 的命令行客户端与 Python API。上游固定为 PyPI 2.0.0，GPL-3.0-or-later；本归档只修复分页时首请求 params 被重复追加的问题。

配方从固定 sdist 构建真实 wheel，并执行完整 unittest suite。运行依赖的官方纯 Python wheels 固定 URL/SHA 并随包保留各自元数据与许可证；setuptools、responses 和 PyYAML 仅用于构建或测试。仅向 Conan 私有 build/package 目录解压依赖，不全局安装。

CLI 入口为 `wlc`；Python 入口为 `from wlc import Weblate`。功能调用需要用户自行配置的 Weblate URL/凭据，测试只使用随包固件与本机回环服务。

Windows 主机完整219项及一个安装消费者通过。OHOS H1-008原218项、安装消费者和官方W3工具rc0，H1-009另补新增单测1/1；未声称一次合跑219。CLI version/help的官方L2 SKIP/WARNING保留；W4、PR及提审按原交付入口继续，详见版本notes和test-report。
