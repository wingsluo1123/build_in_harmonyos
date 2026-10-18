# SOAPsnp 1.03 适配记录

源码为 Ubuntu 官方 archive 保存的 1.03 upstream orig（SOAPsnpZ），许可证 GPL-3.0-or-later。

保留原 Makefile，移除 x86 MMX/SSE 参数，补 cstring 声明和 --version。使用 Boost 的 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 选项；boost/1.84.0、zlib/1.3.1 静态归档按完整路径链接。

上游无自动测试。新增8个集成用例与1个鸿蒙完整消费者，共9/9通过。完整消费者生成校准矩阵，再由新进程读取矩阵并比较完整共识输出。

实际验证环境：OHOS 7.0.0.32 Beta/API26/AArch64 QEMU，使用官方 OHOS6 profile 元数据。

**编译结束**：2026-10-14
**最终状态**：built
