# libupnpp

libupnpp 是基于 libnpupnp 的 C++ UPnP 设备和控制点封装。
上游：https://www.lesbonscomptes.com/upmpdcli/ 。

1.0.4 默认交付共享库、公共头文件及 pkg-config/CMake 消费元数据。
OHOS 安装后的版本库及 SONAME 别名为真实文件，按当前 SDK 重新签名；
不修改系统目录或已发布依赖。当前验证范围为 OHOS 6 arm64 / Clang 15。
详见版本目录的测试报告；真机通过不等于比赛 CI 或正式发布。
