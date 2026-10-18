# unittest-mixins

为 Python unittest 提供临时目录、环境变量、导入路径、输出捕获和延迟断言辅助类。上游：[nedbat/unittest-mixins](https://github.com/nedbat/unittest-mixins)，许可证 Apache-2.0。

运行依赖 six/1.17.0；构建使用 setuptools/84.0.0，上游测试使用已发布的 pytest/9.1.1。Conan 载荷仅包含原版 Python 模块、生成的 egg-info 与许可证，不携带测试、字节码或主机二进制。

HarmonyOS 上保留上游 TempDirMixin 的原始行为，另以真实 HMDFS 挂载、非 root UID、chmod 后实际写入与清理验证平台机制。覆盖率测量工具 coverage 是本任务待补齐的父项，覆盖率测量尚未执行；31 项原版测试已独立运行，无源码、断言或守卫修改。

当前为本地适配，正式验证、PR、远端 CI、审核和发布状态分别记录于版本报告。
