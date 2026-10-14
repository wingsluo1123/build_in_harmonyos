# 1.0.4 适配记录

源码和算法未修改。Meson 没有注册测试，但发布源码的 TEST_BASE64 主函数有七个
字符串向量及一个四零字节向量，必须完整执行。发布包未附其 readfile.h；随配方
提供真正的文件/标准输入读取助手，不改主函数或结果比较，不返回假数据。

真实失败顺序：任务私有 Conan 下载触发 SemLock ENOSPC；Meson 无法通过裸名
启动归档工具；临时 VirtualBuildEnv 构造关闭自动环境生成；Ninja 1.13.2 固定的
HNP bash 路径在此真机缺失；安装共享对象/别名需要重新签名；CMake 未提供
HarmonyOS 消费者的运行时链接规则。分别修复，不删除测试或改变平台全局配置。

下载串行设置只在本轮真机的任务私有 Conan home 生效；不将宿主故障写成源码
问题。Ninja 使用已发布 1.12.1，依赖 curl 与已发布 libnpupnp 的版本保持一致。
Meson ar/pkg-config/Ninja 均解析为真实绝对工具，临时 VirtualBuildEnv 显式
auto_generate=True。消费者的原生 RPATH 只存在于 test_package，不写入交付库。

安装后先验证全部别名指向同一原始库，再变为真实、保留模式的文件；每个安装
副本使用当前 SDK 去掉旧签名并重新签名，最后原子替换，仅处理当前包的文件。
不改共享 Conan 缓存中的其他包，不改 /lib、/system 或用户 SSH 服务。

最终 r13 W3_PASS。构建与原始测试、安装后 API 消费者均通过；完整官方 finish
及比赛 CI 状态以各自独立证据为准，不用真机结果冒充发布结果。
