# microsocks 1.0.5 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4 / OHOS aarch64
- 状态: built

## 编译步骤

1. `ohc-run.py init-build microsocks 1.0.5 --url=...` — 下载源码、创建骨架
2. 手动编译: `make -j2` — 编译成功，仅有 pragma 警告（不影响）
3. `ohc-run.py conan-init microsocks 1.0.5` — 生成 conanfile.py + conandata.yml + test_package/
4. 修改 conanfile.py: package_type=application, 直接生成config.mak, make -C指向source_folder
5. `ohc-run.py conan-verify microsocks 1.0.5` — G1-G4全通过
6. `ohc-run.py finish microsocks 1.0.5 built` — W3本地CI模拟通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create失败: configure不存在 | 旧patch用/dev/null格式创建configure，conan无法正确应用 | 移除patch，conanfile.py直接生成config.mak |
| 2 | conan create失败: tools.build:compiler_executables:c不存在 | conf是dict类型，不是单独的key | 用self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)获取 |
| 3 | conan create失败: No makefile found | basic_layout创建build-release子目录，Makefile在source目录 | 用make -C指向source_folder |
| 4 | test_package失败: assert MicroSocks not found | microsocks --help输出到stderr(dprintf(2,...)) | 用shell脚本包装，捕获stderr |
| 5 | W3 CI失败: L0c无测试源文件, L0d无self.run() | test_package缺少.sh源文件，test()用subprocess | 添加test_microsocks.sh，test()改用self.run() |

## 源码修改

无补丁。conanfile.py直接在build()中生成config.mak文件。

## 依赖版本

无外部依赖。仅需要系统 libc 和 libpthread。

## 功能测试结果

microsocks --help 输出正常，包含 MicroSocks SOCKS5 Server 帮助信息。

## 注意事项

- microsocks 没有 --version 选项，验证时使用 --help
- microsocks --help 退出码为1，输出到stderr
- 项目使用 config.mak 而非 configure 脚本进行配置
- 编译有 pragma 警告（#pragma RcB2），不影响功能
- conan basic_layout 会创建 build-release 子目录，需用 make -C 指向 source_folder

---

**编译结束**: 2026-07-15
**最终状态**: built
