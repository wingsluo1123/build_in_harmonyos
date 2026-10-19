# xdu 3.0 功能测试报告

**日期**: 2026-10-17
**平台**: HarmonyOS (OHOS, arm64)
**构建方式**: Conan 2.29.1 (OHOS 适配版) + 手工直编（Imakefile 项目，按 README 官方 cc 命令）
**Profile**: ohos-aarch64 (os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15)
**依赖**: libxaw/1.0.14 + libxt/1.3.1 + libxmu/1.3.1.1 + libxpm/3.5.17 + libxext/6.4.0.1 + libx11/1.8.13（制品仓已发布）；libxcb/1.17.0 + libxau/1.0.11（运行期 DT_NEEDED）
**补丁**: 无（纯编译期选项适配，未修改上游源码）

## 测试摘要

| # | 测试 | 描述 | 结果 |
|---|------|------|------|
| 1 | xdu 二进制存在且可执行 | 验证打包产物 bin/xdu 安装且可执行 | ✅ PASS |
| 2 | xdu -help（无 DISPLAY） | XtAppInitialize 报 "Can't open display" 干净退出（rc=1），证明 libXaw7/libXt/libXext/libX11 动态链接链完整 | ✅ PASS |
| 3 | xdu 无参数（stdin 非 tty） | 同样在 XtAppInitialize 干净退出，库加载正常 | ✅ PASS |

**通过**: 3/3 | **失败**: 0/3 | **跳过**: 0

**上游测试**: xdu 3.0 无自动化测试套件（Imakefile 仅有 ComplexProgramTarget/InstallAppDefaults 目标，无 check/TESTS；源码树无 tests/ 目录；xdu.man 无测试章节），上游用例 0/0，无需运行。

---

## 测试环境

- **Conan 版本**: 2.29.1 (OHOS 适配版)
- **Profile**: ci/conan/profiles/ohos-aarch64
- **编译器**: /data/service/hnp/bin/clang (clang 15.0.4)
- **签名**: llvm-objcopy + binary-sign-tool（ELF 自签，OHOS 内核拒绝未签名 ELF）

## 测试结论

✅ **总体评价**: 通过。二进制安装正确、动态链接链完整（无 DISPLAY 环境 XtAppInitialize 干净退出，缺库时 loader 会报 "Error loading shared library" + exit 127，可区分）。

**已知限制（R40）**: xdu 属图形/渲染类（X11 Athena 工具）。headless 环境测试仅验证动态链接链完整，窗口渲染功能未经真机验证，需人工确认适配完整性（真机环境可补 Xvfb 渲染冒烟）。

---

*测试命令: test_package/test_xdu.sh（conan create 自动执行，3/3 PASS，详见 reports/conan-create.txt）*
