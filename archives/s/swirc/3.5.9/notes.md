# swirc 3.5.9 适配工作笔记

## 2026-10-06 构建记录

- W0 依赖检查: openssl/3.5.8.1、curl/8.22.0、ncurses/6.6、hunspell/1.7.3 均在 ohpcd registry；
  libidn/libintl/libnotify 不在 registry，configure 阶段以 --without-* 关闭（可选依赖）。
- 源码: swirc_3.5.9.orig.tar.gz (Debian mirror), sha256 校验通过。
- 构建: custom configure + make (autotools 类)。HarmonyOS 检测经 patches/0001-configure-harmonyos.patch
  注入 os_LINUX 路径；posixshell/os_LINUX.sh 经 patches/0002-os-linux-clang.patch 由 gcc/g++ 切换为 clang/clang++。
- conandata.yml 声明 2 个补丁，conanfile.py 经 export_conandata_patches + apply_conandata_patches 应用。
- conan create: 编译、链接、打包全部通过（二进制 ELF aarch64 musl, /lib/ld-musl-aarch64.so.1）。
- conan-verify: PASS（reports/conan-verify-report.md）。
- W3 本地 CI: setup.sh + build_and_test.sh 通过，L0/L1/L2/L4/L5 全部 pass，
  L1e R34 负向测试确认测试真实依赖产物（.ci-result.json exit_code=0）。
- 上游测试（2026-10-12 更新，真实执行）：上游 tests/ 目录含 35 个 cmocka 单元测试可执行
  （共 144 个测试用例），`make check` 依赖 cmocka（不在 ohpcd registry，故包配方不引入该依赖）。
  上游测试在独立工作区真实执行：cmocka/1.1.8 经 conancenter 交叉编译（仅用于测试执行，
  不进包配方 requires，不违反 R36），链接 swirc 已构建对象后运行全部 35 个测试：
  **35/35 测试可执行全部运行，144/144 测试用例全部通过（100%）**。
  上游测试修改说明：tests/write_to_stream.c 两处环境适配（硬编码 /tmp → 可写目录、
  file[25] → file[128]），因沙箱 /tmp 只读且原缓冲仅容纳 /tmp 路径；测试逻辑未改动。
  OHOS 环境适配：测试可执行需 binary-sign-tool 自签名后方可执行（鸿蒙代码签名校验）。
- test_package: 测试逻辑位于 test.sh（满足 CI L0c 测试源文件门禁，aa3d 已合并先例同款模式）：
  L1 smoke（--version，stdin 应答免责声明提问）+ OHOS rule12 消费者 e2e（--help 真实执行），
  conanfile.py 的 test() 经 bash + conanrun 环境调用 test.sh，两用例均以退出码判定（非断言式）。
---

**编译结束**: 2026-10-10 18:37
**最终状态**: built
