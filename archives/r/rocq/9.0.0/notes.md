# Rocq 9.0.0 适配笔记

## 编译环境
- 构建系统: Dune (configure + dune build)
- 编译日期: 2026-07-02
- 编译器: clang
- 状态: success

## 编译步骤
1. 下载源码: rocq-9.0.0.tar.gz (从 GitHub releases 或本地 tarball)
2. 配置: sh ./configure -prefix <prefix> -no-ask -native-compiler no -bytecode-compiler yes
3. 构建: dune build --root . -j1 rocq-runtime.install coq-core.install coqide-server.install
   - 单线程构建 (-j1) 避免 OHOS 上的资源限制
4. 安装: 手动复制 _build/install/default/ 中的文件
   - dune install 在 OHOS 上有路径遍历问题

## 遇到的问题与解决方案
- Coq -> Rocq 重命名: 9.0.0 是改名后首个版本
- OHOS ELF 限制: 原生 rocqworker 被阻止，使用 bytecode 版本替代
- dune install 路径问题: 手动复制代替 dune install
- 源码下载: GitHub SSL 可能失败，使用本地 tarball 备选

## 依赖版本
- OCaml 4.14.1 (bytecode, 系统安装)
- Dune 3.17.0 (系统安装)
- Findlib 1.9.8 (系统安装)
- ZArith 1.14 (系统安装)
- Menhir 20260209 (系统安装)
- GMP 6.3.0 (系统安装)

## 验证结果
- rocq 二进制正常生成
- rocq --version 输出 9.0.0
- test_rocq.v 可以编译验证
- 测试套件: make check (上游自测, 500+ 单元测试)

## 注意事项
- Rocq 是 OCaml 生态中最大的包之一
- 所有依赖 (OCaml, Dune, Findlib, ZArith, Menhir) 必须先安装
- rocqworker 必须使用 bytecode 版本 (OHOS 安全要求)
