# nanopb

nanopb 是面向嵌入式和资源受限环境的 Protocol Buffers C 实现，提供低开销的编码、解码运行时。

## 适配内容

- 上游版本：0.4.9.1
- 构建系统：CMake
- 产物：静态库 `protobuf-nanopb` 和 `nanopb/` 头文件
- 依赖：无 Conan 运行时依赖
- 上游官方测试：`tests/` 下的 SCons 测试套件

## Conan 使用

```bash
conan install --requires=nanopb/0.4.9.1 --build=missing
```

消费方可链接 `nanopb::protobuf-nanopb-static`，或使用 Conan 生成的 `cpp_info.libs` 中的 `protobuf-nanopb`。

## 上游信息

- 项目主页：https://jpa.kapsi.fi/nanopb/
- 源码仓库：https://github.com/nanopb/nanopb
