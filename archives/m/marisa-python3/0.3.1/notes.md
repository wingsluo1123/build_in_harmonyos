# 0.3.1 HarmonyOS PC 适配

- MARISA、Python 和 SWIG 使用已发布 Conan 制品，不源码构建前置依赖。
- 原始 Python 3 绑定沿用旧分配错误宏参数；核心 0.3.1 的宏改为异常类型参数。
  保留五处空指针防护，改为真实 `std::bad_alloc`，并在 SWIG 接口中先映射到
  Python MemoryError，再处理通用异常。修改源接口后重新生成包装器，不手改生成文件。
- CMake 构建扩展并保留五个原始 C++ 测试源，链接已发布 MARISA。
  完整执行官方 Python 3 示例；消费者核对两层模块来源以排除系统同名模块。
- 安装后仅对本包 `_marisa.so` 去除旧签名并重新签名，不修改依赖包。
- 使用包前缀化 Python 解释器与 HOME 变量，不全局设置 PYTHONHOME 干扰 Conan。
- 真机验证已通过，不能据此标记比赛 CI 或制品发布完成。libkkc 须等本包正式发布。
