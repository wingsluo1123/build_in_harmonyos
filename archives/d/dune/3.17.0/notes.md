# Dune 3.17.0 适配笔记

## 编译环境
- 构建系统: Dune 自举 (ocaml boot/bootstrap.ml -> make release)
- 编译日期: 2026-07-02
- 编译器: clang / clang++
- 状态: success

## 编译步骤
1. 下载源码: dune-3.17.0.tar.gz
2. 应用补丁:
   - boot/duneboot.ml: 优先使用 bytecode 而非 .opt 原生二进制 (OHOS 安全)
   - dune-project: 添加 (version 3.17.0) 用于正确版本报告
   - src/dune_rules/which.ml: 不优先 .opt 变体
   - vendor/spawn/src/spawn_stubs.c: 守护 pthread_setcancelstate
3. 自举: ocaml boot/bootstrap.ml -> 生成 _boot/dune.exe
4. 发布构建: make release -> 生成 @install 目标

## 遇到的问题与解决方案
- OHOS 安全限制: 原生 ELF 二进制被阻止执行，改用 bytecode 自举
- pthread_setcancelstate: OHOS 未实现此函数，添加条件编译守护
- 版本报告: dune-project 缺少 (version 3.17.0) 声明，手动添加

## 依赖版本
- OCaml 4.14.1 (bytecode, 系统安装)
- 无其他 Conan 管理依赖

## 验证结果
- dune 二进制正常生成，可执行
- dune --version 输出 3.17.0
- 测试套件: dune runtest (上游自测)

## 注意事项
- Dune 是 OCaml 生态核心构建工具，Rocq/Menhir 等包依赖此包
- 下次升级需检查 bootstrap 脚本是否有变化
