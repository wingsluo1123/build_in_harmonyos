# Gleam

## 描述
Gleam是一个静态类型的函数式编程语言，运行在Erlang虚拟机（BEAM）上。

## 特性
- **静态类型**：强大的类型系统，编译时类型检查
- **函数式编程**：支持函数式编程范式
- **BEAM生态系统**：与Erlang/Elixir生态兼容
- **多平台编译**：可编译到Erlang和JavaScript
- **内置工具链**：包含编译器、构建工具、格式化器和包管理器

## 版本信息
当前版本：1.17.0-r0

## 部署方式
从源码编译 (Rust/Cargo)，生成动态链接 musl 二进制

## 运行时依赖
- musl libc (系统自带 /lib/ld-musl-aarch64.so.1)
- Erlang/OTP（用于编译后的Gleam程序运行，编译器本身不需要）

## 官方网站
https://gleam.run/

## 许可证
Apache-2.0