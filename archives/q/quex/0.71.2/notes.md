# quex 0.71.2 适配笔记

## 编译环境
- 构建系统: custom（纯 Python 工具，无 configure/CMake 编译步骤）
- 适配日期: 2026-10-16
- 编译器: clang/clang++（仅 test_package 生成校验用，不编译 quex 自身）
- 平台: HarmonyOS aarch64（真机预检待回填）
- 状态: built（配方完成，待真机 rule4 门禁）

## 上游信息
- 上游仓库: https://quex.sourceforge.net/
- 源码包: https://downloads.sourceforge.net/project/quex/quex-0.71.2.zip
- SHA256: 0453227304a37497e247e11b41a1a8eb04bcd0af06a3f9d627d706b175a8a965（与 Homebrew 公式一致）
- 许可证: MIT
- 内容结构: quex-exe.py（入口）、quex/（Python 包，含 code_base 运行时模板）、demo/C 与 demo/Cpp（示例，430 文件）、manpage/quex.1、unit_test_results.txt（0.71.2 zip 内 0 字节空日志，非可运行套件）

## 适配步骤

1. `get()` 解包 quex-0.71.2.zip。
2. `build()` 运行 `python3 quex-exe.py --help` 烟囱测试，并 walk 源码树确认无 test*.py/_test.py 可运行套件，输出 `HMBS_UPSTREAM_TEST_RESULT`（no_tests）。
3. `package()` 将 `quex-exe.py` 与 `quex/`（含 `quex/code_base` 运行时模板）复制到 `share/quex`，将 COPYRIGHT/MIT-License 放入 `licenses`，生成 `bin/quex` 包装脚本（设置 QUEX_PATH 后 exec python3）。
4. `test_package` 运行 `quex --help`、`quex --version`，并用自带 `tiny.qx`（官方文档 tiny 示例）生成 C 词法分析器，校验输出非空且包含 NUMBER/IDENTIFIER。

## 上游测试审计结论

- 顶层无 tests/ 或 test/ 目录，无 make check/ctest/pytest 入口；`unit_test_results.txt` 在 0.71.2 zip 内为 0 字节空文件（build 时 getsize 取证），不可运行。
- `quex/engine/analyzer/examine/TEST-later/` 有 11 个 test-*.py，但目录后缀 `-later` 即上游禁用的 hwut 套件（hwut 只扫描 TEST 目录），且 hwut 运行器本身不在发布包内，需形状参数 + GOOD/ 比对，无法当 pytest/ctest/make check 运行（build 时 walk 逐个列出取证）。
- `quex/engine/state_machine/algebra/TESTS/` 仅剩 helper/essay 片段，无可运行驱动；`quex/code_base/TESTS/` 为生成器脚本 + test_c 固件，非测试驱动。
- `demo/` 各示例仅构建预生成的 lexer.c/lexer.cpp，无 TESTS/ctest/pytest 注册。
- Homebrew 测试仅做单次 demo 生成烟囱测试，不视为上游套件。
- 因此 `upstream_tests_exist: false`，`upstream_test_total: 0`，功能覆盖由 test_package 的 4 项生成校验承担。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 检出上游 main 失败（gama 补丁文件名含回车） | 上游树中存在以回车结尾的文件名，Windows 无法建文件 | 保持 `core.protectNTFS=false` 本地配置，用 `git archive` 解包并跳过坏文件；不提交该文件变更 |
| 2 | quex 无编译步骤，传统 autotools/CMake 模板不适用 | 上游为纯 Python 生成器 | 采用 custom 安装配方：复制 Python 包 + 包装脚本，参考 Homebrew 安装方式 |
| 3 | 生成器需要 QUEX_PATH | quex-exe.py 依赖该变量定位 quex 模块与模板 | bin/quex 包装脚本自动设置并导出，用户无感 |
| 5 | CI #96102 test_package 0/4: FileNotFoundError quex | nested python driver used bare quex lookup, conanrun PATH did not reach grandchild subprocess | conanfile resolves bin/quex + share/quex absolutely from package_folder and passes as argv, driver adds python+quex-exe.py fallback, no PATH dependence |
| 4 | 真机 test_package 第 3 项失败：`Missing identifier in analyzer class name specification`（2/4） | `-o` 接的是裸分析器标识符，不接受绝对路径；旧命令把 `/tmp/.../tiny_lexer` 直接传给 `-o` 触发参数校验失败 | test_package 改为 `cd TMP && quex -i tiny.qx -o tiny_lexer --language C`（与官方 `quex -i tiny.qx -o tiny --language C` 同形）；tiny.qx 同步修正 `<<EOF>>` 与官方一致 |

## 依赖版本

- 无第三方运行时依赖；仅需系统 python3（真机由 HMBS_PYTHON3 提供）。

## 验证结果

- 本地：未在本机运行 conan（按任务守则，验证转真机）。
- 真机预检：待 HMBS 后台执行后回填（`quex --help`、`--version`、tiny.qx 生成三段输出与两个 JSON 标记）。
- 上游测试通过率：上游无可运行套件（0/0，no_tests）。
- 新增测试通过率：待真机回填（目标 4/4）。

## 注意事项

- `bin/quex` 依赖 `python3` 在 PATH 中；OHOS 真机与 CI 均提供。
- 生成的 C 词法分析器编译需加 `-I<package>/share/quex/code_base`（用法见 demo/README）。
- 本配方未修改上游源码，无 patches/。
