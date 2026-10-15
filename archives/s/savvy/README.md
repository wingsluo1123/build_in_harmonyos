# savvy

## 简介
SAV 变体文件格式的官方 C++ 接口库，无缝支持 BCF/VCF 文件。库主体 `savvy`
为 header-only（include/savvy/*.hpp），附带 `sav` 命令行工具（import/export/
head/index/sort/stat 等子命令，用于 SAV 与 VCF/BCF 互转）。

## OHOS 适配
- header-only INTERFACE 库 + `sav` CLI：包为 header-library（不能用
  application——Conan 2 的 CMakeDeps 对 application 会丢弃 cpp_info.includedirs，
  消费者 `<savvy/xxx.hpp>` file not found），consumers 经 `savvy::savvy`
  头文件接口使用，CLI 走 bin/sav（bindirs + software-level commands.json）
- 压缩依赖经 libshrinkwrap 提供（其 requires xz/zlib/zstd）
- 上游 `find_package(shrinkwrap)`/裸目标名适配为 `shrinkwrap::shrinkwrap`
- 上游测试用 assert()，CI Release(NDEBUG) 下给 savvy-test 加 `-UNDEBUG`
  使断言真实生效（生产 sav 不受影响）
- 无独立补丁文件，四个 portability 改动由 build() 内 replace_in_file 落地

## 依赖
- libshrinkwrap（内传递 xz / zlib / zstd）

## 功能验证
```c++
savvy::reader input("sample.sav");   // 读取 SAV/BCF/VCF
savvy::variant var;
while (input.read(var)) { /* ... */ }
```
`conan create` 时自动编译并运行上游 5 个 ctest 用例（convert-file / subset /
random-access / stride-reduce / missing-headers）与消费者测试（varint 往返 +
`sav --version` 冒烟）。

## 版本
- 2.1.0: built (2026-10-13)，待真机预检

## 参考
- 上游: https://github.com/statgen/savvy
- 许可证: MPL-2.0
