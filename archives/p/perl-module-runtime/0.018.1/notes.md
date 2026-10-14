# Module::Runtime 0.018 / adaptation repair 0.018.1

当前主线 `0.018` 只保留元数据，没有 conanfile.py/conandata.yml；远端精确
`perl-module-runtime/0.018` 禁构建回退解析失败。这里恢复真正可执行配方，
不是重新提交同版本或声称上游发布了 0.018.1。

采用官方 0.018 源，声明真正已发布的 Perl 5.42.2。MakeMaker 的解释器核心
目录、架构目录与模块安装根分别绑定；原11程序/365断言全部执行，不减
原分母，不关闭 taint 或导入错误测试，不造共享目录或依赖结果。

独立原生 r1223 已11/11、365/365、零skip/TODO/失败；正式Conan、实际
消费者与鸿蒙专项、配对知识草稿、Pre-PR、Issue任务身份、Review、平台
CI与提审尚须分别通过。状态保留candidate，不能迁移原生结果为平台通过。
