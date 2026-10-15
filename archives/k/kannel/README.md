# Kannel

Kannel 1.4.5 的 HarmonyOS PC 原生 Conan 配方。上游只构建静态 C 支持库及网关程序，不声明不存在的共享模式。

安装四个支持库、公共头，以及 bearerbox、smsbox、wapbox、wmlsc、wmlsdasm、gw-config。下游优先使用 `kannel::kannel`。使用 gw-config 的编译/链接参数时须激活 Conan build 环境，依赖根由当前 Conan 图提供，不引用原构建机器的目录。

上游 14 组完整注册检查在配方中执行；测试专用证书每次由已发布 OpenSSL 生成，不降低生产 TLS 安全要求。强制线程取消在 OHOS 上诚实返回 ENOTSUP，调用方须采用协作停止和 wake/join。未验证外部实际电信网络或运营商设备互操作。
