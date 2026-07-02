# Menhir 20260209 适配笔记

## 编译环境
- 构建系统: Dune (多阶段自举构建)
- 编译日期: 2026-07-02
- 编译器: clang
- 状态: success

## 编译步骤
1. 下载源码: menhir-20260209.tar.gz
2. 构建: dune build --profile release --root . @install -j1
   - 仅构建 install 目标 (排除 demos, benchmarks)
   - 使用 -j1 确保 bootstrap 安全 (stage1 -> stage2 依赖)
3. 安装: dune install --prefix=<prefix> --root .

## 遇到的问题与解决方案
- Bootstrap 安全性: 使用 -j1 避免多阶段构建中的竞态条件
- 构建目标: 仅构建 @install 目标，排除不必要的 demos 和 benchmarks

## 依赖版本
- OCaml 4.14.1 (系统安装)
- Dune 3.17.0 (系统安装)

## 验证结果
- menhir 二进制正常生成
- menhir --version 输出正确版本
- 测试套件: dune runtest (上游自测)

## 注意事项
- Menhir 是 Rocq 的依赖项 (解析器生成)
- Menhir 必须在 Rocq 之前安装
