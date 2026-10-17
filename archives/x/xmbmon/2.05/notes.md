# xmbmon 2.05 适配说明

保留原版mbmon和xmbmon前端，通过C接口桥接平台热管理服务，读取system_h、Battery、shell_frame。
原版ISA/SMBus直接访问依赖x86端口I/O，未在aarch64执行。四项原始诊断已在WSL x86_64
对照运行，4项均以255失败；WSL root复查仍报告I/O不可用，详见reports/test-report.md。
温度名称保留系统语义，不重命名为CPU/主板。

平台服务使用`std::__h`，SDK使用`std::__n1`。共享桥接库隔离平台C++ ABI，前端仅调用C接口。
19个固定版本头文件保留provenance和Apache-2.0声明。内部接口按已测固件约束，非跨版本公共NDK承诺。
复用E077：链接时设置最终RPATH，安装时保持已签名ELF字节。

`--fan-raw`读取主机HDC采集器原子发布的两路真实raw记录。单位未确认RPM，超过5秒或记录异常返回N/A和exit3。
原版`-F`的RPM输出继续为N/A。主板电压按本轮范围排除，不以电池电压替代。

本机GUI由独立部署辅助脚本运行官方OHOS Xvfb和浏览器查看器，支持刷新与两档缩放，不是ArkUI窗口。
详情见integration.md、reports/test-report.md及reports/display/README.md。

本次仅申请C候选及验收范围确认，工程功能仍为partial。原生构建和已声明测试通过，不宣称完整主板监测或专项通过。
---

**编译结束**: 2026-10-06 17:28
**最终状态**: built
