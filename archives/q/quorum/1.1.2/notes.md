# 1.1.2 原生适配笔记

保留四个原始生产工具、Perl 前端、adapter FASTA、query/histo 辅助工具。
上游一项 TEST_P 实例化 Values(1,10,20,40)，原始分母为 4；每个实例仍使用原始 100000 序列/10 线程语义。只把旧 GoogleTest 宏改成现代同义宏，没有减少断言或参数。

GNU 私有 `ext/stdio_filebuf` gzip 输出替换为真实 zlib 写入流，覆盖 xsputn、overflow、sync 和关闭，不使用 stub。
已发布 Jellyfish 被标为 application，默认 Conan traits 没有转发头文件/库。下游明确请求 headers=True、libs=True，指向包中真实安装内容；不改写或重编依赖。移除对上游旧捆绑 GTest include 根的遮蔽，使用已发布 GTest。
Perl 的默认选项大小写折叠会混淆文档中的 `-p`（prefix）与 `-P`（paired files）；使用 no_ignore_case 保留两种功能。消费者调用包图中 Perl 的准确路径，而不是环境中 bare perl。

失败 r1–r5 的日志保留，未拼接为通过。r6 原生 Conan create RC0，上游 4/4、消费者 8/8；12 阶段完整并 release/postrelease PASS。
新增知识 E9945 与已有 E221 的增量边界：不可变、已发布混合工具/库依赖的下游显式 traits，不是建议错误标记新上游包，也不修复 ABI 缺失。

正式 finish、知识查重、HD1–4 重判及 PRE_CREATE/POST_CREATE 尚未完成；当前没有 Issue/PR/worker CI 或 release。
